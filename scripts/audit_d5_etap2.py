#!/usr/bin/env python3
"""D5-B — test identyfikowalnosci. Specyfikacja zamrozona: docs/D5_ETAP2_SPEC.md.

CO TO JEST, A CZYM NIE JEST.
Jedno pytanie: **czy nierownowaga zdarzen agresora w RTH da sie statystycznie
odroznic od ROWNOCZESNEGO momentum ceny w RTH?**

NIE liczy: przyszlych zwrotow, korelacji z przyszlym P&L, skutecznosci
kierunku, Sharpe'a, profit factora, optymalnego progu, najlepszego segmentu
dnia, horyzontu utrzymania ani strategii long/short. **Zero zuzytych prob.**

Model pomocniczy NIE ZAWIERA przyszlego zwrotu:
    I ~ m + |m| + m^2 + sign(m) + log(1+volume) + efekty pory dnia
gdzie `m` jest momentum w TYM SAMYM oknie.

Uruchomienie:
    python3 scripts/audit_d5_etap2.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
KAT = Path("data/raw/d5b_rth")
PLIK_0730 = Path("data/raw/mnq_trades_2026-07-30.dbn.zst")

OKNO_S = 60          # sekund
RTH_MIN = 390        # 09:30-16:00 ET
PROG_VIF = 5.0
UDZIAL_SESJI = 0.75  # >=75% kompletnych sesji z VIF < progu
MAX_KONC = 0.20      # zadna sesja > 20% zmiennosci I_count
KUBELEK_MIN = 30     # dlugosc kubelka pory dnia


def granice_rth(sesja: str) -> tuple[dt.datetime, dt.datetime]:
    """RTH WYPROWADZONE ZE STREFY ET — nigdy ze stalej UTC."""
    y, m, d = map(int, sesja.split("-"))
    return (dt.datetime(y, m, d, 9, 30, tzinfo=ET).astimezone(UTC),
            dt.datetime(y, m, d, 16, 0, tzinfo=ET).astimezone(UTC))


def wczytaj(p: Path) -> pl.DataFrame:
    import databento as db
    return pl.from_pandas(db.DBNStore.from_file(p).to_df().reset_index())


# --------------------------------------------------------------- agregacja --
def zdarzenia(d: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """`candidate_aggressor_event` = (ts_event, sequence, side).

    NAZWA JEST CZESCIA SPECYFIKACJI: to deterministyczna grupa wypelnien
    o wspolnym kluczu technicznym, uzywana jako EMPIRYCZNE PRZYBLIZENIE
    jednego zdarzenia agresora — nie zidentyfikowane zlecenie uczestnika.
    """
    znane = d.filter(pl.col("side") != "N")
    g = (
        znane.sort(["ts_recv", "sequence"])
        .group_by(["ts_event", "sequence", "side"])
        .agg([
            pl.col("ts_recv").max().alias("ts_recv"),   # gdy cale zdarzenie znane
            pl.col("size").sum().alias("size"),
            pl.len().alias("wypelnien"),
            pl.col("price").min().alias("p_min"),
            pl.col("price").max().alias("p_max"),
        ])
    )
    kontrola = {
        "wypelnien_raw": d.height,
        "wypelnien_ze_strona": znane.height,
        "wypelnien_NONE": d.height - znane.height,
        "zdarzen": g.height,
        "suma_size_raw": int(znane["size"].sum()),
        "suma_size_zdarzen": int(g["size"].sum()),
    }
    return g, kontrola


def testy_niezmiennikow(k: dict) -> list[str]:
    """Osiem niezmiennikow z §3 specyfikacji — sprawdzane PRZED VIF."""
    bledy = []
    if k["suma_size_zdarzen"] != k["suma_size_raw"]:
        bledy.append(f"suma size: {k['suma_size_zdarzen']} != {k['suma_size_raw']}")
    if k["zdarzen"] > k["wypelnien_ze_strona"]:
        bledy.append("liczba zdarzen > liczba wypelnien")
    return bledy


# ------------------------------------------------------------------ okna ----
def okna_sesji(d: pl.DataFrame, g: pl.DataFrame, a: dt.datetime,
               b: dt.datetime) -> pl.DataFrame:
    """Jeden wiersz na okno 60 s. Okna WYRÓWNANE DO PELNYCH MINUT PO `ts_recv`.

    Okno bez transakcji = obserwacja BRAKUJACA, nie zerowy zwrot — dlatego
    laczymy przez `inner`, nie uzupelniamy zerami.
    """
    w = pl.col("ts_recv").dt.truncate(f"{OKNO_S}s")

    # momentum i wolumen z WYPELNIEN (cena pierwszego i ostatniego w oknie)
    ceny = (
        d.sort(["ts_recv", "sequence"]).with_columns(w.alias("okno"))
        .group_by("okno")
        .agg([
            pl.col("price").first().alias("p_first"),
            pl.col("price").last().alias("p_last"),
            pl.col("size").sum().alias("wolumen"),
            pl.len().alias("wypelnien"),
        ])
    )
    # kontrola B: nierownowaga po SUROWYCH WYPELNIENIACH
    fill = (
        d.filter(pl.col("side") != "N").with_columns(w.alias("okno"))
        .group_by("okno")
        .agg([(pl.col("side") == "B").sum().alias("f_buy"),
              (pl.col("side") == "A").sum().alias("f_sell"),
              pl.col("size").filter(pl.col("side") == "B").sum().alias("v_buy"),
              pl.col("size").filter(pl.col("side") == "A").sum().alias("v_sell")])
    )
    # glowna A: nierownowaga po ZDARZENIACH
    ev = (
        g.with_columns(w.alias("okno")).group_by("okno")
        .agg([(pl.col("side") == "B").sum().alias("n_buy"),
              (pl.col("side") == "A").sum().alias("n_sell")])
    )
    o = ceny.join(fill, on="okno", how="inner").join(ev, on="okno", how="inner")
    return o.filter((pl.col("okno") >= a) & (pl.col("okno") < b)).sort("okno")


# ------------------------------------------------------------------ VIF -----
def _r2(y: np.ndarray, X: np.ndarray) -> float:
    Xa = np.c_[np.ones(len(y)), X]
    beta, *_ = np.linalg.lstsq(Xa, y, rcond=None)
    r = y - Xa @ beta
    return float(1 - r.var() / y.var()) if y.var() > 0 else float("nan")


def kontrolne(o: pl.DataFrame, pory: bool) -> np.ndarray:
    m = o["m"].to_numpy()
    X = np.c_[m, np.abs(m), m ** 2, np.sign(m),
              np.log1p(o["wolumen"].to_numpy().astype(float))]
    if pory:
        k = o["kubelek"].to_numpy()
        for v in np.unique(k)[1:]:      # jeden kubelek jako baza
            X = np.c_[X, (k == v).astype(float)]
    return X


def main() -> int:
    sesje = sorted(p.name.split("_")[-1].removesuffix(".dbn.zst")
                   for p in KAT.glob("*.dbn.zst"))
    sesje.append("2026-07-30")
    sesje.sort()
    print(f"=== D5-B: {len(sesje)} sesji RTH ===")

    czesci, kontrole_agg, sha_widziane = [], [], set()
    for s in sesje:
        a, b = granice_rth(s)
        p = PLIK_0730 if s == "2026-07-30" else KAT / f"mnq_trades_rth_{s}.dbn.zst"
        d = wczytaj(p)
        if s == "2026-07-30":                      # pelna doba -> tnij do RTH
            d = d.filter((pl.col("ts_recv") >= a) & (pl.col("ts_recv") < b))
        # kontrola duplikatow na granicach
        klucz = (s, int(d["ts_recv"].min().timestamp()), int(d["ts_recv"].max().timestamp()))
        if klucz in sha_widziane:
            sys.exit(f"BLAD: duplikat zakresu {klucz}")
        sha_widziane.add(klucz)

        g, k = zdarzenia(d)
        k["sesja"] = s
        kontrole_agg.append(k)
        bledy = testy_niezmiennikow(k)
        if bledy:
            sys.exit(f"BLAD niezmiennikow {s}: {bledy}")

        o = okna_sesji(d, g, a, b).with_columns(pl.lit(s).alias("sesja"))
        czesci.append(o)
        print(f"  {s}  wypelnien {k['wypelnien_raw']:>9,}  zdarzen {k['zdarzen']:>9,}  "
              f"okien {o.height:>4}", flush=True)

    o = pl.concat(czesci)
    # zmienne
    o = o.with_columns([
        (pl.col("p_last") / pl.col("p_first")).log().alias("m"),
        ((pl.col("n_buy") - pl.col("n_sell")) /
         (pl.col("n_buy") + pl.col("n_sell"))).alias("A_count"),
        ((pl.col("f_buy") - pl.col("f_sell")) /
         (pl.col("f_buy") + pl.col("f_sell"))).alias("B_fill"),
        ((pl.col("v_buy") - pl.col("v_sell")) /
         (pl.col("v_buy") + pl.col("v_sell"))).alias("C_volume"),
    ]).drop_nulls(["m", "A_count", "B_fill", "C_volume"])
    # kubelek pory dnia liczony od poczatku RTH danej sesji
    o = o.with_columns(
        ((pl.col("okno").dt.hour().cast(pl.Int32) * 60
          + pl.col("okno").dt.minute().cast(pl.Int32)) // KUBELEK_MIN).alias("kubelek")
    )

    kompletne = [k["sesja"] for k in kontrole_agg if k["sesja"] != "2026-07-03"]
    print(f"\nokien lacznie: {o.height:,}   sesji: {o['sesja'].n_unique()}   "
          f"kompletnych: {len(kompletne)}")

    print("\n=== TEST IDENTYFIKOWALNOSCI ===")
    wyniki = {}
    for nazwa, kol in (("A  I_count (GLOWNA)", "A_count"),
                       ("B  po wypelnieniach", "B_fill"),
                       ("C  I_volume", "C_volume")):
        y = o[kol].to_numpy()
        r2p = _r2(y, kontrolne(o, pory=True))
        r2b = _r2(y, kontrolne(o, pory=False))
        vif_p, vif_b = 1 / max(1 - r2p, 1e-12), 1 / max(1 - r2b, 1e-12)
        dz = []
        for s in kompletne:
            m = o.filter(pl.col("sesja") == s)
            if m.height < 50:
                continue
            v = _r2(m[kol].to_numpy(), kontrolne(m, pory=True))
            dz.append(1 / max(1 - v, 1e-12))
        dz = np.array(dz)
        # koncentracja zmiennosci po sesjach
        ss = o.group_by("sesja").agg(
            ((pl.col(kol) - y.mean()) ** 2).sum().alias("ss"))["ss"].to_numpy()
        konc = float(ss.max() / ss.sum())
        wyniki[kol] = dict(pooled_vif=vif_p, pooled_vif_bez_pory=vif_b,
                           mediana_dzienna=float(np.median(dz)),
                           p10=float(np.percentile(dz, 10)),
                           p90=float(np.percentile(dz, 90)),
                           udzial_ponizej=float((dz < PROG_VIF).mean()),
                           max_koncentracja=konc, sesji=len(dz))
        print(f"\n  {nazwa}")
        print(f"    pooled VIF (z porami dnia) : {vif_p:8.3f}   R²={r2p:.4f}")
        print(f"    pooled VIF (bez por dnia)  : {vif_b:8.3f}   R²={r2b:.4f}")
        print(f"    dzienny VIF: mediana {np.median(dz):7.3f}  p10 {np.percentile(dz,10):6.3f}"
              f"  p90 {np.percentile(dz,90):7.3f}")
        print(f"    sesji z VIF < {PROG_VIF}: {(dz < PROG_VIF).sum()}/{len(dz)} "
              f"({100*(dz<PROG_VIF).mean():.1f}%)")
        print(f"    max udzial jednej sesji w zmiennosci: {100*konc:.2f}%")

    a = wyniki["A_count"]
    war = {
        "pooled VIF < 5": a["pooled_vif"] < PROG_VIF,
        "mediana dziennego VIF < 5": a["mediana_dzienna"] < PROG_VIF,
        ">=75% sesji z VIF < 5": a["udzial_ponizej"] >= UDZIAL_SESJI,
        "zadna sesja > 20% zmiennosci": a["max_koncentracja"] <= MAX_KONC,
    }
    print("\n" + "=" * 64)
    for n, v in war.items():
        print(f"  {'OK ' if v else 'NIE'}  {n}")
    zgodne = ((a["pooled_vif"] < PROG_VIF) == (wyniki["B_fill"]["pooled_vif"] < PROG_VIF)
              == (wyniki["C_volume"]["pooled_vif"] < PROG_VIF))
    print(f"  {'OK ' if zgodne else 'NIE'}  A/B/C zgodne co do werdyktu")
    werdykt = ("D5-B GO" if all(war.values()) and zgodne else
               "D5-B INCONCLUSIVE" if all(war.values()) else "D5-B NO-GO")
    print(f"\n  WERDYKT: {werdykt}")
    print("=" * 64)

    Path("reports").mkdir(exist_ok=True)
    Path("reports/D5_etap2_wyniki.json").write_text(
        json.dumps({"werdykt": werdykt, "warunki": war, "zgodne_ABC": zgodne,
                    "wyniki": wyniki, "okien": o.height,
                    "sesji": o["sesja"].n_unique(),
                    "kontrole_agregacji": kontrole_agg}, indent=1, default=str),
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
