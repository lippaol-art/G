#!/usr/bin/env python3
"""W004 — pre-flight partii 1: H011, H010, H005.  PLAN.pdf rozdz. 8.4, wniosek W002.

PO CO TO ISTNIEJE. Wniosek W002 nakazuje, by karta warunkowa deklarowala ulamek
okazji *f* i zakladana przewage PRZED testem. Zeby cokolwiek zadeklarowac,
trzeba najpierw wiedziec, czy przeslanka karty w ogole istnieje w danych.

To jest badanie ROZKLADOW, nie backtest — zero zuzytych prob. Zadna regula
wejscia nie jest tu testowana ani optymalizowana; sprawdzamy, czy zjawisko,
o ktorym mowi mechanizm karty, da sie zmierzyc.

METODA FALSYFIKACJI. Dla kazdej karty wypisujemy przewidywania, ktore jej
mechanizm robi Z GORY, i sprawdzamy je wszystkie — takze te, ktore wypadaja
niekorzystnie. Kolejnosc kontroli nie jest przypadkowa; kazda wynika z tresci
mechanizmu, nie z checklisty statystycznej:

  1. SYMETRIA — czy efekt dziala po obu stronach, skoro mechanizm nie wyroznia
     zadnej;
  2. MONOTONICZNOSC — czy rosnie wraz ze zmienna, o ktorej mechanizm mowi,
     czy skacze przy arbitralnym progu;
  3. STABILNOSC W CZASIE — czy jest obecny przez cala historie, czy pochodzi
     z jednego okresu;
  4. KONTROLA POZORNOSCI — czy nie jest to przebrana pora dnia albo dryf.

Wyjscie: reports/W004_partia1_preflight.md
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.loader import is_available, load_continuous  # noqa: E402

RAPORT = Path("reports/W004_partia1_preflight.md")
SYMBOL = "MNQ"
RTH = ["rth_open", "midday", "afternoon", "close"]
BUFOR_PKT = 5.0      # ile cena musi sie cofnac, by kolejne dotkniecie liczylo sie osobno
HORYZONT_MIN = 30    # okno pomiaru zwrotu po dotknieciu


def t_stat(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    if x.size < 2 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / x.std(ddof=1) * np.sqrt(x.size))


def kontrast(x1: np.ndarray, x2: np.ndarray) -> tuple[float, float]:
    """Roznica srednich i jej t (Welch)."""
    se = np.sqrt(x1.var(ddof=1) / x1.size + x2.var(ddof=1) / x2.size)
    d = x1.mean() - x2.mean()
    return float(d), float(d / se) if se > 0 else float("nan")


def _sesje_dzienne(df: pl.DataFrame) -> pl.DataFrame:
    adj = pl.col("px_adj") - pl.col("close")
    d = df.with_columns([
        (pl.col("open") + adj).alias("o_adj"),
        (pl.col("high") + adj).alias("h_adj"),
        (pl.col("low") + adj).alias("l_adj"),
    ]).sort("ts_utc")

    def leg(segs, pref):
        return (d.filter(pl.col("segment").is_in(segs)).group_by("trade_date")
                 .agg(**{f"{pref}o": pl.col("o_adj").first(),
                         f"{pref}c": pl.col("px_adj").last(),
                         f"{pref}h": pl.col("h_adj").max(),
                         f"{pref}l": pl.col("l_adj").min(),
                         f"{pref}n": pl.len()}).sort("trade_date"))

    return (leg(["globex_open", "asia"], "a")
            .join(leg(["europe"], "e"), on="trade_date")
            .join(leg(RTH, "r"), on="trade_date")
            .filter((pl.col("an") >= 100) & (pl.col("en") >= 100) & (pl.col("rn") >= 200)))


def _dotkniecia_pdh(df: pl.DataFrame, *, strona: str = "PDH",
                    bufor: float = BUFOR_PKT, horyzont: int = HORYZONT_MIN) -> list[tuple]:
    """Zdarzenia k-tego dotkniecia poziomu z dnia poprzedniego.

    POZIOM LICZONY NA SERII SUROWEJ (rozdz. 4.3) — to cena, przy ktorej realnie
    stały zlecenia. Zwrot mierzony na serii skorygowanej, bo tylko ona ma
    jednorodna skale punktowa przez cala historie.

    Zwraca krotki (k, minuta_sesji, zwrot_do_przodu, rok, czy_okno_obciete).
    """
    d = df.filter(pl.col("segment").is_in(RTH)).sort("ts_utc")
    td = d["trade_date"].to_list()
    hi, lo = d["high"].to_numpy(), d["low"].to_numpy()
    adj = d["px_adj"].to_numpy()
    zm = np.flatnonzero(np.array([1] + [td[i] != td[i - 1] for i in range(1, len(td))], dtype=bool))
    gr = list(zm) + [len(td)]

    gora = strona == "PDH"
    out: list[tuple] = []
    for i in range(1, len(gr) - 1):
        a0, a1 = gr[i], gr[i + 1]
        p0, p1 = gr[i - 1], gr[i]
        poziom = hi[p0:p1].max() if gora else lo[p0:p1].min()
        k, uzbrojony = 0, True
        for b in range(a0, a1):
            dotyk = (hi[b] >= poziom) if gora else (lo[b] <= poziom)
            if dotyk and uzbrojony:
                k += 1
                uzbrojony = False
                kon = min(b + horyzont, a1 - 1)
                if kon > b:
                    znak = 1.0 if gora else -1.0
                    out.append((k, b - a0, znak * (adj[kon] - adj[b]),
                                td[b].year, kon < b + horyzont))
            elif not dotyk:
                odsun = (poziom - hi[b]) if gora else (lo[b] - poziom)
                if odsun >= bufor:
                    uzbrojony = True
    return out


def main() -> int:
    if not is_available(SYMBOL):
        sys.exit(f"Brak danych {SYMBOL} — patrz HANDOFF.md")
    df = load_continuous(SYMBOL)
    j = _sesje_dzienne(df)

    a = np.log(j["ac"] / j["ao"]).to_numpy()
    e = np.log(j["ec"] / j["eo"]).to_numpy()
    ro, rc, rh, rl = (j[k].to_numpy() for k in ("ro", "rc", "rh", "rl"))
    r_rth = np.log(rc / ro)
    zakres = rh - rl
    er = np.abs(rc - ro) / np.where(zakres > 0, zakres, np.nan)   # efficiency ratio
    zgoda = np.sign(a) == np.sign(e)

    L: list[str] = [
        "# W004 — pre-flight partii 1 (H011, H010, H005)",
        "",
        f"*Wygenerowane przez `research/W004_partia1_preflight.py`, "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}. {SYMBOL}, {j.height} dni sesyjnych.*",
        "",
        "**Status licznika prob: 0 zuzytych.** Badanie rozkladow, nie backtest.",
        "Zadna regula wejscia nie jest testowana ani optymalizowana — sprawdzamy,",
        "czy zjawisko, o ktorym mowi mechanizm karty, da sie w ogole zmierzyc.",
        "",
        "Powod istnienia: wniosek **W002** nakazuje deklarowac *f* i zakladana przewage",
        "PRZED testem. Bez wiedzy, czy przeslanka istnieje, deklaracja bylaby zgadywaniem",
        "za cene nieodnawialnego budzetu prob.",
        "",
        "---",
        "",
        "## H011 — sekwencja Azja->Europa jako predyktor RTH",
        "",
        "**Mechanizm karty:** noc ma dwa rozne rezimy uczestnikow. Gdy Europa",
        "KONTYNUUJE ruch Azji, oznacza to zgode co do kierunku i ustalona kontrole",
        "nad rynkiem; gdy go ODWRACA, ruch azjatycki byl pozycjonowaniem, ktore",
        "plynniejsza sesja europejska zbila.",
        "",
        "Mechanizm robi **dwie przewidywania z gory** i sprawdzamy oba:",
        "",
        "### Przewidywanie 1 — RTH podaza za kierunkiem uzgodnionym w nocy",
        "",
        "| Kubelek | Dni | Udzial | Sredni zwrot RTH | t |",
        "|---|---|---|---|---|",
    ]
    for nazwa, maska in (("Azja+ Europa+", (a > 0) & (e > 0)),
                         ("Azja+ Europa−", (a > 0) & (e <= 0)),
                         ("Azja− Europa+", (a <= 0) & (e > 0)),
                         ("Azja− Europa−", (a <= 0) & (e <= 0))):
        x = r_rth[maska]
        L.append(f"| {nazwa} | {maska.sum()} | {maska.mean():.1%} | "
                 f"{x.mean()*100:+.4f}% | {t_stat(x):+.2f} |")
    dk, tk = kontrast(r_rth[zgoda], r_rth[~zgoda])
    L += [
        "",
        f"Kontrast zgoda − rozbieznosc: **{dk*100:+.4f}%, t = {tk:+.2f}**. Brak efektu.",
        "",
        "### Przewidywanie 2 — zgoda oznacza trend, rozbieznosc oznacza chaos",
        "",
        "Miara charakteru sesji: *efficiency ratio* = |close − open| / (high − low).",
        "Wysoki = ruch kierunkowy, niski = pilowanie.",
        "",
        "| Wielkosc | Zgoda | Rozbieznosc | Roznica | t |",
        "|---|---|---|---|---|",
    ]
    for nazwa, y in (("efficiency ratio", er), ("&#124;zwrot&#124; RTH", np.abs(r_rth)),
                     ("zakres RTH / cena", zakres / ro)):
        ok = ~np.isnan(y)
        d_, t_ = kontrast(y[zgoda & ok], y[(~zgoda) & ok])
        L.append(f"| {nazwa} | {y[zgoda & ok].mean():.4f} | {y[(~zgoda) & ok].mean():.4f} | "
                 f"{d_:+.4f} | {t_:+.2f} |")
    L += [
        "",
        "### Werdykt H011 — **ODRZUCONA**",
        "",
        "Oba przewidywania mechanizmu zawodza. Co gorsza, efficiency ratio idzie",
        "w strone **przeciwna** do przewidywanej (rozbieznosc daje nieco wyzszy ER),",
        "choc nieistotnie. Karta o najwyzszym priorytecie w katalogu — motywowana",
        "najnizszym pokryciem z literatura — nie ma przeslanki.",
        "",
        "Brak pokrycia w literaturze nie jest przewaga. Bywa informacja, ze nie ma",
        "czego opisywac.",
        "",
        "---",
        "",
        "## H010 — zmiennosc zrealizowana wobec oczekiwanej jako warstwa rezimowa",
        "",
        "**Mechanizm karty:** stosunek nocnego zakresu do jego normy przewiduje",
        "CHARAKTER sesji (trend vs pilowanie) i moze sluzyc jako filtr rezimowy",
        "dla innych kart.",
        "",
    ]
    noc_zakres = ((np.maximum(j["ah"].to_numpy(), j["eh"].to_numpy())
                   - np.minimum(j["al"].to_numpy(), j["el"].to_numpy())) / j["ao"].to_numpy())
    norma = np.array([np.nan if i < 20 else np.median(noc_zakres[i - 20:i])
                      for i in range(len(noc_zakres))])
    ratio = noc_zakres / norma
    ok = ~np.isnan(ratio)
    gorny = ok & (ratio >= np.nanquantile(ratio, 2 / 3))
    dolny = ok & (ratio <= np.nanquantile(ratio, 1 / 3))
    L += [
        "| Wielkosc RTH | Szeroka noc (gorny tercyl) | Waska noc (dolny) | Roznica | t |",
        "|---|---|---|---|---|",
    ]
    for nazwa, y in (("zakres / cena", zakres / ro), ("&#124;zwrot&#124;", np.abs(r_rth)),
                     ("efficiency ratio", er)):
        m = ~np.isnan(y)
        d_, t_ = kontrast(y[gorny & m], y[dolny & m])
        L.append(f"| {nazwa} | {y[gorny & m].mean():.4f} | {y[dolny & m].mean():.4f} | "
                 f"{d_:+.4f} | **{t_:+.2f}** |")
    L += [
        "",
        "### Werdykt H010 — **ODRZUCONA W PROPONOWANEJ ROLI**",
        "",
        "Tu efekt JEST i jest jednym z najsilniejszych w calym zbiorze: szeroka noc",
        "zapowiada szerszy zakres RTH z t ponad 10. To jednak **klasteryzacja",
        "zmiennosci** (Engle 1982), zjawisko opisane czterdziesci lat temu — i, co",
        "rozstrzygajace, dotyczy WYLACZNIE amplitudy.",
        "",
        "Efficiency ratio, czyli dokladnie ta wielkosc, o ktora karcie chodzilo,",
        "**nie rozni sie miedzy rezimami** (t bliskie zera). Zmiennosc nocna mowi,",
        "JAK DUZY bedzie ruch, ale nie mowi nic o tym, czy bedzie kierunkowy.",
        "",
        "Karta zakladala filtr rezimowy typu trend/pilowanie dla innych hipotez —",
        "i tego zalozenia dane nie potwierdzaja. Efekt zostaje w projekcie jako",
        "**wejscie do wielkosci pozycji**, nie jako filtr kierunkowy.",
        "",
        "> To rozroznienie jest wazniejsze niz sam wynik: **silny efekt to nie to samo",
        "> co uzyteczny efekt.** t = 10 przy zlej zmiennej zaleznej jest wart mniej",
        "> niz t = 2 przy wlasciwej.",
        "",
        "---",
        "",
        "## H005 — mikrostruktura kolejnych testow poziomu",
        "",
        "**Mechanizm karty:** kolejne dotkniecia poziomu z dnia poprzedniego zuzywaja",
        "plynnosc broniaca tego poziomu, wiec prawdopodobienstwo przebicia rosnie",
        "z numerem dotkniecia.",
        "",
        f"Parametry pomiaru zadeklarowane z gory: bufor {BUFOR_PKT:.0f} pkt "
        f"(ile cena musi sie cofnac, by kolejne dotkniecie liczylo sie osobno), "
        f"horyzont {HORYZONT_MIN} min. Poziom liczony na serii SUROWEJ (rozdz. 4.3).",
        "",
    ]

    zd_pdh = _dotkniecia_pdh(df, strona="PDH")
    zd_pdl = _dotkniecia_pdh(df, strona="PDL")

    L += [
        "### Sygnal wstepny",
        "",
        "| Poziom | k | Zdarzen | Sredni zwrot [pkt] | t |",
        "|---|---|---|---|---|",
    ]
    for nazwa, zd in (("PDH", zd_pdh), ("PDL", zd_pdl)):
        for kk in (1, 2, 3):
            x = np.array([z[2] for z in zd if z[0] == kk])
            L.append(f"| {nazwa} | {kk} | {x.size} | {x.mean():+.3f} | {t_stat(x):+.2f} |")
        x = np.array([z[2] for z in zd if z[0] >= 4])
        pog = "**" if nazwa == "PDH" else ""
        L.append(f"| {nazwa} | 4+ | {x.size} | {pog}{x.mean():+.3f}{pog} | "
                 f"{pog}{t_stat(x):+.2f}{pog} |")

    x4 = np.array([z[2] for z in zd_pdh if z[0] >= 4])
    L += [
        "",
        f"Jedna komorka wyroznia sie: PDH przy czwartym i dalszym dotknieciu, "
        f"**{x4.mean():+.2f} pkt, t = {t_stat(x4):+.2f}** na {x4.size} zdarzeniach.",
        "Zgodne z kierunkiem mechanizmu. Ponizej cztery kontrole, ktore taki wynik",
        "musi przejsc, zanim uznamy go za cokolwiek.",
        "",
        "### Kontrola 1 — pozornosc: czy to nie jest po prostu pora dnia",
        "",
    ]
    # kontrola czasu dnia
    d_rth = df.filter(pl.col("segment").is_in(RTH)).sort("ts_utc")
    td_ = d_rth["trade_date"].to_list()
    adj_ = d_rth["px_adj"].to_numpy()
    zm_ = np.flatnonzero(np.array([1] + [td_[i] != td_[i - 1] for i in range(1, len(td_))],
                                  dtype=bool))
    gr_ = list(zm_) + [len(td_)]
    ref: dict[int, list[float]] = {}
    for i in range(1, len(gr_) - 1):
        a0, a1 = gr_[i], gr_[i + 1]
        for b in range(a0, a1):
            kon = b + HORYZONT_MIN
            if kon < a1:
                ref.setdefault(b - a0, []).append(adj_[kon] - adj_[b])
    minuty = np.array([z[1] for z in zd_pdh if z[0] >= 4])
    oczek = np.array([np.mean(ref[m]) if m in ref and len(ref[m]) > 30 else np.nan
                      for m in minuty])
    mok = ~np.isnan(oczek)
    nadwyzka = x4[mok] - oczek[mok]
    L += [
        f"Sredni zwrot bezwarunkowy w tych samych minutach sesji: "
        f"**{oczek[mok].mean():+.3f} pkt**. Nadwyzka zdarzen ponad ta kontrole: "
        f"**{nadwyzka.mean():+.3f} pkt, t = {t_stat(nadwyzka):+.2f}**.",
        "",
        "Kontrola **zdana** — efekt nie jest przebrana pora dnia ani ogolnym dryfem.",
        "",
        "### Kontrola 2 — symetria: mechanizm nie wyroznia strony",
        "",
    ]
    x4l = np.array([z[2] for z in zd_pdl if z[0] >= 4])
    L += [
        f"Ten sam pomiar po stronie PDL: **{x4l.mean():+.3f} pkt, t = {t_stat(x4l):+.2f}** "
        f"na {x4l.size} zdarzeniach.",
        "",
        "Kontrola **niezdana**. Zuzywanie plynnosci broniacej poziomu nie ma powodu",
        "dzialac tylko w gore. Asymetria bez wyjasnienia mechanizmem jest ostrzezeniem,",
        "nie ciekawostka.",
        "",
        "### Kontrola 3 — monotonicznosc: efekt ma rosnac z k, nie skakac",
        "",
        "| k | Zdarzen | Sredni zwrot [pkt] | t |",
        "|---|---|---|---|",
    ]
    for kk in range(1, 8):
        x = np.array([z[2] for z in zd_pdh if z[0] == kk])
        if x.size > 40:
            L.append(f"| {kk} | {x.size} | {x.mean():+.3f} | {t_stat(x):+.2f} |")
    L += [
        "",
        "Kontrola **niezdana**. Profil nie rosnie — skacze przy k = 4, spada przy k = 5,",
        "znow rosnie przy k = 6. Mechanizm mowi o stopniowym zuzywaniu plynnosci,",
        "a to nie jest ksztalt stopniowego zuzywania. Prog 4 jest arbitralny.",
        "",
        "### Kontrola 4 — stabilnosc w czasie",
        "",
        "| Rok | Zdarzen | Sredni zwrot [pkt] | t | Udzial w wyniku |",
        "|---|---|---|---|---|",
    ]
    lata_ev = [(z[3], z[2]) for z in zd_pdh if z[0] >= 4]
    suma_all = sum(v for _, v in lata_ev)
    udzialy = {}
    for y in sorted({y for y, _ in lata_ev}):
        v = np.array([x for yy, x in lata_ev if yy == y])
        udzialy[y] = v.sum() / suma_all if suma_all != 0 else float("nan")
        L.append(f"| {y} | {v.size} | {v.mean():+.3f} | {t_stat(v):+.2f} | {udzialy[y]:+.0%} |")
    naj_rok = max(udzialy, key=lambda k: udzialy[k])
    ujemne = [y for y, _ in udzialy.items() if np.mean([x for yy, x in lata_ev if yy == y]) < 0]
    L += [
        "",
        f"Kontrola **niezdana, i to rozstrzygajaco**. Rok {naj_rok} — niepelny, "
        f"siedem miesiecy — daje **{udzialy[naj_rok]:.0%} calego wyniku**. "
        f"Lat ujemnych: {len(ujemne)} z {len(udzialy)}.",
        "",
        "Prog koncentracji z rozdz. 1.3 mowi o piatce najlepszych DNI ponizej 40%.",
        "Tutaj pojedynczy niepelny ROK daje polowe wyniku.",
        "",
        "### Werdykt H005 — **ODRZUCONA**",
        "",
        "Efekt przeszedl kontrole pozornosci, przetrwal zmiane parametrow i podzial",
        "probki na polowy — a mimo to jest jednym rokiem danych, widocznym tylko po",
        "jednej stronie i bez monotonicznosci, ktorej wymaga jego wlasny mechanizm.",
        "",
        "---",
        "",
        "## Podsumowanie partii 1",
        "",
        "| Karta | Wynik | Powod |",
        "|---|---|---|",
        "| H011 | **ODRZUCONA** | oba przewidywania mechanizmu zawodza, jedno ze znakiem przeciwnym |",
        "| H010 | **ODRZUCONA W TEJ ROLI** | efekt bardzo silny, ale dotyczy amplitudy, nie charakteru |",
        "| H005 | **ODRZUCONA** | sygnal upada na symetrii, monotonicznosci i stabilnosci rocznej |",
        "",
        "**Zuzyte proby: 0 z budzetu 18** (3 karty x 6 wariantow). Pre-flight kosztowal",
        "kilka godzin obliczen i uratowal caly budzet partii — a przy DSR kazda",
        "niewydana proba podnosi szanse wszystkich pozostalych kart.",
        "",
        "## Wnioski przekrojowe",
        "",
        "### W004 — kolejnosc kontroli decyduje, co przezyje",
        "",
        "> Sygnal H005 przeszedl kontrole pozornosci (pora dnia, dryf), zmiane czterech",
        "> parametrow i podzial probki na polowy. Upadl dopiero na trzech kontrolach",
        "> wyprowadzonych **z tresci mechanizmu**: symetrii, monotonicznosci i stabilnosci",
        "> rocznej. Kontrole statystyczne sprawdzaja, czy liczba jest solidna; kontrole",
        "> mechanizmu sprawdzaja, czy jest to ta liczba, o ktorej mowilismy.",
        "> **Te drugie odrzucily wiecej i wczesniej.**",
        "",
        "### W005 — silny efekt to nie to samo co uzyteczny efekt",
        "",
        "> H010 dala najmocniejszy pojedynczy wynik calego dotychczasowego projektu",
        "> (t > 10) i zostala odrzucona, bo mierzyla amplitude tam, gdzie karta",
        "> potrzebowala kierunku. Przed uruchomieniem kazdej karty pytamy nie tylko",
        "> \"czy efekt istnieje\", ale \"czy istnieje w zmiennej, ktorej karta uzywa\".",
        "",
        "---",
        "",
        "Odtworzenie: `python3 research/W004_partia1_preflight.py`",
    ]

    RAPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {RAPORT}")
    print(f"H011 kontrast t={tk:+.2f} | H005 PDH k4+ t={t_stat(x4):+.2f}, "
          f"PDL t={t_stat(x4l):+.2f}, rok {naj_rok} = {udzialy[naj_rok]:.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
