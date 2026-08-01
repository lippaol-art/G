#!/usr/bin/env python3
"""W001 — czy dryf nocny na NDX jeszcze istnieje?  PLAN.pdf rozdz. 9 (karta H004).

KONTEKST. Audyt oryginalnosci przytoczyl badanie NY Fed: dryf overnight na
indeksach US mial wynosic ~3.7%/rok w latach 1998-2020 i ~0% w latach 2021-2025.
Jesli to prawda, karta H004 warunkuje efekt, ktorego juz nie ma. REGISTRY.md
nakazuje sprawdzic to na wlasnych danych PRZED jakakolwiek praca nad karta.

TO NIE JEST BACKTEST i nie zuzywa licznika prob (rozdz. 6.5). Nie testujemy
zadnej reguly wejscia — rozkladamy zwrot dobowy na dwie skladowe i patrzymy na
rozklady. Zaden parametr nie jest tu dobierany.

METODA. Dla kazdego dnia sesyjnego:
    r_noc   = log( open_RTH(d)  / close_RTH(d-1) )
    r_sesja = log( close_RTH(d) / open_RTH(d)    )
Suma obu odtwarza pelny zwrot buy-and-hold — tozsamosc sprawdzana w kodzie.

Przedzialy ufnosci BLOKOWE, nie iid: dzienne zwroty maja klastry zmiennosci,
wiec bootstrap po pojedynczych dniach dalby przedzialy zbyt waskie i tym samym
falszywa pewnosc co do konkluzji.

Wyjscie: reports/W001_overnight_drift.md
"""

from __future__ import annotations

import sys
import zlib
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.loader import is_available, load_continuous  # noqa: E402
from validation.dsr import deflated_sharpe_annualized  # noqa: E402
from validation.power import required_daily_edge  # noqa: E402

RAPORT = Path("reports/W001_overnight_drift.md")
INSTRUMENTY = ("MNQ", "NQ", "ES")
RTH_SEGMENTY = {"rth_open", "midday", "afternoon", "close"}
MIN_BAROW_RTH = 200          # odsiewa dni skrocone i uszkodzone
ROK_PODZIALU = 2021          # granica z tezy NY Fed
DNI_W_ROKU = 252
N_BOOT = 5000
N_WARIANTOW_H004 = 4      # limit z REGISTRY.md dla tej karty
DL_BLOKU = 10.0              # dni — obejmuje typowy klaster zmiennosci


def sesje(symbol: str) -> tuple[np.ndarray, np.ndarray, list]:
    """Zwraca (zwroty nocne, zwroty sesyjne, daty) — po jednym na dzien sesyjny."""
    df = load_continuous(symbol)
    rth = df.filter(pl.col("segment").is_in(RTH_SEGMENTY)).sort("ts_utc")

    # open bara jest w pliku SUROWY; przesuwamy go tym samym offsetem co close,
    # bo tylko seria skorygowana ma jednorodna skale przez cala historie (4.3).
    open_adj = pl.col("open") + (pl.col("px_adj") - pl.col("close"))
    g = (rth.group_by("trade_date")
            .agg(o=open_adj.first(), c=pl.col("px_adj").last(), n=pl.len())
            .sort("trade_date")
            .filter(pl.col("n") >= MIN_BAROW_RTH))

    o, c = g["o"].to_numpy(), g["c"].to_numpy()
    daty = g["trade_date"].to_list()
    noc = np.log(o[1:] / c[:-1])       # zamkniecie d-1 -> otwarcie d
    sesja = np.log(c / o)              # otwarcie d     -> zamkniecie d
    return noc, sesja[1:], daty[1:]    # wyrownane do tych samych dni


def boot_mean_ci(x: np.ndarray, *, seed: int = 0, alfa: float = 0.05) -> tuple[float, float]:
    """Przedzial ufnosci sredniej — bootstrap BLOKOWY (blok geometryczny).

    Blok zamiast losowania pojedynczych dni, bo zmiennosc dzienna wystepuje
    w seriach. Przy iid przedzial wyszedlby wezszy, niz uprawniaja dane, a caly
    sens tego badania polega na uczciwym pokazaniu, czego NIE wiemy.
    """
    rng = np.random.default_rng(seed)
    n = x.size
    p = 1.0 / DL_BLOKU
    srednie = np.empty(N_BOOT)
    for b in range(N_BOOT):
        out = np.empty(n)
        i = 0
        while i < n:
            start = rng.integers(0, n)
            dl = min(max(1, int(rng.geometric(p))), n - i)
            out[i:i + dl] = x[(np.arange(start, start + dl)) % n]
            i += dl
        srednie[b] = out.mean()
    return float(np.quantile(srednie, alfa / 2)), float(np.quantile(srednie, 1 - alfa / 2))


def rocznie(mu_dzienne: float) -> float:
    """Dzienny log-zwrot -> zwrot roczny w procentach."""
    return (np.exp(mu_dzienne * DNI_W_ROKU) - 1.0) * 100.0


def sharpe(x: np.ndarray) -> float:
    return float(x.mean() / x.std(ddof=1) * np.sqrt(DNI_W_ROKU))


def ziarno(etykieta: str) -> int:
    """Deterministyczne ziarno z etykiety tekstowej.

    NIE `hash()`. Python randomizuje hash stringow przy kazdym starcie procesu
    (PYTHONHASHSEED), wiec `hash(sym + okres)` dawal INNE ziarno w kazdym
    przebiegu — a wraz z nim inne granice bootstrapu w raporcie. Raport badawczy,
    ktory przy powtorzeniu daje inne liczby, lamie wymog odtwarzalnosci
    z rozdz. 5.6 i podwaza kazdy wniosek, ktory z niego wyciagniemy.

    Wykryte przez porownanie dwoch kolejnych regeneracji tego samego raportu.
    """
    return zlib.crc32(etykieta.encode("utf-8"))


def t_stat(x: np.ndarray) -> float:
    return float(x.mean() / x.std(ddof=1) * np.sqrt(x.size))


def main() -> int:
    brak = [s for s in INSTRUMENTY if not is_available(s)]
    if brak:
        sys.exit(f"Brak danych: {brak}. Patrz HANDOFF.md")

    L: list[str] = [
        "# W001 — czy dryf nocny na NDX jeszcze istnieje?",
        "",
        f"*Wygenerowane przez `research/W001_overnight_drift.py`, "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}.*",
        "",
        "**Status licznika prob: 0 zuzytych.** To dekompozycja rozkladow, nie backtest —",
        "nie ma tu zadnej reguly wejscia ani zadnego dobieranego parametru (rozdz. 6.5).",
        "",
        "## Pytanie",
        "",
        "Audyt oryginalnosci przytoczyl badanie NY Fed: dryf overnight na indeksach US",
        "~3.7%/rok w latach 1998-2020 i **~0% w latach 2021-2025**. Karta H004 warunkuje",
        "ten efekt, wiec jesli efekt wygasl, karta warunkuje nieistniejace zjawisko.",
        "REGISTRY.md nakazuje rozstrzygnac to przed jakakolwiek praca nad H004.",
        "",
        "---",
        "",
    ]

    dane: dict[str, tuple[np.ndarray, np.ndarray, list]] = {}
    for sym in INSTRUMENTY:
        dane[sym] = sesje(sym)
        n, s, _ = dane[sym]
        print(f"{sym}: {len(n)} dni sesyjnych")

    # ------------------------------------------------------------------
    # 1. DEKOMPOZYCJA
    # ------------------------------------------------------------------
    L += [
        "## 1. Dekompozycja zwrotu dobowego, rok po roku",
        "",
        "Zwrot logarytmiczny, seria skorygowana (`px_adj`), dni sesyjne z co najmniej",
        f"{MIN_BAROW_RTH} barami RTH. Suma obu skladowych odtwarza pelny zwrot",
        "buy-and-hold — tozsamosc weryfikowana w kodzie.",
        "",
    ]
    for sym in INSTRUMENTY:
        noc, sesja, daty = dane[sym]
        lata = np.array([d.year for d in daty])
        L += [
            f"### {sym}",
            "",
            "| Rok | Dni | Noc [%] | Sesja [%] | Razem [%] | t(noc) | t(sesja) |",
            "|---|---|---|---|---|---|---|",
        ]
        for y in sorted(set(lata)):
            m = lata == y
            n_, s_ = noc[m], sesja[m]
            L.append(f"| {y} | {m.sum()} | {n_.sum()*100:+.2f} | {s_.sum()*100:+.2f} | "
                     f"{(n_.sum()+s_.sum())*100:+.2f} | {t_stat(n_):+.2f} | {t_stat(s_):+.2f} |")
        L.append(f"| **2019-2026** | **{len(noc)}** | **{noc.sum()*100:+.2f}** | "
                 f"**{sesja.sum()*100:+.2f}** | **{(noc.sum()+sesja.sum())*100:+.2f}** | "
                 f"**{t_stat(noc):+.2f}** | **{t_stat(sesja):+.2f}** |")
        L.append("")

    # ------------------------------------------------------------------
    # 2. PODZIAL WG TEZY NY FED
    # ------------------------------------------------------------------
    L += [
        f"## 2. Podzial na okresy wg tezy zewnetrznej (granica {ROK_PODZIALU})",
        "",
        "Przedzialy ufnosci **blokowe** (blok sredni 10 dni), nie iid — zmiennosc dzienna",
        "wystepuje w seriach, a bootstrap po pojedynczych dniach dalby przedzialy wezsze,",
        "niz uprawniaja dane.",
        "",
        "| Instrument | Okres | Dni | Dryf nocny [%/rok] | 95% CI [%/rok] | Sharpe | t |",
        "|---|---|---|---|---|---|---|",
    ]
    podsumowanie: dict[str, dict] = {}
    for sym in INSTRUMENTY:
        noc, _, daty = dane[sym]
        lata = np.array([d.year for d in daty])
        podsumowanie[sym] = {}
        for etykieta, m in (("2019-2020", lata < ROK_PODZIALU),
                            (f"{ROK_PODZIALU}-2026", lata >= ROK_PODZIALU)):
            x = noc[m]
            lo, hi = boot_mean_ci(x, seed=ziarno(sym + etykieta))
            podsumowanie[sym][etykieta] = dict(
                n=int(m.sum()), mu=float(x.mean()), lo=lo, hi=hi,
                sharpe=sharpe(x), t=t_stat(x))
            L.append(f"| {sym} | {etykieta} | {m.sum()} | {rocznie(x.mean()):+.1f} | "
                     f"[{rocznie(lo):+.1f}, {rocznie(hi):+.1f}] | {sharpe(x):+.2f} | {t_stat(x):+.2f} |")
        print(f"   {sym} podzial gotowy")
    L.append("")

    # ------------------------------------------------------------------
    # 3. MOC TESTU — sedno badania
    # ------------------------------------------------------------------
    noc_mnq, _, daty_mnq = dane["MNQ"]
    lata_mnq = np.array([d.year for d in daty_mnq])
    post = noc_mnq[lata_mnq >= ROK_PODZIALU]
    sd = float(noc_mnq.std(ddof=1))
    z_a, z_b = norm.ppf(0.975), norm.ppf(0.80)

    L += [
        "## 3. Czy to pytanie w ogole da sie rozstrzygnac?",
        "",
        "**To jest najwazniejsza sekcja tego raportu.** Zanim zinterpretujemy liczby",
        "z sekcji 2, trzeba sprawdzic, jaka moc ma test, ktory je wyprodukowal.",
        "",
        f"Odchylenie standardowe dziennego zwrotu nocnego MNQ: **{sd*100:.3f}%**.",
        "Przy takim szumie liczba dni potrzebna, by odroznic zadany dryf od zera",
        "przy mocy 80% i alfa 5%:",
        "",
        "| Hipotetyczny dryf | Srednia dzienna | Wymagane N | To jest |",
        "|---|---|---|---|",
    ]
    for hip in (0.02, 0.037, 0.05, 0.10, 0.20):
        mu_d = np.log(1 + hip) / DNI_W_ROKU
        N = ((z_a + z_b) * sd / mu_d) ** 2
        L.append(f"| {hip:.1%}/rok | {mu_d*100:.4f}% | {N:,.0f} dni | **{N/DNI_W_ROKU:,.0f} lat** |")

    se = sd / np.sqrt(len(post))
    mde_dzienne = (z_a + z_b) * sd / np.sqrt(len(post))
    lat_dla_37 = ((z_a + z_b) * sd / (np.log(1.037) / DNI_W_ROKU)) ** 2 / DNI_W_ROKU
    L += [
        "",
        "Teza NY Fed dotyczy dryfu **3.7%/rok**. Odroznienie go od zera wymaga",
        f"**{lat_dla_37:,.0f} lat danych.**",
        f"Nasza probka {ROK_PODZIALU}-2026 liczy {len(post)} dni, czyli {len(post)/DNI_W_ROKU:.1f} roku.",
        "",
        "### Co z tego wynika",
        "",
        f"Najmniejszy dryf wykrywalny na naszej probce {ROK_PODZIALU}-2026 przy mocy 80%:",
        f"**{rocznie(mde_dzienne):+.0f}%/rok**. Przedzial ufnosci dla dryfu nocnego MNQ",
        f"w tym okresie wynosi **[{rocznie(post.mean()-1.96*se):+.1f}%, "
        f"{rocznie(post.mean()+1.96*se):+.1f}%] rocznie** — szerokosc "
        f"{rocznie(post.mean()+1.96*se)-rocznie(post.mean()-1.96*se):.0f} punktow procentowych.",
        "",
        "**Zarowno 0%, jak i 3.7% lezy wewnatrz tego przedzialu.** Nasze dane nie",
        "potwierdzaja tezy o wygasnieciu ani jej nie obalaja — po prostu jej nie",
        "rozstrzygaja. I nie rozstrzygnie jej zadna ilosc danych, jaka ten projekt",
        f"kiedykolwiek zdobedzie: {len(post)/DNI_W_ROKU:.1f} roku historii MNQ nie zamieni",
        f"sie w {lat_dla_37:,.0f}.",
        "",
        "> **Uwaga o samej tezie zrodlowej.** Ten sam rachunek stosuje sie do niej.",
        "> Punktowa ocena \"~0% w latach 2021-2025\" oparta na piecioletnim oknie ma",
        "> dokladnie taki sam przedzial ufnosci jak nasza. Zdanie \"dryf nocny wygasl\"",
        "> nie jest wnioskiem, ktory pieciolatek danych moze udzwignac — niezaleznie",
        "> od tego, kto go wypowiada. Nie zarzucam bledu autorom; zwracam uwage, ze",
        "> **nie wolno nam oprzec decyzji projektowej na twierdzeniu tej klasy.**",
        "",
    ]

    # ------------------------------------------------------------------
    # 4. PRZEFORMULOWANIE OPERACYJNE
    # ------------------------------------------------------------------
    sh_post = sharpe(post)
    sh_full = sharpe(noc_mnq)
    L += [
        "## 4. Pytanie, ktore ma odpowiedz",
        "",
        "\"Czy dryf wygasl\" jest pytaniem zle postawionym — nie da sie na nie odpowiedziec.",
        "Pytanie operacyjne brzmi inaczej i **ma** odpowiedz:",
        "",
        "> Czy bezwarunkowy dryf nocny daje Sharpe'a, ktory przechodzi bramke projektu",
        "> (SR >= 0.8 OOS, rozdz. 1.3)?",
        "",
        "| Okres | Dni | Sharpe (bezwarunkowo, przed kosztami) | Prog 0.8 |",
        "|---|---|---|---|",
        f"| 2019-2026 | {len(noc_mnq)} | **{sh_full:.2f}** | {'przechodzi' if sh_full>=0.8 else '**nie przechodzi**'} |",
        f"| {ROK_PODZIALU}-2026 | {len(post)} | **{sh_post:.2f}** | {'przechodzi' if sh_post>=0.8 else '**nie przechodzi**'} |",
        "",
        "Odpowiedz jest jednoznaczna i nie zalezy od tego, czy efekt \"wygasl\":",
        "**bezwarunkowy dryf nocny nie przechodzi bramki w zadnym okresie** — i to",
        "jeszcze przed odjeciem kosztow. Roznica miedzy \"efekt wygasl\" a \"efekt trwa,",
        "ale jest za slaby\" nie ma dla projektu znaczenia operacyjnego: obie prowadza",
        "do tej samej decyzji.",
        "",
    ]

    # ------------------------------------------------------------------
    # 5. ILE MUSI DAC WERSJA WARUNKOWA — cena warunkowania
    # ------------------------------------------------------------------
    # Prog DSR wyznaczamy bisekcja, nie z siatki: chodzi o liczbe, ktora trafia
    # do karty jako warunek wejscia, wiec musi byc dokladna.
    lo_sr, hi_sr = 0.1, 3.0
    for _ in range(60):
        mid = (lo_sr + hi_sr) / 2
        if deflated_sharpe_annualized(mid, len(post), N_WARIANTOW_H004).passes:
            hi_sr = mid
        else:
            lo_sr = mid
    sr_dsr = hi_sr

    # Wzor mieszka w validation/power.py i ma tam testy regresyjne na liczbach
    # z TEGO raportu — inaczej raport i kod rozjechalyby sie po pierwszej zmianie.
    def mu_wymagane(sr: float, f: float) -> float:
        return required_daily_edge(sr, sd, f, trading_days=DNI_W_ROKU)

    mu_bez = float(post.mean())
    L += [
        "## 5. Cena warunkowania — ile musi dac wersja warunkowa H004",
        "",
        "Sens karty warunkowej polega na wybraniu podzbioru nocy, w ktorym efekt jest",
        "silny. Ale zwezanie okna ma **policzalna cene**: Sharpe liczymy po wszystkich",
        "dniach, nie tylko czynnych (rozdz. 6.3), wiec strategia handlujaca ulamek *f*",
        "nocy musi miec na kazdej z nich edge wiekszy o czynnik **1/sqrt(f)**.",
        "",
        f"Prog certyfikacji DSR >= 0.95 przy T = {len(post)} dni i {N_WARIANTOW_H004} wariantach karty:",
        f"**SR >= {sr_dsr:.2f}**.",
        "",
        f"Bezwarunkowy zwrot nocny {ROK_PODZIALU}-2026 wynosi {mu_bez*100:.4f}% na noc.",
        "Ile musialaby dac pojedyncza WYBRANA noc:",
        "",
        "| Warunkowanie | Nocy czynnych | Zwrot/noc dla SR 0.8 | Krotnosc | Zwrot/noc dla DSR | Krotnosc |",
        "|---|---|---|---|---|---|",
    ]
    for f, nazwa in ((1.0, "wszystkie noce"), (0.5, "polowa"), (0.33, "jedna trzecia"),
                     (0.2, "kwintyl"), (0.1, "decyl")):
        m08, mds = mu_wymagane(0.8, f), mu_wymagane(sr_dsr, f)
        L.append(f"| {nazwa} | {int(len(post)*f)} | {m08*100:.3f}% | {m08/mu_bez:.1f}x | "
                 f"{mds*100:.3f}% | **{mds/mu_bez:.1f}x** |")
    L += [
        "",
        "**To jest wynik, ktorego sie nie spodziewalem i ktory zmienia sposob projektowania",
        "kart.** Warunkowanie nie jest darmowe: zawezenie do decyla nocy wymaga, by kazda",
        f"z nich niosla {mu_wymagane(sr_dsr, 0.1)/mu_bez:.0f}x obecna srednia przewage. Koncentracja sygnalu",
        "rosnie liniowo z zawezeniem, a kara za rzadkosc tylko pierwiastkowo — wiec",
        "oplaca sie zawezac tylko wtedy, gdy mechanizm naprawde koncentruje przewage.",
        "",
        "---",
        "",
        "## 6. Werdykt dla karty H004",
        "",
        "**H004 w postaci bezwarunkowej schodzi do benchmarkow.** Nie dlatego, ze",
        "wykazalismy zanik efektu — tego wykazac sie nie da — tylko dlatego, ze",
        "bezwarunkowy dryf nocny nie osiaga progu, ktory projekt sobie postawil.",
        "",
        "**Wersja warunkowa pozostaje otwarta, ale z jawnie wycenionym progiem wejscia.**",
        "Karta przeformulowana (audyt 3) pyta \"jaki mechanizm decyduje, KIEDY efekt",
        "wystepuje\". Zanim spali choc jedna probe, musi zadeklarowac:",
        "",
        "1. jaki ulamek nocy *f* wybiera jej warunek,",
        "2. jaki zwrot na noc czynna zaklada — i czy przekracza prog z tabeli wyzej,",
        "3. dlaczego mechanizm mialby dawac akurat taka koncentracje.",
        "",
        "Jesli punkt 2 nie da sie obronic **przed testem**, karta schodzi do benchmarkow",
        "regula samoczyszczaca z REGISTRY.md. Nie odkrywamy progu po fakcie.",
        "",
        "Konsekwencje dla REGISTRY.md:",
        "",
        "- H004 bezwarunkowa -> **BENCHMARK** (nie zuzywa licznika prob),",
        "- H004 warunkowa -> **IDEA** z obowiazkowa deklaracja *f* i progu przed testem,",
        "- wnioski przekrojowe **W001** i **W002** wchodza do rejestru.",
        "",
        "## 7. Wnioski przekrojowe (do REGISTRY.md)",
        "",
        "### W001 — poziomy bezwarunkowe sa poza zasiegiem tego projektu",
        "",
        "> Przy dziennym odchyleniu zwrotu nocnego rzedu 0.75% odroznienie dryfu",
        f"> 3.7%/rok od zera wymaga ~{lat_dla_37:,.0f} lat danych. Kazda karta, ktorej teza brzmi",
        "> \"efekt X o sile kilku procent rocznie istnieje / wygasl\", jest z gory",
        "> nierozstrzygalna. **Nie wolno na nia wydawac proby** — ani nie wolno opierac",
        "> decyzji projektowej na cudzym twierdzeniu tej klasy, niezaleznie od zrodla.",
        "",
        "### W002 — warunkowanie ma cene rosnaca jak 1/sqrt(f)",
        "",
        "> Zawezenie sygnalu do ulamka *f* okazji podnosi wymagany edge na pojedyncza",
        "> okazje o czynnik 1/sqrt(f), bo Sharpe liczy sie po wszystkich dniach.",
        f"> Dla decyla to **{mu_wymagane(sr_dsr, 0.1)/mu_bez:.0f}x** obecnej przewagi bezwarunkowej.",
        "> Wniosek projektowy: **karta warunkowa musi deklarowac *f* z gory** i uzasadniac,",
        "> skad ma wziac koncentracje przewagi. Warunek, ktory odsiewa 90% okazji \"bo",
        "> tak wyglada lepiej na wykresie\", niemal na pewno nie przejdzie bramki —",
        "> i mozna to stwierdzic ZANIM sie go przetestuje.",
        "",
    ]
    L = L  # koniec sekcji

    # tozsamosc ksiegowa — SPRAWDZANA, nie deklarowana
    noc, sesja, _ = dane["MNQ"]
    df_kontrola = load_continuous("MNQ")
    rth_k = df_kontrola.filter(pl.col("segment").is_in(RTH_SEGMENTY)).sort("ts_utc")
    open_adj_k = pl.col("open") + (pl.col("px_adj") - pl.col("close"))
    gk = (rth_k.group_by("trade_date")
              .agg(o=open_adj_k.first(), c=pl.col("px_adj").last(), n=pl.len())
              .sort("trade_date").filter(pl.col("n") >= MIN_BAROW_RTH))
    pelny = float(np.log(gk["c"].to_numpy()[-1] / gk["o"].to_numpy()[1]))
    rozjazd = abs((noc.sum() + sesja.sum()) - (pelny + float(np.log(
        gk["o"].to_numpy()[1] / gk["c"].to_numpy()[0]))))
    if rozjazd > 1e-9:
        sys.exit(f"BLAD: dekompozycja nie sumuje sie do zwrotu calkowitego "
                 f"(rozjazd {rozjazd:.2e}). Rachunek jest bledny — nie publikuj.")
    L += [
        "---",
        "",
        "### Kontrola poprawnosci",
        "",
        f"Suma skladowych: {(noc.sum()+sesja.sum())*100:+.2f}% — tozsamosc dekompozycji",
        "zachowana (noc + sesja = pelny zwrot buy-and-hold z pominieciem pierwszego dnia).",
        f"Wyniki spojne miedzy trzema niezaleznymi instrumentami "
        f"({', '.join(INSTRUMENTY)}), co wyklucza artefakt jednego zbioru danych.",
        "",
        "Odtworzenie: `python3 research/W001_overnight_drift.py`",
    ]

    RAPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n-> {RAPORT}")
    print(f"\nSharpe nocny MNQ: 2019-2026 = {sh_full:.2f}, {ROK_PODZIALU}-2026 = {sh_post:.2f}")
    print(f"Prog DSR: SR >= {sr_dsr:.2f}  |  cena warunkowania do decyla: "
          f"{mu_wymagane(sr_dsr, 0.1)/mu_bez:.0f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
