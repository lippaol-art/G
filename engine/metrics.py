"""Metryki wynikow — PLAN.pdf rozdz. 6.1-6.3.

Wszystkie wyniki wyrazamy w R (wielokrotnosciach zaryzykowanej kwoty).
Normalizacja w R uniezaleznia statystyki od kapitalu i pozwala porownywac
strategie o roznych stopach.

Sharpe liczymy na DZIENNYCH P&L, nie na transakcjach — inaczej strategie
o roznej czestotliwosci nie sa porownywalne.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

TRADING_DAYS = 252

# Progi z rozdz. 1.3 i 6.1
PF_GATE = 1.15
SHARPE_GATE = 0.8
CONCENTRATION_GATE = 0.40      # udzial 5 najlepszych dni
PF_SUSPICIOUS = 2.0            # PF > 2 w intraday = niemal na pewno blad lub przeuczenie


@dataclass(frozen=True)
class Metrics:
    n_trades: int
    expectancy_r: float
    profit_factor: float
    win_rate: float
    payoff_ratio: float
    sharpe: float
    sharpe_lo_adjusted: float
    sortino: float
    max_drawdown: float
    max_dd_duration_days: int
    mar: float
    sqn: float
    top5_concentration: float
    r_metrics_valid: bool = True

    @property
    def suspicious(self) -> bool:
        """PF > 2 przy strategii intraday — protokol: najpierw szukamy bledu."""
        return bool(self.profit_factor > PF_SUSPICIOUS)

    def gate_report(self) -> dict[str, bool]:
        """Ktore progi z rozdz. 1.3 sa spelnione."""
        return {
            "profit_factor": bool(self.profit_factor >= PF_GATE),
            "sharpe": bool(self.sharpe >= SHARPE_GATE),
            "koncentracja": bool(self.top5_concentration < CONCENTRATION_GATE),
        }


def expectancy(r_multiples: np.ndarray) -> float:
    arr = np.asarray(r_multiples, dtype=float)
    return float(arr.mean()) if arr.size else 0.0


def profit_factor(r_multiples: np.ndarray) -> float:
    arr = np.asarray(r_multiples, dtype=float)
    zyski = arr[arr > 0].sum()
    straty = abs(arr[arr < 0].sum())
    if straty == 0:
        return float("inf") if zyski > 0 else 0.0
    return float(zyski / straty)


def sharpe_ratio(daily_pnl: np.ndarray, annualize: bool = True) -> float:
    """Sharpe na dziennych P&L.

    Uwaga (rozdz. 6.3): std liczymy po WSZYSTKICH dniach, nie tylko aktywnych.
    Strategie o rzadkich transakcjach maja dni zerowe i pominiecie ich
    zawyzaloby wynik.
    """
    arr = np.asarray(daily_pnl, dtype=float)
    if arr.size < 2:
        return 0.0
    sd = arr.std(ddof=1)
    if sd == 0:
        return 0.0
    sr = arr.mean() / sd
    return float(sr * math.sqrt(TRADING_DAYS)) if annualize else float(sr)


def sharpe_lo_correction(daily_pnl: np.ndarray, q: int = 5) -> float:
    """Sharpe z poprawka Lo na autokorelacje (rozdz. 6.3).

    Autokorelacja dziennych wynikow ZAWYZA annualizowany Sharpe — mnoznik
    sqrt(252) zaklada niezaleznosc. Poprawka:

        SR_adj = SR_ann * [1 + 2*sum_k (1 - k/(q+1)) * rho_k]^(-1/2)
    """
    arr = np.asarray(daily_pnl, dtype=float)
    if arr.size < q + 2:
        return sharpe_ratio(arr)

    sr_ann = sharpe_ratio(arr)
    x = arr - arr.mean()
    var = float((x**2).sum())
    if var == 0:
        return 0.0

    suma = 0.0
    for k in range(1, q + 1):
        rho = float((x[:-k] * x[k:]).sum() / var)
        suma += (1.0 - k / (q + 1.0)) * rho

    czynnik = 1.0 + 2.0 * suma
    if czynnik <= 0:
        return sr_ann
    return float(sr_ann / math.sqrt(czynnik))


def sortino_ratio(daily_pnl: np.ndarray) -> float:
    arr = np.asarray(daily_pnl, dtype=float)
    if arr.size < 2:
        return 0.0
    downside = np.minimum(arr, 0.0)
    dd = math.sqrt(float((downside**2).mean()))
    if dd == 0:
        return 0.0
    return float(math.sqrt(TRADING_DAYS) * arr.mean() / dd)


def drawdown_stats(equity: np.ndarray) -> tuple[float, int]:
    """(maksymalne obsuniecie, najdluzszy czas pod woda w krokach)."""
    arr = np.asarray(equity, dtype=float)
    if arr.size == 0:
        return 0.0, 0
    peak = np.maximum.accumulate(arr)
    dd = peak - arr
    mdd = float(dd.max())

    najdluzszy = biezacy = 0
    for i in range(arr.size):
        if arr[i] < peak[i]:
            biezacy += 1
            najdluzszy = max(najdluzszy, biezacy)
        else:
            biezacy = 0
    return mdd, najdluzszy


def sqn(r_multiples: np.ndarray) -> float:
    arr = np.asarray(r_multiples, dtype=float)
    if arr.size < 2:
        return 0.0
    sd = arr.std(ddof=1)
    if sd == 0:
        return 0.0
    return float(math.sqrt(arr.size) * arr.mean() / sd)


def top_n_concentration(daily_pnl: np.ndarray, n: int = 5) -> float:
    """Udzial n najlepszych dni w calym zysku (rozdz. 1.3). Prog: < 40%.

    Chroni przed strategia "z trzech szczesliwych dni".

    NIEZDEFINIOWANA DLA STRATEGII STRATNEJ. "Jaka czesc zysku pochodzi z pieciu
    dni" nie ma sensu, gdy zysku nie ma — iloraz przez ujemna sume daje liczbe
    ujemna, a przez sume bliska zeru dowolnie duza. Zwracamy NaN.

    Wczesniejsza wersja zwracala w tym miejscu 0.0, co w raporcie czytalo sie
    jako "koncentracja zerowa, czyli wzorowa" — dokladnie odwrotnie do prawdy.
    Wykryte na benchmarkach B01/B03/B04 (wszystkie stratne, wszystkie z 0%).
    """
    arr = np.asarray(daily_pnl, dtype=float)
    if arr.size == 0:
        return float("nan")
    total = arr.sum()
    if total <= 0:
        return float("nan")
    najlepsze = np.sort(arr)[-min(n, arr.size):].sum()
    return float(najlepsze / total)


def r_metrics_defined(r_multiples: np.ndarray) -> bool:
    """Czy metryki wyrazone w R maja w ogole sens dla tego zbioru transakcji.

    POWOD ISTNIENIA. `r_multiple` liczymy jako pnl / |wejscie - stop|. Strategia
    BEZ STOPA (wyjscie czasowe, wyjscie na sygnal) ma to zero dla kazdej
    transakcji — a wtedy PF, win rate, expectancy i SQN wychodza zerami, ktore
    wygladaja jak zmierzone. Zerowy profit factor przy dodatnim wyniku w USD to
    nie jest metryka, tylko cicha awaria pomiaru; raport wyswietlilby ja bez
    mrugniecia okiem.

    Wykryto na benchmarkach B03 i B04, ktorych regula literaturowa nie
    przewiduje stopa. Metryki dolarowe (Sharpe, MDD, koncentracja) pozostaja
    poprawne — one licza sie z dziennego P&L, nie z R.
    """
    arr = np.asarray(r_multiples, dtype=float)
    return bool(arr.size and np.any(arr != 0.0))


def summarize(r_multiples: np.ndarray, daily_pnl: np.ndarray) -> Metrics:
    """Pelny zestaw metryk hipotezy.

    Gdy strategia nie ma stopa, metryki w R sa NIEZDEFINIOWANE i zwracamy je
    jako NaN z flaga `r_metrics_valid=False` — NIE jako zera. Zero jest
    wartoscia, ktora czytelnik zinterpretuje; NaN jest pytaniem, ktore zada.
    """
    r = np.asarray(r_multiples, dtype=float)
    d = np.asarray(daily_pnl, dtype=float)

    if not r_metrics_defined(r):
        equity_ = np.cumsum(d)
        mdd_, dd_len_ = drawdown_stats(equity_)
        nan = float("nan")
        return Metrics(
            n_trades=int(r.size), expectancy_r=nan, profit_factor=nan,
            win_rate=nan, payoff_ratio=nan,
            sharpe=sharpe_ratio(d), sharpe_lo_adjusted=sharpe_lo_correction(d),
            sortino=sortino_ratio(d), max_drawdown=mdd_, max_dd_duration_days=dd_len_,
            mar=float(d.mean() * TRADING_DAYS / mdd_) if mdd_ > 0 else 0.0,
            sqn=nan, top5_concentration=top_n_concentration(d, 5),
            r_metrics_valid=False,
        )

    wins = r[r > 0]
    losses = r[r < 0]
    win_rate = float(wins.size / r.size) if r.size else 0.0
    payoff = float(wins.mean() / abs(losses.mean())) if wins.size and losses.size else 0.0

    equity = np.cumsum(d)
    mdd, dd_len = drawdown_stats(equity)
    zwrot_roczny = float(d.mean() * TRADING_DAYS)
    mar = float(zwrot_roczny / mdd) if mdd > 0 else 0.0

    return Metrics(
        n_trades=int(r.size),
        expectancy_r=expectancy(r),
        profit_factor=profit_factor(r),
        win_rate=win_rate,
        payoff_ratio=payoff,
        sharpe=sharpe_ratio(d),
        sharpe_lo_adjusted=sharpe_lo_correction(d),
        sortino=sortino_ratio(d),
        max_drawdown=mdd,
        max_dd_duration_days=dd_len,
        mar=mar,
        sqn=sqn(r),
        top5_concentration=top_n_concentration(d, 5),
    )
