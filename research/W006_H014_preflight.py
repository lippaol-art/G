#!/usr/bin/env python3
"""W006 — pre-flight H014: dywergencja NQ-ES.  PLAN.pdf rozdz. 8.4, wniosek W002.

Karta H014 twierdzi, ze NDX PRZEreagowuje na szok stopowy wzgledem SPX, wiec
rezyduum NQ - beta*ES powinno sie odwracac. Karta byla czesciowo testowalna bez
dokupywania danych: NQ i ES sa w repo od Etapu 1.

Brakujacym elementem jest kalendarz zdarzen makro (rozdz. 4.5). Zamiast go
zmyslac, uzywamy naturalnego proxy: **wielkosci rezyduum pierwszej godziny**.
Szok stopowy, jesli dziala tak, jak opisuje mechanizm, musi sie objawic wlasnie
duzym rezyduum — wiec warunkowanie na jego wielkosci testuje te sama przeslanke.

Zero zuzytych prob — badanie rozkladow, nie backtest.

Wyjscie: reports/W006_H014_preflight.md
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.costs import POINT_VALUE  # noqa: E402
from engine.loader import is_available, load_continuous  # noqa: E402

RAPORT = Path("reports/W006_H014_preflight.md")
PIERWSZA_GODZINA = ["rth_open"]                       # 09:30-10:30 ET
RESZTA_SESJI = ["midday", "afternoon", "close"]       # 10:30-16:00 ET
POZIOM_INDEKSU = 23000.0     # rzad wielkosci MNQ na koniec probki — do przeliczen na USD
KOSZT_1_NOGA, KOSZT_2_NOGI = 2.20, 4.40


def t_stat(x: np.ndarray) -> float:
    return float(x.mean() / x.std(ddof=1) * np.sqrt(x.size))


def noga(symbol: str, segmenty: list[str], pref: str) -> pl.DataFrame:
    """Zwrot sesyjny odcinka, na serii skorygowanej (rozdz. 4.3)."""
    d = load_continuous(symbol)
    adj = pl.col("px_adj") - pl.col("close")
    d = d.with_columns((pl.col("open") + adj).alias("o_adj")).sort("ts_utc")
    return (d.filter(pl.col("segment").is_in(segmenty)).group_by("trade_date")
             .agg(**{f"{pref}o": pl.col("o_adj").first(),
                     f"{pref}c": pl.col("px_adj").last(),
                     f"{pref}n": pl.len()}).sort("trade_date"))


def main() -> int:
    for s in ("NQ", "ES"):
        if not is_available(s):
            sys.exit(f"Brak danych {s} — patrz HANDOFF.md")

    j = (noga("NQ", PIERWSZA_GODZINA, "n1")
         .join(noga("NQ", RESZTA_SESJI, "n2"), on="trade_date")
         .join(noga("ES", PIERWSZA_GODZINA, "e1"), on="trade_date")
         .join(noga("ES", RESZTA_SESJI, "e2"), on="trade_date")
         .filter((pl.col("n1n") >= 40) & (pl.col("n2n") >= 200)
                 & (pl.col("e1n") >= 40) & (pl.col("e2n") >= 200)))

    r1n = np.log(j["n1c"] / j["n1o"]).to_numpy()
    r1e = np.log(j["e1c"] / j["e1o"]).to_numpy()
    r2n = np.log(j["n2c"] / j["n2o"]).to_numpy()
    r2e = np.log(j["e2c"] / j["e2o"]).to_numpy()
    b1 = float(np.polyfit(r1e, r1n, 1)[0])
    b2 = float(np.polyfit(r2e, r2n, 1)[0])
    z1, z2 = r1n - b1 * r1e, r2n - b2 * r2e
    r_sesja = np.log(j["n2c"] / j["n1o"]).to_numpy()
    lata = np.array([d.year for d in j["trade_date"].to_list()])

    L: list[str] = [
        "# W006 — pre-flight H014 (dywergencja NQ-ES)",
        "",
        f"*Wygenerowane przez `research/W006_H014_preflight.py`, "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}. N = {j.height} dni wspolnych.*",
        "",
        "**Status licznika prob: 0 zuzytych.**",
        "",
        "Karta twierdzi, ze NDX **przereagowuje** na szok stopowy wzgledem SPX, wiec",
        "rezyduum NQ − β·ES powinno sie odwracac. Kalendarza makro jeszcze nie mamy,",
        "wiec zamiast go zmyslac uzywamy proxy: **wielkosci rezyduum pierwszej godziny**.",
        "Szok, jesli dziala jak opisuje mechanizm, musi sie objawic duzym rezyduum.",
        "",
        "## 1. Konstrukcja rezyduum",
        "",
        "| Wielkosc | Wartosc |",
        "|---|---|",
        f"| β(NQ~ES), pierwsza godzina | {b1:.3f} |",
        f"| β(NQ~ES), reszta sesji | {b2:.3f} |",
        f"| sd zwrotu NQ (cala sesja) | {r_sesja.std(ddof=1)*100:.3f}% |",
        f"| **sd rezyduum NQ − βES** | **{z2.std(ddof=1)*100:.3f}%** |",
        f"| **Redukcja szumu przez hedge ES** | **{(1 - z2.std(ddof=1)/r_sesja.std(ddof=1))*100:.0f}%** |",
        "",
        "Redukcja szumu jest realna i duza — i to ona czyni te karte atrakcyjna",
        "na papierze, bo obniza wymagany edge o ten sam czynnik. Sekcja 4 pokazuje,",
        "dlaczego to nie wystarcza.",
        "",
        "## 2. Przewidywanie mechanizmu: rezyduum ma sie ODWRACAC",
        "",
        f"korelacja(z₁, z₂) = **{np.corrcoef(z1, z2)[0,1]:+.4f}** "
        "— dodatnia oznacza kontynuacje, ujemna odwrocenie.",
        "",
        "| Warunek | *f* | N | Sredni wynik fade'u | t |",
        "|---|---|---|---|---|",
    ]
    for q, nazwa in ((0.9, "gorny decyl \\|z₁\\|"), (2 / 3, "gorny tercyl \\|z₁\\|"),
                     (0.0, "wszystkie dni")):
        m = np.abs(z1) >= np.quantile(np.abs(z1), q)
        pnl = -np.sign(z1[m]) * z2[m]
        L.append(f"| {nazwa} | {m.mean():.2f} | {m.sum()} | {pnl.mean()*100:+.4f}% | "
                 f"**{t_stat(pnl):+.2f}** |")
    L += [
        "",
        "### Werdykt: karta odrzucona, i to z dwoch niezaleznych powodow",
        "",
        "**Kierunek jest odwrotny** — rezyduum kontynuuje, zamiast wracac.",
        "",
        "**Warunkowanie dziala na opak** — i to jest rozstrzygajace. Efekt jest",
        "najsilniejszy na WSZYSTKICH dniach i najslabszy w gornym decylu. Gdyby",
        "mechanizm mowil prawde, byloby odwrotnie: im wiekszy szok, tym wieksze",
        "przereagowanie. Przeslanka o szoku stopowym zostaje tym obalona niezaleznie",
        "od znaku.",
        "",
        "Karte ze zlym znakiem mozna odwrocic. Karte, ktorej warunek warunkujacy",
        "**pogarsza** wynik, mozna tylko wyrzucic — bo to znaczy, ze warunek nie ma",
        "z efektem nic wspolnego.",
        "",
        "## 3. Wariant kontynuacyjny — statystycznie niezly",
        "",
    ]
    pnl = np.sign(z1) * z2
    sr_brutto = float(pnl.mean() / pnl.std(ddof=1) * np.sqrt(252))
    L += [
        "| Miara | Wartosc |",
        "|---|---|",
        f"| N (*f* = 1.00) | {pnl.size} |",
        f"| Sredni wynik | {pnl.mean()*100:+.4f}% dziennie |",
        f"| t | **{t_stat(pnl):+.2f}** |",
        f"| **Sharpe brutto** | **{sr_brutto:+.2f}** |",
        "",
        "### Stabilnosc roczna — test, ktory zabil H005",
        "",
        "| Rok | N | Sredni wynik | t | Udzial w wyniku |",
        "|---|---|---|---|---|",
    ]
    suma = pnl.sum()
    for y in sorted(set(lata)):
        m = lata == y
        x = pnl[m]
        L.append(f"| {y} | {m.sum()} | {x.mean()*100:+.4f}% | {t_stat(x):+.2f} | "
                 f"{x.sum()/suma:+.0%} |")
    dodatnie = sum(1 for y in sorted(set(lata)) if pnl[lata == y].mean() > 0)
    naj = max(sorted(set(lata)), key=lambda y: pnl[lata == y].sum())
    L += [
        "",
        f"Lat dodatnich: **{dodatnie} z {len(set(lata))}**. Najlepszy rok ({naj}) daje "
        f"**{pnl[lata == naj].sum()/suma:.0%}** wyniku.",
        "",
        "Stabilnosc jest tu **wyraznie lepsza niz w H005**, ktore zginelo na jednym roku",
        "dajacym ponad polowe wyniku. Statystycznie to wyglada na cos prawdziwego.",
        "",
        "## 4. Ekonomia — i tu wariant umiera",
        "",
        "| Struktura | Brutto/dzien | Koszt | Netto/dzien | **Sharpe netto** |",
        "|---|---|---|---|---|",
    ]
    brutto = pnl * POZIOM_INDEKSU * POINT_VALUE
    for nazwa, koszt in (("1 noga (tylko MNQ)", KOSZT_1_NOGA),
                         ("**2 nogi (MNQ + MES)**", KOSZT_2_NOGI),
                         ("2 nogi, stress ×2 (bramka 7.6)", 2 * KOSZT_2_NOGI)):
        netto = brutto - koszt
        sr = float(netto.mean() / netto.std(ddof=1) * np.sqrt(252))
        L.append(f"| {nazwa} | {brutto.mean():+.2f} USD | {koszt:.2f} | "
                 f"{netto.mean():+.2f} USD | **{sr:+.2f}** |")
    L += [
        "",
        f"**Koszty dwoch nog zjadaja {KOSZT_2_NOGI/brutto.mean():.0%} przewagi brutto.**",
        f"Sharpe spada z {sr_brutto:.2f} do {(brutto - KOSZT_2_NOGI).mean()/(brutto - KOSZT_2_NOGI).std(ddof=1)*np.sqrt(252):.2f}, "
        "a pod obowiazkowym stress-testem ×2 wynik jest **ujemny**.",
        "",
        "Jest w tym gorzka ironia: ta sama konstrukcja dwunozna, ktora redukuje szum",
        f"o {(1 - z2.std(ddof=1)/r_sesja.std(ddof=1))*100:.0f}% i przez to podnosi Sharpe brutto, wymaga drugiej nogi —",
        "a ta noga kosztuje wiecej, niz warta jest redukcja szumu przy tej wielkosci",
        "przewagi. **Hedge oplaca sie dopiero powyzej progu edge'u, ktorego tu nie ma.**",
        "",
        "Dlatego nie otwieram dla tego wariantu nowego ID. Zmierzony obiekt nie",
        "przechodzi bramki w zadnej ze swoich handlowalnych postaci; otwarcie karty",
        "oznaczaloby wydanie prob na cos, o czym juz wiemy, ze upada na kosztach.",
        "",
        "## 5. Wniosek przekrojowy W006",
        "",
        "> **Redukcja szumu przez hedge nie jest darmowa i przy malym edge'u jest",
        "> stratna.** Druga noga podwaja koszt round-turn (2.20 -> 4.40 USD), wiec",
        "> karta hedgowana musi wykazac przewage brutto **wyzsza niz wynikaloby z samego",
        "> progu Sharpe'a** — o tyle, ile kosztuje dodatkowa noga. Prog oplacalnosci",
        f"> hedge'u przy naszych kosztach: okolo **{KOSZT_2_NOGI/POINT_VALUE:.0f} punktow MNQ** przewagi brutto na",
        "> transakcje. Ponizej tego progu lepiej handlowac jedna noge z wiekszym szumem.",
        "",
        "Zastosowanie praktyczne: **H013 handluje jedna noge** (rezyduum jest tam",
        "sygnalem, nie pozycja), wiec tego problemu nie ma. Roznica strukturalna",
        "miedzy tymi kartami jest wieksza, niz sugeruje ich wspolna klasa K6.",
        "",
        "---",
        "",
        "Odtworzenie: `python3 research/W006_H014_preflight.py`",
    ]

    RAPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {RAPORT}")
    print(f"fade t (wszystkie/tercyl/decyl), SR brutto {sr_brutto:.2f}, "
          f"SR netto 2 nogi {(brutto-KOSZT_2_NOGI).mean()/(brutto-KOSZT_2_NOGI).std(ddof=1)*np.sqrt(252):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
