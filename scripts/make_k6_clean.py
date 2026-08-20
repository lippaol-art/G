#!/usr/bin/env python3
"""Budowa data/clean/k6_equities.parquet — PLAN.pdf rozdz. 4.7.

Odpowiednik `scripts/make_clean.py` dla warstwy akcyjnej. Cztery kroki, z ktorych
dwa srodkowe nie maja odpowiednika po stronie kontraktow terminowych:

  1. sklejenie odcinkow rocznych,
  2. SKLEJENIE TICKEROW po dacie — FB przed 2022-06-09, META od tej daty; ten
     sam symbol "FB" wystepuje takze w latach 2025-2026 i nalezy juz do INNEJ
     spolki (patrz `engine.equities.nalezy_do_szeregu`),
  3. WYKRYCIE I KOREKTA SPLITOW — z raportem kazdego kandydata, takze
     odrzuconego, bo korekta ma byc audytowalna,
  4. segmenty doby gieldowej i zapis parquet.

Wyjscie:
  data/clean/k6_equities.parquet
  reports/k6_data_quality.md
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.equities import (  # noqa: E402
    POPRZEDNIE_TICKERY,
    nalezy_do_szeregu,
    segment_akcji,
    skoryguj_ceny,
)

RAW = Path("data/raw")
#: PARTYCJONOWANIE PER SYMBOL, nie jeden plik. Powod jest twardy: pelny zbior
#: wazy 179 MB, a GitHub odrzuca pojedyncze pliki powyzej 100 MB — push
#: zakonczylby sie bledem po przeslaniu calosci. Partycje po symbolu daja
#: 11-22 MB kazda i przy okazji pozwalaja wczytac jedna spolke bez czytania
#: dziesieciu.
WYJSCIE_KAT = Path("data/clean/k6")
RAPORT = Path("reports/k6_data_quality.md")
GRUPY = ("mega", "fb", "qqq", "soxx")


def wczytaj_grupe(nazwa: str) -> pl.DataFrame | None:
    import databento as db

    pliki = sorted(RAW.glob(f"k6_{nazwa}_ohlcv-1m_*.dbn.zst"))
    if not pliki:
        return None
    czesci = []
    for p in pliki:
        pdf = db.DBNStore.from_file(p).to_df()
        if pdf.empty:
            continue
        czesci.append(pl.from_pandas(pdf.reset_index()))
    if not czesci:
        return None
    return pl.concat(czesci, how="diagonal_relaxed").select(
        ["ts_event", "symbol", "open", "high", "low", "close", "volume"]
    )


def main() -> int:
    czesci = []
    for g in GRUPY:
        df = wczytaj_grupe(g)
        if df is None:
            print(f"  {g}: brak plikow, pomijam")
            continue
        print(f"  {g}: {df.height:,} rekordow, symbole {sorted(df['symbol'].unique())}")
        czesci.append(df)
    if not czesci:
        sys.exit("BLAD: brak danych K6 w data/raw. Uruchom scripts/build_k6.py")

    df = pl.concat(czesci, how="diagonal_relaxed")
    df = df.with_columns(
        pl.col("ts_event").dt.convert_time_zone("America/New_York").alias("et")
    ).with_columns([
        pl.col("et").dt.date().alias("trade_date"),
        pl.col("et").dt.hour().alias("et_h"),
        pl.col("et").dt.minute().alias("et_m"),
    ])

    # --- krok 2: sklejenie tickerow po dacie
    przed = df.height
    docelowe = {stary: nowy for nowy, (stary, _) in POPRZEDNIE_TICKERY.items()}
    maski = []
    for sym in sorted(df["symbol"].unique()):
        cel = docelowe.get(sym, sym)
        maski.append((sym, cel))
    zachowaj = []
    for sym, cel in maski:
        czesc = df.filter(pl.col("symbol") == sym)
        if sym == cel and cel not in POPRZEDNIE_TICKERY:
            zachowaj.append(czesc.with_columns(pl.lit(cel).alias("symbol")))
            continue
        dni = czesc["trade_date"].to_list()
        ok = np.array([nalezy_do_szeregu(cel, sym, d) for d in dni])
        odrzucone = int((~ok).sum())
        if odrzucone:
            print(f"  {sym} -> {cel}: odrzucono {odrzucone:,} rekordow poza zakresem dat")
        zachowaj.append(czesc.filter(pl.Series(ok)).with_columns(pl.lit(cel).alias("symbol")))
    df = pl.concat(zachowaj, how="diagonal_relaxed").sort(["symbol", "ts_event"])
    print(f"  po sklejeniu tickerow: {df.height:,} ({przed - df.height:,} odrzuconych)")

    # --- krok 3: splity, per symbol, na dziennym zamknieciu RTH
    df = df.with_columns(
        pl.struct(["et_h", "et_m"]).map_elements(
            lambda s: segment_akcji(s["et_h"], s["et_m"]), return_dtype=pl.String
        ).alias("segment")
    )
    raporty = {}
    skorygowane = []
    for sym in sorted(df["symbol"].unique()):
        czesc = df.filter(pl.col("symbol") == sym).sort("ts_event")
        dzienne = (czesc.filter(pl.col("segment") == "rth")
                        .group_by("trade_date")
                        .agg(c=pl.col("close").last(), v=pl.col("volume").sum())
                        .sort("trade_date"))
        rep = None
        if dzienne.height > 20:
            _, _, rep = skoryguj_ceny(
                dzienne["trade_date"].to_list(),
                dzienne["c"].to_numpy(), dzienne["v"].to_numpy(), symbol=sym,
            )
            raporty[sym] = rep
        mnoznik = np.ones(czesc.height)
        if rep is not None:
            for k in rep.przyjete:
                if k.wspolczynnik is None:
                    continue
                maska = np.array([d < k.dzien for d in czesc["trade_date"].to_list()])
                mnoznik[maska] *= k.wspolczynnik
        skorygowane.append(czesc.with_columns([
            (pl.col("open") / pl.Series(mnoznik)).alias("open"),
            (pl.col("high") / pl.Series(mnoznik)).alias("high"),
            (pl.col("low") / pl.Series(mnoznik)).alias("low"),
            (pl.col("close") / pl.Series(mnoznik)).alias("close"),
            (pl.col("volume") * pl.Series(mnoznik)).cast(pl.Float64).alias("volume"),
            pl.Series(mnoznik).alias("split_factor"),
        ]))
    df = pl.concat(skorygowane, how="diagonal_relaxed").sort(["symbol", "ts_event"])

    out = df.select([
        pl.col("ts_event").alias("ts_utc"), "symbol", "open", "high", "low", "close",
        "volume", "trade_date", "segment", "split_factor",
    ])
    WYJSCIE_KAT.mkdir(parents=True, exist_ok=True)
    laczny_rozmiar = 0
    for sym in sorted(out["symbol"].unique()):
        cel = WYJSCIE_KAT / f"{sym.lower()}_1m.parquet"
        out.filter(pl.col("symbol") == sym).write_parquet(
            cel, compression="zstd", compression_level=19)
        laczny_rozmiar += cel.stat().st_size
        if cel.stat().st_size > 90e6:
            sys.exit(f"BLAD: {cel} ma {cel.stat().st_size/1e6:.0f} MB — powyzej 90 MB "
                     "plik nie przejdzie przez limit GitHuba (100 MB).")
    print(f"\n-> {WYJSCIE_KAT}/ ({laczny_rozmiar / 1e6:.1f} MB w "
          f"{out['symbol'].n_unique()} plikach, {out.height:,} barow)")

    # --- raport jakosci
    L = [
        "# Warstwa K6 — kontrola jakosci",
        "",
        f"*Wygenerowane przez `scripts/make_k6_clean.py`, "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}.*",
        "",
        f"Barow M1: **{out.height:,}**, symboli: {out['symbol'].n_unique()}, "
        f"zakres {out['trade_date'].min()} -> {out['trade_date'].max()}",
        "",
        "## Splity — kazdy kandydat, takze odrzucony",
        "",
        "Detektor wymaga DWOCH warunkow naraz: wspolczynnik ceny bliski prostemu",
        "ulamkowi ORAZ wolumen skalujacy sie tym samym czynnikiem. Krach po wynikach",
        "spelnia pierwszy, ale nie drugi — i wlasnie dlatego nie jest korygowany.",
        "",
        "| Symbol | Dzien | Cena x | Wolumen x | Wspolczynnik | Werdykt |",
        "|---|---|---|---|---|---|",
    ]
    n_przyjete = n_odrzucone = 0
    for sym in sorted(raporty):
        for k in raporty[sym].kandydaci:
            w = f"{k.wspolczynnik:.3f}" if k.wspolczynnik else "—"
            werdykt = "**SPLIT**" if k.przyjety else f"ruch rynku ({k.powod[:40]})"
            L.append(f"| {sym} | {k.dzien} | {k.stosunek_ceny:.3f} | "
                     f"{k.stosunek_wolumenu:.2f} | {w} | {werdykt} |")
            n_przyjete += k.przyjety
            n_odrzucone += not k.przyjety
    L += [
        "",
        f"Przyjetych jako splity: **{n_przyjete}**, odrzuconych jako ruch rynku: "
        f"**{n_odrzucone}**.",
        "",
        "## Sklejenie tickerow — co zostalo odrzucone i dlaczego",
        "",
        "Symbol nie identyfikuje spolki jednoznacznie w czasie. Odciecie po dacie",
        "jest obustronne, bo zanieczyszczenie idzie z obu stron:",
        "",
        "| Zrodlo | Okres | Ceny | Werdykt |",
        "|---|---|---|---|",
        "| FB | 2019-05 → 2022-06-08 | jak Facebook | **przyjete** jako historia META |",
        "| FB | 2025-2026 (470 rekordow) | inna spolka | odrzucone |",
        "| META | 2021-06-30 → 2022-01-28 (38 920 rekordow) | **11.73-17.17 USD** | odrzucone |",
        "| META | od 2022-06-09 | jak Meta Platforms | **przyjete** |",
        "",
        "Wiersz trzeci jest najgrozniejszy: symbol META istnial PRZED przejeciem go",
        "przez Meta Platforms i nalezal do spolki notowanej po ~15 USD, podczas gdy",
        "Facebook kosztowal wtedy 300-380 USD. Wszystkie 147 dni tych notowan pokrywa",
        "sie z dniami, dla ktorych mamy juz FB. Sklejenie po samej nazwie dolozyloby",
        "dzienne zwroty rzedu +/-95% i zatrulo sume wazona skladnikow indeksu.",
        "",
        "## Pokrycie per symbol",
        "",
        "| Symbol | Barow | Dni | Pierwszy | Ostatni |",
        "|---|---|---|---|---|",
    ]
    for sym in sorted(out["symbol"].unique()):
        c = out.filter(pl.col("symbol") == sym)
        L.append(f"| {sym} | {c.height:,} | {c['trade_date'].n_unique():,} | "
                 f"{c['trade_date'].min()} | {c['trade_date'].max()} |")
    L += ["", "Odtworzenie: `python3 scripts/make_k6_clean.py`"]
    RAPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPORT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"-> {RAPORT}  (splity: {n_przyjete} przyjete, {n_odrzucone} odrzucone)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
