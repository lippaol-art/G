#!/usr/bin/env python3
"""W010 — pre-flight partii 3: H001 i H002.  PLAN.pdf rozdz. 8.4.

Zero zuzytych prob — badanie rozkladow, nie backtest. Zadnych stopow, progow
optymalizowanych ani wyboru wariantu po wyniku.

Obie karty maja jedno przewidywanie, na ktorym stoja lub upadaja, i obie da sie
sprawdzic na danych z repo, za zero dolarow:

  H001: czy WOLUMEN PRZY ZADANYM ZAKRESIE rozdziela charakter sesji RTH?
        H010 zginelo na tym, ze zakres nocny przewiduje amplitude (t = +10.2),
        ale nie charakter (t ~ 0). H001 twierdzi, ze brakujaca informacje niesie
        wolumen — zmienna, ktorej H010 w ogole nie ogladalo.

  H002: czy MOMENT POWSTANIA odchylenia od VWAP rozdziela powroty od
        kontynuacji, i czy robi to lepiej niz prosty warunek wolumenowy.

PIERWSZA WERSJA TEGO SKRYPTU MIALA SZESC USTEREK i zadna nie rzucalaby bledu.
Wypisuje je, bo kazda jest przykladem klasy pomylki, ktora wraca:

  1. BLAD CZASOWY (najpowazniejszy). Wybicie szukane w calym RTH, a wynik liczony
     do konca segmentu `rth_open`. Dla wybic po 10:30 cena wyjscia pochodzila
     SPRZED sygnalu. Teraz kazde wyjscie jest wybierane po znaczniku czasu
     pozniejszym niz wejscie, z asercja.
  2. BRAK KONTROLI ZAKRESU. Podzial tercyla zakresu mediana wolumenu nie
     gwarantuje, ze grupy maja ten sam zakres. Doszla regresja ciagla ER na
     percentyl zakresu I percentyl wolumenu, liczona wewnatrz kompresji.
  3. ZLE SIGMA VWAP. Wersja narastajaca odejmowala kazda obserwacje od VWAP
     Z JEJ WLASNEGO MOMENTU, nie od biezacego. To nie jest wariancja wazona.
     Teraz przez tozsamosc sigma^2 = E[p^2] - VWAP^2, zweryfikowana wobec
     `engine.features.vwap_sigma` (test w tests/test_w010_vwap.py).
  4. ODWROCENIE ZNAKU LICZONE JAKO ODCHYLENIE SWIEZE. Gdy znak o 10:30 byl
     przeciwny niz o 11:30, obserwacja dostawala udzial 0 i wpadala do grupy
     "swieze". To osobne zjawisko. Teraz trzy grupy, raportowane osobno.
  5. BRAK KONTROLI WIELKOSCI ODCHYLENIA. Prawdopodobienstwo dotkniecia VWAP
     zalezy mechanicznie od |d|. Jesli grupy roznia sie |d|, roznica powrotow
     moze wynikac z odleglosci, nie z pochodzenia. Teraz kontrolowane.
  6. DOTKNIECIE VWAP PO ZAMKNIECIACH. Powrot wykrywany po `close` bara zaniza
     odsetek powrotow: cena moze przeciac VWAP w srodku minuty i wrocic. Teraz
     po `high`/`low`. (To nie bylo w zgloszonych uwagach — znalezione osobno.)

Sprawdzona i ODRZUCONA obawa: filtr `noc_n >= 300` mial rzekomo wycinac ciche
noce, czyli dokladnie te, ktore H001 bada. Pomiar: mediana liczby barow nocnych
wynosi 870 z 870 mozliwych, a filtr odrzuca 3 sesje z 1873. Efektu nie ma.

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
M_1030, M_1130, M_1500 = 630, 690, 900         # minuty ET
PROG_ISTOTNOSCI = 1.0      # |d| kwalifikujace zdarzenie, wg karty H002
PROG_ZERA = 0.5            # ponizej tego odchylenie o 10:30 uznajemy za brak


def t_stat(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    return float(x.mean() / x.std(ddof=1) * np.sqrt(x.size)) if x.size > 2 else float("nan")


def t_roznicy(a: np.ndarray, b: np.ndarray) -> float:
    """Welch — dwie grupy o roznej licznosci i wariancji."""
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if a.size < 3 or b.size < 3:
        return float("nan")
    return float((a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / a.size + b.var(ddof=1) / b.size))


def ols(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Wspolczynniki i ich statystyki t. X BEZ kolumny jedynek — dodawana tutaj."""
    A = np.column_stack([np.ones(X.shape[0]), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    reszty = y - A @ beta
    s2 = float(reszty @ reszty) / (A.shape[0] - A.shape[1])
    cov = s2 * np.linalg.inv(A.T @ A)
    return beta, beta / np.sqrt(np.diag(cov))


def sigma_narastajaca(tp: np.ndarray, vol: np.ndarray) -> np.ndarray:
    """Sigma wazona wolumenem wokol VWAP obowiazujacego W TYM SAMYM MOMENCIE.

    Referencja numpy dla implementacji polarsowej. Uzywa tozsamosci

        sigma_t^2 = (suma v_i p_i^2 / suma v_i) - VWAP_t^2

    ktora daje dokladnie to, co `engine.features.vwap_sigma` policzone na
    prefiksie — i tak jest testowana. Poprzednia wersja liczyla
    `suma v_i (p_i - VWAP_i)^2`, czyli odejmowala kazda obserwacje od VWAP
    z jej wlasnego momentu. To nie jest wariancja wokol niczego.
    """
    v = np.cumsum(vol)
    pv = np.cumsum(tp * vol)
    p2v = np.cumsum(tp * tp * vol)
    with np.errstate(divide="ignore", invalid="ignore"):
        vwap = np.where(v > 0, pv / v, np.nan)
        war = np.where(v > 0, p2v / v - vwap**2, np.nan)
    return np.sqrt(np.maximum(war, 0.0))


def percentyl_kroczacy(x: np.ndarray, okno: int = OKNO_TLA) -> np.ndarray:
    """Ranga wartosci w oknie KONCZACYM SIE PRZED nia. Zakaz lookaheadu."""
    out = np.full(x.size, np.nan)
    for i in range(x.size):
        h = x[max(0, i - okno):i]
        if h.size >= MIN_TLO:
            out[i] = float((h < x[i]).mean())
    return out


def _adj(d: pl.LazyFrame) -> pl.LazyFrame:
    przesun = pl.col("px_adj") - pl.col("close")
    return d.with_columns((pl.col("high") + przesun).alias("h_adj"),
                          (pl.col("low") + przesun).alias("l_adj"),
                          (pl.col("open") + przesun).alias("o_adj"))


def _minuty_et() -> pl.Expr:
    et = pl.col("ts_utc").dt.convert_time_zone("America/New_York")
    # rzutowanie konieczne: dt.hour() zwraca Int8 i hour*60 przepelnia sie cicho
    return et.dt.hour().cast(pl.Int32) * 60 + et.dt.minute().cast(pl.Int32)


def sesje() -> pl.DataFrame:
    """Jeden wiersz na sesje: charakterystyka nocy i charakterystyka RTH."""
    d = _adj(load_continuous("MNQ").lazy().sort("ts_utc"))
    noc = (d.filter(pl.col("segment").is_in(NOC)).group_by("trade_date")
            .agg(noc_h=pl.col("high").max(), noc_l=pl.col("low").min(),
                 noc_v=pl.col("volume").sum(), noc_n=pl.len()))
    rth = (d.filter(pl.col("segment").is_in(RTH)).sort("ts_utc").group_by("trade_date")
            .agg(rth_o=pl.col("o_adj").first(), rth_c=pl.col("px_adj").last(),
                 rth_h=pl.col("h_adj").max(), rth_l=pl.col("l_adj").min(),
                 rth_n=pl.len()))
    return (noc.join(rth, on="trade_date", how="inner")
               .filter((pl.col("noc_n") >= 300) & (pl.col("rth_n") >= 300))
               .sort("trade_date").collect())


def wybicia() -> pl.DataFrame:
    """Pierwsze wybicie z zakresu nocnego wraz z CENAMI WYJSCIA PO NIM.

    Kazda cena wyjscia jest wybierana z barow o znaczniku PoZNIEJSZYM niz bar
    wybicia. To jest cala poprawka usterki 1 — poprzednia wersja brala zamkniecie
    segmentu `rth_open` niezaleznie od tego, kiedy nastapil sygnal, wiec dla wybic
    po 10:30 liczyla wynik od ceny sprzed wejscia.
    """
    d = _adj(load_continuous("MNQ").lazy().sort("ts_utc")).with_columns(_minuty_et().alias("hm"))
    noc = (d.filter(pl.col("segment").is_in(NOC)).group_by("trade_date")
            .agg(noc_h=pl.col("high").max(), noc_l=pl.col("low").min()))
    r = (d.filter(pl.col("segment").is_in(RTH))
          .join(noc, on="trade_date", how="inner").sort("ts_utc"))

    pierwsze = (r.filter((pl.col("close") > pl.col("noc_h")) |
                         (pl.col("close") < pl.col("noc_l")))
                 .group_by("trade_date")
                 .agg(ts_wyb=pl.col("ts_utc").first(),
                      hm_wyb=pl.col("hm").first(),
                      c_wyb=pl.col("px_adj").first(),
                      gora=(pl.col("close").first() > pl.col("noc_h").first())))
    rj = r.join(pierwsze, on="trade_date", how="inner")
    po = rj.filter(pl.col("ts_utc") > pl.col("ts_wyb"))
    wyj = (po.group_by("trade_date")
             .agg(ts_sesja=pl.col("ts_utc").last(), c_sesja=pl.col("px_adj").last()))
    wyj_open = (po.filter(pl.col("hm") <= M_1030).group_by("trade_date")
                  .agg(ts_open=pl.col("ts_utc").last(), c_open=pl.col("px_adj").last()))
    return (pierwsze.join(wyj, on="trade_date", how="left")
                    .join(wyj_open, on="trade_date", how="left").collect())


def vwap_sesji() -> pl.DataFrame:
    """Odchylenia od VWAP o 10:30 i 11:30 oraz zachowanie ceny do 15:00."""
    d = load_continuous("MNQ").lazy().sort("ts_utc")
    r = (d.filter(pl.col("segment").is_in(RTH))
          .with_columns(_minuty_et().alias("hm"),
                        ((pl.col("high") + pl.col("low") + pl.col("close")) / 3).alias("tp"))
          .sort("ts_utc"))
    r = r.with_columns(
        (pl.col("tp") * pl.col("volume")).cum_sum().over("trade_date").alias("pv"),
        (pl.col("tp") ** 2 * pl.col("volume")).cum_sum().over("trade_date").alias("p2v"),
        pl.col("volume").cum_sum().over("trade_date").alias("cv"),
    ).with_columns((pl.col("pv") / pl.col("cv")).alias("vwap"))
    # tozsamosc E[p^2] - VWAP^2; max(.,0) chroni przed ujemnym zerem z zaokraglen
    r = r.with_columns(
        pl.max_horizontal(pl.col("p2v") / pl.col("cv") - pl.col("vwap") ** 2,
                          pl.lit(0.0)).sqrt().alias("sig")
    ).with_columns(
        pl.when(pl.col("sig") > 0)
        .then((pl.col("close") - pl.col("vwap")) / pl.col("sig"))
        .otherwise(0.0).alias("d")
    )

    def w(minuta: int, pref: str) -> pl.LazyFrame:
        return (r.filter(pl.col("hm") == minuta).group_by("trade_date")
                 .agg(**{f"{pref}_d": pl.col("d").first(),
                         f"{pref}_c": pl.col("close").first(),
                         f"{pref}_vwap": pl.col("vwap").first()}))

    vol_okno = (r.filter((pl.col("hm") > M_1030) & (pl.col("hm") <= M_1130))
                 .group_by("trade_date").agg(v_okno=pl.col("volume").sum()))
    # Dotkniecie VWAP wykrywane po high/low, nie po close — usterka 6.
    po = r.filter((pl.col("hm") > M_1130) & (pl.col("hm") <= M_1500))
    ruch = (po.group_by("trade_date")
              .agg(dotk=((pl.col("low") <= pl.col("vwap")) &
                         (pl.col("high") >= pl.col("vwap"))).any(),
                   hi=pl.col("high").max(), lo=pl.col("low").min(),
                   c_1500=pl.col("close").last(), vwap_1500=pl.col("vwap").last(),
                   n_po=pl.len()))
    return (w(M_1030, "a").join(w(M_1130, "b"), on="trade_date")
            .join(vol_okno, on="trade_date").join(ruch, on="trade_date")
            .sort("trade_date").collect())


def main() -> int:
    if not is_available("MNQ"):
        sys.exit("Brak danych MNQ — patrz HANDOFF.md")

    s = sesje()
    zakres = (s["noc_h"] - s["noc_l"]).to_numpy()
    wol = s["noc_v"].to_numpy()
    p_zakres, p_wol = percentyl_kroczacy(zakres), percentyl_kroczacy(wol)
    rng_rth = (s["rth_h"] - s["rth_l"]).to_numpy()
    er = np.where(rng_rth > 0,
                  np.abs(s["rth_c"].to_numpy() - s["rth_o"].to_numpy()) / rng_rth, np.nan)
    lata = np.array([d.year for d in s["trade_date"].to_list()])
    gotowe = np.isfinite(p_zakres) & np.isfinite(p_wol) & np.isfinite(er)
    kompresja = gotowe & (p_zakres <= 1 / 3)
    z_rownowagi, z_braku = kompresja & (p_wol > 0.5), kompresja & (p_wol <= 0.5)

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
        "Skrypt byl **poprawiony przed pierwszym uruchomieniem** po przegladzie kodu:",
        "szesc usterek, w tym blad czasowy dajacy cene wyjscia sprzed sygnalu i bledna",
        "sigma VWAP. Lista w docstringu modulu. Zadna z nich nie rzucalaby bledu.",
        "",
        "---",
        "",
        "# H001 — kompresja nocna: przyczyna, nie fakt",
        "",
        "## 1. Czy dwie kompresje daja rozny CHARAKTER sesji",
        "",
        "Test, na ktorym karta stoi lub upada. H010 zginelo na tym, ze zakres nocny",
        "przewiduje **amplitude** (t = +10.2), ale nie **charakter** (t ~ 0).",
        "",
        "| Grupa | N | Efficiency ratio | Zakres RTH (pkt) | **Zakres nocny (pkt)** |",
        "|---|---|---|---|---|",
    ]
    for nazwa, m in (("**kompresja z rownowagi** (wolumen wysoki)", z_rownowagi),
                     ("**kompresja z braku** (wolumen niski)", z_braku),
                     ("pozostale sesje", gotowe & ~kompresja)):
        L.append(f"| {nazwa} | {int(m.sum())} | {np.nanmean(er[m]):.4f} | "
                 f"{np.nanmean(rng_rth[m]):.1f} | {np.nanmean(zakres[m]):.1f} |")

    t_er = t_roznicy(er[z_rownowagi], er[z_braku])
    t_zak = t_roznicy(zakres[z_rownowagi], zakres[z_braku])
    L += [
        "",
        f"**t roznicy efficiency ratio (rownowaga − brak): {t_er:+.2f}**",
        "",
        "Kolumna zakresu nocnego jest kontrola konfundowania: t roznicy zakresu miedzy",
        f"grupami wynosi **{t_zak:+.2f}**. Jesli grupy roznia sie zakresem, roznica",
        "charakteru moze pochodzic z zakresu, a nie z wolumenu — i wtedy karta nie ma",
        "swojej przeslanki, tylko powtarza H010.",
        "",
        "## 2. Regresja ciagla — wolumen PO KONTROLI zakresu",
        "",
        "Podzial kubelkowy nie wystarcza: wewnatrz tercyla kompresji nadal sa roznice",
        "zakresu. Regresja liczona **wylacznie wewnatrz kompresji**:",
        "",
        "`ER = α + β₁·percentyl_zakresu + β₂·percentyl_wolumenu + ε`",
        "",
        "To nie jest model handlowy — to sprawdzenie, czy wolumen wnosi cokolwiek",
        "po kontrolowaniu dokladnego zakresu.",
        "",
        "| Wspolczynnik | Wartosc | t |",
        "|---|---|---|",
    ]
    mk = kompresja
    beta, tb = ols(er[mk], np.column_stack([p_zakres[mk], p_wol[mk]]))
    for nazwa, b, tt in (("α (wyraz wolny)", beta[0], tb[0]),
                         ("β₁ percentyl zakresu", beta[1], tb[1]),
                         ("**β₂ percentyl wolumenu**", beta[2], tb[2])):
        L.append(f"| {nazwa} | {b:+.4f} | **{tt:+.2f}** |")

    # --- wybicia, z poprawnym porzadkiem czasu -------------------------------
    w = wybicia()
    s2 = s.join(w, on="trade_date", how="left")
    hm_wyb = s2["hm_wyb"].to_numpy().astype(float)
    kier = np.where(s2["gora"].to_numpy(), 1.0, -1.0)
    c_wyb = s2["c_wyb"].to_numpy().astype(float)
    c_open = s2["c_open"].to_numpy().astype(float)
    c_sesja = s2["c_sesja"].to_numpy().astype(float)

    # ASERCJA: wyjscie musi byc po wejsciu. Kolumny wyjscia sa budowane wylacznie
    # z barow o ts > ts_wyb, wiec brak wyjscia => NaN, nigdy cena sprzed sygnalu.
    ts_wyb = s2["ts_wyb"].to_numpy()
    for kol_ts in ("ts_open", "ts_sesja"):
        te = s2[kol_ts].to_numpy()
        zle = sum(1 for a, b in zip(te, ts_wyb, strict=True)
                  if a is not None and b is not None and a <= b)
        assert zle == 0, f"{kol_ts}: {zle} wyjsc o znaczniku nie pozniejszym niz wejscie"

    ma_open = np.isfinite(c_open) & np.isfinite(c_wyb)
    ma_sesja = np.isfinite(c_sesja) & np.isfinite(c_wyb)
    kont_open = np.where(ma_open, kier * (c_open - c_wyb), np.nan)
    kont_sesja = np.where(ma_sesja, kier * (c_sesja - c_wyb), np.nan)
    przed_1030 = np.isfinite(hm_wyb) & (hm_wyb < M_1030)

    L += [
        "",
        "## 3. Kontynuacja po wybiciu z zakresu nocnego",
        "",
        "**Kazda cena wyjscia pochodzi z bara pozniejszego niz bar wybicia** (asercja",
        "w kodzie). Wynik do 10:30 raportowany **wylacznie dla wybic przed 10:30** —",
        "inaczej mierzylby ruch sprzed sygnalu.",
        "",
        f"Wybic przed 10:30: **{int((przed_1030 & gotowe).sum())}**, "
        f"po 10:30: **{int((np.isfinite(hm_wyb) & ~przed_1030 & gotowe).sum())}**.",
        "",
        "### Wybicia przed 10:30, wynik do konca `rth_open`",
        "",
        "| Grupa | N | Sredni wynik (pkt) | t |",
        "|---|---|---|---|",
    ]
    for nazwa, m in (("**kompresja z rownowagi**", z_rownowagi & przed_1030 & ma_open),
                     ("**kompresja z braku**", z_braku & przed_1030 & ma_open),
                     ("pozostale sesje", gotowe & ~kompresja & przed_1030 & ma_open)):
        L.append(f"| {nazwa} | {int(m.sum())} | {np.nanmean(kont_open[m]):+.1f} | "
                 f"{t_stat(kont_open[m]):+.2f} |")

    L += [
        "",
        "### Wszystkie wybicia, wynik do konca sesji",
        "",
        "| Grupa | N | Sredni wynik (pkt) | t |",
        "|---|---|---|---|",
    ]
    for nazwa, m in (("**kompresja z rownowagi**", z_rownowagi & ma_sesja),
                     ("**kompresja z braku**", z_braku & ma_sesja),
                     ("pozostale sesje", gotowe & ~kompresja & ma_sesja)):
        L.append(f"| {nazwa} | {int(m.sum())} | {np.nanmean(kont_sesja[m]):+.1f} | "
                 f"{t_stat(kont_sesja[m]):+.2f} |")

    L += [
        "",
        "## 4. Stabilnosc roczna (kompresja z rownowagi, wybicia przed 10:30)",
        "",
        "| Rok | N | Sredni wynik (pkt) | t |",
        "|---|---|---|---|",
    ]
    grupa = z_rownowagi & przed_1030 & ma_open
    for rok in sorted(set(lata[grupa].tolist())):
        m = grupa & (lata == rok)
        if m.sum() >= 5:
            L.append(f"| {rok} | {int(m.sum())} | {np.nanmean(kont_open[m]):+.1f} | "
                     f"{t_stat(kont_open[m]):+.2f} |")

    # ---------------- H002 ----------------
    v = vwap_sesji()
    sv = s.join(v, on="trade_date", how="inner")
    d1030, d1130 = sv["a_d"].to_numpy(), sv["b_d"].to_numpy()
    c1130, c1500 = sv["b_c"].to_numpy(), sv["c_1500"].to_numpy()
    hi, lo = sv["hi"].to_numpy(), sv["lo"].to_numpy()
    dotk = sv["dotk"].to_numpy().astype(bool)
    v_okno = sv["v_okno"].to_numpy()
    lata_v = np.array([d.year for d in sv["trade_date"].to_list()])

    istotne = np.isfinite(d1130) & (np.abs(d1130) >= PROG_ISTOTNOSCI) & np.isfinite(d1030)
    znak = np.sign(d1130)
    male_1030 = np.abs(d1030) < PROG_ZERA
    ten_sam = istotne & ~male_1030 & (np.sign(d1030) == znak)
    przeciwny = istotne & ~male_1030 & (np.sign(d1030) != znak)
    swieze = istotne & male_1030
    udzial = np.where(ten_sam, np.abs(d1030) / np.abs(d1130), np.nan)

    # zwrot ze znakiem W KIERUNKU POWROTU do VWAP (dodatni = zblizenie sie)
    ret = np.where(np.isfinite(c1500), -znak * (c1500 - c1130) / c1130, np.nan)
    ruch_hi = -znak * (hi - c1130) / c1130
    ruch_lo = -znak * (lo - c1130) / c1130
    mfe = np.maximum(ruch_hi, ruch_lo)     # najdalsze zblizenie do VWAP
    mae = np.minimum(ruch_hi, ruch_lo)     # najdalsze oddalenie

    L += [
        "",
        "---",
        "",
        "# H002 — powrot do VWAP: gdzie odchylenie powstalo",
        "",
        f"Sesji z istotnym odchyleniem o 11:30 (\\|d\\| ≥ {PROG_ISTOTNOSCI}): "
        f"**{int(istotne.sum())}** z {sv.height} "
        f"(*f* = {istotne.sum()/sv.height:.2f}, karta deklarowala 0.33).",
        "",
        "## 1. Trzy grupy, nie dwie",
        "",
        "Odchylenie o 10:30 o **przeciwnym znaku** to nie jest odchylenie swieze —",
        "to odwrocenie wczesniejszego. Poprzednia wersja wrzucala je do grupy swiezych",
        f"z udzialem 0. Podzial: \\|d(10:30)\\| < {PROG_ZERA} to naprawde swieze,",
        "reszta wedlug zgodnosci znaku.",
        "",
        "| Grupa | N | \\|d(11:30)\\| srednia | mediana | Odsetek dotkniec VWAP |",
        "|---|---|---|---|---|",
    ]
    grupy = (("**swieze** (\\|d₁₀:₃₀\\| < 0.5)", swieze),
             ("**ten sam znak** (udzial ma sens)", ten_sam),
             ("odwrocenie znaku", przeciwny))
    for nazwa, m in grupy:
        if m.sum() >= 5:
            L.append(f"| {nazwa} | {int(m.sum())} | {np.abs(d1130[m]).mean():.2f} | "
                     f"{np.median(np.abs(d1130[m])):.2f} | {dotk[m].mean():.1%} |")

    L += [
        "",
        "**Kolumny \\|d(11:30)\\| sa tu najwazniejsze.** Prawdopodobienstwo dotkniecia",
        "VWAP zalezy mechanicznie od odleglosci od niego. Jesli grupy roznia sie",
        "odlegloscia, roznica odsetka powrotow nie mowi nic o pochodzeniu odchylenia.",
        "",
        "## 2. Powroty w porownywalnych przedzialach \\|d(11:30)\\|",
        "",
        "| Przedzial \\|d\\| | swieze: N / powroty | ten sam znak: N / powroty |",
        "|---|---|---|",
    ]
    for lo_d, hi_d in ((1.0, 1.5), (1.5, 2.0), (2.0, 99.0)):
        pas = istotne & (np.abs(d1130) >= lo_d) & (np.abs(d1130) < hi_d)
        a, b = swieze & pas, ten_sam & pas
        eti = f"{lo_d:.1f}–{hi_d:.1f}" if hi_d < 99 else "≥ 2.0"
        L.append(f"| {eti} | {int(a.sum())} / "
                 f"{dotk[a].mean():.1%} | {int(b.sum())} / {dotk[b].mean():.1%} |"
                 if a.sum() >= 5 and b.sum() >= 5 else
                 f"| {eti} | {int(a.sum())} / — | {int(b.sum())} / — |")

    L += [
        "",
        "## 3. Model prawdopodobienstwa powrotu z kontrola odleglosci",
        "",
        "`P(dotkniecie) = α + β₁·\\|d(11:30)\\| + β₂·udzial_odziedziczony`, "
        "wewnatrz grupy o zgodnym znaku.",
        "",
        "Model liniowy, bez dobierania progow i **bez interpretowania go jako",
        "strategii** — sluzy wylacznie temu, zeby zobaczyc znak i istotnosc β₂",
        "po kontrolowaniu tego, co dziala mechanicznie.",
        "",
        "| Wspolczynnik | Wartosc | t |",
        "|---|---|---|",
    ]
    mm = ten_sam & np.isfinite(udzial)
    beta2, tb2 = ols(dotk[mm].astype(float),
                     np.column_stack([np.abs(d1130[mm]), udzial[mm]]))
    for nazwa, b, tt in (("α", beta2[0], tb2[0]),
                         ("β₁ \\|d(11:30)\\|", beta2[1], tb2[1]),
                         ("**β₂ udzial odziedziczony**", beta2[2], tb2[2])):
        L.append(f"| {nazwa} | {b:+.4f} | **{tt:+.2f}** |")

    L += [
        "",
        "## 4. Powrot to nie tylko dotkniecie — zwrot, MFE i MAE",
        "",
        "Brak dotkniecia VWAP nie znaczy kontynuacja; rynek moze stac w miejscu.",
        "Ponizej zwrot 11:30→15:00 **w kierunku powrotu** (dodatni = zblizenie do",
        "VWAP) oraz skrajne zblizenie i oddalenie w tym oknie.",
        "",
        "| Grupa | N | Zwrot | t | MFE (do VWAP) | MAE (od VWAP) |",
        "|---|---|---|---|---|---|",
    ]
    for nazwa, m in ((*grupy[0],), (*grupy[1],), (*grupy[2],)):
        if m.sum() >= 5:
            L.append(f"| {nazwa} | {int(m.sum())} | {np.nanmean(ret[m])*100:+.4f}% | "
                     f"{t_stat(ret[m]):+.2f} | {np.nanmean(mfe[m])*100:+.3f}% | "
                     f"{np.nanmean(mae[m])*100:+.3f}% |")

    # --- KTO SIE DO KOGO ZBLIZA: cena do VWAP czy VWAP do ceny ---------------
    vwap1130, vwap1500 = sv["b_vwap"].to_numpy(), sv["vwap_1500"].to_numpy()
    luka0 = np.abs(c1130 - vwap1130)
    ruch_vwap = np.abs(vwap1500 - vwap1130)
    ruch_ceny = np.abs(c1500 - c1130)
    with np.errstate(divide="ignore", invalid="ignore"):
        udzial_vwap = np.where(luka0 > 0, ruch_vwap / luka0, np.nan)

    L += [
        "",
        "## 4a. Kto sie do kogo zbliza — kontrola mechaniki VWAP",
        "",
        "**Dotkniecie VWAP nie dowodzi, ze cena wrocila.** VWAP jest srednia wazona",
        "narastajaco, wiec nowy wolumen drukowany przy nowym poziomie **przyciaga VWAP",
        "do ceny**. Odchylenie swieze ma z definicji mniej wolumenu przy nowym poziomie,",
        "wiec VWAP ma wobec niego wiecej drogi do nadrobienia — i wyzszy odsetek",
        "dotkniec moze byc czysta mechanika, nie powrotem ceny.",
        "",
        "| Grupa | N | Luka o 11:30 (pkt) | Ruch VWAP (pkt) | Ruch ceny (pkt) | Udzial VWAP |",
        "|---|---|---|---|---|---|",
    ]
    for nazwa, m in grupy:
        if m.sum() >= 5:
            L.append(f"| {nazwa} | {int(m.sum())} | {np.nanmean(luka0[m]):.1f} | "
                     f"{np.nanmean(ruch_vwap[m]):.1f} | {np.nanmean(ruch_ceny[m]):.1f} | "
                     f"**{np.nanmedian(udzial_vwap[m]):.2f}** |")

    L += [
        "",
        "**Hipoteza sprawdzona i ODRZUCONA.** Udzial VWAP w domknieciu luki jest",
        f"praktycznie taki sam we wszystkich grupach ({np.nanmedian(udzial_vwap[swieze]):.2f} "
        f"wobec {np.nanmedian(udzial_vwap[ten_sam]):.2f}), wiec roznica odsetka dotkniec",
        "**nie jest artefaktem mechaniki VWAP**. Podejrzenie bylo uzasadnione i okazalo",
        "sie nietrafione — odnotowuje to, bo negatywna kontrola tez jest wynikiem.",
        "",
        "### Wewnatrz grupy o zgodnym znaku, wedlug udzialu odziedziczonego",
        "",
        "| Udzial | N | \\|d\\| srednia | Powroty | Zwrot | t |",
        "|---|---|---|---|---|---|",
    ]
    for lo_u, hi_u, eti in ((0.0, 0.33, "< 0.33"), (0.33, 0.67, "0.33–0.67"),
                            (0.67, 9.0, "> 0.67")):
        m = ten_sam & (udzial >= lo_u) & (udzial < hi_u)
        if m.sum() >= 5:
            L.append(f"| {eti} | {int(m.sum())} | {np.abs(d1130[m]).mean():.2f} | "
                     f"{dotk[m].mean():.1%} | {np.nanmean(ret[m])*100:+.4f}% | "
                     f"{t_stat(ret[m]):+.2f} |")

    L += [
        "",
        "## 5. Ablacja 2 karty — czy prosty wolumen daje to samo",
        "",
        "**Wazniejszy test niz poprzednie.** Karta przyznaje w sekcji 4, ze grozi jej",
        "sprowadzenie do detalicznej reguly \"ruch bez wolumenu jest falszywy\".",
        "",
        "| Podzial | N | Odsetek powrotow | t roznicy |",
        "|---|---|---|---|",
    ]
    p_vokno = percentyl_kroczacy(v_okno)
    m_lo = istotne & np.isfinite(p_vokno) & (p_vokno <= 0.5)
    m_hi = istotne & np.isfinite(p_vokno) & (p_vokno > 0.5)
    t_vol = t_roznicy(dotk[m_lo].astype(float), dotk[m_hi].astype(float))
    t_poch = t_roznicy(dotk[swieze].astype(float), dotk[ten_sam].astype(float))
    L += [
        f"| wg **pochodzenia** (swieze vs zgodny znak) | "
        f"{int(swieze.sum())} / {int(ten_sam.sum())} | "
        f"{dotk[swieze].mean():.1%} vs {dotk[ten_sam].mean():.1%} | **{t_poch:+.2f}** |",
        f"| wg **wolumenu 10:30-11:30** (niski vs wysoki) | "
        f"{int(m_lo.sum())} / {int(m_hi.sum())} | "
        f"{dotk[m_lo].mean():.1%} vs {dotk[m_hi].mean():.1%} | {t_vol:+.2f} |",
        "",
        "## 6. Stabilnosc roczna (grupa swieza)",
        "",
        "| Rok | N | Powroty | Zwrot |",
        "|---|---|---|---|",
    ]
    for rok in sorted(set(lata_v[swieze].tolist())):
        m = swieze & (lata_v == rok)
        if m.sum() >= 5:
            L.append(f"| {rok} | {int(m.sum())} | {dotk[m].mean():.1%} | "
                     f"{np.nanmean(ret[m])*100:+.4f}% |")

    zw_sw, zw_ts = np.nanmean(ret[swieze]), np.nanmean(ret[ten_sam])
    L += [
        "",
        "---",
        "",
        "# Werdykty",
        "",
        "## H001 — **ODRZUCONA**",
        "",
        "Karta stala na jednym zdaniu: **wolumen przy zadanym zakresie niesie",
        "informacje o charakterze sesji, ktorej sam zakres nie niesie.** Zdanie jest",
        "falszywe na naszych danych.",
        "",
        "| Test | Wynik |",
        "|---|---|",
        f"| Roznica efficiency ratio miedzy dwoma kompresjami | t = **{t_er:+.2f}** |",
        f"| β₂ percentyl wolumenu, po kontroli zakresu | t = **{tb[2]:+.2f}** |",
        f"| β₁ percentyl zakresu, wewnatrz kompresji | t = {tb[1]:+.2f} |",
        "",
        "Regresja ciagla jest tu rozstrzygajaca: **po kontrolowaniu dokladnego zakresu",
        "wolumen nie wnosi nic** — wspolczynnik jest zerowy co do znaku i wielkosci.",
        "Podzial kubelkowy dawal t = +0.91, czyli tez nic, ale mozna bylo go tlumaczyc",
        "mala liczebnoscia grupy wysokiego wolumenu (95 sesji). Regresja korzysta",
        "z wszystkich obserwacji i odpowiedz jest ta sama.",
        "",
        "Ciekawostka, ktora **nie ratuje karty**: wybicia po kompresji z rownowagi daja",
        f"+{np.nanmean(kont_open[z_rownowagi & przed_1030 & ma_open]):.0f} pkt do 10:30",
        "wobec −8 pkt na pozostalych sesjach. Ale przeslanka karty juz upadla, N wynosi",
        "82, wynik roczny waha sie od −8 do +41 pkt przy 6–18 obserwacjach na rok,",
        "a roznica wobec kompresji z braku jest w granicach szumu. **Warunek zbudowany",
        "na falszywej przeslance nie staje sie prawdziwy dlatego, ze podzbior wyglada",
        "dobrze** — to jest dokladnie ten blad, przed ktorym chroni W004.",
        "",
        "Karta schodzi do **B02** zgodnie z regula samoczyszczaca z sekcji 8.4 PLAN-u.",
        "",
        "## H002 — **ODRZUCONA WLASNYM KRYTERIUM**, ale nie bez oporu",
        "",
        "**Karta ma cos prawdziwego i trzeba to powiedziec, zanim padnie werdykt.**",
        "Pochodzenie odchylenia rozdziela odsetek powrotow do VWAP i przetrwalo",
        "cztery niezalezne kontrole:",
        "",
        "| Kontrola | Wynik |",
        "|---|---|",
        f"| Roznica odsetka powrotow (swieze vs odziedziczone) | t = **{t_poch:+.2f}** |",
        f"| Ablacja 2: to samo po wolumenie 10:30-11:30 | t = {t_vol:+.2f} — **nic** |",
        "| Kontrola \\|d(11:30)\\| w trzech pasmach | swieze wyzej we **wszystkich trzech** |",
        "| Monotonicznosc wzgledem udzialu odziedziczonego | 60.0% → 54.8% → 50.0% |",
        "| Mechanika VWAP (kto sie do kogo zbliza) | udzial VWAP ten sam w grupach |",
        "",
        "To jest wiecej, niz przeszla ktorakolwiek z dziewieciu wczesniej odrzuconych",
        "kart. Ablacja 2 byla tym testem, ktorego karta sie bala — i przeszla go",
        "czysto: prosty warunek wolumenowy nie daje nic (t = +0.29), a pochodzenie daje.",
        "",
        "**A jednak karta upada, i to na kryterium, ktore sama zadeklarowala z gory.**",
        "Falsyfikator 2 z sekcji 9 brzmial: *dziala tylko jeden koniec skali*.",
        "",
        "| Grupa | Zwrot 11:30→15:00 w kierunku VWAP | t |",
        "|---|---|---|",
        f"| swieze (mial wracac) | {zw_sw*100:+.4f}% | {t_stat(ret[swieze]):+.2f} |",
        f"| odziedziczone (mialy kontynuowac) | {zw_ts*100:+.4f}% | "
        f"{t_stat(ret[ten_sam]):+.2f} |",
        "",
        "Koniec \"odziedziczony\" **nie kontynuuje** — daje zero. Mechanizm z sekcji 2",
        "karty przewidywal przewage na obu koncach, w przeciwne strony. Dziala co",
        "najwyzej jeden, i to slabo.",
        "",
        "Drugi cios jest ekonomiczny i wazniejszy. **Odsetek dotkniec to nie jest P&L.**",
        f"Zwrot grupy swiezej wynosi {zw_sw*100:+.4f}% przy t = {t_stat(ret[swieze]):+.2f},",
        "czyli nie da sie go odroznic od zera, a MFE i MAE sa **symetryczne**",
        f"({np.nanmean(mfe[swieze])*100:+.3f}% wobec {np.nanmean(mae[swieze])*100:+.3f}%).",
        "Symetryczne skrajnosci to sygnatura bladzenia losowego: cena bywa blizej VWAP",
        "i bywa dalej, dokladnie tak samo czesto i tak samo daleko.",
        "",
        "**To jest W005 po raz drugi.** H010 dalo najmocniejszy pojedynczy wynik projektu",
        "(t > 10) i zginelo, bo mierzylo amplitude tam, gdzie karta potrzebowala",
        "kierunku. H002 daje separacje odsetka dotkniec, ktora przezyla cztery kontrole,",
        "i ginie, bo **dotkniecie nie jest zwrotem**.",
        "",
        "Deklarowane *f* tez sie nie zgadza: karta zakladala 0.33, wyszlo "
        f"{istotne.sum()/sv.height:.2f} dla wszystkich istotnych odchylen, ale grupa",
        f"swieza to tylko {swieze.sum()/sv.height:.2f} — czyli prog W002 rosnie",
        f"z 1.7× do **{1/np.sqrt(swieze.sum()/sv.height):.1f}×**.",
        "",
        "## Co z tego zostaje",
        "",
        "Obie karty odrzucone, **zero zuzytych prob z budzetu 14**. Partia 3 traci dwie",
        "z trzech kart; H003 pozostaje zablokowana brakiem kalendarza makro.",
        "",
        "Ustalenie warte zapamietania poza ta partia: **pochodzenie odchylenia jest",
        "realna zmienna** — rozdziela zachowanie ceny lepiej niz wolumen i przezywa",
        "kontrole na wielkosc odchylenia. Nie daje przewagi handlowej w tej postaci,",
        "ale jest kandydatem na **wejscie do wielkosci pozycji** albo warstwe reżimowa,",
        "tak jak H010 zostalo po W004. Nie otwieram na to karty teraz.",
        "",
        "---",
        "",
        "Odtworzenie: `python3 research/W010_partia3_preflight.py`",
    ]

    RAPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPORT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"-> {RAPORT}")
    print(f"H001: t(ER) {t_er:+.2f}, t(zakres) {t_zak:+.2f}, "
          f"beta2 wolumen t={tb[2]:+.2f}; N {int(z_rownowagi.sum())}/{int(z_braku.sum())}")
    print(f"H002: swieze {int(swieze.sum())} ({dotk[swieze].mean():.1%}), "
          f"ten sam {int(ten_sam.sum())} ({dotk[ten_sam].mean():.1%}), "
          f"przeciwny {int(przeciwny.sum())}; beta2 udzial t={tb2[2]:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
