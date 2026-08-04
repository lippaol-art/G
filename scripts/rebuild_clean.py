#!/usr/bin/env python3
"""Kontrolowana przebudowa `data/clean/` po naprawie kalendarza CME.

PO CO OSOBNY SKRYPT, SKORO ISTNIEJE `make_clean.py`.
Bo tu chodzi nie o zbudowanie danych, tylko o UDOWODNIENIE, ze zmienilo sie
dokladnie to, co mialo sie zmienic — i o odmowe podmiany w przeciwnym razie.
`make_clean.py` nadpisuje pliki bez porownania z poprzednia wersja.

PROCEDURA (zatwierdzona przez wlasciciela projektu):
  1. buduj z tych samych plikow `data/raw/` do katalogu TYMCZASOWEGO,
  2. porownaj stary i nowy zbior kolumna po kolumnie,
  3. podmien `data/clean/` ATOMOWO dopiero po zgodzie z zakresem zmian.

ZAKRES DOZWOLONYCH ZMIAN — poza nim skrypt PRZERYWA:
  * `short_day`  : wylacznie False -> True,
  * `gap_kind`   : wylacznie "anomaly" -> "expected".

ZABRONIONE: liczba wierszy, znaczniki czasu, OHLC, wolumen, `px_raw`, `px_adj`,
`trade_date`, `segment`, `contract`, `days_to_roll`, `halt_window`,
`dst_transition`, `data_condition`.

Uruchomienie:
    python3 scripts/rebuild_clean.py            # tylko porownanie (sucho)
    python3 scripts/rebuild_clean.py --zastosuj # porownanie + podmiana
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.dataset import build_continuous, load_degraded_days  # noqa: E402
from scripts.make_clean import normalize_databento, read_raw_chunks  # noqa: E402

CLEAN = Path("data/clean")
SYMBOLE = (("MNQ", "mnq_1m_cont"), ("NQ", "nq_1m_cont"), ("ES", "es_1m_cont"))

#: Kolumny, ktorym WOLNO sie zmienic, wraz z jedynym dozwolonym kierunkiem.
DOZWOLONE = {
    "short_day": "False -> True",
    "gap_kind": "anomaly -> expected",
}
#: Kolumny, ktorych zmiana jest bledem — lista jawna, nie "wszystko inne",
#: zeby dopisanie kolumny do schematu nie osunelo kontroli po cichu.
ZABRONIONE = (
    "ts_utc", "open", "high", "low", "close", "volume", "contract",
    "trade_date", "segment", "px_raw", "px_adj", "halt_window",
    "days_to_roll", "dst_transition", "data_condition",
)


def zbuduj(symbol: str) -> pl.DataFrame:
    raw = read_raw_chunks(symbol, "ohlcv-1m")
    df, _ = build_continuous(normalize_databento(raw),
                             degraded_days=load_degraded_days())
    return df.drop("et_hour") if "et_hour" in df.columns else df


def porownaj(stary: pl.DataFrame, nowy: pl.DataFrame, sym: str) -> dict:
    """Zwraca raport roznic albo przerywa, gdy zmiana wyszla poza zakres."""
    bledy: list[str] = []
    if stary.height != nowy.height:
        bledy.append(f"liczba wierszy {stary.height:,} -> {nowy.height:,}")
    if set(stary.columns) != set(nowy.columns):
        bledy.append(f"zmiana zestawu kolumn: {set(nowy.columns) ^ set(stary.columns)}")
    if bledy:
        sys.exit(f"STOP [{sym}]: " + "; ".join(bledy))

    raport: dict[str, object] = {"symbol": sym, "wierszy": stary.height}

    for kol in ZABRONIONE:
        roznych = int((stary[kol] != nowy[kol]).sum())
        if roznych:
            sys.exit(f"STOP [{sym}]: kolumna ZABRONIONA `{kol}` ma {roznych:,} "
                     "roznic — przebudowa NIE zostanie zastosowana")
    raport["kolumny_zabronione_bez_zmian"] = list(ZABRONIONE)

    # short_day — wylacznie False -> True
    sd_st, sd_no = stary["short_day"], nowy["short_day"]
    zmiany_sd = int((sd_st != sd_no).sum())
    zle_sd = int((sd_st & ~sd_no).sum())
    if zle_sd:
        sys.exit(f"STOP [{sym}]: short_day True -> False w {zle_sd:,} wierszach")
    raport["short_day_false_na_true"] = zmiany_sd
    raport["short_day_dni"] = int(
        stary.with_columns(nowy["short_day"].alias("_n"))
        .filter(pl.col("short_day") != pl.col("_n"))["trade_date"].n_unique())

    # gap_kind — wylacznie anomaly -> expected
    gk = stary.select("gap_kind").with_columns(nowy["gap_kind"].alias("nowy"))
    zmiany_gk = gk.filter(pl.col("gap_kind") != pl.col("nowy"))
    kierunki = (zmiany_gk.group_by(["gap_kind", "nowy"]).len()
                .sort("len", descending=True).to_dicts())
    zle_gk = [k for k in kierunki
              if not (k["gap_kind"] == "anomaly" and k["nowy"] == "expected")]
    if zle_gk:
        sys.exit(f"STOP [{sym}]: gap_kind zmienil sie inaczej niz "
                 f"anomaly->expected: {zle_gk}")
    raport["gap_kind_anomaly_na_expected"] = zmiany_gk.height
    raport["gap_kind_kierunki"] = kierunki
    return raport


def main() -> int:
    p = argparse.ArgumentParser(description="Kontrolowana przebudowa data/clean/")
    p.add_argument("--zastosuj", action="store_true",
                   help="podmien pliki po pomyslnym porownaniu")
    args = p.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="clean_rebuild_"))
    print(f"katalog tymczasowy: {tmp}\n")
    raporty, sciezki = [], []

    for sym, plik in SYMBOLE:
        print(f"=== {sym} ===", flush=True)
        nowy = zbuduj(sym)
        stary = pl.read_parquet(CLEAN / f"{plik}.parquet")
        r = porownaj(stary, nowy, sym)

        out = tmp / f"{plik}.parquet"
        nowy.write_parquet(out, compression="zstd", compression_level=19)
        r["sha256_stary"] = hashlib.sha256(
            (CLEAN / f"{plik}.parquet").read_bytes()).hexdigest()
        r["sha256_nowy"] = hashlib.sha256(out.read_bytes()).hexdigest()
        r["plik"] = f"{plik}.parquet"
        raporty.append(r)
        sciezki.append((out, CLEAN / f"{plik}.parquet"))
        print(f"  wierszy {r['wierszy']:,}  short_day +{r['short_day_false_na_true']:,} "
              f"({r['short_day_dni']} dni)  gap_kind {r['gap_kind_anomaly_na_expected']}"
              f"  kolumny zabronione: 0 roznic\n", flush=True)

    print("=" * 64)
    print("  WSZYSTKIE ZMIANY W ZATWIERDZONYM ZAKRESIE")
    print("=" * 64)

    if not args.zastosuj:
        print("\nTryb suchy — nic nie podmieniono. Uruchom z --zastosuj.")
        return 0

    # PODMIANA ATOMOWA: `os.replace` w obrebie tego samego systemu plikow jest
    # niepodzielne, wiec nie da sie zostawic pliku w polowie zapisany.
    for zrodlo, cel in sciezki:
        obok = cel.with_suffix(".parquet.nowy")
        shutil.copy2(zrodlo, obok)
        os.replace(obok, cel)
        print(f"  podmieniono {cel}")

    Path("reports").mkdir(exist_ok=True)
    Path("reports/przebudowa_clean.json").write_text(
        json.dumps({"zakres_dozwolony": DOZWOLONE, "symbole": raporty},
                   indent=1, default=str), encoding="utf-8")
    print("\n-> reports/przebudowa_clean.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
