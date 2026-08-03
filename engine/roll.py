"""Rolowanie kontraktu ciaglego i back-adjust roznicowy.

Specyfikacja: PLAN.pdf rozdz. 4.3.

DWIE DECYZJE, OBIE PODJETE JAWNIE:

  (a) KIEDY ROLOWAC — regula WOLUMENOWA, nie kalendarzowa.
      Rolujemy w dniu, w ktorym wolumen kontraktu nastepnego przewyzsza wolumen
      biezacego. Odzwierciedla to faktyczna migracje plynnosci, ktora
      handlowalibysmy na zywo. Dla indeksow wypada zwykle ~8 dni przed
      wygasnieciem.

  (b) JAK SKLEIC POZIOMY — BACK-ADJUST ROZNICOWY.
      W dniu rolowania spread S = close(nowy) - close(stary); cala historia
      wstecz przesuwana o S. Roznice cen (a wiec P&L w punktach, ATR, zakresy)
      zachowane idealnie — a na nich pracuje 100% naszych obliczen.

ROZDZIELENIE SERII (kluczowa poprawka v1.1):
      Back-adjust przesuwa historie o stala. Wewnatrz jednego kontraktu relacje
      sa zachowane, ale NA GRANICY ROLOWANIA poziom siegajacy wstecz przestaje
      odpowiadac cenie, ktora realnie byla na tablicy. PDH z serii skorygowanej
      to poziom, ktorego nikt nigdy nie widzial.

      px_raw  -> poziomy miedzysesyjne (PDH/PDL/PDC), reakcje na poziomy
      px_adj  -> P&L, equity, statystyki zwrotow
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# Kody miesiecy CME. MNQ/NQ/ES uzywaja cyklu kwartalnego: H, M, U, Z.
MONTH_CODES = {
    "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
    "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
}


def contract_expiry(symbol: str, *, decade_base: int = 2020) -> tuple[int, int]:
    """Wygasniecie kontraktu (rok, miesiac) odczytane z kodu symbolu.

    KLUCZOWE DLA POPRAWNOSCI ROLOWANIA. Kolejnosci kontraktow NIE WOLNO
    wyznaczac z daty pierwszego notowania: kontrakty listuja sie ponad rok
    przed wygasnieciem i czesto tego samego dnia. Na realnych danych MNQ
    sortowanie po pierwszym barze dalo kolejnosc 'M3, Z3, U3' — grudzien przed
    wrzesniem — przez co regula wolumenowa liczyla rolowanie WSTECZ,
    z kontraktu grudniowego na wrzesniowy.

    Format: [ROOT][kod miesiaca][cyfra roku], np. MNQH5 = marzec 2025.
    Cyfra roku jest jednoznaczna tylko w obrebie dekady — `decade_base`
    okresla, do ktorej dekady ja odnosic (dla naszego zakresu 2019-2026
    cyfra 9 oznacza 2019, cyfry 0-6 lata 2020-2026).
    """
    s = symbol.strip().upper()
    if len(s) < 2:
        raise ValueError(f"symbol za krotki: {symbol!r}")

    rok_cyfra = s[-1]
    kod_mies = s[-2]
    if not rok_cyfra.isdigit() or kod_mies not in MONTH_CODES:
        raise ValueError(f"nie moge odczytac wygasniecia z {symbol!r}")

    cyfra = int(rok_cyfra)
    rok = decade_base + cyfra
    # Cyfra wyrazne wieksza od biezacej dekady oznacza dekade poprzednia
    # (9 -> 2019, gdy decade_base = 2020).
    if cyfra >= 7:
        rok = decade_base - 10 + cyfra

    return rok, MONTH_CODES[kod_mies]


@dataclass(frozen=True)
class RollEvent:
    """Pojedyncze rolowanie: z kontraktu na kontrakt, ze spreadem."""

    roll_date: date
    from_contract: str
    to_contract: str
    spread: float          # close(nowy) - close(stary)

    def __repr__(self) -> str:
        return (f"RollEvent({self.roll_date}: {self.from_contract} -> "
                f"{self.to_contract}, spread={self.spread:+.2f})")


@dataclass(frozen=True)
class ContractDay:
    """Dzien sesyjny jednego kontraktu — wejscie do wyznaczania rolowan."""

    trade_date: date
    contract: str
    close: float
    volume: int


def third_friday(year: int, month: int) -> date:
    """Trzeci piatek miesiaca — dzien wygasniecia kontraktow indeksowych CME."""
    d = date(year, month, 1)
    # dni do pierwszego piatku (weekday 4)
    do_piatku = (4 - d.weekday()) % 7
    return date(year, month, 1 + do_piatku + 14)


def find_roll_dates(
    days_by_contract: dict[str, list[ContractDay]],
    contract_order: list[str],
    *,
    window_days: int = 45,
    min_consecutive: int = 3,
) -> list[RollEvent]:
    """Wyznacza daty rolowan regula wolumenowa — z dwoma zabezpieczeniami.

    Naiwna wersja ("pierwszy dzien, w ktorym nastepny ma wiekszy wolumen")
    zawodzi na realnych danych, bo kontrakty listuja sie ponad rok przed
    wygasnieciem. Na rzadkim dniu, gdy oba maja znikomy obrot, dalszy kontrakt
    potrafi przypadkiem przebic blizszy — i rolowanie wypada np. dziesiec
    miesiecy za wczesnie, ze spreadem rzedu setek punktow.

    Dwa warunki, ktore to eliminuja:

    1. OKNO PRZY WYGASNIECIU (`window_days`) — kandydatow szukamy wylacznie
       w oknie konczacym sie wygasnieciem biezacego kontraktu. Poza tym oknem
       zaden z kontraktow nie jest jeszcze przednim miesiacem.

    2. TRWALOSC PRZEWAGI (`min_consecutive`) — wolumen nastepnego musi
       przewyzszac biezacy przez kilka kolejnych DNI NOTOWANIA. To odpowiedz
       na ryzyko wskazane w audycie: pojedyncza transakcja pakietowa nie moze
       przesadzac o dacie rolowania.
    """
    events: list[RollEvent] = []

    for cur, nxt in zip(contract_order, contract_order[1:], strict=False):
        cur_days = {d.trade_date: d for d in days_by_contract.get(cur, [])}
        nxt_days = {d.trade_date: d for d in days_by_contract.get(nxt, [])}
        wspolne = sorted(set(cur_days) & set(nxt_days))
        if not wspolne:
            continue

        try:
            rok, mies = contract_expiry(cur)
            wygasniecie = third_friday(rok, mies)
            okno_od = wygasniecie - timedelta(days=window_days)
            kandydaci = [d for d in wspolne if okno_od <= d <= wygasniecie]
            # BEZ fallbacku do calego zakresu: brak danych przy wygasnieciu
            # oznacza, ze nie mamy podstaw do wyznaczenia rolowania. Siegniecie
            # po dane sprzed miesiecy dawaloby wlasnie te bledna date, przed
            # ktora zabezpiecza okno.
        except ValueError:
            # Symbolu nie da sie rozpoznac — dopiero wtedy caly wspolny zakres.
            kandydaci = wspolne

        seria = 0
        for i, d in enumerate(kandydaci):
            if nxt_days[d].volume > cur_days[d].volume:
                seria += 1
                if seria >= min_consecutive:
                    # rolujemy w PIERWSZYM dniu serii, nie w ostatnim
                    d0 = kandydaci[i - min_consecutive + 1]
                    events.append(RollEvent(
                        roll_date=d0,
                        from_contract=cur,
                        to_contract=nxt,
                        spread=nxt_days[d0].close - cur_days[d0].close,
                    ))
                    break
            else:
                seria = 0

    return events


def cumulative_offsets(events: list[RollEvent]) -> dict[str, float]:
    """Skumulowane przesuniecie back-adjustu dla kazdego kontraktu.

    Kontrakt najnowszy ma offset 0 (jego ceny sa "prawdziwe"); kazdy wczesniejszy
    dostaje sume spreadow wszystkich pozniejszych rolowan.

    Zwraca mape kontrakt -> offset, gdzie:  px_adj = px_raw + offset
    """
    if not events:
        return {}

    offsets: dict[str, float] = {events[-1].to_contract: 0.0}
    running = 0.0
    for ev in reversed(events):
        running += ev.spread
        offsets[ev.from_contract] = running
    return offsets


def adjust_price(px_raw: float, contract: str, offsets: dict[str, float]) -> float:
    """px_raw -> px_adj. Kontrakt bez wpisu traktujemy jako najnowszy (offset 0)."""
    return px_raw + offsets.get(contract, 0.0)


def unadjust_price(px_adj: float, contract: str, offsets: dict[str, float]) -> float:
    """px_adj -> px_raw. Potrzebne przy liczeniu poziomow referencyjnych."""
    return px_adj - offsets.get(contract, 0.0)


def verify_continuity(
    adjusted_closes: list[tuple[date, float]],
    events: list[RollEvent],
    *,
    tolerance: float = 1e-6,
) -> list[str]:
    """DIAGNOSTYKA granic rolowania. **NIE JEST BRAMKA PASS/FAIL** (Etap 2.5).

    Idea z rozdz. 5.6 byla taka: w serii ciaglej nie moze istniec bar, ktorego
    open odbiega od poprzedniego close o spread rolowania. Nieskorygowane
    sklejenie zostawia takie skoki, a strategia "kupuj spadki" "zarabia" na
    lukach, ktore nigdy nie byly handlowalne — jeden z najczestszych sposobow,
    w jaki amatorskie backtesty futures produkuja fikcyjne zyski.

    DLACZEGO TO NIE MOZE ROZSTRZYGAC O POPRAWNOSCI BACK-ADJUSTU.
    Kryterium brzmi "skok >= |spread|", a zwykly ruch rynku miedzy sasiednimi
    sesjami bywa wielokrotnie wiekszy od spreadu kontraktowego. Zmierzone na
    naszych danych: funkcja zglasza 17 z 29 granic MNQ, 18/29 NQ i 12/29 ES
    przy DOKLADNIE ZEROWYM rozrzucie offsetu we wszystkich 90 kontraktach.
    Skrajny przypadek: 2020-03-13, ruch 659 pkt w szczycie krachu covidowego,
    przy spreadzie -13.50 pkt. Kryterium jest NIEIDENTYFIKOWALNE — nie odroznia
    ruchu rynku od bledu korekty, a problem lezy w jego konstrukcji, nie
    w wartosci progu, wiec zmiana progu niczego nie naprawia.

    CO ROZSTRZYGA ZAMIAST TEGO. Niezmiennik arytmetyczny: offset back-adjustu
    (`px_adj - close`) musi byc STALY w obrebie kontraktu. Odpowiedz jest
    dokladnie zerowa albo back-adjust jest zepsuty. To on wydaje PASS/FAIL
    w `scripts/data_quality.py`; ta funkcja dostarcza wylacznie materialu
    do obejrzenia.

    Funkcja NIE ZOSTALA USUNIETA — duzy skok przy granicy rolowania jest wart
    obejrzenia, nawet jesli sam w sobie niczego nie dowodzi.

    Zwraca liste zgloszen diagnostycznych (pusta = brak czego ogladac).
    """
    zgloszenia: list[str] = []
    by_date = dict(adjusted_closes)

    for ev in events:
        idx = [d for d, _ in adjusted_closes]
        if ev.roll_date not in by_date:
            continue
        pos = idx.index(ev.roll_date)
        if pos == 0:
            continue
        prev_close = by_date[idx[pos - 1]]
        this_close = by_date[ev.roll_date]
        skok = abs(this_close - prev_close)
        if skok > abs(ev.spread) - tolerance and abs(ev.spread) > tolerance:
            zgloszenia.append(
                f"{ev.roll_date}: duzy skok {skok:.2f} przy granicy rolowania "
                f"{ev.from_contract}->{ev.to_contract} (spread {ev.spread:.2f}). "
                "Heurystyka nie rozroznia ruchu rynku od bledu korekty — "
                "weryfikuj razem z niezmiennikiem stalosci offsetu."
            )
    return zgloszenia


def days_to_roll(current: date, events: list[RollEvent]) -> int | None:
    """Ile dni do najblizszego rolowania. Flaga dla silnika (rozdz. 4.2 krok 8).

    Zwraca None, gdy nie ma juz rolowan w przod.
    """
    przyszle = [e.roll_date for e in events if e.roll_date >= current]
    return (min(przyszle) - current).days if przyszle else None
