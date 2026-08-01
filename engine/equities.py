"""Akcje: sklejanie tickerow i korekta splitow — PLAN.pdf rozdz. 4.7 (warstwa K6).

Odpowiednik `engine/roll.py` dla instrumentow kasowych. Dwa problemy, ktorych
kontrakty terminowe nie maja, a akcje maja oba:

  (a) TICKER ZMIENIA SIE W CZASIE. Meta handlowala sie jako FB do 2022-06-09.
      Zapytanie o "META" za rok 2019 zwraca pusty wynik — po cichu gubi spolke,
      nie rzucajac bledu.

  (b) SPLITY. Databento podaje ceny JAK HANDLOWANE. Na dzien splitu 20:1 surowa
      cena spada o 95% i wyglada jak krach. W sumie wazonej skladnikow indeksu
      taki "krach" przenosi sie wprost na sygnal.

ROZNICA WOBEC KONTRAKTOW: korekta jest MULTIPLIKATYWNA, nie roznicowa. Przy
rolowaniu futures przesuwamy historie o staly SPREAD, bo znaczenie ma roznica
cen. Przy splicie dzielimy historie przez WSPOLCZYNNIK, bo znaczenie ma stosunek
— split nie zmienia wartosci pozycji, zmienia liczbe akcji.

DLACZEGO NIE WYKRYWAMY SPLITOW SAMA WIELKOSCIA RUCHU. Meta spadla 3 lutego 2022
o 26% w jedna sesje. To nie byl split — to byla reakcja na wyniki. Prog oparty
na samej wielkosci zmiany "poprawilby" ten krach, kasujac prawdziwe zdarzenie
rynkowe, ktore dla karty H013 jest wrecz najciekawszym punktem danych.

Stad DWA NIEZALEZNE WARUNKI, ktore musza zajsc jednoczesnie:

  1. wspolczynnik ceny blisko prostego ulamka (2, 3, 4, 5, 10, 20, 3/2, 4/3...),
  2. wolumen skaluje sie tym samym wspolczynnikiem — bo po splicie k:1 handluje
     sie okolo k razy wiecej akcji o k razy nizszej cenie.

Warunek 2 jest kluczowy: krach cenowy NIE zmienia liczby akcji w obrocie
w sposob proporcjonalny do spadku, a split zmienia — z definicji. Zadne
zdarzenie fundamentalne nie podrabia obu warunkow naraz.

Kazdy kandydat trafia do raportu razem z dowodami, takze odrzucony. Korekta ma
byc audytowalna, nie automatyczna.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np

#: Ticker -> (poprzednik, data zmiany). Szereg sklejamy w jeden pod nowa nazwa.
POPRZEDNIE_TICKERY: dict[str, tuple[str, date]] = {
    "META": ("FB", date(2022, 6, 9)),
}

#: Wspolczynniki splitow dopuszczane przez detektor. Lista jest krotka
#: i zaczyna sie od 1.5 CELOWO.
#:
#: Kusi, zeby dopisac 5/4, 4/3, 7/5 — takie splity istnieja. Ale odpowiadaja
#: spadkom ceny o 20-30%, czyli dokladnie temu, co robi megacap po zlych
#: wynikach. Meta stracila 26% dnia 03.02.2022, Netflix 35% w kwietniu tego
#: samego roku. Dopuszczenie tych ulamkow oznacza, ze detektor "poprawi"
#: prawdziwe reakcje na wyniki — a te sa dla karty H013 nie szumem, tylko
#: CALYM PRZEDMIOTEM BADANIA.
#:
#: Asymetria ryzyka jest jednoznaczna. Przeoczony split 5:4 to jeden bledny
#: zwrot dla jednej spolki, widoczny w raporcie jakosci. Skasowany krach po
#: wynikach to wyciecie najbardziej informacyjnego zdarzenia w calym zbiorze,
#: i to w sposob niewidoczny. Wybieramy pierwsze ryzyko.
#:
#: Megacapy w naszym zakresie dzielily sie 2:1, 3:1, 4:1, 5:1, 10:1 i 20:1 —
#: wszystkie powyzej progu.
DOPUSZCZALNE_WSPOLCZYNNIKI: tuple[float, ...] = (
    1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 15.0, 20.0, 30.0,
)

PROG_KANDYDATA = 0.22        # |log(ratio)| — okolo 20% zmiany ceny

#: Tolerancja dopasowania wspolczynnika. Wbrew pierwszemu odruchowi NIE nalezy
#: jej zaciskac: split daje stosunek precyzyjny, ale w dniu splitu cena porusza
#: sie takze normalnie. Split 20:1 przy ruchu +2% daje stosunek 19.6, nie 20.0.
#: Tolerancja 1.5% gubila takie przypadki — sprawdzone testem.
#:
#: Bezpieczenstwo zapewnia nie ciasna tolerancja, tylko RZADKA LISTA
#: wspolczynnikow. Po usunieciu ulamkow ponizej 1.5 najblizsza para to 1.5 i 2.0,
#: odlegle o 33% — przy takim rozstepie 3% tolerancji nie moze pomylic sasiadow,
#: a krach o 26% (stosunek 1.35) lezy 10% od najblizszego dopuszczalnego i jest
#: odrzucany juz na cenie, bez siegania po wolumen.
TOLERANCJA_CENY = 0.03
MIN_STOSUNEK_WOLUMENU = 1.4  # wolumen musi wzrosnac co najmniej tyle razy
OKNO_WOLUMENU = 5            # dni po kazdej stronie do usrednienia obrotu


@dataclass(frozen=True)
class KandydatSplitu:
    """Podejrzany skok ceny wraz z dowodami za i przeciw."""

    symbol: str
    dzien: date
    stosunek_ceny: float          # close(d-1) / close(d) — dla splitu k:1 wynosi ~k
    wspolczynnik: float | None    # dopasowany prosty ulamek albo None
    stosunek_wolumenu: float      # wolumen po / wolumen przed
    przyjety: bool
    powod: str

    def __repr__(self) -> str:
        w = "PRZYJETY" if self.przyjety else "ODRZUCONY"
        return (f"{self.symbol} {self.dzien}: cena x{self.stosunek_ceny:.3f}, "
                f"wolumen x{self.stosunek_wolumenu:.2f} -> {w} ({self.powod})")


@dataclass
class RaportSplitow:
    kandydaci: list[KandydatSplitu] = field(default_factory=list)

    @property
    def przyjete(self) -> list[KandydatSplitu]:
        return [k for k in self.kandydaci if k.przyjety]

    @property
    def odrzucone(self) -> list[KandydatSplitu]:
        return [k for k in self.kandydaci if not k.przyjety]

    def summary(self) -> str:
        return (f"kandydatow {len(self.kandydaci)}, "
                f"przyjetych jako splity {len(self.przyjete)}, "
                f"odrzuconych jako ruch rynku {len(self.odrzucone)}")


def dopasuj_wspolczynnik(stosunek: float) -> float | None:
    """Najblizszy prosty wspolczynnik splitu albo None, gdy zaden nie pasuje.

    Sprawdzamy takze odwrotnosci — split odwrotny (reverse split) podnosi cene
    zamiast ja obnizac i wystepuje u spolek po duzych spadkach.
    """
    najlepszy, najlepszy_blad = None, float("inf")
    for w in DOPUSZCZALNE_WSPOLCZYNNIKI:
        for kandydat in (w, 1.0 / w):
            blad = abs(stosunek - kandydat) / kandydat
            if blad < najlepszy_blad:
                najlepszy, najlepszy_blad = kandydat, blad
    return najlepszy if najlepszy_blad <= TOLERANCJA_CENY else None


def wykryj_splity(
    dni: list[date],
    close: np.ndarray,
    volume: np.ndarray,
    symbol: str = "",
) -> RaportSplitow:
    """Kandydaci na split w dziennym szeregu jednej spolki.

    Wejscie musi byc posortowane rosnaco po dacie i pozbawione luk wewnatrz dnia
    (jeden wiersz = jeden dzien sesyjny).
    """
    rep = RaportSplitow()
    n = len(dni)
    if n < 2 * OKNO_WOLUMENU + 2:
        return rep

    close = np.asarray(close, dtype=float)
    volume = np.asarray(volume, dtype=float)

    for i in range(1, n):
        if close[i] <= 0 or close[i - 1] <= 0:
            continue
        stosunek = close[i - 1] / close[i]
        if abs(np.log(stosunek)) < PROG_KANDYDATA:
            continue

        w = dopasuj_wspolczynnik(stosunek)

        # Wolumen: srednia z okna przed i po. Przy splicie k:1 liczba akcji
        # w obrocie rosnie okolo k-krotnie — czego krach cenowy nie robi.
        a = max(0, i - OKNO_WOLUMENU)
        b = min(n, i + OKNO_WOLUMENU)
        przed = float(np.mean(volume[a:i])) if i > a else 0.0
        po = float(np.mean(volume[i:b])) if b > i else 0.0
        stos_wol = (po / przed) if przed > 0 else 0.0

        if w is None:
            powod = f"wspolczynnik {stosunek:.3f} nie odpowiada zadnemu splitowi"
            przyjety = False
        elif stos_wol < MIN_STOSUNEK_WOLUMENU and stosunek > 1.0:
            powod = (f"cena pasuje do {w:.3f}, ale wolumen wzrosl tylko "
                     f"x{stos_wol:.2f} — to ruch rynku, nie split")
            przyjety = False
        else:
            powod = f"cena i wolumen zgodne ze splitem {w:.3f}"
            przyjety = True

        rep.kandydaci.append(KandydatSplitu(
            symbol=symbol, dzien=dni[i], stosunek_ceny=stosunek,
            wspolczynnik=w, stosunek_wolumenu=stos_wol,
            przyjety=przyjety, powod=powod,
        ))
    return rep


def wspolczynniki_korekty(dni: list[date], rep: RaportSplitow) -> np.ndarray:
    """Mnoznik korekty ceny dla kazdego dnia — historia sprzed splitu w dol.

    Analogia do `roll.cumulative_offsets`, ale multiplikatywna: najnowszy okres
    ma mnoznik 1.0, a kazdy wczesniejszy jest dzielony przez iloczyn wszystkich
    pozniejszych splitow.

        px_skorygowana = px_surowa / mnoznik
    """
    mnozniki = np.ones(len(dni), dtype=float)
    for k in rep.przyjete:
        if k.wspolczynnik is None:
            continue
        maska = np.array([d < k.dzien for d in dni])
        mnozniki[maska] *= k.wspolczynnik
    return mnozniki


def skoryguj_ceny(
    dni: list[date],
    close: np.ndarray,
    volume: np.ndarray,
    symbol: str = "",
) -> tuple[np.ndarray, np.ndarray, RaportSplitow]:
    """Ceny i wolumen skorygowane o splity. Zwraca takze raport do przejrzenia.

    Wolumen korygujemy w DRUGA STRONE niz cene: po splicie k:1 akcji jest
    k razy wiecej, wiec historyczny wolumen mnozymy przez k, zeby byl
    porownywalny z dzisiejszym.
    """
    rep = wykryj_splity(dni, close, volume, symbol=symbol)
    m = wspolczynniki_korekty(dni, rep)
    return np.asarray(close, dtype=float) / m, np.asarray(volume, dtype=float) * m, rep


def scal_tickery(symbol: str) -> list[str]:
    """Wszystkie nazwy, pod ktorymi spolka handlowala sie w naszym zakresie.

    Uzywane przy wczytywaniu: szereg sklejamy w jeden pod nazwa AKTUALNA, bo to
    ona jest kluczem w tabeli wag indeksu.

    UWAGA: sama lista nazw NIE WYSTARCZA do sklejenia — patrz `nalezy_do_szeregu`.
    """
    poprzedni = POPRZEDNIE_TICKERY.get(symbol)
    return [poprzedni[0], symbol] if poprzedni else [symbol]


def nalezy_do_szeregu(symbol_docelowy: str, symbol_rekordu: str, dzien: date) -> bool:
    """Czy rekord `symbol_rekordu` z dnia `dzien` nalezy do szeregu spolki.

    TICKER JEST NAZWA, NIE TOZSAMOSCIA — i gielda go PRZETWARZA. Po tym, jak Meta
    porzucila "FB" w czerwcu 2022, symbol zostal z czasem przypisany INNEJ spolce.
    W naszych danych widac to wprost: zapytanie o FB zwraca 84 tysiace rekordow
    za rok 2022 (do 8 czerwca wlacznie), zero za lata 2023-2024 i **ponownie po
    kilkaset rekordow za lata 2025-2026**.

    Sklejenie po samej nazwie wstawiloby wiec obcy papier w srodek historii Mety.
    Blad nie rzucilby wyjatku — dolozylby kilkaset barow spolki o innej cenie
    i innym wolumenie, co w sumie wazonej skladnikow indeksu daje sygnal
    wygladajacy na prawdziwy.

    Stad odciecie po dacie, obustronne:
      * poprzednik liczy sie WYLACZNIE przed data zmiany,
      * nazwa aktualna WYLACZNIE od daty zmiany.
    """
    poprzedni = POPRZEDNIE_TICKERY.get(symbol_docelowy)
    if poprzedni is None:
        return symbol_rekordu == symbol_docelowy

    stary, kiedy = poprzedni
    if symbol_rekordu == stary:
        return dzien < kiedy
    if symbol_rekordu == symbol_docelowy:
        return dzien >= kiedy
    return False


def data_zmiany_tickera(symbol: str) -> date | None:
    poprzedni = POPRZEDNIE_TICKERY.get(symbol)
    return poprzedni[1] if poprzedni else None
