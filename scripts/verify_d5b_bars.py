#!/usr/bin/env python3
"""D5-B §10 — rekonstrukcja `ohlcv-1m` dla CALEGO miesiaca i porownanie.

Specyfikacja zamrozona `docs/D5_ETAP2_SPEC.md` §10 wymaga, zeby **kazda
niezgodnosc byla wyjasniona PRZED liczeniem VIF**. Ten skrypt jest ta bramka:
audytu identyfikowalnosci nie wolno traktowac jako wyniku, dopoki ta kontrola
nie przejdzie albo dopoki kazde odchylenie nie ma wyjasnienia zapisanego
w raporcie.

Kontrolujemy trzy rzeczy:
  1. brak duplikatow zakresow miedzy plikami sesji (w tym granica z 2026-07-30),
  2. rekonstrukcja O/H/L/C/V z wypelnien vs bary dostawcy, minuta po minucie,
  3. pokrycie: czy kazda minuta RTH ma odpowiednik po obu stronach.

Agregacja po `ts_recv` — ustalenie Etapu 1, patrz `scripts/audit_d5_etap1.py`.

Uruchomienie:
    python3 scripts/verify_d5b_bars.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import polars as pl

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
KAT = Path("data/raw/d5b_rth")
PLIK_0730 = Path("data/raw/mnq_trades_2026-07-30.dbn.zst")
BARY = Path("data/clean/mnq_1m_cont.parquet")


def granice_rth(sesja: str) -> tuple[dt.datetime, dt.datetime]:
    """RTH WYPROWADZONE ZE STREFY ET — nigdy ze stalej UTC."""
    y, m, d = map(int, sesja.split("-"))
    return (dt.datetime(y, m, d, 9, 30, tzinfo=ET).astimezone(UTC),
            dt.datetime(y, m, d, 16, 0, tzinfo=ET).astimezone(UTC))


def wczytaj(p: Path) -> pl.DataFrame:
    import databento as db
    return pl.from_pandas(db.DBNStore.from_file(p).to_df().reset_index())


def rekonstruuj(d: pl.DataFrame) -> pl.DataFrame:
    """Bary M1 z wypelnien. SORTOWANIE PRZED GRUPOWANIEM jest konieczne —
    `first()`/`last()` biora kolejnosc z ramki, nie z czasu."""
    return (
        d.sort(["ts_recv", "sequence"])
        .with_columns(pl.col("ts_recv").dt.truncate("1m").alias("ts_utc"))
        .group_by("ts_utc")
        .agg([
            pl.col("price").first().alias("r_open"),
            pl.col("price").max().alias("r_high"),
            pl.col("price").min().alias("r_low"),
            pl.col("price").last().alias("r_close"),
            pl.col("size").sum().cast(pl.Int64).alias("r_volume"),
        ])
        .sort("ts_utc")
    )


def main() -> int:
    sesje = sorted(p.name.split("_")[-1].removesuffix(".dbn.zst")
                   for p in KAT.glob("*.dbn.zst"))
    sesje.append("2026-07-30")
    sesje.sort()

    nasze = (
        pl.read_parquet(BARY)
        .filter(pl.col("contract") == "MNQU6")
        .select("ts_utc", "open", "high", "low", "close", "volume")
        .with_columns(pl.col("volume").cast(pl.Int64))
    )

    print(f"=== D5-B §10: rekonstrukcja ohlcv-1m, {len(sesje)} sesji RTH ===\n")
    zakresy: list[tuple[str, int, int]] = []
    wiersze, niezgodne_wiersze = [], []

    for s in sesje:
        a, b = granice_rth(s)
        p = PLIK_0730 if s == "2026-07-30" else KAT / f"mnq_trades_rth_{s}.dbn.zst"
        d = wczytaj(p)
        if s == "2026-07-30":                       # pelna doba -> tnij do RTH
            d = d.filter((pl.col("ts_recv") >= a) & (pl.col("ts_recv") < b))

        t0 = int(d["ts_recv"].min().timestamp())
        t1 = int(d["ts_recv"].max().timestamp())
        # 1. DUPLIKATY: zakresy roznych sesji nie moga sie przecinac.
        for s2, u0, u1 in zakresy:
            if t0 <= u1 and u0 <= t1:
                sys.exit(f"BLAD: zakresy {s} i {s2} przecinaja sie")
        zakresy.append((s, t0, t1))

        rek = rekonstruuj(d)
        odc = nasze.filter((pl.col("ts_utc") >= a) & (pl.col("ts_utc") < b))
        z = odc.join(rek, on="ts_utc", how="inner")

        d_o = (z["open"] - z["r_open"]).abs().to_numpy()
        d_h = (z["high"] - z["r_high"]).abs().to_numpy()
        d_l = (z["low"] - z["r_low"]).abs().to_numpy()
        d_c = (z["close"] - z["r_close"]).abs().to_numpy()
        d_v = (z["volume"] - z["r_volume"]).to_numpy()

        n = dict(
            sesja=s, barow_dostawcy=odc.height, barow_rekonstrukcji=rek.height,
            wspolnych=z.height,
            tylko_dostawca=odc.height - z.height,
            tylko_rekonstrukcja=rek.height - z.height,
            open=int((d_o > 1e-9).sum()), high=int((d_h > 1e-9).sum()),
            low=int((d_l > 1e-9).sum()), close=int((d_c > 1e-9).sum()),
            volume=int((d_v != 0).sum()),
            suma_roznic_wolumenu=int(d_v.sum()),
            max_roznica_wolumenu=int(np.abs(d_v).max()) if len(d_v) else 0,
        )
        wiersze.append(n)
        zle = n["open"] + n["high"] + n["low"] + n["close"] + n["volume"] \
            + n["tylko_dostawca"] + n["tylko_rekonstrukcja"]
        if zle:
            niezgodne_wiersze.append(n)
            # wypisz konkretne minuty — bez tego "wyjasnij niezgodnosc" jest puste
            zl = z.filter(
                ((pl.col("open") - pl.col("r_open")).abs() > 1e-9)
                | ((pl.col("high") - pl.col("r_high")).abs() > 1e-9)
                | ((pl.col("low") - pl.col("r_low")).abs() > 1e-9)
                | ((pl.col("close") - pl.col("r_close")).abs() > 1e-9)
                | (pl.col("volume") != pl.col("r_volume"))
            )
            n["minuty"] = [str(x) for x in zl["ts_utc"].to_list()[:20]]
        print(f"  {s}  bary {odc.height:>4}/{rek.height:<4} wsp {z.height:>4}  "
              f"niezg O{n['open']} H{n['high']} L{n['low']} C{n['close']} "
              f"V{n['volume']}  brak {n['tylko_dostawca']}/{n['tylko_rekonstrukcja']}",
              flush=True)

    suma = {k: sum(w[k] for w in wiersze) for k in
            ("wspolnych", "open", "high", "low", "close", "volume",
             "tylko_dostawca", "tylko_rekonstrukcja")}
    print("\n" + "=" * 64)
    print(f"  minut porownanych      : {suma['wspolnych']:,}")
    print(f"  niezgodnych open       : {suma['open']:,}")
    print(f"  niezgodnych high       : {suma['high']:,}")
    print(f"  niezgodnych low        : {suma['low']:,}")
    print(f"  niezgodnych close      : {suma['close']:,}")
    print(f"  niezgodnych volume     : {suma['volume']:,}")
    print(f"  minut tylko u dostawcy : {suma['tylko_dostawca']:,}")
    print(f"  minut tylko w rekonstr.: {suma['tylko_rekonstrukcja']:,}")
    czysto = all(v == 0 for k, v in suma.items() if k != "wspolnych")
    print(f"\n  {'ZGODNOSC PELNA' if czysto else 'SA NIEZGODNOSCI — WYJASNIJ PRZED VIF'}")
    print("=" * 64)

    Path("reports").mkdir(exist_ok=True)
    Path("reports/D5_etap2_bary.json").write_text(
        json.dumps({"zgodnosc_pelna": czysto, "sumy": suma,
                    "sesje": wiersze,
                    "zakresy_utc": [{"sesja": s, "od": t0, "do": t1}
                                    for s, t0, t1 in zakresy]},
                   indent=1, default=str),
        encoding="utf-8")
    return 0 if czysto else 1


if __name__ == "__main__":
    raise SystemExit(main())
