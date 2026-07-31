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
from datetime import date


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


def find_roll_dates(
    days_by_contract: dict[str, list[ContractDay]],
    contract_order: list[str],
) -> list[RollEvent]:
    """Wyznacza daty rolowan regula wolumenowa.

    Dla kazdej pary kolejnych kontraktow szuka pierwszego dnia, w ktorym
    wolumen nastepnego przewyzsza wolumen biezacego, i zapisuje spread cen
    zamkniecia z TEGO SAMEGO dnia (oba kontrakty musza miec tego dnia notowanie).
    """
    events: list[RollEvent] = []

    for cur, nxt in zip(contract_order, contract_order[1:], strict=False):
        cur_days = {d.trade_date: d for d in days_by_contract.get(cur, [])}
        nxt_days = {d.trade_date: d for d in days_by_contract.get(nxt, [])}
        wspolne = sorted(set(cur_days) & set(nxt_days))

        for d in wspolne:
            if nxt_days[d].volume > cur_days[d].volume:
                events.append(RollEvent(
                    roll_date=d,
                    from_contract=cur,
                    to_contract=nxt,
                    spread=nxt_days[d].close - cur_days[d].close,
                ))
                break

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
    """Sprawdza, czy po adjustmencie zniknely sztuczne skoki w dniach rolowan.

    To jest test z rozdz. 5.6: w serii ciaglej nie moze istniec bar, ktorego
    open odbiega od poprzedniego close o spread rolowania. Nieskorygowane
    sklejenie zostawia takie skoki, a strategia "kupuj spadki" "zarabia" na
    lukach, ktore nigdy nie byly handlowalne — jeden z najczestszych sposobow,
    w jaki amatorskie backtesty futures produkuja fikcyjne zyski.

    Zwraca liste opisow naruszen (pusta = OK).
    """
    naruszenia: list[str] = []
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
            naruszenia.append(
                f"{ev.roll_date}: skok {skok:.2f} bliski spreadowi rolowania "
                f"{ev.spread:.2f} — back-adjust nie zadzialal"
            )
    return naruszenia


def days_to_roll(current: date, events: list[RollEvent]) -> int | None:
    """Ile dni do najblizszego rolowania. Flaga dla silnika (rozdz. 4.2 krok 8).

    Zwraca None, gdy nie ma juz rolowan w przod.
    """
    przyszle = [e.roll_date for e in events if e.roll_date >= current]
    return (min(przyszle) - current).days if przyszle else None
