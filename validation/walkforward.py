"""Walk-forward z purgingiem i embargo.

Specyfikacja: PLAN.pdf rozdz. 7.1, 7.3.

Podzial historii:
    |—— eksploracja + IS (60%) ——|—— OOS walk-forward (40%) ——|—— lockbox (6 mies.) ——|

Okna: IS 12 mies. -> OOS 3 mies. -> przesuniecie o 3 mies.
Wynik hipotezy = metryki krzywej zszytej WYLACZNIE z okien OOS.

PURGING I EMBARGO obowiazuja WSZYSTKIE strategie, nie tylko swing (poprawka v1.1):
zmiennosc wewnatrzdzienna jest silnie autokorelowana, wiec bar tuz po granicy okna
niesie informacje o barze tuz przed nia. Wersja 1.0 zwalniala intraday z tego wymogu —
blednie.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# Domyslne parametry (rozdz. 7.1, 7.3)
IS_MONTHS = 12
OOS_MONTHS = 3
LOCKBOX_MONTHS = 6
EMBARGO_INTRADAY = timedelta(minutes=60)
EMBARGO_SWING_DAYS = 5


@dataclass(frozen=True)
class Window:
    """Pojedyncze okno walk-forward.

    Miedzy `is_end` a `oos_start` lezy strefa purge+embargo, ktorej NIE uzywamy
    ani do treningu, ani do testu — to cena za brak przecieku przez granice.
    """

    is_start: date
    is_end: date
    oos_start: date
    oos_end: date

    @property
    def purge_days(self) -> int:
        return (self.oos_start - self.is_end).days

    def __repr__(self) -> str:
        return (f"Window(IS {self.is_start}..{self.is_end}, "
                f"OOS {self.oos_start}..{self.oos_end}, purge={self.purge_days}d)")


@dataclass(frozen=True)
class Split:
    """Pelny podzial historii na okna + lockbox."""

    windows: tuple[Window, ...]
    lockbox_start: date
    lockbox_end: date

    def __len__(self) -> int:
        return len(self.windows)

    @property
    def oos_days_total(self) -> int:
        """Laczna dlugosc zszytego OOS — kluczowa dla DSR (maksymalizacja T)."""
        return sum((w.oos_end - w.oos_start).days for w in self.windows)


def _add_months(d: date, months: int) -> date:
    """Przesuniecie o miesiace bez zewnetrznych zaleznosci."""
    y, m = divmod(d.month - 1 + months, 12)
    y += d.year
    m += 1
    # Ostatni dzien miesiaca docelowego, gdy dzien zrodlowy nie istnieje (31 -> 30/28)
    day = d.day
    while day > 28:
        try:
            return date(y, m, day)
        except ValueError:
            day -= 1
    return date(y, m, day)


def embargo_for(horizon: str, max_position_days: int = 0) -> timedelta:
    """Bufor embargo zaleznie od horyzontu strategii (rozdz. 7.3).

    intraday : purge do konca dnia sesyjnego + embargo >= 60 min
    swing    : purge = maks. horyzont pozycji + embargo 5 dni
    """
    if horizon == "intraday":
        return timedelta(days=1) + EMBARGO_INTRADAY
    if horizon == "swing":
        return timedelta(days=max_position_days + EMBARGO_SWING_DAYS)
    raise ValueError(f"nieznany horyzont: {horizon!r} (oczekiwano 'intraday' albo 'swing')")


def make_split(
    start: date,
    end: date,
    *,
    horizon: str = "intraday",
    is_months: int = IS_MONTHS,
    oos_months: int = OOS_MONTHS,
    lockbox_months: int = LOCKBOX_MONTHS,
    max_position_days: int = 0,
) -> Split:
    """Buduje sekwencje okien walk-forward + lockbox na koncu historii.

    PRZED KAZDYM ODCZYTEM LOCKBOXA — wpis do `validation/lockbox_log.json`
    (data UTC, hipoteza, powod, SHA). Wpis powstaje PRZED odczytem, nie po:
    po fakcie nie jest juz kontrola, tylko relacja. Bez dziennika regula ponizej
    istnieje wylacznie w tym docstringu i nie da sie stwierdzic, ile razy
    sejf otwarto — a to jest jedyna liczba, ktora tu cokolwiek znaczy.

    Lockbox to ostatnie `lockbox_months` miesiecy, ktorych NIE dotykamy w zadnej
    iteracji badawczej. Sluzy wylacznie do finalnej, jednorazowej weryfikacji
    kandydata. Jedno spojrzenie = zuzycie sejfu (odnotowane w rejestrze).
    """
    if end <= start:
        raise ValueError("end musi byc pozniejszy niz start")

    lockbox_start = _add_months(end, -lockbox_months)
    if lockbox_start <= start:
        raise ValueError(
            f"Historia {start}..{end} jest za krotka na lockbox {lockbox_months} mies."
        )

    embargo = embargo_for(horizon, max_position_days)
    windows: list[Window] = []

    is_start = start
    while True:
        is_end = _add_months(is_start, is_months)
        oos_start = is_end + embargo
        oos_end = _add_months(oos_start, oos_months)

        if oos_end > lockbox_start:
            break

        windows.append(Window(is_start, is_end, oos_start, oos_end))
        is_start = _add_months(is_start, oos_months)

    if not windows:
        raise ValueError(
            f"Brak pelnych okien dla historii {start}..{lockbox_start} "
            f"przy IS={is_months}m, OOS={oos_months}m"
        )

    return Split(tuple(windows), lockbox_start, end)


def stitch_oos(window_results: list[list[float]]) -> list[float]:
    """Zszywa dzienne wyniki z okien OOS w jeden ciagly szereg.

    To na nim liczymy metryki hipotezy ORAZ DSR — maksymalizacja T jest
    jedyna dzwignia po stronie danych (rozdz. 6.5).
    """
    out: list[float] = []
    for r in window_results:
        out.extend(r)
    return out


def is_oos_divergence(pf_is: float, pf_oos: float) -> float:
    """Rozjazd IS/OOS jako ulamek. > 0.5 to czerwona flaga przeuczenia (rozdz. 7.1)."""
    if pf_is <= 0:
        raise ValueError("pf_is musi byc dodatni")
    return abs(pf_is - pf_oos) / pf_is
