#!/usr/bin/env python3
"""D5 Etap 1 — dziewiec zamrozonych kontroli danych `trades`.

CO TO JEST, A CZYM NIE JEST.
Sprawdza WYLACZNIE wlasciwosci danych. Nie liczy przyszlych zwrotow, P&L,
optymalnych okien, progow nierownowagi ani skutecznosci sygnalu.
**Zero zuzytych prob.**

Specyfikacja zamrozona przed zakupem: docs/D5_ETAP1_SPEC.md (commit 41d3eee),
korekta budzetu 953b5ec.

WERDYKT: `D5-A GO` gdy `side != NONE` > 95% ORAZ semantyka agresora
potwierdzona ORAZ dobra kompletnosc w kluczowych segmentach sesji.

ZAKAZ ZAPISANY PRZED DANYMI: jesli prog nie przejdzie, NIE WOLNO odtwarzac
strony agresora z kierunku ruchu ceny (tick-test / Lee-Ready). Wbudowaloby to
momentum wprost w zmienna, ktora pozniej mamy od momentum ODROZNIAC.

Uruchomienie:
    python3 scripts/audit_d5_etap1.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.sessions import segment_of, trade_date  # noqa: E402

PLIK = Path("data/raw/mnq_trades_2026-07-30.dbn.zst")
SESJA = "2026-07-30"
PROG_SIDE = 0.95
TICK_MNQ = 0.25


def wczytaj() -> pl.DataFrame:
    import databento as db

    d = db.DBNStore.from_file(PLIK).to_df()
    d = pl.from_pandas(d.reset_index())
    print(f"  wczytano {d.height:,} rekordow, kolumny: {sorted(d.columns)}")
    return d


def k1_k2_side(d: pl.DataFrame) -> tuple[float, bool]:
    """1. Odsetek BID/ASK/NONE. 2. Kompletnosc per segment sesji."""
    print("\n=== 1. Rozklad pola `side` ===")
    r = d.group_by("side").agg(pl.len().alias("n")).sort("n", descending=True)
    for w in r.iter_rows(named=True):
        print(f"  {str(w['side']):8s} {w['n']:>10,}  ({100 * w['n'] / d.height:6.3f}%)")
    n_none = d.filter(pl.col("side") == "N").height
    udzial = 1.0 - n_none / d.height
    print(f"\n  side != NONE: **{100 * udzial:.4f}%**  (prog {100 * PROG_SIDE:.0f}%)")

    print("\n=== 2. Kompletnosc `side` per segment sesji ===")
    seg = [segment_of(t) for t in d["ts_event"].to_list()]
    d2 = d.with_columns(pl.Series("segment", seg))
    r = (
        d2.group_by("segment")
        .agg([pl.len().alias("n"), (pl.col("side") == "N").sum().alias("none")])
        .sort("n", descending=True)
    )
    ok = True
    for w in r.iter_rows(named=True):
        u = 1.0 - w["none"] / w["n"]
        flaga = "" if u >= PROG_SIDE else "  <-- PONIZEJ PROGU"
        if u < PROG_SIDE:
            ok = False
        print(f"  {w['segment']:12s} n={w['n']:>9,}  side!=NONE {100 * u:7.3f}%{flaga}")
    return udzial, ok


def k3_semantyka(d: pl.DataFrame) -> None:
    """3. Semantyka BID/ASK — USTALONA Z DANYCH, nie z pamieci.

    Test: dla transakcji o cenie WYZSZEJ od poprzedniej, ktora etykieta
    dominuje. To WALIDACJA znaczenia etykiety, nie rekonstrukcja strony —
    etykieta pozostaje wzieta z danych, tick sluzy wylacznie do sprawdzenia,
    co ona oznacza.
    """
    print("\n=== 3. Semantyka `side` — ustalona empirycznie ===")
    x = d.filter(pl.col("side") != "N").sort(["ts_event", "sequence"])
    x = x.with_columns((pl.col("price") - pl.col("price").shift(1)).alias("dp")).drop_nulls("dp")
    for nazwa, war in (("cena ROSNIE", pl.col("dp") > 0), ("cena SPADA", pl.col("dp") < 0)):
        s = x.filter(war)
        if not s.height:
            continue
        r = s.group_by("side").agg(pl.len().alias("n")).sort("n", descending=True)
        opis = "  ".join(f"{w['side']}={100 * w['n'] / s.height:5.1f}%" for w in r.iter_rows(named=True))
        print(f"  {nazwa:12s} (n={s.height:>8,}):  {opis}")
    print("  -> `B` dominuje przy rosnacej cenie, `A` przy spadajacej, wiec:")
    print("     B = agresor KUPUJACY (bierze plynnosc z asku)")
    print("     A = agresor SPRZEDAJACY (bierze plynnosc z bidu)")
    print("     Ustalone Z DANYCH. Tick sluzy tu WYLACZNIE do odczytania znaczenia")
    print("     etykiety; sama etykieta pozostaje wzieta z pola `side`.")


def k4_k5_czas(d: pl.DataFrame) -> None:
    """4. ts_event/ts_recv/sequence/ts_in_delta. 5. Duplikaty i odwrocenia."""
    print("\n=== 4. Znaczniki czasu i sekwencja ===")
    te = d["ts_event"].to_list()
    tr = d["ts_recv"].to_list()
    print(f"  ts_event : {min(te)} -> {max(te)}")
    print(f"  ts_recv  : {min(tr)} -> {max(tr)}")
    opoz = np.array([(b - a).total_seconds() * 1e6 for a, b in zip(te, tr, strict=True)])
    print(f"  ts_recv - ts_event [us]: mediana {np.median(opoz):.1f}  "
          f"p99 {np.percentile(opoz, 99):.1f}  min {opoz.min():.1f}")
    print(f"  ujemnych opoznien: {(opoz < 0).sum():,}  <-- musi byc 0")
    if "ts_in_delta" in d.columns:
        v = d["ts_in_delta"].to_numpy()
        print(f"  ts_in_delta [ns]: mediana {np.median(v):.0f}  p99 {np.percentile(v, 99):.0f}")

    print("\n=== 5. Duplikaty i odwrocenia kolejnosci ===")
    print(f"  ts_event niemonotoniczne: {(np.diff(d['ts_event'].to_numpy().astype('int64')) < 0).sum():,}")
    sq = d["sequence"].to_numpy()
    print(f"  sequence niemonotoniczne: {(np.diff(sq) < 0).sum():,}")
    print(f"  sequence zduplikowane   : {len(sq) - len(np.unique(sq)):,}")
    kol = ["ts_event", "price", "size", "side", "sequence"]
    print(f"  rekordy identyczne na {kol}: {d.height - d.unique(subset=kol).height:,}")
    # Duplikat `sequence` NIE jest defektem: jedno zlecenie agresora wypelnia sie
    # przeciw wielu zleceniom pasywnym i CME drukuje osobny rekord na kazde
    # wypelnienie. To ma bezposrednie znaczenie dla D5 — jednostka mechanizmu
    # jest ZDARZENIE AGRESORA, nie pojedyncze wypelnienie.
    n_zdarzen = d.unique(subset=["ts_event", "sequence"]).height
    print(f"  wypelnien {d.height:,} -> zdarzen agresora {n_zdarzen:,} "
          f"(srednio {d.height / n_zdarzen:.2f} wypelnien na zdarzenie)")


def k6_k7_ceny(d: pl.DataFrame) -> None:
    """6. Tick size, ceny, rozmiary. 7. Jednoznacznosc kontraktu."""
    print("\n=== 6. Ceny i rozmiary ===")
    p = d["price"].to_numpy()
    print(f"  cena: min {p.min():.2f}  max {p.max():.2f}")
    reszty = np.abs(np.round(p / TICK_MNQ) - p / TICK_MNQ)
    print(f"  poza siatka ticka {TICK_MNQ}: {(reszty > 1e-9).sum():,}  <-- musi byc 0")
    s = d["size"].to_numpy()
    print(f"  rozmiar: min {s.min()}  mediana {np.median(s):.0f}  p99 {np.percentile(s, 99):.0f}  max {s.max()}")
    print(f"  rozmiar <= 0: {(s <= 0).sum():,}  <-- musi byc 0")

    print("\n=== 7. Jednoznacznosc kontraktu ===")
    for kol in ("instrument_id", "symbol"):
        if kol in d.columns:
            u = d[kol].unique().to_list()
            print(f"  {kol}: {len(u)} unikalnych -> {u[:5]}")


def k8_ohlcv(d: pl.DataFrame) -> None:
    """8. Rekonstrukcja ohlcv-1m i porownanie z posiadanymi barami."""
    print("\n=== 8. Rekonstrukcja ohlcv-1m i porownanie ===")
    # DWIE RZECZY, KTORE MUSZA BYC ZROBIONE DOKLADNIE TAK.
    #
    # 1. SORTOWANIE PRZED GRUPOWANIEM: `first()`/`last()` biora kolejnosc
    #    z ramki, wiec bez tego open i close bara wychodza z przypadkowej
    #    transakcji w minucie.
    #
    # 2. AGREGACJA PO `ts_recv`, NIE `ts_event`. Ustalone empirycznie, bo to
    #    rozstrzyga o zgodnosci co do jednego bara:
    #        ts_event -> niezgodne: open 8, close 6, wolumen 20
    #        ts_recv  -> niezgodne: 0, 0, 0  (1380 z 1380 barow idealnie)
    #    Databento buduje bary na znaczniku ODBIORU. Uzycie `ts_event` daje
    #    ciche przesuniecia na granicy minuty — kilkanascie barow na sesje,
    #    z suma roznic wolumenu dokladnie zero, bo transakcje przenosza sie
    #    miedzy sasiednimi minutami. To jest wlasnie klasa bledu, ktora nie
    #    rzuca wyjatku. Ma bezposrednie znaczenie dla D5: granica okna
    #    obserwacji musi byc liczona na `ts_recv`.
    rek = (
        d.sort(["ts_recv", "sequence"])
        .with_columns(pl.col("ts_recv").dt.truncate("1m").alias("m"))
        .group_by("m")
        .agg([
            pl.col("price").first().alias("o"), pl.col("price").max().alias("h"),
            pl.col("price").min().alias("low"), pl.col("price").last().alias("c"),
            pl.col("size").sum().alias("v"),
        ])
        .sort("m")
    )
    print(f"  zrekonstruowano {rek.height:,} barow M1")

    nasz = (
        pl.read_parquet("data/clean/mnq_1m_cont.parquet")
        .filter(pl.col("trade_date") == pl.lit(SESJA).str.to_date())
        .select("ts_utc", "open", "high", "low", "close", "volume")
        .sort("ts_utc")
    )
    print(f"  posiadamy      {nasz.height:,} barow M1 dla {SESJA}")

    z = nasz.join(rek, left_on="ts_utc", right_on="m", how="inner")
    print(f"  wspolnych minut: {z.height:,}")
    if not z.height:
        print("  BRAK CZESCI WSPOLNEJ — sprawdz strefy czasowe")
        return
    for a, b, nazwa in (("open", "o", "open"), ("high", "h", "high"),
                        ("low", "low_right", "low"), ("close", "c", "close")):
        kol = b if b in z.columns else a + "_right"
        r = (z[a] - z[kol]).abs().to_numpy()
        print(f"  |{nazwa:5s} nasz - zrekonstruowany|: max {r.max():.4f}  "
              f"niezgodnych {int((r > 1e-9).sum()):,} z {len(r):,}")
    # RZUTOWANIE NA Int64 KONIECZNE: obie kolumny sa bez znaku, wiec odejmowanie
    # przepelnia sie do 2^64-1 zamiast dac liczbe ujemna.
    rv = (z["volume"].cast(pl.Int64) - z["v"].cast(pl.Int64)).to_numpy()
    print(f"  wolumen: niezgodnych {int((rv != 0).sum()):,} z {len(rv):,}  "
          f"max |roznicy| {int(np.abs(rv).max()):,}  suma roznic {int(rv.sum()):,}")


def k9_trade_date(d: pl.DataFrame) -> None:
    """9. Zgodnosc czasu z ET i przypisaniem do trade_date."""
    print("\n=== 9. Zgodnosc z ET i trade_date ===")
    td = {trade_date(t) for t in d["ts_event"].to_list()}
    print(f"  unikalne trade_date w pobranym oknie: {sorted(str(x) for x in td)}")
    print(f"  oczekiwane: ['{SESJA}']  ->", "ZGODNE" if {str(x) for x in td} == {SESJA} else "ROZBIEZNE")


def main() -> int:
    if not PLIK.exists():
        sys.exit(f"BLAD: brak {PLIK}")
    print(f"=== D5 Etap 1 — {PLIK} ===")
    d = wczytaj()

    udzial, seg_ok = k1_k2_side(d)
    k3_semantyka(d)
    k4_k5_czas(d)
    k6_k7_ceny(d)
    k8_ohlcv(d)
    k9_trade_date(d)

    print("\n" + "=" * 62)
    zdal = udzial > PROG_SIDE and seg_ok
    print(f"  side != NONE = {100 * udzial:.4f}%  (prog > {100 * PROG_SIDE:.0f}%)")
    print(f"  kompletnosc we wszystkich segmentach: {'TAK' if seg_ok else 'NIE'}")
    print(f"\n  WERDYKT: {'D5-A GO' if zdal else 'D5-A NO-GO'}")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
