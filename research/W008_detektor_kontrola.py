#!/usr/bin/env python3
"""W008 — detektor reakcji jako KONTROLA kalendarza.  PLAN.pdf rozdz. 4.5, karta H013.

ROLA TEGO SKRYPTU JEST SCISLE OGRANICZONA I TO JEST CALY JEGO SENS.

Detektor liczy, gdzie w danych widac duza reakcje po zamknieciu sesji. **Nie
dodaje ani nie usuwa zadnego zdarzenia z proby H013.** Probe definiuje wylacznie
kalendarz EDGAR (`data/clean/earnings.csv`), bo wybieranie zdarzen po wielkosci
badanej reakcji byloby skazeniem selekcja — karta pokazalaby wtedy efekt
niezaleznie od tego, czy mechanizm istnieje.

Detektor odpowiada na trzy pytania, z ktorych zadne nie dotyczy skladu proby:

  1. KOMPLETNOSC DANYCH. Czy sa publikacje z kalendarza, przy ktorych nasze dane
     nie pokazuja zadnej reakcji ani obrotu? To wskazuje na dziure w danych
     cenowych, a nie na spokojna publikacje — i tego inaczej nie zobaczymy.

  2. TLO ZDARZENIOWE. Ile jest duzych reakcji po zamknieciu BEZ wpisu 8-K 2.02?
     To sa inne newsy: guidance, zmiany w zarzadzie, decyzje regulacyjne,
     przejecia, szoki sektorowe. Liczba ta jest wazna dla H013, bo mowi, jak
     czesto rezyduum moze byc napedzane czyms innym niz wyniki.

  3. CZY REAKCJA W OGOLE ISTNIEJE. Jesli publikacje wynikow nie odrozniaja sie
     rozkladem od zwyklych dni, przeslanka karty upada, zanim zaczniemy liczyc
     rezyduum.

Precision i recall sa tu miarami DETEKTORA wzgledem kalendarza, nie odwrotnie.
Kalendarz jest prawda; detektor jest testowany.

Zero zuzytych prob — badanie rozkladow, nie backtest.

Wyjscie: reports/W008_detektor_kontrola.md
"""

from __future__ import annotations

import csv
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.earnings import AMC, CIK  # noqa: E402

RAPORT = Path("reports/W008_detektor_kontrola.md")
KALENDARZ = Path("data/clean/earnings.csv")
K6 = Path("data/clean/k6")

OKNO_TLA = 60           # sesji do policzenia typowego obrotu i typowego ruchu
MIN_TLO = 30            # ponizej tego nie liczymy ilorazow — brak odniesienia


def reakcje_po_zamknieciu(symbol: str) -> pl.DataFrame:
    """Zwrot i obrot w oknie after-hours kazdej sesji, wraz z tlem kroczacym.

    OKNO JEST TO SAMO, KTOREGO UZYWA KARTA H013: 16:00-17:00 ET (sekcja 6 karty),
    a nie caly segment after-hours do 20:00. Roznica nie jest kosmetyczna —
    MSFT 27.07.2021 poruszyl sie w after-hours o 3.33%, po czym **wrocil do punktu
    wyjscia** i o 19:59 stal 0.01% od zamkniecia RTH. Pomiar na koncu segmentu
    pokazalby dla tej publikacji zerowa reakcje.

    Dla porownania liczymy tez wersje do konca segmentu (`ruch_20`), zeby raport
    mogl pokazac, jak czesto ruch po wynikach sie zawraca.
    """
    d = pl.scan_parquet(K6 / f"{symbol.lower()}_1m.parquet")
    godzina_et = pl.col("ts_utc").dt.convert_time_zone("America/New_York").dt.hour()
    rth = (d.filter(pl.col("segment") == "rth").sort("ts_utc")
            .group_by("trade_date").agg(c_rth=pl.col("close").last(), n_rth=pl.len()))
    minuta_et = pl.col("ts_utc").dt.convert_time_zone("America/New_York").dt.minute()
    # Minuta 16:00 to wydruk aukcji zamkniecia — jest codziennie i jest ogromna.
    # Wliczona do obrotu rozcienczylaby sygnal do niepoznaki: iloraz obrotu w dni
    # publikacji wychodzil przez to 1.77x zamiast wartosci rozrozniajacej.
    # Cena jej potrzebuje (to zamkniecie), obrot nie.
    ah = (d.filter((pl.col("segment") == "afterhours") & (godzina_et == 16))
           .sort("ts_utc")
           .group_by("trade_date")
           .agg(c_ah=pl.col("close").last(),
                v_ah=pl.col("volume").filter(minuta_et > 0).sum(),
                n_ah=pl.len()))
    pelne = (d.filter(pl.col("segment") == "afterhours").sort("ts_utc")
              .group_by("trade_date").agg(c_20=pl.col("close").last()))
    # Ostatnie notowanie przed otwarciem sesji kasowej — najpozniejsza cena, jaka
    # karta moglaby zobaczyc, zanim wejdzie w pozycje. To nie jest lookahead.
    pre = (d.filter(pl.col("segment") == "premarket").sort("ts_utc")
            .group_by("trade_date").agg(c_pre=pl.col("close").last()))
    j = (rth.join(ah, on="trade_date", how="left")
            .join(pelne, on="trade_date", how="left")
            .join(pre, on="trade_date", how="left")
            .sort("trade_date").filter(pl.col("n_rth") >= 60).collect())

    j = j.with_columns(
        ((pl.col("c_ah") / pl.col("c_rth")).log().abs()).alias("ruch"),
        ((pl.col("c_20") / pl.col("c_rth")).log().abs()).alias("ruch_20"),
        # zwroty ze znakiem — do pytania o okno pomiaru
        ((pl.col("c_ah") / pl.col("c_rth")).log()).alias("r17"),
        ((pl.col("c_pre").shift(-1) / pl.col("c_rth")).log()).alias("r_pre"),
        pl.col("v_ah").fill_null(0.0),
    )
    # tlo kroczace, przesuniete o 1 — dzien badany nie wchodzi do wlasnego tla
    return j.with_columns(
        tlo_ruch=pl.col("ruch").rolling_median(OKNO_TLA, min_samples=MIN_TLO).shift(1),
        tlo_obrot=pl.col("v_ah").rolling_median(OKNO_TLA, min_samples=MIN_TLO).shift(1),
    )


def wczytaj_kalendarz() -> dict[str, set[date]]:
    """Symbol -> zbior dni publikacji AMC. Tylko AMC: BMO nie ma okna after-hours."""
    if not KALENDARZ.exists():
        sys.exit(f"Brak {KALENDARZ} — uruchom scripts/build_earnings.py")
    wynik: dict[str, set[date]] = {s: set() for s in CIK}
    with KALENDARZ.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["klasa"] == AMC:
                wynik[r["symbol"]].add(
                    datetime.fromisoformat(r["akceptacja_et"]).date())
    return wynik


def main() -> int:
    brak = [s for s in CIK if not (K6 / f"{s.lower()}_1m.parquet").exists()]
    if brak:
        sys.exit(f"Brak danych K6: {', '.join(brak)}")

    kal = wczytaj_kalendarz()
    tabele = {s: reakcje_po_zamknieciu(s) for s in CIK}

    # Jeden wiersz na (spolka, sesja), z etykieta z kalendarza
    wiersze = []
    for s, t in tabele.items():
        for r in t.iter_rows(named=True):
            if r["tlo_ruch"] is None or r["ruch"] is None:
                continue
            wiersze.append({
                "symbol": s,
                "dzien": r["trade_date"],
                "ruch": r["ruch"],
                "ruch_20": r["ruch_20"],
                "r17": r["r17"],
                "r_pre": r["r_pre"],
                "iloraz_obrotu": (r["v_ah"] / r["tlo_obrot"]
                                  if r["tlo_obrot"] and r["tlo_obrot"] > 0 else 0.0),
                "wynik": r["trade_date"] in kal[s],
                "n_ah": r["n_ah"] or 0,
            })

    ruch = np.array([w["ruch"] for w in wiersze])
    ruch20 = np.array([w["ruch_20"] if w["ruch_20"] is not None else np.nan
                       for w in wiersze])
    obrot = np.array([w["iloraz_obrotu"] for w in wiersze])
    etyk = np.array([w["wynik"] for w in wiersze])
    n_wynik = int(etyk.sum())
    zawroty = int((ruch20[etyk] < 0.5 * ruch[etyk]).sum())

    # Porownanie okien pomiaru — tylko publikacje AMC z kompletem obu odczytow
    r17 = np.array([w["r17"] if w["r17"] is not None else np.nan for w in wiersze])
    rpre = np.array([w["r_pre"] if w["r_pre"] is not None else np.nan for w in wiersze])
    ok = etyk & np.isfinite(r17) & np.isfinite(rpre)
    a, b = r17[ok], rpre[ok]
    n_por = int(ok.sum())
    kor = float(np.corrcoef(a, b)[0, 1])
    nachyl = float(np.polyfit(a, b, 1)[0])
    istotne = np.abs(b) > 0.002          # pomijamy zdarzenia bez ruchu — iloraz bez sensu
    mediana_udzialu = float(np.median(np.abs(a[istotne]) / np.abs(b[istotne])))
    niezgodne_znaki = int((np.sign(a[istotne]) != np.sign(b[istotne])).sum())
    n_istotne = int(istotne.sum())

    L: list[str] = [
        "# W008 — detektor reakcji jako kontrola kalendarza",
        "",
        f"*Wygenerowane przez `research/W008_detektor_kontrola.py`, "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}. "
        f"{len(wiersze)} par (spolka, sesja), w tym {n_wynik} publikacji AMC.*",
        "",
        "**Status licznika prob: 0 zuzytych.**",
        "",
        "Detektor **nie definiuje proby** i nie moze jej definiowac — probe daje",
        "kalendarz EDGAR. Tu jest testowany detektor, nie kalendarz. Uzasadnienie:",
        "docstring `engine/earnings.py`.",
        "",
        "Kontrola obejmuje wylacznie publikacje **AMC**, bo tylko one maja okno",
        "after-hours w dniu publikacji. BMO wypadaja z tej kontroli z konstrukcji.",
        "",
        "## 1. Czy publikacje w ogole odrozniaja sie od zwyklych dni",
        "",
        "| Wielkosc | Dni publikacji | Pozostale dni | Iloraz |",
        "|---|---|---|---|",
    ]
    for nazwa, x, mnoznik, jedn in (("Ruch after-hours (mediana)", ruch, 100, "%"),
                                    ("Ruch after-hours (srednia)", ruch, 100, "%"),
                                    ("Iloraz obrotu (mediana)", obrot, 1, "×")):
        f = np.median if "mediana" in nazwa else np.mean
        a, b = float(f(x[etyk])), float(f(x[~etyk]))
        L.append(f"| {nazwa} | {a*mnoznik:.2f}{jedn} | {b*mnoznik:.2f}{jedn} | "
                 f"**{a/b:.1f}×** |")

    L += [
        "",
        "To jest **warunek konieczny calej karty**, sprawdzony przed czymkolwiek",
        "innym: gdyby publikacje nie odrozniały sie rozkladem od zwyklych sesji,",
        "nie byloby czego transmitowac na indeks. Odroznia sie i to bardzo wyraznie.",
        "",
        "Obrot liczony **z pominieciem minuty 16:00**, czyli wydruku aukcji zamkniecia.",
        "Aukcja jest codziennie i jest ogromna, wiec wliczona do sumy rozcienczala",
        "sygnal do niepoznaki — iloraz obrotu w dni publikacji wychodzil wtedy 1.8×",
        "zamiast obecnych ~96×, a detektor wygladal na bezuzyteczny. Cena potrzebuje",
        "tego wydruku (to jest zamkniecie), obrot nie.",
        "",
        "### Okno pomiaru ma znaczenie — i to duze",
        "",
        "Karta mierzy okno **16:00-17:00 ET** (sekcja 6). Gdyby mierzyc do konca",
        "segmentu after-hours (20:00 ET), wyszlyby inne liczby:",
        "",
        "| Okno | Mediana ruchu w dni publikacji |",
        "|---|---|",
        f"| **16:00-17:00 (karta)** | **{np.median(ruch[etyk])*100:.2f}%** |",
        f"| 16:00-20:00 (caly segment) | {np.median(ruch20[etyk])*100:.2f}% |",
        "",
        f"Dla **{zawroty} z {n_wynik} publikacji** ruch do 17:00 jest wiekszy niz ruch",
        "do 20:00 o co najmniej polowe — reakcja czesciowo **zawraca jeszcze przed",
        "koncem sesji pozagieldowej**. Skrajny przypadek: MSFT 27.07.2021 poruszyl sie",
        "o 3.33%, a o 19:59 stal 0.01% od zamkniecia RTH.",
        "",
        "### Pomiar o 17:00 jest slabym estymatorem repricingu — to jest wazne",
        "",
        "Trzy publikacje z sekcji 3 wygladaja na \"brak reakcji\" przy obrocie",
        "130-270× tla. Przebieg wewnatrz godziny tlumaczy, dlaczego:",
        "",
        "| Zdarzenie | Zakres 16:00-17:00 | Zwrot na 16:59 | Zwrot na 19:59 |",
        "|---|---|---|---|",
        "| META 2021-01-27 | 255.00 – 274.50 (**6.4%**) | **+0.01%** | −2.28% |",
        "| AMZN 2023-10-26 | 118.47 – 126.00 (**5.3%**) | **+0.04%** | +5.21% |",
        "| AVGO 2025-09-04 | 302.97 – 313.24 (**2.3%**) | **+0.03%** | +4.59% |",
        "",
        "Kurs przechodzi przez cala amplitude reakcji i wraca do punktu wyjscia",
        "dokladnie na koniec okna, po czym osiada kilka procent dalej. **Pojedynczy",
        "odczyt o 17:00 nie mierzy tego, co karta chce zmierzyc.**",
        "",
        "Zmierzone na calej probie AMC — zwrot na 17:00 wobec ostatniego notowania",
        f"przed otwarciem sesji kasowej (N = {n_por}):",
        "",
        "| Wielkosc | Wartosc |",
        "|---|---|",
        f"| korelacja(r₁₇, r_przedotwarciem) | **{kor:.3f}** |",
        f"| nachylenie regresji r_przed ~ r₁₇ | {nachyl:.2f} |",
        f"| mediana \\|r₁₇\\| / \\|r_przed\\| | {mediana_udzialu:.0%} |",
        f"| zdarzen, gdzie znak r₁₇ ≠ znak r_przed | **{niezgodne_znaki} "
        f"z {n_istotne} ({niezgodne_znaki/n_istotne:.0%})** |",
        "",
        "Ostatni wiersz jest rozstrzygajacy dla konstrukcji karty. Sygnal karty to",
        "**znak rezyduum**; jesli w kazdym takim przypadku znak samego zwrotu skladnika",
        "zdazy sie odwrocic miedzy 17:00 a otwarciem, to rezyduum liczone na 17:00",
        "opisuje stan, ktorego w momencie wejscia juz nie ma.",
        "",
        "**Co z tym robimy — i czego NIE robimy.** Nie zmieniam teraz definicji okna,",
        "bo wybor okna po zobaczeniu, ktore daje lepszy wynik, bylby strojeniem",
        "(regula R2). Zamiast tego pytanie o okno wchodzi do pre-flightu jako",
        "**deklarowane z gory rozstrzygniecie na kryterium pomiarowym**, nie na P&L:",
        "okno ma byc tym, ktore najwierniej opisuje stan skladnika **w momencie",
        "wejscia w pozycje**. Kandydatem naturalnym jest ostatnie notowanie przed",
        "otwarciem RTH — jest dostepne przed transakcja, wiec nie jest lookaheadem,",
        "i z definicji opisuje moment, w ktorym karta dziala.",
        "",
        "## 2. Skutecznosc detektora wzgledem kalendarza",
        "",
        "| Prog ruchu | Prog obrotu | Wykryte | Precision | Recall |",
        "|---|---|---|---|---|",
    ]
    najlepszy = None
    for p_ruch in (0.01, 0.02, 0.03):
        for p_obrot in (2.0, 5.0, 10.0):
            trafienie = (ruch >= p_ruch) & (obrot >= p_obrot)
            tp = int((trafienie & etyk).sum())
            wykryte = int(trafienie.sum())
            prec = tp / wykryte if wykryte else 0.0
            rec = tp / n_wynik if n_wynik else 0.0
            f1 = 2 * prec * rec / (prec + rec) if prec + rec > 0 else 0.0
            if najlepszy is None or f1 > najlepszy[0]:
                najlepszy = (f1, p_ruch, p_obrot, trafienie)
            L.append(f"| {p_ruch*100:.0f}% | {p_obrot:.0f}× | {wykryte} | "
                     f"{prec:.1%} | {rec:.1%} |")

    assert najlepszy is not None
    _, pr, po, traf = najlepszy
    L += [
        "",
        f"Najlepszy kompromis: ruch ≥ {pr*100:.0f}%, obrot ≥ {po:.0f}× tla.",
        "**Ta wartosc nie jest do niczego uzywana** — sluzy wylacznie do wyliczenia",
        "rozbieznosci ponizej. Zaden prog nie wchodzi do proby H013.",
        "",
        "## 3. Publikacje bez widocznej reakcji — kontrola kompletnosci danych",
        "",
    ]
    ciche = [w for w, t in zip(wiersze, traf, strict=True) if w["wynik"] and not t]
    bez_barow = [w for w in ciche if w["n_ah"] < 5]
    L += [
        f"**{len(ciche)} z {n_wynik} publikacji** nie przekracza progu detektora.",
        f"Z tego **{len(bez_barow)}** ma mniej niz 5 barow after-hours, czyli jest",
        "podejrzeniem **dziury w danych**, a nie spokojnej publikacji.",
        "",
    ]
    if bez_barow:
        L += ["| Spolka | Sesja | Barow AH | Ruch |", "|---|---|---|---|"]
        L += [f"| {w['symbol']} | {w['dzien']} | {w['n_ah']} | {w['ruch']*100:.2f}% |"
              for w in sorted(bez_barow, key=lambda x: x["dzien"])[:20]]
        L.append("")
    else:
        L += ["Zadna publikacja nie ma pustego okna after-hours — **dane sa pod tym",
              "wzgledem kompletne**. To wazne, bo brak barow czytalby sie jako",
              "zerowa reakcja i wchodzil do sredniej jako pomiar.", ""]

    najciszsze = sorted([w for w in ciche if w["n_ah"] >= 5],
                        key=lambda x: x["ruch"])[:10]
    if najciszsze:
        L += [
            "Publikacje o najmniejszej reakcji przy kompletnych danych — **zostaja",
            "w probie**, bo odrzucenie ich byloby dokladnie tym selection biasem,",
            "ktorego unikamy:",
            "",
            "| Spolka | Sesja | Ruch AH | Iloraz obrotu |",
            "|---|---|---|---|",
        ]
        L += [f"| {w['symbol']} | {w['dzien']} | {w['ruch']*100:.2f}% | "
              f"{w['iloraz_obrotu']:.1f}× |" for w in najciszsze]
        L.append("")

    L += [
        "## 4. Duze reakcje bez publikacji — tlo zdarzeniowe",
        "",
    ]
    obce = [w for w, t in zip(wiersze, traf, strict=True) if t and not w["wynik"]]
    per_rok: dict[int, int] = {}
    for w in obce:
        per_rok[w["dzien"].year] = per_rok.get(w["dzien"].year, 0) + 1
    L += [
        f"**{len(obce)} sesji** ma duza reakcje po zamknieciu bez wpisu 8-K 2.02 —",
        f"to okolo **{len(obce)/max(len(obce)+n_wynik,1):.0%}** wszystkich duzych",
        "reakcji. Sa to inne zdarzenia: guidance, zmiany w zarzadzie, decyzje",
        "regulacyjne, przejecia, szoki sektorowe.",
        "",
        "**Dla H013 jest to liczba istotna, a nie ciekawostka.** Rezyduum karty moze",
        "byc napedzane takim zdarzeniem u innego skladnika, ktory tego wieczoru nie",
        "publikowal wynikow. Karta liczy rezyduum ze WSZYSTKICH osmiu spolek, wiec",
        "nie ma tu pomylki w konstrukcji — ale interpretacja \"to reakcja na wyniki\"",
        "jest o tyle slabsza, o ile duze jest to tlo.",
        "",
        "| Rok | Sesji z duza reakcja bez 8-K |",
        "|---|---|",
    ]
    L += [f"| {rok} | {n} |" for rok, n in sorted(per_rok.items())]

    L += [
        "",
        "## 5. Wniosek dla kalendarza",
        "",
        "Detektor **nie znalazl podstaw do zmiany kalendarza** i nie ma prawa go",
        "zmieniac. Jego wynik jest kontrola jakosci danych i miara tla, nic wiecej.",
        "",
        "Rozbieznosci z sekcji 3 i 4 sa spodziewane z konstrukcji: detektor mierzy",
        "wielkosc reakcji, kalendarz mierzy fakt publikacji, a to sa rozne rzeczy.",
        "Gdyby zgadzaly sie w 100%, oznaczaloby to, ze jedno z nich jest zbudowane",
        "z drugiego — czyli dokladnie ta pulapke, ktorej caly ten podzial unika.",
        "",
        "---",
        "",
        "Odtworzenie: `python3 research/W008_detektor_kontrola.py`",
    ]

    RAPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {RAPORT}")
    print(f"   publikacji AMC {n_wynik}, cichych {len(ciche)} "
          f"(bez barow {len(bez_barow)}), obcych duzych reakcji {len(obce)}")
    print(f"   mediana ruchu: publikacje {np.median(ruch[etyk])*100:.2f}%, "
          f"reszta {np.median(ruch[~etyk])*100:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
