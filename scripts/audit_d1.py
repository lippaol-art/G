#!/usr/bin/env python3
"""Audyt wykonalnosci kierunku D1 — rebalansowanie funduszy lewarowanych.

CO TO JEST, A CZYM NIE JEST.
To NIE jest backtest i NIE zuzywa proby. Skrypt nie liczy ani jednego zwrotu
okna wynikowego, nie mierzy P&L i nie zawiera reguly wejscia. Mierzy WYLACZNIE
wlasciwosci proponowanego regresora:

  * czy dane o aktywach istnieja i sa dostepne point-in-time,
  * jak duze sa kreacje i umorzenia jednostek,
  * czy przeplyw inwestorow kompensuje rebalans (Ivanov & Lenkey 2018),
  * ile z bledu estymatora PIT da sie skorygowac znanym efektem NAV,
  * czy szacowany przeplyw da sie STATYSTYCZNIE ODROZNIC od samego zwrotu dnia.

Ostatni punkt jest falsyfikatorem nr 8 audytu: jesli ΔE jest praktycznie
wspolliniowe z benchmarkiem B04, kierunek nie dostaje karty — niezaleznie od
tego, jak dobry jest mechanizm.

ZRODLO DANYCH (darmowe, publiczne):
    https://accounts.profunds.com/etfdata/ByFund/{TICKER}-historical_nav.csv

Pliki NIE sa commitowane do repo — sa zewnetrzne i odtwarzalne z powyzszego
adresu. Skrypt sprawdza sumy kontrolne, zeby audyt dal sie zweryfikowac.

Uruchomienie:
    python3 scripts/audit_d1.py --katalog <sciezka_z_csv>
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Wszechswiat: WYLACZNIE fundusze o stalej dziennej dzwigni na SAM indeks
# Nasdaq-100. Fundusze na inny benchmark (rowna waga, Magnificent 7) NIE
# wchodza — patrz docs/D1_AUDYT_MECHANIZMU.md, sekcja o pulapkach nazewnictwa.
FUNDUSZE = {"TQQQ": 3.0, "QLD": 2.0, "SQQQ": -3.0, "QID": -2.0, "PSQ": -1.0}

OKNO_ADV = 20          # sesji do sredniego obrotu, WYLACZNIE poprzednich
MNOZNIK_MNQ = 2.0      # USD za punkt


def wczytaj(katalog: Path) -> dict[str, dict[date, dict]]:
    out: dict[str, dict[date, dict]] = {}
    for t in FUNDUSZE:
        p = katalog / f"{t}.csv"
        if not p.exists():
            sys.exit(f"BLAD: brak {p}. Pobierz z accounts.profunds.com (patrz docstring).")
        d = {}
        for r in csv.DictReader(p.open()):
            dt = datetime.strptime(r["Date"], "%m/%d/%Y").date()
            d[dt] = {
                "nav": float(r["NAV"]),
                "sh": float(r["Shares Outstanding (000)"]) * 1000,
                "aum": float(r["Assets Under Management"]),
            }
        out[t] = d
        print(f"  {t:5s} n={len(d):5d}  {min(d)} -> {max(d)}  "
              f"sha256={hashlib.sha256(p.read_bytes()).hexdigest()[:16]}")
    return out


def sesje_mnq() -> tuple[dict[date, float], dict[date, float]]:
    """Zwrot sesyjny i ADV point-in-time z WLASNYCH danych."""
    d = pl.read_parquet("data/clean/mnq_1m_cont.parquet").with_columns(
        (pl.col("volume") * pl.col("close") * MNOZNIK_MNQ).alias("usd")
    )
    s = (
        d.group_by("trade_date")
        .agg([pl.col("px_adj").last().alias("c"), pl.col("usd").sum().alias("obrot")])
        .sort("trade_date")
        .with_columns(
            (pl.col("c") / pl.col("c").shift(1) - 1).alias("r"),
            # ADV liczone z 20 POPRZEDNICH sesji — .shift(1) wyklucza dzien biezacy,
            # ktorego obrot powstaje dopiero po wejsciu. Bez tego byloby lookahead.
            pl.col("obrot").rolling_mean(window_size=OKNO_ADV).shift(1).alias("adv"),
        )
        .drop_nulls()
    )
    return (
        dict(zip(s["trade_date"].to_list(), s["r"].to_list(), strict=True)),
        dict(zip(s["trade_date"].to_list(), s["adv"].to_list(), strict=True)),
    )


def _r2(y: np.ndarray, X: np.ndarray) -> float:
    Xa = np.c_[np.ones(len(y)), X]
    beta, *_ = np.linalg.lstsq(Xa, y, rcond=None)
    return float(1 - (y - Xa @ beta).var() / y.var())


def main() -> int:
    ap = argparse.ArgumentParser(description="Audyt wykonalnosci D1 — bez pomiaru P&L")
    ap.add_argument("--katalog", required=True, type=Path)
    args = ap.parse_args()

    print("=== Zrodla ===")
    dane = wczytaj(args.katalog)
    rm, am = sesje_mnq()
    w = sorted(set(rm) & set.intersection(*[set(d) for d in dane.values()]))
    print(f"\nSesji wspolnych: {len(w)}  ({w[0]} -> {w[-1]})")

    print("\n=== 1. Tozsamosc AUM = NAV x jednostki (czy wiersz jest wielkoscia po zamknieciu) ===")
    for t in FUNDUSZE:
        r = dane[t][w[-1]]
        print(f"  {t:5s} |AUM - NAV*jednostki| = {abs(r['aum'] - r['nav'] * r['sh']):.2f}")

    print("\n=== 2. Kreacje i umorzenia jednostek ===")
    for t, L in FUNDUSZE.items():
        d = dane[t]
        z = np.array([(d[b]["sh"] - d[a]["sh"]) / d[a]["sh"]
                      for a, b in zip(w, w[1:], strict=False) if d[a]["sh"] > 0])
        print(f"  {t:5s} L={L:+.0f}  mediana|Δ|={100 * np.median(np.abs(z)):5.2f}%  "
              f"p90={100 * np.percentile(np.abs(z), 90):5.2f}%")

    print("\n=== 3. Offset Ivanova-Lenkeya: corr(Δjednostek, r) ===")
    for t, L in FUNDUSZE.items():
        d = dane[t]
        par = [(rm[x], (d[x]["sh"] - d[p]["sh"]) / d[p]["sh"])
               for p, x in zip(w, w[1:], strict=False) if d[p]["sh"] > 0]
        a = np.array([q[0] for q in par])
        b = np.array([q[1] for q in par])
        print(f"  {t:5s} L={L:+.0f}  corr={np.corrcoef(a, b)[0, 1]:+.3f}")

    # --- estymatory K ---
    naiw, kor, prawda, R, daty = [], [], [], [], []
    for p, x in zip(w, w[1:], strict=False):
        r = rm[x]
        naiw.append(sum(L * (L - 1) * dane[t][p]["aum"] for t, L in FUNDUSZE.items()))
        kor.append(sum(L * (L - 1) * dane[t][p]["aum"] * (1 + L * r)
                       for t, L in FUNDUSZE.items()))
        prawda.append(sum(L * (L - 1) * dane[t][x]["aum"] for t, L in FUNDUSZE.items()))
        R.append(r)
        daty.append(x)
    naiw, kor, prawda, R = (np.array(v) for v in (naiw, kor, prawda, R))

    print("\n=== 4. Blad estymatora point-in-time ===")
    for nazwa, K in (("naiwny (A z t-1)", naiw), ("skorygowany o efekt NAV", kor)):
        b = (prawda - K) / K
        print(f"  {nazwa:26s} mediana|b|={100 * np.median(np.abs(b)):5.2f}%  "
              f"p90={100 * np.percentile(np.abs(b), 90):5.2f}%  "
              f"corr(b,r)={np.corrcoef(b, R)[0, 1]:+.3f}")

    print("\n=== 5. FALSYFIKATOR: czy ΔE da sie odroznic od B04 ===")
    adv = np.array([am[d] for d in daty])
    kontrola = np.c_[R, np.abs(R), R ** 2, np.sign(R)]
    for nazwa, Y in (("ΔE surowe", kor * R), ("ΔE / ADV", kor * R / adv)):
        print(f"  {nazwa}")
        vify = []
        for rok in sorted({d.year for d in daty}):
            m = np.array([i for i, d in enumerate(daty) if d.year == rok])
            if len(m) < 50:
                continue
            v = _r2(Y[m], kontrola[m])
            vif = 1 / max(1 - v, 1e-9)
            vify.append(vif)
            print(f"     {rok}: R²={v:.4f}  VIF={vif:6.1f}  SE x{np.sqrt(vif):.1f}")
        v = _r2(Y, kontrola)
        print(f"     cala proba: R²={v:.4f}  VIF={1 / (1 - v):.1f}")
        print(f"     sredni VIF wewnatrz roku: {np.mean(vify):.1f} -> "
              f"efektywne N przy celu 400: {400 / np.mean(vify):.0f}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
