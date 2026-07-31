"""Straznicy niezmiennikow silnika — bledy, ktore nie wygladaja jak bledy.

Najgrozniejsze pomylki w backtestingu nie objawiaja sie jako awaria, tylko jako
DOBRE WYNIKI. Strategia, ktora podejrzala przyszlosc, nie rzuca wyjatkiem —
rysuje piekna krzywa kapitalu. Dlatego te zabezpieczenia sa architektoniczne:
nie polegaja na dyscyplinie autora strategii, tylko czynia bledna operacje
technicznie niewykonalna.

Specyfikacja: PLAN.pdf rozdz. 5.1 (zasady konstrukcyjne), 4.2 (wolumen zero),
4.3 (rozdzielenie serii px_raw/px_adj).
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence


class LookaheadError(RuntimeError):
    """Strategia probowala siegnac po dane z przyszlosci."""


class ZeroVolumeExecutionError(RuntimeError):
    """Proba wykonania zlecenia w barze, w ktorym nie bylo transakcji."""


class AdjustedSeriesError(RuntimeError):
    """Poziom referencyjny liczony na serii skorygowanej zamiast surowej."""


class HistoryView(Sequence):
    """Okno historii widoczne dla strategii — TYLKO do biezacego bara wlacznie.

    To nie jest konwencja ani ostrzezenie w dokumentacji. Widok fizycznie nie
    udostepnia barow pozniejszych niz `cutoff`: proba siegniecia dalej konczy
    sie `LookaheadError`, a nie cichym zwroceniem danych z przyszlosci.

    Dzieki temu przeciek informacji jest bledem WYKRYWALNYM, a nie subtelnym
    zawyzeniem wyniku, ktore ujawni sie dopiero na zywym rachunku.

    >>> bars = [10, 20, 30, 40, 50]
    >>> view = HistoryView(bars, cutoff=2)   # widac bary 0,1,2
    >>> len(view)
    3
    >>> view[-1]
    30
    >>> view[3]
    Traceback (most recent call last):
    LookaheadError: ...
    """

    __slots__ = ("_data", "_cutoff")

    def __init__(self, data: Sequence, cutoff: int):
        if cutoff < -1:
            raise ValueError("cutoff musi byc >= -1")
        self._data = data
        self._cutoff = cutoff

    @property
    def cutoff(self) -> int:
        return self._cutoff

    def __len__(self) -> int:
        return self._cutoff + 1

    def __getitem__(self, idx):
        n = len(self)
        if isinstance(idx, slice):
            start, stop, step = idx.indices(n)
            return [self._data[i] for i in range(start, stop, step)]
        if idx < 0:
            idx += n
        if idx < 0:
            raise IndexError("indeks poza zakresem historii")
        if idx >= n:
            raise LookaheadError(
                f"Proba odczytu bara {idx} przy cutoff={self._cutoff}. "
                "Strategia widzi wylacznie dane do biezacego bara wlacznie "
                "(PLAN.pdf rozdz. 5.1). Sygnal liczony na close -> wykonanie "
                "na open NASTEPNEGO bara."
            )
        return self._data[idx]

    def __iter__(self) -> Iterator:
        for i in range(len(self)):
            yield self._data[i]

    def __repr__(self) -> str:
        return f"HistoryView(len={len(self)}, cutoff={self._cutoff})"

    def last(self, n: int = 1) -> list:
        """Ostatnie n barow (do biezacego wlacznie)."""
        if n <= 0:
            raise ValueError("n musi byc dodatnie")
        start = max(0, len(self) - n)
        return [self._data[i] for i in range(start, len(self))]


def assert_tradeable(bar, *, context: str = "") -> None:
    """Blokuje wykonanie w barze o zerowym wolumenie (rozdz. 4.2).

    Databento nie drukuje bara, gdy nie bylo transakcji — brak bara to poprawny
    opis rynku. Ale gdy bar istnieje z volume == 0 (albo powstal z forward-fill),
    symulowanie w nim transakcji produkuje zysk, ktorego nie dalo sie zrealizowac.
    """
    vol = getattr(bar, "volume", None)
    if vol is None:
        raise ZeroVolumeExecutionError(f"Bar bez informacji o wolumenie{_ctx(context)}")
    if vol <= 0:
        raise ZeroVolumeExecutionError(
            f"Proba wykonania w barze o wolumenie {vol}{_ctx(context)}. "
            "Wolumen zero znaczy, ze nie bylo gdzie sie wykonac "
            "(PLAN.pdf rozdz. 4.2). Forward-fill jest dozwolony dla wskaznikow, "
            "ale zakazany dla barow wejscia i stop-lossa."
        )


def assert_raw_series(series_kind: str, *, what: str = "poziom referencyjny") -> None:
    """Pilnuje, by poziomy miedzysesyjne liczyc na cenach surowych (rozdz. 4.3).

    Back-adjust przesuwa historie sprzed rolowania o stala wartosc. Wewnatrz
    jednego kontraktu relacje sa zachowane, ale NA GRANICY ROLOWANIA poziomy
    siegajace wstecz przestaja odpowiadac cenom, ktore realnie byly na tablicy.
    PDH z serii skorygowanej to poziom, ktorego nikt nigdy nie widzial.
    """
    if series_kind != "raw":
        raise AdjustedSeriesError(
            f"{what} liczony na serii '{series_kind}', wymagana 'raw' "
            "(PLAN.pdf rozdz. 4.3). Poziomy miedzysesyjne licz na px_raw; "
            "serii skorygowanej uzywaj wylacznie do P&L i statystyk zwrotow."
        )


def _ctx(context: str) -> str:
    return f" [{context}]" if context else ""
