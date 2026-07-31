#!/usr/bin/env python3
"""Budowa data/clean/ z pobranych plikow data/raw/ — PLAN.pdf rozdz. 4.2.

Laczy odcinki roczne, przepuszcza przez pipeline `engine.dataset.build_continuous`
i zapisuje parquet o schemacie wymaganym przez `engine.loader`.

Wpis do data/manifest.md jest OBOWIAZKOWY (rozdz. 4.1): dostawca zmienil
normalizacje GLBX.MDP3 w lipcu 2026, wiec bez przypietej daty pobrania i sumy
kontrolnej nie odtworzymy pozniej, na czym liczone byly wyniki.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.dataset import build_continuous, load_degraded_days, normalize_databento  # noqa: E402
from engine.loader import clean_path  # noqa: E402

RAW = Path("data/raw")
CLEAN = Path("data/clean")
MANIFEST = Path("data/manifest.md")


def read_raw_chunks(symbol: str, schema: str = "ohlcv-1m") -> pl.DataFrame:
    """Wczytuje wszystkie odcinki roczne symbolu i skleja w jeden DataFrame."""
    import databento as db

    pliki = sorted(RAW.glob(f"{symbol.lower()}_{schema}_*.dbn.zst"))
    if not pliki:
        sys.exit(f"BLAD: brak plikow {symbol} w {RAW}. Uruchom scripts/build_dataset.py")

    czesci = []
    for p in pliki:
        pdf = db.DBNStore.from_file(p).to_df()
        pdf = pdf.reset_index()          # ts_event z indeksu do kolumny
        czesci.append(pl.from_pandas(pdf))
        print(f"  {p.name}: {len(pdf):,} rekordow")

    return pl.concat(czesci, how="diagonal_relaxed")


def append_manifest(symbol: str, path: Path, rep, sha: str) -> None:
    naglowek = "" if MANIFEST.exists() else (
        "# Manifest danych\n\n"
        "Kazda regeneracja `data/clean/` dopisuje wpis. Wersja schematu i data\n"
        "pobrania sa PRZYPIETE — dostawca zmienil normalizacje GLBX.MDP3 w lipcu\n"
        "2026, wiec bez tego nie odtworzymy, na czym liczone byly wyniki.\n"
    )
    wpis = f"""
---

## {symbol.upper()} {datetime.now().isoformat(timespec='seconds')}

| Pole | Wartosc |
|---|---|
| Plik | `{path}` |
| SHA-256 | `{sha}` |
| Rozmiar | {path.stat().st_size / 1e6:.1f} MB |
| Dataset | GLBX.MDP3, schema ohlcv-1m, stype_in=parent |
| Zakres | {rep.first_ts} -> {rep.last_ts} |
| Barow surowych | {rep.n_raw:,} |
| Po deduplikacji | {rep.n_after_dedup:,} |
| Barow koncowo | {rep.n_final:,} |
| Kontraktow | {rep.n_contracts} |
| Rolowan | {len(rep.roll_events)} |
| Naruszen OHLC (odrzucone) | {rep.ohlc_violations} |
| Ujemny wolumen (odrzucone) | {rep.negative_volume} |
| Barow o zerowym wolumenie | {rep.zero_volume_bars:,} |
| Barow w dniach degraded | {rep.degraded_bars:,} |
| Luk oczekiwanych | {rep.expected_gaps:,} |
| **Luk anomalnych** | **{len(rep.anomaly_gaps):,}** |

### Rolowania
"""
    linie = [f"- {e.roll_date}: {e.from_contract} -> {e.to_contract} (spread {e.spread:+.2f})"
             for e in rep.roll_events]
    tresc = naglowek + wpis + "\n".join(linie) + "\n"
    with MANIFEST.open("a", encoding="utf-8") as f:
        f.write(tresc)


def main() -> int:
    p = argparse.ArgumentParser(description="Budowa data/clean/ z data/raw/")
    p.add_argument("--symbol", default="MNQ")
    p.add_argument("--schema", default="ohlcv-1m")
    args = p.parse_args()

    print(f"Wczytywanie odcinkow {args.symbol}...")
    raw = read_raw_chunks(args.symbol, args.schema)
    print(f"  razem: {raw.height:,} rekordow surowych")

    print("Normalizacja (filtr spreadow, jednostki cen)...")
    norm = normalize_databento(raw)
    print(f"  po odfiltrowaniu spreadow: {norm.height:,} ({raw.height - norm.height:,} usunietych)")

    print("Budowa kontraktu ciaglego...")
    df, rep = build_continuous(norm, degraded_days=load_degraded_days())
    print(f"  {rep.summary()}")

    CLEAN.mkdir(parents=True, exist_ok=True)
    out = clean_path(args.symbol, "1m")
    # Poziom 19 zamiast domyslnego: 47.8 -> 35.2 MB na MNQ (-26%) bez zmiany
    # danych. Ma znaczenie, bo parquet trafia do historii gita przy KAZDEJ
    # regeneracji. Zmierzone alternatywy: wezsze typy nie daja nic (kompresja
    # juz to lapie), ceny jako Int32 w tickach sa GORSZE (39.9 MB).
    df = df.drop("et_hour") if "et_hour" in df.columns else df
    df.write_parquet(out, compression="zstd", compression_level=19)

    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"\n-> {out} ({out.stat().st_size / 1e6:.1f} MB)")
    print(f"   SHA-256: {sha[:32]}...")

    append_manifest(args.symbol, out, rep, sha)
    print(f"-> wpis dopisany do {MANIFEST}")

    if rep.anomaly_gaps:
        print(f"\n⚠ Luk anomalnych: {len(rep.anomaly_gaps)} — przejrzyj sanity-report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
