#!/usr/bin/env python3
"""Sanity-report danych — PLAN.pdf rozdz. 4.6.

Generuje reports/data_quality.md. Uruchamiac po KAZDEJ regeneracji data/clean/.

NAJWAZNIEJSZA ZASADA (rozdz. 4.2):
    Liczba barow na dzien NIE jest stala i brak bara NIE jest defektem.
    Databento nie drukuje bara, gdy w minucie nie bylo transakcji. Dlatego
    raport rozbija liczby PER SEGMENT (oczekiwana gestosc zalezy od plynnosci)
    i klasyfikuje kazda luke, zamiast porownywac do sztywnego progu ~1380/dzien.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.loader import REQUIRED_COLUMNS, clean_path  # noqa: E402

REPORTS = Path("reports")


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while blok := f.read(chunk):
            h.update(blok)
    return h.hexdigest()


def _sekcja_segmenty(df: pl.DataFrame) -> str:
    agg = (
        df.group_by("segment")
        .agg([
            pl.len().alias("barow"),
            pl.col("volume").sum().alias("wolumen"),
            (pl.col("volume") == 0).sum().alias("zerowy_wolumen"),
        ])
        .sort("barow", descending=True)
    )
    dni = df["trade_date"].n_unique()
    linie = ["| Segment | Barów | Barów/dzień | Wolumen | Bary o wol. 0 |",
             "|---|---:|---:|---:|---:|"]
    for r in agg.iter_rows(named=True):
        na_dzien = r["barow"] / dni if dni else 0
        linie.append(
            f"| {r['segment']} | {r['barow']:,} | {na_dzien:.0f} | "
            f"{r['wolumen']:,} | {r['zerowy_wolumen']:,} |"
        )
    return "\n".join(linie)


def _sekcja_lata(df: pl.DataFrame) -> str:
    agg = (
        df.with_columns(pl.col("trade_date").dt.year().alias("rok"))
        .group_by("rok")
        .agg([pl.len().alias("barow"), pl.col("trade_date").n_unique().alias("dni")])
        .sort("rok")
    )
    linie = ["| Rok | Barów | Dni sesyjnych | Barów/dzień |", "|---|---:|---:|---:|"]
    for r in agg.iter_rows(named=True):
        linie.append(f"| {r['rok']} | {r['barow']:,} | {r['dni']:,} | "
                     f"{r['barow'] / max(r['dni'], 1):.0f} |")
    return "\n".join(linie)


def _sekcja_luki(df: pl.DataFrame) -> str:
    zliczenia = df.group_by("gap_kind").agg(pl.len().alias("n")).sort("n", descending=True)
    linie = ["| Rodzaj luki | Liczba |", "|---|---:|"]
    for r in zliczenia.iter_rows(named=True):
        linie.append(f"| `{r['gap_kind']}` | {r['n']:,} |")

    anomalie = df.filter(pl.col("gap_kind") == "anomaly")
    if anomalie.height:
        linie += ["", f"**Anomalii do przejrzenia: {anomalie.height}**", "",
                  "| Znacznik czasu | Segment | Dzień sesyjny |", "|---|---|---|"]
        for r in anomalie.head(25).iter_rows(named=True):
            linie.append(f"| {r['ts_utc']} | {r['segment']} | {r['trade_date']} |")
        if anomalie.height > 25:
            linie.append(f"| … | *(jeszcze {anomalie.height - 25})* | |")
    else:
        linie += ["", "**Brak anomalii — wszystkie luki wyjaśnione kalendarzem.**"]
    return "\n".join(linie)


def _sekcja_rolowania(df: pl.DataFrame) -> str:
    kontrakty = (
        df.group_by("contract")
        .agg([
            pl.col("trade_date").min().alias("od"),
            pl.col("trade_date").max().alias("do"),
            pl.len().alias("barow"),
        ])
        .sort("od")
    )
    linie = [f"Kontraktów w serii ciągłej: **{kontrakty.height}**", "",
             "| Kontrakt | Od | Do | Barów |", "|---|---|---|---:|"]
    for r in kontrakty.iter_rows(named=True):
        linie.append(f"| {r['contract']} | {r['od']} | {r['do']} | {r['barow']:,} |")

    rozjazd = df.filter(pl.col("px_raw") != pl.col("px_adj")).height
    linie += ["", f"Barów z niezerowym przesunięciem back-adjustu: **{rozjazd:,}** "
                  f"({100 * rozjazd / max(df.height, 1):.1f}%)"]
    if rozjazd == 0 and kontrakty.height > 1:
        linie.append("\n⚠️ **Wiele kontraktów, ale zero przesunięć — back-adjust nie zadziałał.**")
    return "\n".join(linie)


def _sekcja_outliery(df: pl.DataFrame) -> str:
    d = df.with_columns(
        ((pl.col("high") - pl.col("low")) / pl.col("close").abs()).alias("zakres_wzgl")
    )
    out = d.filter(pl.col("zakres_wzgl") > 0.005).sort("zakres_wzgl", descending=True)
    linie = [f"Barów o zakresie > 0.5% w jednej minucie: **{out.height:,}** "
             f"({100 * out.height / max(df.height, 1):.3f}%)"]
    if out.height:
        linie += ["", "Dziesięć skrajnych:", "",
                  "| Znacznik | Zakres | Segment |", "|---|---:|---|"]
        for r in out.head(10).iter_rows(named=True):
            linie.append(f"| {r['ts_utc']} | {100 * r['zakres_wzgl']:.2f}% | {r['segment']} |")
    return "\n".join(linie)


def build_report(symbol: str, timeframe: str = "1m") -> str:
    path = clean_path(symbol, timeframe)
    if not path.exists():
        sys.exit(f"BLAD: brak {path}. Najpierw uruchom scripts/build_dataset.py "
                 "(procedura w HANDOFF.md).")

    df = pl.read_parquet(path)
    brakuje = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if brakuje:
        sys.exit(f"BLAD: plik nie spelnia schematu, brak kolumn: {brakuje}")

    czesci = [
        f"# Sanity-report danych — {symbol.upper()} {timeframe}",
        "",
        f"Wygenerowano: {datetime.now().isoformat(timespec='seconds')}  ",
        f"Plik: `{path}`  ",
        f"SHA-256: `{sha256_of(path)}`  ",
        f"Rozmiar: {path.stat().st_size / 1e6:.1f} MB",
        "",
        "## Podstawowe liczby",
        "",
        f"- Barów: **{df.height:,}**",
        f"- Zakres: **{df['ts_utc'].min()}** → **{df['ts_utc'].max()}**",
        f"- Dni sesyjnych: **{df['trade_date'].n_unique():,}**",
        f"- Barów o zerowym wolumenie: **{df.filter(pl.col('volume') == 0).height:,}**",
        "",
        "## Gęstość per segment doby",
        "",
        "Oczekiwana liczba barów zależy od płynności segmentu — brak bara w cienkiej",
        "godzinie sesji azjatyckiej jest normą, nie defektem (rozdz. 4.2).",
        "",
        _sekcja_segmenty(df),
        "",
        "## Pokrycie w czasie",
        "",
        _sekcja_lata(df),
        "",
        "## Klasyfikacja luk",
        "",
        _sekcja_luki(df),
        "",
        "## Rolowania i back-adjust",
        "",
        _sekcja_rolowania(df),
        "",
        "## Outliery zakresu",
        "",
        _sekcja_outliery(df),
        "",
        "---",
        "",
        "*Raport generowany przez `scripts/data_quality.py` wg specyfikacji PLAN.pdf rozdz. 4.6.*",
    ]
    return "\n".join(czesci)


def main() -> int:
    p = argparse.ArgumentParser(description="Sanity-report oczyszczonych danych")
    p.add_argument("--symbol", default="MNQ")
    p.add_argument("--timeframe", default="1m")
    args = p.parse_args()

    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"data_quality_{args.symbol.lower()}.md"
    out.write_text(build_report(args.symbol, args.timeframe), encoding="utf-8")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
