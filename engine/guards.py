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


# ==========================================================================
# ZAKRESY ZMIENNYCH — druga warstwa po rzutowaniu typow
# ==========================================================================
#
# DLACZEGO TO ISTNIEJE. Odejmowanie kolumn bez znaku przepelnia sie do ~1,8e19
# zamiast dac liczbe ujemna. Blad NIE rzuca wyjatku i NIE psuje wykresu —
# zmienia werdykt. W tym projekcie wystapil DWA razy: przy roznicy wolumenow
# (Etap 1 D5) i przy `n_buy - n_sell` (Etap 2 D5, falszywy `NO-GO`).
#
# Sama zasada "rzutuj na Int64" okazala sie niewystarczajaca, bo trzeba jeszcze
# pamietac, zeby ja zastosowac. Asercja zakresu jest kontrola NIEZALEZNA od
# tego, czy autor pamietal: zmienna o znanych z konstrukcji granicach musi
# w nich lezec, a wartosc poza nimi jest dowodem bledu obliczenia, nie
# wlasnoscia rynku.
#
# Zasada: asercja NA ZMIENNEJ, w miejscu jej obliczenia — nie na typie.


class RangeError(ValueError):
    """Zmienna wyszla poza zakres, ktory ma z konstrukcji."""


def _skrajne(wartosci) -> tuple[float, float]:
    """(min, max) dla numpy, polars Series i zwyklych sekwencji."""
    import math

    surowy_lo: object
    surowy_hi: object
    if isinstance(wartosci, (int, float)):   # pojedyncza liczba tez jest zakresem
        surowy_lo = surowy_hi = wartosci
    elif hasattr(wartosci, "min") and hasattr(wartosci, "max"):
        surowy_lo, surowy_hi = wartosci.min(), wartosci.max()
    else:
        seq = list(wartosci)
        if not seq:
            return 0.0, 0.0
        surowy_lo, surowy_hi = min(seq), max(seq)
    if surowy_lo is None or surowy_hi is None:   # pusta seria — nie ma czego badac
        return 0.0, 0.0
    lo, hi = float(surowy_lo), float(surowy_hi)  # type: ignore[arg-type]
    if math.isnan(lo) or math.isnan(hi):
        raise RangeError("wartosci zawieraja NaN — zakres nierozstrzygalny")
    return lo, hi


def assert_w_zakresie(wartosci, lo: float, hi: float, *, nazwa: str,
                      tol: float = 1e-9) -> None:
    """Ogolna asercja zakresu domknietego [lo, hi]."""
    a, b = _skrajne(wartosci)
    if a < lo - tol or b > hi + tol:
        raise RangeError(
            f"{nazwa}: wartosci w [{a!r}, {b!r}], wymagane [{lo}, {hi}]. "
            "Wartosc poza zakresem konstrukcyjnym oznacza BLAD OBLICZENIA "
            "(typowo przepelnienie odejmowania kolumn bez znaku), "
            "a nie wlasnosc danych."
        )


def assert_imbalance(wartosci, *, nazwa: str = "imbalance") -> None:
    """Nierownowaga (a-b)/(a+b) dla nieujemnych a, b: zawsze w [-1, +1]."""
    assert_w_zakresie(wartosci, -1.0, 1.0, nazwa=nazwa)


def assert_udzial(wartosci, *, nazwa: str = "udzial") -> None:
    """Udzial czesci w calosci: zawsze w [0, 1]."""
    assert_w_zakresie(wartosci, 0.0, 1.0, nazwa=nazwa)


def assert_prawdopodobienstwo(wartosci, *, nazwa: str = "prawdopodobienstwo") -> None:
    """Prawdopodobienstwo: zawsze w [0, 1]."""
    assert_w_zakresie(wartosci, 0.0, 1.0, nazwa=nazwa)


def assert_liczebnosc(wartosci, *, nazwa: str = "liczebnosc") -> None:
    """Liczebnosc: nigdy ujemna. Wartosc ujemna to zwykle roznica liczonych
    wielkosci, ktora nie powinna byc liczebnoscia."""
    a, _ = _skrajne(wartosci)
    if a < 0:
        raise RangeError(f"{nazwa}: wartosc ujemna ({a!r}), liczebnosc musi byc >= 0")


def assert_vif(wartosci, *, nazwa: str = "VIF") -> None:
    """VIF = 1/(1-R^2) dla R^2 w [0,1): zawsze >= 1.

    Wartosc ponizej 1 oznacza ujemne R^2, czyli dopasowanie gorsze od sredniej —
    przy regresji Z WYRAZEM WOLNYM jest to niemozliwe i swiadczy o bledzie
    numerycznym albo o modelu bez wyrazu wolnego, ktory trzeba obsluzyc jawnie.
    """
    a, _ = _skrajne(wartosci)
    if a < 1.0 - 1e-9:
        raise RangeError(
            f"{nazwa}: {a!r} < 1. VIF < 1 wymaga ujemnego R^2, co przy regresji "
            "z wyrazem wolnym jest niemozliwe — sprawdz obliczenie."
        )
