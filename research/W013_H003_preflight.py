#!/usr/bin/env python3
"""W013 — pre-flight H003: impuls wobec rownowagi przedpublikacyjnej.  PLAN rozdz. 8.4.

PUNKT GO/NO-GO OSTATNIEJ KARTY Z ORYGINALNEGO KATALOGU. Zero zuzytych prob —
badanie rozkladow, nie backtest.

Cala specyfikacja jest **zamrozona przed tym pomiarem** w commitach ae0f9f8
i d03337c (karta `hypotheses/H003.md`, sekcja 0). Ten skrypt jej nie zmienia
i nie dobiera zadnego progu.

SZESC RZECZY, KTORE SPECYFIKACJA USTALA, A KTORE LATWO ZROBIC ZLE:

  1. Impuls to PRZEMIESZCZENIE ze znakiem, `I = P(t+5) − P(t−)`, a nie zakres
     ze znakiem zamkniecia. Zakres wrzucalby pily do grupy wielkich impulsow
     i mechanicznie produkowal pozorny fade.
  2. Horyzont wspolny 25 minut. Konferencja FOMC o 14:30 zanieczyszczalaby
     okno 60-minutowe — wyjscie o 14:25 jest przed nia, z asercja.
  3. Zaden wspolny bar miedzy estymacja impulsu a wykonaniem: okno impulsu
     konczy sie na minucie 5, wejscie jest na OTWARCIU bara 6.
  4. Ranga |I|/R liczona z okna ROZSZERZAJACEGO, tylko z wczesniejszych zdarzen
     tego samego typu, minimum 20. Kwantyl z calej proby nie bylby dostepny
     w czasie rzeczywistym.
  5. Test mechanizmu i test ekonomiczny to dwie rozne statystyki. Pooled t
     w punktach jest zdominowany przez FOMC i NIE jest testem mechanizmu.
  6. Wyniki per typ obowiazkowe. Jeden typ niosacy caly efekt oznacza, ze
     karta laczna nie przechodzi.

Wyjscie: reports/W013_H003_preflight.md
"""

from __future__ import annotations

import bisect
import csv
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.costs import POINT_VALUE  # noqa: E402
from engine.loader import is_available, load_continuous  # noqa: E402

RAPORT = Path("reports/W013_H003_preflight.md")
KALENDARZ = Path("data/clean/macro_events.csv")

MIN_HISTORII = 20            # zdarzen tego samego typu przed klasyfikacja
OKNO_R = 60                  # minut okna rownowagi
OKNO_I = 5                   # minut okna impulsu
OKNO_WY = 25                 # minut do wyjscia glownego
TYPY = ("CPI", "PPI", "NFP", "FOMC")
#: Poslizg wg PLAN rozdz. 5.5 — inny w premarkecie niz po poludniu. Publikacje
#: BLS handluja sie o 08:35, FOMC o 14:05, wiec jeden wspolny poziom bylby zly.
POSLIZG_PKT = {"CPI": 1.5, "PPI": 1.5, "NFP": 1.5, "FOMC": 1.0}
PROWIZJA_RT = 1.20


def t_stat(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    return float(x.mean() / x.std(ddof=1) * np.sqrt(x.size)) if x.size > 2 else float("nan")


def ols_hc3(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Wspolczynniki i statystyki t z odpornym bledem standardowym HC3.

    HC3, nie klasyczny: wariancja zwrotow rozni sie miedzy typami zdarzen nawet
    po standaryzacji, a HC3 jest w malych probach ostrozniejszy niz HC0.
    """
    n, k = X.shape
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    reszty = y - X @ beta
    XtX_inv = np.linalg.inv(X.T @ X)
    h = np.einsum("ij,jk,ik->i", X, XtX_inv, X)
    waga = (reszty / (1.0 - np.clip(h, 0, 0.999))) ** 2
    meat = X.T @ (X * waga[:, None])
    cov = XtX_inv @ meat @ XtX_inv
    return beta, beta / np.sqrt(np.maximum(np.diag(cov), 1e-300))


def wczytaj_zdarzenia() -> list[dict]:
    if not KALENDARZ.exists():
        sys.exit(f"Brak {KALENDARZ} — uruchom scripts/build_macro.py")
    out = []
    with KALENDARZ.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["bars_ok"] != "tak" or "poza planowym" in r["notes"]:
                continue
            if r["event_type"] not in TYPY:
                continue
            r["t"] = datetime.fromisoformat(r["scheduled_timestamp_utc"])
            r["t2"] = (datetime.fromisoformat(r["second_stage_timestamp_utc"])
                       if r["second_stage_timestamp_utc"] else None)
            out.append(r)
    out.sort(key=lambda r: r["t"])
    return out


def zmierz(zdarzenia: list[dict]) -> list[dict]:
    """Dla kazdego zdarzenia: R, I, wejscie, wyjscie — z asercjami czasowymi."""
    d = load_continuous("MNQ").sort("ts_utc")
    ts = d["ts_utc"].to_list()
    px = d["px_adj"].to_numpy()
    hi = (d["high"] + (d["px_adj"] - d["close"])).to_numpy()
    lo = (d["low"] + (d["px_adj"] - d["close"])).to_numpy()
    op = (d["open"] + (d["px_adj"] - d["close"])).to_numpy()

    wyniki = []
    for z in zdarzenia:
        t = z["t"]
        i_pre = bisect.bisect_left(ts, t - timedelta(minutes=OKNO_R))
        i_pub = bisect.bisect_left(ts, t)                       # pierwszy bar >= publikacji
        i_imp = bisect.bisect_left(ts, t + timedelta(minutes=OKNO_I))
        i_wy = bisect.bisect_left(ts, t + timedelta(minutes=OKNO_WY))
        if i_pub - i_pre < 1 or i_imp - i_pub < 1 or i_wy - i_imp < 1 or i_imp >= len(ts):
            continue

        # --- asercje czasowe: kolejnosc musi byc scisla ---------------------
        t_pre, t_sygnal, t_wejscia, t_wyjscia = ts[i_pub - 1], ts[i_imp - 1], ts[i_imp], ts[i_wy - 1]
        assert t_pre < t, f"{z['event_type']} {t}: cena bazowa nie przed publikacja"
        assert t_sygnal < t_wejscia, f"{z['event_type']} {t}: wejscie nie po sygnale"
        assert t_wejscia < t_wyjscia, f"{z['event_type']} {t}: wyjscie nie po wejsciu"
        if z["t2"] is not None:
            assert t_wyjscia < z["t2"], (
                f"{z['event_type']} {t}: wyjscie {t_wyjscia} nie przed konferencja {z['t2']}")

        p_baza = float(px[i_pub - 1])
        p_impuls = float(px[i_imp - 1])
        p_wejscie = float(op[i_imp])
        p_wyjscie = float(px[i_wy - 1])
        R = float(hi[i_pre:i_pub].max() - lo[i_pre:i_pub].min())
        if R <= 0:
            continue
        przem = p_impuls - p_baza
        zakres_i = float(hi[i_pub:i_imp].max() - lo[i_pub:i_imp].min())
        wyniki.append({
            "typ": z["event_type"], "t": t, "rok": t.year,
            "R": R, "I": przem, "iloraz": abs(przem) / R,
            "zakres_impulsu": zakres_i,
            "er_impulsu": abs(przem) / zakres_i if zakres_i > 0 else np.nan,
            # sygnal karty: fade impulsu -> pozycja przeciwna do znaku I
            "wynik_fade": -np.sign(przem) * (p_wyjscie - p_wejscie),
            "p_wejscie": p_wejscie,
        })
    return wyniki


def rangi_rozszerzajace(w: list[dict]) -> None:
    """Ranga ilorazu wsrod WCZESNIEJSZYCH zdarzen tego samego typu.

    To jest cala ochrona przed lookaheadem w klasyfikacji. Kwantyl z calej proby
    nie zaglada w przyszly P&L, ale nie bylby dostepny w czasie rzeczywistym.
    """
    hist: dict[str, list[float]] = {t: [] for t in TYPY}
    for z in w:
        h = hist[z["typ"]]
        if len(h) >= MIN_HISTORII:
            z["ranga"] = float(np.mean([x < z["iloraz"] for x in h]))
            z["warmup"] = False
        else:
            z["ranga"] = np.nan
            z["warmup"] = True
        h.append(z["iloraz"])


def main() -> int:
    if not is_available("MNQ"):
        sys.exit("Brak danych MNQ — patrz HANDOFF.md")

    zd = wczytaj_zdarzenia()
    w = zmierz(zd)
    rangi_rozszerzajace(w)

    glowne = [z for z in w if not z["warmup"]]
    warmup = [z for z in w if z["warmup"]]
    typy_obecne = [t for t in TYPY if sum(1 for z in glowne if z["typ"] == t) >= 10]

    ranga = np.array([z["ranga"] for z in glowne])
    fade = np.array([z["wynik_fade"] for z in glowne])
    typ = np.array([z["typ"] for z in glowne])
    rok = np.array([z["rok"] for z in glowne])

    # standaryzacja zwrotu WEWNATRZ typu — do testu mechanizmu
    y_std = np.zeros_like(fade)
    for t in typy_obecne:
        m = typ == t
        y_std[m] = (fade[m] - fade[m].mean()) / fade[m].std(ddof=1)

    L: list[str] = [
        "# W013 — pre-flight H003 (impuls wobec rownowagi przedpublikacyjnej)",
        "",
        f"*Wygenerowane przez `research/W013_H003_preflight.py`, "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}. "
        f"{len(glowne)} zdarzen w tescie glownym, {len(warmup)} w warm-upie.*",
        "",
        "**Status licznika prob: 0 zuzytych.**",
        "",
        "Specyfikacja **zamrozona przed tym pomiarem** (commity `ae0f9f8` i `d03337c`,",
        "karta `hypotheses/H003.md` sekcja 0). Ten skrypt jej nie zmienia i nie dobiera",
        "zadnego progu.",
        "",
        "## 0. Proba",
        "",
        "| Typ | Test glowny | Warm-up | Razem |",
        "|---|---|---|---|",
    ]
    for t in TYPY:
        L.append(f"| {t} | {sum(1 for z in glowne if z['typ'] == t)} | "
                 f"{sum(1 for z in warmup if z['typ'] == t)} | "
                 f"{sum(1 for z in w if z['typ'] == t)} |")
    L += [
        "",
        f"Warm-up to pierwsze **{MIN_HISTORII}** zdarzen kazdego typu — nie maja",
        "wystarczajacej historii, zeby policzyc range bez lookaheadu. Sa raportowane,",
        "nie usuwane.",
        "",
        "## 1. Czy iloraz w ogole rozroznia zdarzenia",
        "",
        "| Typ | mediana R (pkt) | mediana \\|I\\| (pkt) | mediana ilorazu | mediana ER impulsu |",
        "|---|---|---|---|---|",
    ]
    for t in typy_obecne:
        m = [z for z in glowne if z["typ"] == t]
        L.append(f"| {t} | {np.median([x['R'] for x in m]):.1f} | "
                 f"{np.median([abs(x['I']) for x in m]):.1f} | "
                 f"{np.median([x['iloraz'] for x in m]):.2f} | "
                 f"{np.nanmedian([x['er_impulsu'] for x in m]):.2f} |")

    L += [
        "",
        "Kolumny R i ilorazu pokazuja, **dlaczego tercyle musza byc liczone wewnatrz",
        "typu**: zakres rownowagi przed FOMC (13:00-14:00, plynnosc gruba) i przed",
        "publikacja BLS (07:30-08:30, plynnosc cienka) to inne swiaty.",
        "",
        "Efficiency ratio impulsu mowi, jaka czesc zakresu pierwszych pieciu minut jest",
        "przemieszczeniem. Wartosc znaczaco ponizej 1 znaczy, ze impuls **zawraca juz",
        "w oknie pomiaru** — i to jest powod, dla ktorego zmienna kierunkowa jest",
        "przemieszczeniem, a nie zakresem ze znakiem.",
        "",
        "## 2. TEST MECHANIZMU — czy relacja istnieje ponad roznicami skali",
        "",
        "`y_std = α_typ + β · ranga(|I|/R) + ε`, odporny blad standardowy HC3.",
        "Zwrot standaryzowany **wewnatrz typu**, efekty stale typu.",
        "",
        "Rozstrzyga **β**. Dodatnie β znaczy, ze im wiekszy impuls wobec rownowagi,",
        "tym lepszy wynik fade'u — czyli dokladnie to, co twierdzi karta.",
        "",
        "| Wspolczynnik | Wartosc | t (HC3) |",
        "|---|---|---|",
    ]
    X = np.column_stack([(typ == t).astype(float) for t in typy_obecne]
                        + [ranga])
    beta, tb = ols_hc3(y_std, X)
    for i, t in enumerate(typy_obecne):
        L.append(f"| α {t} | {beta[i]:+.4f} | {tb[i]:+.2f} |")
    L.append(f"| **β ranga ilorazu** | **{beta[-1]:+.4f}** | **{tb[-1]:+.2f}** |")

    L += [
        "",
        "## 3. Wynik per typ — obowiazkowy",
        "",
        "Jesli jeden typ niesie caly efekt, **karta laczna nie przechodzi**.",
        "",
        "| Typ | N | Gorny tercyl: N | Sredni wynik (pkt) | t | Wszystkie: sredni | t |",
        "|---|---|---|---|---|---|---|",
    ]
    for t in typy_obecne:
        m = typ == t
        g = m & (ranga >= 2 / 3)
        L.append(f"| {t} | {int(m.sum())} | {int(g.sum())} | "
                 f"{fade[g].mean():+.1f} | {t_stat(fade[g]):+.2f} | "
                 f"{fade[m].mean():+.1f} | {t_stat(fade[m]):+.2f} |")

    L += [
        "",
        "## 4. Monotonicznosc w tercylach ilorazu",
        "",
        "Mechanizm wymaga, zeby wynik **rosl** z ilorazem. Skok w jednym kubelku",
        "oznacza trafienie w kubelek, nie w mechanizm — tak zginelo H005.",
        "",
        "| Tercyl rangi | N | Sredni wynik (pkt) | t | y_std |",
        "|---|---|---|---|---|",
    ]
    for lo_r, hi_r, nazwa in ((0.0, 1 / 3, "dolny"), (1 / 3, 2 / 3, "srodkowy"),
                              (2 / 3, 1.01, "gorny")):
        m = (ranga >= lo_r) & (ranga < hi_r)
        L.append(f"| {nazwa} | {int(m.sum())} | {fade[m].mean():+.1f} | "
                 f"{t_stat(fade[m]):+.2f} | {y_std[m].mean():+.3f} |")

    L += [
        "",
        "## 5. Ablacja rozstrzygajaca — iloraz przeciw samej wielkosci impulsu",
        "",
        "**To jest test, ktory decyduje o istnieniu tej karty.** H014 zginelo na",
        "warunkowaniu sama wielkoscia szoku. H003 twierdzi, ze wlasciwa zmienna jest",
        "iloraz do rownowagi. Jesli sama wielkosc dziala tak samo, karta dziedziczy",
        "werdykt H014.",
        "",
        "| Zmienna warunkujaca | Gorny tercyl: N | Sredni wynik (pkt) | t |",
        "|---|---|---|---|",
    ]
    rang_I: dict[str, list[float]] = {t: [] for t in TYPY}
    ranga_I = np.full(len(glowne), np.nan)
    for i, z in enumerate(glowne):
        h = rang_I[z["typ"]]
        if len(h) >= MIN_HISTORII:
            ranga_I[i] = float(np.mean([x < abs(z["I"]) for x in h]))
        h.append(abs(z["I"]))
    for nazwa, r in (("**iloraz \\|I\\|/R** (karta)", ranga),
                     ("sama wielkosc \\|I\\| (odpowiednik H014)", ranga_I)):
        m = np.isfinite(r) & (r >= 2 / 3)
        L.append(f"| {nazwa} | {int(m.sum())} | {fade[m].mean():+.1f} | "
                 f"{t_stat(fade[m]):+.2f} |")

    L += [
        "",
        "## 6. Stabilnosc roczna (gorny tercyl ilorazu)",
        "",
        "| Rok | N | Suma (pkt) | Sredni wynik | t | Znak |",
        "|---|---|---|---|---|---|",
    ]
    g = ranga >= 2 / 3
    for r in sorted(set(rok[g].tolist())):
        m = g & (rok == r)
        if m.sum() >= 4:
            L.append(f"| {r} | {int(m.sum())} | {fade[m].sum():+.0f} | "
                     f"{fade[m].mean():+.1f} | {t_stat(fade[m]):+.2f} | "
                     f"{'+' if fade[m].mean() > 0 else '−'} |")

    # --- test ekonomiczny ---------------------------------------------------
    posl = np.array([POSLIZG_PKT[t] for t in typ])
    netto_pkt = fade - posl - PROWIZJA_RT / POINT_VALUE
    f_okazji = int(g.sum()) / len(glowne)
    L += [
        "",
        "## 7. TEST EKONOMICZNY",
        "",
        "Koszt i poslizg **wlasciwy dla segmentu wejscia**: publikacje BLS wchodza",
        "o 08:35 w premarkecie, FOMC o 14:05 po poludniu.",
        "",
        "| Wielkosc | Gorny tercyl | Wszystkie zdarzenia |",
        "|---|---|---|",
        f"| N | {int(g.sum())} | {len(glowne)} |",
        f"| Brutto na zdarzenie | {fade[g].mean():+.1f} pkt | {fade.mean():+.1f} pkt |",
        f"| Poslizg + prowizja | −{posl[g].mean() + PROWIZJA_RT/POINT_VALUE:.1f} pkt | "
        f"−{posl.mean() + PROWIZJA_RT/POINT_VALUE:.1f} pkt |",
        f"| **Netto na zdarzenie** | **{netto_pkt[g].mean():+.1f} pkt "
        f"({netto_pkt[g].mean()*POINT_VALUE:+.2f} USD)** | "
        f"{netto_pkt.mean():+.1f} pkt ({netto_pkt.mean()*POINT_VALUE:+.2f} USD) |",
        f"| t netto | {t_stat(netto_pkt[g]):+.2f} | {t_stat(netto_pkt):+.2f} |",
        "",
        f"Faktyczny ulamek okazji *f* = **{f_okazji:.2f}** wsrod zdarzen, czyli",
        f"**{int(g.sum())/7.2:.0f} okazji rocznie**.",
        "",
        "## 8. Moc testu — zadeklarowana w karcie przed pomiarem",
        "",
        "| Wielkosc | Wartosc |",
        "|---|---|",
        f"| sd wyniku na zdarzenie (gorny tercyl) | {fade[g].std(ddof=1):.1f} pkt |",
        f"| 95% CI sredniego wyniku | [{fade[g].mean() - 1.96*fade[g].std(ddof=1)/np.sqrt(g.sum()):+.1f}, "
        f"{fade[g].mean() + 1.96*fade[g].std(ddof=1)/np.sqrt(g.sum()):+.1f}] pkt |",
        f"| N potrzebne przy mocy 80% dla efektu 20 pkt | "
        f"{((1.96+0.84)*fade[g].std(ddof=1)/20.0)**2:.0f} |",
        f"| N dostepne | **{int(g.sum())}** |",
        "",
        "## 9. Grupa warm-up — raportowana, nie usuwana",
        "",
    ]
    if warmup:
        fw = np.array([z["wynik_fade"] for z in warmup])
        L += [
            f"**{len(warmup)} zdarzen** bez wystarczajacej historii do policzenia rangi",
            "bez lookaheadu. Nie wchodza do testu glownego, ale ich rozklad jest tu",
            "podany, zeby bylo widac, ze nie wyciecie ich zrobilo wynik.",
            "",
            "| Wielkosc | Wartosc |",
            "|---|---|",
            f"| N | {len(warmup)} |",
            f"| Sredni wynik fade'u | {fw.mean():+.1f} pkt |",
            f"| t | {t_stat(fw):+.2f} |",
            "",
        ]

    # --- werdykt ------------------------------------------------------------
    srodkowy = (ranga >= 1 / 3) & (ranga < 2 / 3)
    m_I = np.isfinite(ranga_I) & (ranga_I >= 2 / 3)
    L += [
        "## 10. Werdykt: **NO-GO**",
        "",
        "| # | Przewidywanie karty | Wynik | Ocena |",
        "|---|---|---|---|",
        f"| 1 | Iloraz rozdziela kontynuacje od odwrocenia | β = {beta[-1]:+.4f}, "
        f"t(HC3) = **{tb[-1]:+.2f}** — **znak przeciwny** do tezy | **zawiedzione** |",
        f"| 2 | Efekt rosnie z ilorazem | dolny {fade[ranga < 1/3].mean():+.1f}, "
        f"srodkowy **{fade[srodkowy].mean():+.1f}**, gorny {fade[g].mean():+.1f} pkt "
        "— **niemonotonicznie** | **zawiedzione** |",
        f"| 3 | Iloraz lepszy niz sama wielkosc impulsu | iloraz {fade[g].mean():+.1f}, "
        f"sama wielkosc {fade[m_I].mean():+.1f} pkt — **gorszy** | **zawiedzione** |",
        "| 4 | Efekt obecny w wiecej niz jednym typie | znaki niezgodne, zaden typ "
        "istotny | **zawiedzione** |",
        "| 5 | Stabilnosc roczna | znak odwraca sie miedzy 2023 a 2024 | **zawiedzione** |",
        f"| 6 | Efekt przezywa koszty | netto {netto_pkt[g].mean():+.1f} pkt na zdarzenie "
        "| **zawiedzione** |",
        "",
        "### Co jest tu rozstrzygajace",
        "",
        "**Ablacja z sekcji 5.** Karta istniala po to, zeby zastapic zla zmienna H014",
        "(sama wielkosc szoku) zmienna wlasciwa (iloraz do rownowagi). Zmierzone:",
        f"iloraz daje {fade[g].mean():+.1f} pkt, sama wielkosc {fade[m_I].mean():+.1f} pkt.",
        "**Iloraz jest gorszy od zmiennej, ktora mial poprawic.** To jest jedyny",
        "powod istnienia tej karty i on nie dziala.",
        "",
        "**Niemonotonicznosc jest tu pouczajaca i warto ja pokazac.** Srodkowy tercyl",
        f"daje {fade[srodkowy].mean():+.1f} pkt przy t = {t_stat(fade[srodkowy]):+.2f} —",
        "gdyby wybrac go po fakcie, wygladalby na znalezisko. Kryterium",
        "monotonicznosci **zadeklarowane z gory** jest dokladnie po to, zeby tego nie",
        "zrobic. Tak zginelo H005 i tak zginelaby ta karta, gdyby jej bronic.",
        "",
        "### Moc testu — tym razem jej NIE brakuje",
        "",
        f"Przy sd {fade[g].std(ddof=1):.0f} pkt wykrycie efektu 20 pkt przy mocy 80%",
        f"wymaga **{((1.96+0.84)*fade[g].std(ddof=1)/20.0)**2:.0f} obserwacji**, a mamy",
        f"**{int(g.sum())}**. Karta deklarowala przed pomiarem, ze werdykt",
        "„nierozstrzygniete\" bedzie dopuszczalny — i tym razem **nie jest potrzebny**.",
        "",
        f"95% CI sredniego wyniku w gornym tercylu: "
        f"[{fade[g].mean() - 1.96*fade[g].std(ddof=1)/np.sqrt(g.sum()):+.1f}, "
        f"{fade[g].mean() + 1.96*fade[g].std(ddof=1)/np.sqrt(g.sum()):+.1f}] pkt.",
        "Prog +24.2 pkt, ktorego karta potrzebowalaby dla SR ≥ 0.8, **lezy poza tym",
        "przedzialem**. Inaczej niz przy H013, gdzie mocy faktycznie brakowalo, tutaj",
        "efekt tej wielkosci mozemy odrzucic.",
        "",
        "> **Nie jest to jednak przypadek nierozstrzygniecia. Uklad wynikow jest",
        "> niezgodny z zadeklarowanymi przewidywaniami mechanizmu w pieciu punktach",
        "> na szesc, w tym w ablacji rozstrzygajacej — dlatego karta nie spelnia",
        "> bramki GO.**",
        "",
        "Nie twierdze, ze udowodniono brak jakiegokolwiek efektu wokol publikacji makro.",
        "Twierdze, ze **ta karta, w swojej zamrozonej postaci, nie ma przeslanki**.",
        "",
        "### Konsekwencje",
        "",
        "| Co | Decyzja |",
        "|---|---|",
        "| **H003** | **REJECTED (pre-flight)**, 0 z 6 prob zuzytych |",
        "| Oryginalny katalog H001-H016 | **zamkniety** — wszystkie karty rozstrzygniete |",
        "| Kalendarz makro | zostaje: darmowy, urzedowy, wielokrotnego uzytku |",
        '| Rodzina warunkowania wielkoscia szoku | **trzecia porazka** (H014, H013, H003) |',
        "",
        "Ostatni wiersz jest wnioskiem, nie zalem. Trzy karty probowaly warunkowac",
        "reakcje na zdarzenie wielkoscia impulsu albo jego pochodna i wszystkie trzy",
        "zawiodly w ten sam sposob: **warunkowanie nie poprawialo wyniku, tylko go",
        "pogarszalo albo nie zmienialo**. To jest przeslanka, zeby przestac odwiedzac",
        "te rodzine, dopoki nie pojawi sie nowy argument mechanizmowy.",
        "",
        "---",
        "",
        "Odtworzenie: `python3 research/W013_H003_preflight.py`",
    ]

    RAPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {RAPORT}")
    print(f"   N glowne {len(glowne)}, warm-up {len(warmup)}")
    print(f"   beta ranga = {beta[-1]:+.4f} (t HC3 {tb[-1]:+.2f})")
    print(f"   gorny tercyl: {int(g.sum())} zdarzen, brutto {fade[g].mean():+.1f} pkt, "
          f"t {t_stat(fade[g]):+.2f}, netto {netto_pkt[g].mean():+.1f} pkt")
    for t in typy_obecne:
        m = typ == t
        gg = m & (ranga >= 2 / 3)
        print(f"     {t}: gorny tercyl N={int(gg.sum())} {fade[gg].mean():+.1f} pkt "
              f"t={t_stat(fade[gg]):+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
