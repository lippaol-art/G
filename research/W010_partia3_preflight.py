#!/usr/bin/env python3
"""W010 — pre-flight partii 3: H001 i H002.  PLAN.pdf rozdz. 8.4.

Zero zuzytych prob — badanie rozkladow, nie backtest. Zadnych stopow, progow
optymalizowanych ani wyboru wariantu po wyniku.

Obie karty maja jedno przewidywanie, na ktorym stoja lub upadaja, i obie da sie
je sprawdzic na danych z repo, za zero dolarow:

  H001: czy WOLUMEN PRZY ZADANYM ZAKRESIE rozdziela charakter sesji RTH?
        H010 zginelo na tym, ze zakres nocny przewiduje amplitude (t = +10.2),
        ale nie charakter (t ~ 0). H001 twierdzi, ze brakujaca informacje niesie
        wolumen — zmienna, ktorej H010 w ogole nie ogladalo.

  H002: czy MOMENT POWSTANIA odchylenia od VWAP rozdziela powroty od
        kontynuacji? I — co wazniejsze — czy robi to lepiej niz prosty warunek
        wolumenowy, ktory jest detaliczna regula znana od dekad.

Drugi test H002 jest tu wazniejszy niz pierwszy i jest zapisany w karcie jako
ablacja 2. Karta sama przyznaje w sekcji 4, ze jest to jej najslabszy punkt.

Wyjscie: reports/W010_partia3_preflight.md
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.loader import is_available, load_continuous  # noqa: E402

RAPORT = Path("reports/W010_partia3_preflight.md")
NOC = ("globex_open", "asia", "europe")        # 18:00-08:30 ET, wg karty H001
RTH = ("rth_open", "midday", "afternoon", "close")
OKNO_TLA = 60          # sesji do percentyli kroczacych
MIN_TLO = 30


def t_stat(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    return float(x.mean() / x.std(ddof=1) * np.sqrt(x.size)) if x.size > 2 else float("nan")


def t_roznicy(a: np.ndarray, b: np.ndarray) -> float:
    """Welch — dwie grupy o roznej licznosci i wariancji."""
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    va, vb = a.var(ddof=1) / a.size, b.var(ddof=1) / b.size
    return float((a.mean() - b.mean()) / np.sqrt(va + vb))


def sesje() -> pl.DataFrame:
    """Jeden wiersz na sesje: charakterystyka nocy i charakterystyka RTH."""
    d = load_continuous("MNQ").sort("ts_utc")
    # px_raw do zakresow i poziomow, px_adj do zwrotow (PLAN rozdz. 4.3)
    przesun = pl.col("px_adj") - pl.col("close")
    d = d.with_columns((pl.col("high") + przesun).alias("h_adj"),
                       (pl.col("low") + przesun).alias("l_adj"),
                       (pl.col("open") + przesun).alias("o_adj"))

    noc = (d.filter(pl.col("segment").is_in(NOC)).group_by("trade_date")
            .agg(noc_h=pl.col("high").max(), noc_l=pl.col("low").min(),
                 noc_v=pl.col("volume").sum(), noc_n=pl.len()))
    rth = (d.filter(pl.col("segment").is_in(RTH)).sort("ts_utc").group_by("trade_date")
            .agg(rth_o=pl.col("o_adj").first(), rth_c=pl.col("px_adj").last(),
                 rth_h=pl.col("h_adj").max(), rth_l=pl.col("l_adj").min(),
                 rth_n=pl.len()))
    return (noc.join(rth, on="trade_date", how="inner")
               .filter((pl.col("noc_n") >= 300) & (pl.col("rth_n") >= 300))
               .sort("trade_date"))


def pierwsze_wybicie() -> pl.DataFrame:
    """Kierunek i moment pierwszego zamkniecia M1 poza zakresem nocnym po 09:30.

    Wybicie liczymy na `px_raw`, bo porownujemy z poziomem nocnym z tej samej
    sesji — a wynik po wybiciu na `px_adj`, bo to jest zwrot.
    """
    d = load_continuous("MNQ").sort("ts_utc")
    przesun = pl.col("px_adj") - pl.col("close")
    noc = (d.filter(pl.col("segment").is_in(NOC)).group_by("trade_date")
            .agg(noc_h=pl.col("high").max(), noc_l=pl.col("low").min()))
    r = (d.filter(pl.col("segment").is_in(RTH))
          .join(noc, on="trade_date", how="inner")
          .with_columns((pl.col("px_adj")).alias("c_adj"),
                        (pl.col("open") + przesun).alias("o_adj"))
          .sort("ts_utc"))
    wybite = r.filter((pl.col("close") > pl.col("noc_h")) |
                      (pl.col("close") < pl.col("noc_l")))
    pierwsze = (wybite.group_by("trade_date")
                .agg(ts_wyb=pl.col("ts_utc").first(),
                     kier=pl.when(pl.col("close").first() > pl.col("noc_h").first())
                           .then(1).otherwise(-1),
                     c_wyb=pl.col("c_adj").first()))
    koniec_open = (r.filter(pl.col("segment") == "rth_open").group_by("trade_date")
                    .agg(c_open_end=pl.col("c_adj").last()))
    koniec_sesji = r.group_by("trade_date").agg(c_sesja=pl.col("c_adj").last())
    return (pierwsze.join(koniec_open, on="trade_date")
                    .join(koniec_sesji, on="trade_date").collect())


def vwap_sesji() -> pl.DataFrame:
    """Odchylenie od VWAP sesyjnego o 10:30 i o 11:30 oraz to, czy wrocilo."""
    d = load_continuous("MNQ").sort("ts_utc")
    et = pl.col("ts_utc").dt.convert_time_zone("America/New_York")
    hm = (et.dt.hour().cast(pl.Int32) * 60 + et.dt.minute().cast(pl.Int32))
    r = (d.filter(pl.col("segment").is_in(RTH))
          .with_columns(hm.alias("hm"),
                        ((pl.col("high") + pl.col("low") + pl.col("close")) / 3)
                        .alias("tp"))
          .sort("ts_utc"))
    # VWAP narastajaco w obrebie sesji
    r = r.with_columns(
        (pl.col("tp") * pl.col("volume")).cum_sum().over("trade_date").alias("pv"),
        pl.col("volume").cum_sum().over("trade_date").alias("cv"),
    ).with_columns((pl.col("pv") / pl.col("cv")).alias("vwap"))
    # sigma wazona obrotem, narastajaco
    r = r.with_columns(
        ((pl.col("tp") - pl.col("vwap")).pow(2) * pl.col("volume"))
        .cum_sum().over("trade_date").alias("wss")
    ).with_columns((pl.col("wss") / pl.col("cv")).sqrt().alias("sig"))
    r = r.with_columns(
        pl.when(pl.col("sig") > 0)
        .then((pl.col("close") - pl.col("vwap")) / pl.col("sig"))
        .otherwise(0.0).alias("d")
    )

    def w(minuta: int, nazwa: str) -> pl.LazyFrame:
        return (r.filter(pl.col("hm") == minuta).group_by("trade_date")
                 .agg(**{nazwa: pl.col("d").first(),
                         f"{nazwa}_vwap": pl.col("vwap").first(),
                         f"{nazwa}_c": pl.col("close").first()}))

    # wolumen w oknie 10:30-11:30 — do ablacji 2 karty H002
    vol_okno = (r.filter((pl.col("hm") > 630) & (pl.col("hm") <= 690))
                 .group_by("trade_date").agg(v_okno=pl.col("volume").sum()))
    # czy dotknieto VWAP miedzy 11:30 a 15:00
    po = r.filter((pl.col("hm") > 690) & (pl.col("hm") <= 900))
    dotk = (po.group_by("trade_date")
              .agg(min_d=pl.col("d").min(), max_d=pl.col("d").max(),
                   c_1500=pl.col("close").last()))
    return (w(630, "d1030").join(w(690, "d1130"), on="trade_date")
            .join(vol_okno, on="trade_date").join(dotk, on="trade_date")
            .sort("trade_date").collect())


def percentyl_kroczacy(x: np.ndarray, okno: int = OKNO_TLA) -> np.ndarray:
    """Ranga wartosci w oknie KONCZACYM SIE PRZED nia. Zakaz lookaheadu."""
    out = np.full(x.size, np.nan)
    for i in range(x.size):
        a = max(0, i - okno)
        h = x[a:i]
        if h.size >= MIN_TLO:
            out[i] = float((h < x[i]).mean())
    return out


def main() -> int:
    if not is_available("MNQ"):
        sys.exit("Brak danych MNQ — patrz HANDOFF.md")

    s = sesje()
    zakres = (s["noc_h"] - s["noc_l"]).to_numpy()
    wol = s["noc_v"].to_numpy()
    p_zakres = percentyl_kroczacy(zakres)
    p_wol = percentyl_kroczacy(wol)
    rng_rth = (s["rth_h"] - s["rth_l"]).to_numpy()
    er = np.where(rng_rth > 0,
                  np.abs(s["rth_c"].to_numpy() - s["rth_o"].to_numpy()) / rng_rth,
                  np.nan)
    lata = np.array([d.year for d in s["trade_date"].to_list()])
    gotowe = np.isfinite(p_zakres) & np.isfinite(p_wol) & np.isfinite(er)

    kompresja = gotowe & (p_zakres <= 1 / 3)
    z_rownowagi = kompresja & (p_wol > 0.5)
    z_braku = kompresja & (p_wol <= 0.5)

    L: list[str] = [
        "# W010 — pre-flight partii 3 (H001, H002)",
        "",
        f"*Wygenerowane przez `research/W010_partia3_preflight.py`, "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}. "
        f"{int(gotowe.sum())} sesji MNQ z pelnym tlem.*",
        "",
        "**Status licznika prob: 0 zuzytych.**",
        "",
        "H003 nie jest tu badana — wymaga kalendarza makro, ktorego jeszcze nie ma.",
        "",
        "---",
        "",
        "# H001 — kompresja nocna: przyczyna, nie fakt",
        "",
        "## Przewidywanie 1 — dwie kompresje daja rozny CHARAKTER sesji",
        "",
        "To jest test, na ktorym karta stoi lub upada. H010 zginelo na tym, ze zakres",
        "nocny przewiduje **amplitude** (t = +10.2), ale nie **charakter** (t ~ 0).",
        "H001 twierdzi, ze charakter niesie wolumen przy zadanym zakresie.",
        "",
        "| Grupa | N | Efficiency ratio | Zakres RTH (pkt) |",
        "|---|---|---|---|",
    ]
    for nazwa, m in (("**kompresja z rownowagi** (wolumen wysoki)", z_rownowagi),
                     ("**kompresja z braku** (wolumen niski)", z_braku),
                     ("pozostale sesje", gotowe & ~kompresja)):
        L.append(f"| {nazwa} | {int(m.sum())} | {np.nanmean(er[m]):.4f} | "
                 f"{np.nanmean(rng_rth[m]):.1f} |")

    t_er = t_roznicy(er[z_rownowagi], er[z_braku])
    t_rng = t_roznicy(rng_rth[z_rownowagi], rng_rth[z_braku])
    L += [
        "",
        f"**t roznicy efficiency ratio (rownowaga − brak): {t_er:+.2f}**",
        f"t roznicy zakresu RTH: {t_rng:+.2f}",
        "",
    ]

    # monotonicznosc wzgledem wolumenu wewnatrz kompresji
    L += [
        "## Przewidywanie 2 — monotonicznosc wzgledem wolumenu",
        "",
        "Efekt ma rosnac z wolumenem, a nie skakac w jednym kubelku. **Tak zginelo H005.**",
        "",
        "| Kwartyl wolumenu nocnego (w obrebie kompresji) | N | Efficiency ratio |",
        "|---|---|---|",
    ]
    for i, (lo, hi) in enumerate([(0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.01)], 1):
        m = kompresja & (p_wol >= lo) & (p_wol < hi)
        if m.sum() >= 10:
            L.append(f"| Q{i} ({lo:.2f}–{hi:.2f}) | {int(m.sum())} | "
                     f"{np.nanmean(er[m]):.4f} |")

    # wybicia
    wyb = pierwsze_wybicie()
    s2 = s.join(wyb, on="trade_date", how="left")
    kier = s2["kier"].to_numpy()
    c_wyb = s2["c_wyb"].to_numpy()
    c_open_end = s2["c_open_end"].to_numpy()
    c_sesja = s2["c_sesja"].to_numpy()
    ma_wyb = np.isfinite(c_wyb.astype(float)) if c_wyb.dtype != object else np.array(
        [x is not None for x in c_wyb])
    kier_f = np.nan_to_num(kier.astype(float))
    kont_open = kier_f * (c_open_end.astype(float) - c_wyb.astype(float))
    kont_sesja = kier_f * (c_sesja.astype(float) - c_wyb.astype(float))

    L += [
        "",
        "## Przewidywanie 3 — kontynuacja po wybiciu z zakresu nocnego",
        "",
        "Jesli kompresja z rownowagi oznacza wypracowany poziom, jego przelamanie",
        "powinno miec kontynuacje. Bez stopa i bez progu — sam rozklad zwrotu.",
        "",
        "| Grupa | N wybic | Do konca `rth_open` (pkt) | t | Do konca sesji (pkt) | t |",
        "|---|---|---|---|---|---|",
    ]
    for nazwa, m in (("**kompresja z rownowagi**", z_rownowagi & ma_wyb),
                     ("**kompresja z braku**", z_braku & ma_wyb),
                     ("pozostale sesje", gotowe & ~kompresja & ma_wyb)):
        L.append(f"| {nazwa} | {int(m.sum())} | {np.nanmean(kont_open[m]):+.1f} | "
                 f"{t_stat(kont_open[m]):+.2f} | {np.nanmean(kont_sesja[m]):+.1f} | "
                 f"{t_stat(kont_sesja[m]):+.2f} |")

    # stabilnosc roczna kontynuacji w grupie z rownowagi
    L += [
        "",
        "## Przewidywanie 4 — stabilnosc roczna (kompresja z rownowagi)",
        "",
        "| Rok | N | Kontynuacja do konca `rth_open` | t |",
        "|---|---|---|---|",
    ]
    grupa = z_rownowagi & ma_wyb
    for rok in sorted(set(lata[grupa].tolist())):
        m = grupa & (lata == rok)
        if m.sum() >= 5:
            L.append(f"| {rok} | {int(m.sum())} | {np.nanmean(kont_open[m]):+.1f} | "
                     f"{t_stat(kont_open[m]):+.2f} |")

    # ---------------- H002 ----------------
    v = vwap_sesji()
    sv = s.join(v, on="trade_date", how="inner")
    d1030 = sv["d1030"].to_numpy()
    d1130 = sv["d1130"].to_numpy()
    v_okno = sv["v_okno"].to_numpy()
    min_d, max_d = sv["min_d"].to_numpy(), sv["max_d"].to_numpy()
    lata_v = np.array([d.year for d in sv["trade_date"].to_list()])

    istotne = np.isfinite(d1130) & (np.abs(d1130) >= 1.0)
    ten_sam_znak = istotne & np.isfinite(d1030) & (np.sign(d1030) == np.sign(d1130))
    udzial = np.where(ten_sam_znak, np.abs(d1030) / np.abs(d1130), 0.0)
    udzial = np.where(istotne, udzial, np.nan)
    # powrot = przejscie przez VWAP miedzy 11:30 a 15:00
    wrocilo = np.where(d1130 > 0, min_d <= 0, max_d >= 0)
    p_vokno = percentyl_kroczacy(v_okno)

    L += [
        "",
        "---",
        "",
        "# H002 — powrot do VWAP: gdzie odchylenie powstalo",
        "",
        f"Sesji z istotnym odchyleniem o 11:30 (\\|d\\| >= 1.0): "
        f"**{int(istotne.sum())}** z {sv.height} "
        f"(*f* = {istotne.sum()/sv.height:.2f}, karta deklarowala 0.33).",
        "",
        "## Przewidywanie 1 — udzial odziedziczony rozdziela powroty",
        "",
        "| Udzial odziedziczony | N | Odsetek powrotow do VWAP |",
        "|---|---|---|",
    ]
    grupy = (("swieze (< 0.33)", istotne & (udzial < 0.33)),
             ("posrednie (0.33–0.67)", istotne & (udzial >= 0.33) & (udzial <= 0.67)),
             ("odziedziczone (> 0.67)", istotne & (udzial > 0.67)))
    for nazwa, m in grupy:
        if m.sum() >= 10:
            L.append(f"| {nazwa} | {int(m.sum())} | {wrocilo[m].mean():.1%} |")

    m_sw = istotne & (udzial < 0.33)
    m_od = istotne & (udzial > 0.67)
    t_pow = t_roznicy(wrocilo[m_sw].astype(float), wrocilo[m_od].astype(float))
    L += [
        "",
        f"**t roznicy odsetka powrotow (swieze − odziedziczone): {t_pow:+.2f}**",
        "",
        "## Przewidywanie 2 (ABLACJA 2 KARTY) — czy prosty wolumen daje to samo",
        "",
        "**To jest wazniejszy test niz poprzedni.** Karta sama przyznaje w sekcji 4,",
        "ze grozi jej sprowadzenie do detalicznej reguly \"ruch bez wolumenu jest",
        "falszywy\". Jesli podzial po wolumenie w oknie 10:30-11:30 rozdziela powroty",
        "tak samo dobrze, roznica mechanizmu jest pozorna i karta schodzi do benchmarkow.",
        "",
        "| Podzial | N | Odsetek powrotow | t roznicy |",
        "|---|---|---|---|",
    ]
    m_lo = istotne & np.isfinite(p_vokno) & (p_vokno <= 0.5)
    m_hi = istotne & np.isfinite(p_vokno) & (p_vokno > 0.5)
    t_vol = t_roznicy(wrocilo[m_lo].astype(float), wrocilo[m_hi].astype(float))
    L += [
        f"| wg **pochodzenia** (swieze vs odziedziczone) | "
        f"{int(m_sw.sum())} / {int(m_od.sum())} | "
        f"{wrocilo[m_sw].mean():.1%} vs {wrocilo[m_od].mean():.1%} | **{t_pow:+.2f}** |",
        f"| wg **wolumenu** (niski vs wysoki) | {int(m_lo.sum())} / {int(m_hi.sum())} | "
        f"{wrocilo[m_lo].mean():.1%} vs {wrocilo[m_hi].mean():.1%} | {t_vol:+.2f} |",
        "",
        "## Przewidywanie 3 — stabilnosc roczna (odchylenia swieze)",
        "",
        "| Rok | N | Odsetek powrotow |",
        "|---|---|---|",
    ]
    for rok in sorted(set(lata_v[m_sw].tolist())):
        m = m_sw & (lata_v == rok)
        if m.sum() >= 5:
            L.append(f"| {rok} | {int(m.sum())} | {wrocilo[m].mean():.1%} |")

    L += [
        "",
        "---",
        "",
        "Odtworzenie: `python3 research/W010_partia3_preflight.py`",
    ]

    RAPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {RAPORT}")
    print(f"H001: t(ER) {t_er:+.2f}, N rownowaga {int(z_rownowagi.sum())}, "
          f"brak {int(z_braku.sum())}")
    print(f"H002: t(powroty wg pochodzenia) {t_pow:+.2f}, "
          f"t(wg wolumenu) {t_vol:+.2f}, N istotnych {int(istotne.sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
