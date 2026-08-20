"""Rekonstrukcja kanonicznych akcji agresywnych z MBO.

Specyfikacja nadrzedna: PLAN.pdf rozdz. 4.1 (zrodla i schematy danych), 4.2
(pipeline raw -> clean), 4.6 (kontrola jakosci). Karta H015 z rozdz. 9
zastrzegala, ze lead-lag i mikrostruktura sa **niebadalne na barach M1
i wymagaja `trades`/MBP** — ten modul jest pierwszym krokiem, ktory to
ograniczenie zdejmuje.

Specyfikacja szczegolowa: `docs/D5_ETAP4_SPEC.md` §1 — definicja ZAMROZONA przed zakupem
miesiecznej probki. Ten modul jest jej wierna implementacja i nie wolno zmieniac
regul po zobaczeniu wyniku.

CZTERY REGULY, KAZDA WYNIKAJACA Z POMIARU, NIE Z WYGODY:

1. Rekord `Trade` rozpoczyna transakcje; nastepujace po nim `Fill` naleza do
   niej. Strona i agresor pochodza z BIEZACEGO rekordu `Trade`.

2. Kolejne rekordy `Trade` o tym samym `order_id` i stronie lacza sie w jedna
   akcje WYLACZNIE jako bezposredni ciag w tej samej kopercie `F_LAST`.

3. Ponowne pojawienie sie tego samego `order_id` PO INNYM AGRESORZE to nowa
   akcja. Nie scalamy przez przerwe.

4. `Fill` o `order_id` rownym agresorowi biezacej akcji jest wypelnieniem
   agresora, nie strona pasywna.

DLACZEGO NIE PROSCIEJ. Audyt D5-C wykluczyl dwie prostsze jednostki:
koperta `F_LAST` zawiera >= 2 agresorow w 2,4% przypadkow, wiec nie ma
jednoznacznego znaku; globalny `order_id` zmienia role z agresywnej na pasywna
nawet wewnatrz jednej koperty.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

#: Flaga DBN oznaczajaca ostatni rekord zdarzenia dla instrumentu.
F_LAST = 128


@dataclass(frozen=True)
class RekordMBO:
    """Minimalny rekord MBO — tylko pola potrzebne do rekonstrukcji.

    Osobny typ zamiast rekordu `databento`, zeby testy mogly budowac przypadki
    recznie, bez pliku danych.
    """

    ts_recv: int
    action: str          # "T" | "F" | "A" | "C" | "M" | "R"
    side: str            # "B" | "A" | "N"
    price: int
    size: int
    order_id: int
    flags: int = 0


@dataclass
class AkcjaAgresywna:
    """Kanoniczna jednostka obserwacji D5-B2."""

    order_id: int
    side: str
    koperta: int
    n_trade: int = 0
    rozmiar: int = 0
    n_pasywnych: int = 0
    rozmiar_pasywnych: int = 0
    n_wlasnych: int = 0
    ts_recv_pierwszy: int = 0
    ts_recv_ostatni: int = 0
    _ceny: set[int] = field(default_factory=set, repr=False)

    @property
    def poziomy(self) -> int:
        """Liczba roznych poziomow ceny zdjetych przez te akcje."""
        return len(self._ceny)

    @property
    def minuta(self) -> int:
        """Okno 60 s, do ktorego nalezy akcja.

        Wyznaczane przez `ts_recv` OSTATNIEGO rekordu akcji (§1.5 i §2.1
        specyfikacji). Akcja nigdy nie jest dzielona miedzy okna.
        """
        return self.ts_recv_ostatni // 60_000_000_000


def rekonstruuj(rekordy: Iterable[RekordMBO]) -> Iterator[AkcjaAgresywna]:
    """Strumieniowa rekonstrukcja akcji agresywnych.

    Generator — nie materializuje wyniku, wiec nadaje sie do sesji o dziesiatkach
    milionow rekordow.
    """
    koperta = 0
    biezaca: AkcjaAgresywna | None = None
    ostatni_klucz: tuple[int, str] | None = None

    for r in rekordy:
        if r.action == "T":
            klucz = (r.order_id, r.side)
            # REGULA 2 i 3: laczymy tylko z BEZPOSREDNIO poprzedzajacym
            # rekordem Trade o tym samym kluczu. Inny agresor pomiedzy —
            # nawet gdy ten sam `order_id` wraca — otwiera nowa akcje.
            if biezaca is not None and klucz == ostatni_klucz:
                biezaca.n_trade += 1
                biezaca.rozmiar += r.size
                biezaca._ceny.add(r.price)
                biezaca.ts_recv_ostatni = max(biezaca.ts_recv_ostatni, r.ts_recv)
            else:
                if biezaca is not None:
                    yield biezaca
                biezaca = AkcjaAgresywna(
                    order_id=r.order_id, side=r.side, koperta=koperta,
                    n_trade=1, rozmiar=r.size,
                    ts_recv_pierwszy=r.ts_recv, ts_recv_ostatni=r.ts_recv,
                )
                biezaca._ceny.add(r.price)
            ostatni_klucz = klucz

        elif r.action == "F" and biezaca is not None:
            # REGULA 4: `Fill` o identyfikatorze agresora nie jest pasywny.
            if r.order_id == biezaca.order_id:
                biezaca.n_wlasnych += 1
            else:
                biezaca.n_pasywnych += 1
                biezaca.rozmiar_pasywnych += r.size
            biezaca.ts_recv_ostatni = max(biezaca.ts_recv_ostatni, r.ts_recv)

        if r.flags & F_LAST:
            # REGULA 2: akcja nigdy nie przekracza granicy koperty.
            if biezaca is not None:
                yield biezaca
                biezaca = None
            ostatni_klucz = None
            koperta += 1

    if biezaca is not None:      # ogon bez F_LAST
        yield biezaca


def z_dbn(store, *, tylko_rth: tuple[int, int] | None = None
          ) -> Iterator[RekordMBO]:
    """Adapter: rekordy `databento` -> `RekordMBO`.

    `tylko_rth` to opcjonalna para granic `ts_recv` w nanosekundach.
    """
    for r in store:
        ts = int(r.ts_recv)
        if tylko_rth and not (tylko_rth[0] <= ts < tylko_rth[1]):
            continue
        akcja = r.action if isinstance(r.action, str) else r.action.value
        strona = r.side if isinstance(r.side, str) else r.side.value
        yield RekordMBO(ts_recv=ts, action=akcja, side=strona,
                        price=int(r.price), size=int(r.size),
                        order_id=int(r.order_id), flags=int(r.flags))
