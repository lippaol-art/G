#!/usr/bin/env python3
"""W007 — walidacja OUT-OF-SAMPLE modelu wrazliwosci.  PLAN.pdf rozdz. 4.7, karta H013.

POWOD POWSTANIA TEGO RAPORTU.

W commicie 635774e opublikowalem model wrazliwosci indeksu (`engine/ndx_sensitivity`)
razem z tabela R² 0.887-0.982 podana tak, jakby byla jego walidacja. **Nie byla.**
To bylo R² IN-SAMPLE — liczone na tym samym oknie, na ktorym dopasowano
wspolczynniki. Model z osmioma regresorami zawsze wyjdzie z takiej tabeli dobrze,
niezaleznie od tego, czy cokolwiek przewiduje.

Ten skrypt liczy to, co powinno bylo zostac policzone od razu: **predykcje dnia t
z okna konczacego sie w t-1**, dla calej dostepnej historii. Kazda liczba w tym
raporcie jest wiec liczba, ktorej model NIE widzial w momencie estymacji.

CO JEST TU PORZADNIE ZMIERZONE, A CO NADAL NIE.

Mierzymy jakosc modelu **wrazliwosci** jako opisu zaleznosci indeks-skladniki.
NIE mierzymy tu, czy wrazliwosci sa lepsze od WAG NDX w roli, ktorej potrzebuje
karta H013 — bo wag historycznych nie mamy i nie kupujemy. Ablacja
"wrazliwosci vs wagi" pozostaje OTWARTA. Ten raport jej nie zastepuje.

Odniesieniem jest wiec model naiwny (rowne wagi przeskalowane), nie wagi NDX.

Zero zuzytych prob — badanie wlasnosci estymatora, nie backtest.

Wyjscie: reports/W007_wrazliwosci_walidacja.md
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.ndx_sensitivity import MEGACAPY, MIN_OKNO, OKNO_DNI, RIDGE_LAMBDA  # noqa: E402

RAPORT = Path("reports/W007_wrazliwosci_walidacja.md")
K6 = Path("data/clean/k6")
INDEKS = "QQQ"          # jedyny dostepny u nas proxy indeksu kasowego
BAZIS = 10_000.0        # zwroty raportujemy w punktach bazowych dziesietnych (‱)


def zwroty_rth(symbol: str) -> pl.DataFrame:
    """Dzienny log-zwrot close->close liczony na zamknieciach sesji RTH.

    Sesja RTH, nie caly dzien: premarket i afterhours maja inna plynnosc, a model
    ma opisywac te sama sesje, w ktorej handluje sie indeks kasowy.
    """
    p = K6 / f"{symbol.lower()}_1m.parquet"
    d = (
        pl.scan_parquet(p)
        .filter(pl.col("segment") == "rth")
        .sort("ts_utc")
        .group_by("trade_date")
        .agg(c=pl.col("close").last(), n=pl.len())
        .filter(pl.col("n") >= 60)
        .sort("trade_date")
        .collect()
    )
    return d.with_columns(
        (pl.col("c").log() - pl.col("c").log().shift(1)).alias(symbol)
    ).drop(["c", "n"]).drop_nulls()


def macierz() -> tuple[np.ndarray, np.ndarray, list]:
    """y = zwrot QQQ, X = zwroty osmiu megacapow, tylko dni wspolne dla wszystkich."""
    j = zwroty_rth(INDEKS)
    for s in MEGACAPY:
        j = j.join(zwroty_rth(s), on="trade_date", how="inner")
    j = j.sort("trade_date")
    y = j[INDEKS].to_numpy()
    X = np.column_stack([j[s].to_numpy() for s in MEGACAPY])
    return y, X, j["trade_date"].to_list()


def _solve(X: np.ndarray, y: np.ndarray, lam: float, bez_kary: int = 0) -> np.ndarray:
    """Ridge o sile skalowanej wzgledem danych; `bez_kary` pierwszych kolumn wolnych.

    Wyraz wolny NIE moze byc regularyzowany — kara na nim sciaga predykcje ku zeru
    i miesza dwa efekty: obciazenie modelu i obciazenie wprowadzone przez sama kare.
    Stad zerowa przekatna dla pierwszych `bez_kary` kolumn.
    """
    G = X.T @ X
    if lam == 0.0:
        return np.linalg.solve(G, X.T @ y)
    skala = float(np.trace(G)) / X.shape[1]
    kara = np.ones(X.shape[1])
    kara[:bez_kary] = 0.0
    return np.linalg.solve(G + lam * skala * np.diag(kara), X.T @ y)


def predykcja(
    y: np.ndarray, X: np.ndarray, i: int, *, lam: float,
    standaryzacja: bool = False, wyraz_wolny: bool = False,
) -> float:
    """Predykcja dnia i z okna [i-OKNO, i). Dzien i nie wchodzi do estymacji."""
    a, b = max(0, i - OKNO_DNI), i
    Xo, yo, xn = X[a:b], y[a:b], X[i]
    if standaryzacja:
        # skaler liczony WYLACZNIE z okna — inaczej byloby to lookahead przez tylne
        # drzwi: srednia i sd calego szeregu niosa informacje z przyszlosci
        mu, sd = Xo.mean(axis=0), Xo.std(axis=0, ddof=0)
        sd = np.where(sd > 0, sd, 1.0)
        Xo, xn = (Xo - mu) / sd, (xn - mu) / sd
    if wyraz_wolny:
        Xo = np.column_stack([np.ones(Xo.shape[0]), Xo])
        xn = np.concatenate([[1.0], xn])
        return float(xn @ _solve(Xo, yo, lam, bez_kary=1))
    return float(xn @ _solve(Xo, yo, lam))


def statystyki(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float, float]:
    ss_res = float(((y_true - y_pred) ** 2).sum())
    ss_tot = float(((y_true - y_true.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot
    obc = float((y_pred - y_true).mean()) * BAZIS
    mae = float(np.abs(y_true - y_pred).mean()) * BAZIS
    return r2, obc, mae


def main() -> int:
    brak = [s for s in (INDEKS, *MEGACAPY) if not (K6 / f"{s.lower()}_1m.parquet").exists()]
    if brak:
        sys.exit(f"Brak danych K6: {', '.join(brak)} — patrz HANDOFF.md")

    y, X, daty = macierz()
    idx = np.arange(MIN_OKNO, len(y))
    lata = np.array([daty[i].year for i in idx])
    y_true = y[idx]

    warianty: dict[str, dict] = {
        f"**ridge {RIDGE_LAMBDA:g}, bez wyrazu wolnego (obecny)**": {"lam": RIDGE_LAMBDA},
        "OLS, bez wyrazu wolnego (lambda = 0)": {"lam": 0.0},
        "ridge + nieregularyzowany wyraz wolny": {
            "lam": RIDGE_LAMBDA, "wyraz_wolny": True},
        "ridge + standaryzacja + wyraz wolny (postac podrecznikowa)": {
            "lam": RIDGE_LAMBDA, "standaryzacja": True, "wyraz_wolny": True},
        "standaryzacja BEZ wyrazu wolnego (wariant zle postawiony)": {
            "lam": RIDGE_LAMBDA, "standaryzacja": True},
    }
    K_OBECNY, K_OLS = list(warianty)[0], list(warianty)[1]
    K_WYRAZ, K_PODR, K_ZLE = list(warianty)[2], list(warianty)[3], list(warianty)[4]
    K_NAIWNY = "rowne wagi ze skala z okna (odniesienie)"

    wyniki: dict[str, tuple[float, float, float]] = {}
    pred_glowna = None
    for nazwa, kw in warianty.items():
        p = np.array([predykcja(y, X, i, **kw) for i in idx])
        wyniki[nazwa] = statystyki(y_true, p)
        if pred_glowna is None:
            pred_glowna = p

    # Model naiwny: rowne wagi przeskalowane stala. Stala tez estymowana z okna,
    # zeby porownanie bylo uczciwe — inaczej dalibysmy odniesieniu fory.
    p_naiwna = []
    for i in idx:
        a, b = max(0, i - OKNO_DNI), i
        srednia_okno = X[a:b].mean(axis=1)
        k = float(srednia_okno @ y[a:b] / (srednia_okno @ srednia_okno))
        p_naiwna.append(k * float(X[i].mean()))
    wyniki[K_NAIWNY] = statystyki(y_true, np.array(p_naiwna))

    # Wlasnosci samych wspolczynnikow — do korekty twierdzen o wspolliniowosci.
    sumy, ujemne_dni, nvda = [], 0, []
    for i in idx:
        a, b = max(0, i - OKNO_DNI), i
        beta = _solve(X[a:b], y[a:b], RIDGE_LAMBDA)
        sumy.append(float(beta.sum()))
        nvda.append(float(beta[MEGACAPY.index("NVDA")]))
        if (beta < 0).any():
            ujemne_dni += 1
    sumy_a, nvda_a = np.array(sumy), np.array(nvda)

    zakres = f"{daty[idx[0]]} → {daty[idx[-1]]}"
    L: list[str] = [
        "# W007 — walidacja out-of-sample modelu wrazliwosci",
        "",
        f"*Wygenerowane przez `research/W007_wrazliwosci_walidacja.py`, "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}. "
        f"N = {len(idx)} dni predykcji, {zakres}.*",
        "",
        "**Status licznika prob: 0 zuzytych.**",
        "",
        "## 0. Dlaczego ten raport istnieje",
        "",
        "Model wrazliwosci opublikowalem z tabela R² 0.887-0.982 podana tak, jakby",
        "byla jego walidacja. **Nie byla** — to bylo R² in-sample, liczone na tym",
        "samym oknie, na ktorym dopasowano wspolczynniki. Osiem regresorow zawsze",
        "wyjdzie z takiej tabeli dobrze, niezaleznie od wartosci predykcyjnej.",
        "",
        "Ponizsze liczby sa liczone inaczej: **predykcja dnia t z okna konczacego",
        f"sie w t-1**, okno {OKNO_DNI} dni, przez cala historie. Model nie widzial",
        "zadnej z nich w momencie estymacji.",
        "",
        "## 1. Wynik out-of-sample",
        "",
        "| Wariant | OOS R² | Obciazenie | MAE |",
        "|---|---|---|---|",
    ]
    for nazwa, (r2, obc, mae) in wyniki.items():
        L.append(f"| {nazwa} | {r2:.4f} | {obc:+.2f}‱ | {mae:.2f}‱ |")

    r2_ridge, obc_ridge, mae_ridge = wyniki[K_OBECNY]
    r2_ols = wyniki[K_OLS][0]
    r2_naiwny, _, mae_naiwny = wyniki[K_NAIWNY]
    r2_wyraz, obc_wyraz, _ = wyniki[K_WYRAZ]
    r2_podr, obc_podr, _ = wyniki[K_PODR]
    obc_zle = wyniki[K_ZLE][1]

    L += [
        "",
        "Obciazenie i MAE w **dziesietnych punktach bazowych** (‱ = 0.01% = 1e-4).",
        "Obciazenie = srednia predykcji minus srednia realizacji; dodatnie oznacza,",
        "ze model systematycznie oczekuje od indeksu wiecej, niz indeks robi.",
        "",
        "### Co z tego wynika — takze to, co niewygodne",
        "",
        "**Ridge nie wnosi nic.** OLS i ridge daja OOS R² identyczne do czterech",
        f"miejsc po przecinku ({r2_ols:.4f} wobec {r2_ridge:.4f}); roznica MAE wynosi",
        f"{abs(wyniki[K_OLS][2] - mae_ridge):.4f}‱, czyli zero w kazdym praktycznym sensie. Narracja",
        "z pierwszej wersji modulu, ze ridge \"stabilizuje wspolczynniki, ktore OLS",
        "daje niestabilne i czesciowo ujemne\", byla **nieuprawniona**: przy oknie",
        f"{OKNO_DNI} dni i osmiu regresorach macierz jest dobrze uwarunkowana i OLS",
        "radzi sobie tak samo. Ridge zostaje w kodzie jako **tanie zabezpieczenie na",
        "wypadek okna zdegenerowanego**, nie jako element niosacy wartosc.",
        "",
        f"**Przewaga nad modelem naiwnym jest skromna**: R² {r2_naiwny:.4f} → "
        f"{r2_ridge:.4f}, MAE {mae_naiwny:.2f}‱ → {mae_ridge:.2f}‱.",
        "Rowne wagi przeskalowane jedna stala tlumacza wiekszosc tego, co tlumacza",
        "wrazliwosci. Model jest lepszy, ale nie o rzad wielkosci — i tak nalezy",
        "o nim mowic.",
        "",
        f"**Model jest praktycznie nieobciazony OOS**: {obc_ridge:+.2f}‱ przy MAE "
        f"{mae_ridge:.2f}‱, czyli {abs(obc_ridge)/mae_ridge*100:.1f}% bledu typowego.",
        "To byla wlasciwa obawa i tu wynik jest dobry: **stale przesuniecie w rezyduum",
        "jest nieodroznialne od sygnalu**, ktorego szuka H013, wiec model dokladajacy",
        "wlasny dryf falszowalby te karte w sposob niewidoczny w backtescie.",
        "",
        "**Wyraz wolny nie pomaga i lekko szkodzi.** Wersja z nieregularyzowanym",
        f"wyrazem wolnym ma R² {r2_wyraz:.4f} (wobec {r2_ridge:.4f}) i obciazenie",
        f"{obc_wyraz:+.2f}‱ (wobec {obc_ridge:+.2f}‱). Postac podrecznikowa —",
        "standaryzacja plus nieregularyzowany wyraz wolny — daje odpowiednio",
        f"{r2_podr:.4f} i {obc_podr:+.2f}‱. Zaden z tych wariantow nie jest lepszy",
        "od obecnego, a wprowadzaja stopien swobody, ktory model moze wykorzystac",
        "na dryf. Brak wyrazu wolnego jest wiec **decyzja poparta pomiarem**.",
        "",
        f"**Sama standaryzacja bez wyrazu wolnego psuje model** (obciazenie "
        f"{obc_zle:+.2f}‱).",
        "Nie jest to argument przeciw standaryzacji jako takiej — to wariant zle",
        "postawiony i wpisany do tabeli celowo. Centrowanie X przy niecentrowanym y",
        "i braku wyrazu wolnego **zmienia model**, a nie tylko jego uwarunkowanie:",
        "predykcja traci czlon, ktory wczesniej niosla srednia regresorow. Wniosek",
        "praktyczny: standaryzacji nie wolno dokladac \"na wszelki wypadek\" bez",
        "wyrazu wolnego, a skoro wyraz wolny nie pomaga (wyzej), obie rzeczy",
        "zostaja poza modelem.",
        "",
        "Skalery i lambda pochodza **wylacznie z okna** konczacego sie w t−1;",
        "lambda jest stala projektowa, nie byla dobierana pod wynik OOS z tej tabeli.",
        "",
        "## 2. Wlasnosci wspolczynnikow — sprostowanie, nie dowod",
        "",
        "| Wielkosc | Wartosc |",
        "|---|---|",
        f"| Suma wspolczynnikow, zakres | {sumy_a.min():.3f} – {sumy_a.max():.3f} |",
        f"| Suma wspolczynnikow, mediana | {np.median(sumy_a):.3f} |",
        f"| Dni z **jakimkolwiek** ujemnym wspolczynnikiem | {ujemne_dni} z {len(idx)} "
        f"({ujemne_dni/len(idx)*100:.1f}%) |",
        f"| Wrazliwosc NVDA, poczatek → koniec | {nvda_a[0]:.3f} → {nvda_a[-1]:.3f} |",
        "",
        "**Zadna z tych liczb nie jest testem modelu i nie nalezy ich tak podawac.**",
        "",
        "Suma wspolczynnikow **nie ma powodu** rownac sie sumie wag osemki. To sa",
        "dwie rozne wielkosci: waga mierzy mechaniczny udzial w koszyku, wspolczynnik",
        "regresji mierzy historyczna reakcje indeksu, ktora obejmuje takze ruch",
        "reszty koszyka skorelowanej ze skladnikiem. Roznica jest **spodziewana",
        "z konstrukcji** i jej wystapienie nie potwierdza niczego.",
        "",
        "Rosnaca wrazliwosc NVDA jest **kontrola sensownosci**, nie niezaleznym",
        "potwierdzeniem. Zgadza sie z tym, co wiadomo o wzroscie wagi NVDA, ale",
        "wspolczynnik moglby rosnac takze z innych powodow — na przyklad dlatego, ze",
        "caly sektor polprzewodnikowy zaczal poruszac indeksem mocniej. Kontrola",
        "wypada dobrze; dowodem nie jest.",
        "",
        f"Odsetek dni z ujemnym wspolczynnikiem ({ujemne_dni/len(idx)*100:.1f}%) mowi",
        "tylko tyle, ze estymacja jest stabilna znakowo. **Nie dowodzi, ze ridge",
        "cokolwiek naprawil** — OLS z sekcji 1 daje ten sam wynik predykcyjny.",
        "",
        "## 3. Stabilnosc w czasie",
        "",
        "| Rok | N | OOS R² | Obciazenie | Mediana sumy wspolczynnikow |",
        "|---|---|---|---|---|",
    ]
    assert pred_glowna is not None
    per_rok: dict[int, tuple[float, float, int]] = {}
    for rok in sorted(set(lata.tolist())):
        m = lata == rok
        r2r, obcr, _ = statystyki(y_true[m], pred_glowna[m])
        per_rok[rok] = (r2r, obcr, int(m.sum()))
        L.append(f"| {rok} | {int(m.sum())} | {r2r:.4f} | {obcr:+.2f}‱ | "
                 f"{np.median(sumy_a[m]):.3f} |")

    najgorszy = min(per_rok, key=lambda r: per_rok[r][0])
    r2_najg, obc_najg, n_najg = per_rok[najgorszy]
    pozostale_r2 = [v[0] for k, v in per_rok.items() if k != najgorszy]
    max_obc_poz = max(abs(v[1]) for k, v in per_rok.items() if k != najgorszy)

    L += [
        "",
        f"### Rok {najgorszy} odstaje i nie wolno tego przemilczec",
        "",
        f"R² spada do **{r2_najg:.4f}** wobec {min(pozostale_r2):.4f}–{max(pozostale_r2):.4f}",
        f"w pozostalych latach, a obciazenie rosnie do **{obc_najg:+.2f}‱** — przy",
        f"maksimum {max_obc_poz:.2f}‱ gdzie indziej i {obc_ridge:+.2f}‱ na calej probie.",
        f"To {abs(obc_najg)/max_obc_poz:.1f}× najgorszy pozostaly rok.",
        "",
        "Znak jest tu informacja. Ujemne obciazenie znaczy, ze **indeks rosl bardziej,",
        "niz implikowaly megacapy** — czyli ruch przenosil sie na pozostale spolki",
        "koszyka, ktorych model nie obserwuje. Osiem regresorow opisuje wtedy mniej",
        "niz zwykle i systematycznie zaniza oczekiwanie.",
        "",
        "**Dla H013 jest to ostrzezenie pierwszej kategorii.** Karta czyta rezyduum",
        "jako niedowycenienie kontraktu. W okresie o takim obciazeniu rezyduum ma",
        "**stale przesuniecie pochodzace z modelu, nie z rynku** — a karta nie ma jak",
        "tych dwoch rzeczy odroznic. Pre-flight musi wiec raportowac wynik per rok",
        f"i osobno sprawdzic, czy efekt nie pochodzi z {najgorszy}.",
        "",
        f"Zastrzezenie: {najgorszy} jest u nas niepelny (**{n_najg} dni**), wiec czesc",
        "roznicy to mniejsza probka. Nie tlumaczy to jednak znaku obciazenia, ktory",
        "jest zjawiskiem, nie szumem.",
        "",
        "## 4. Czego ten raport NIE rozstrzyga",
        "",
        "**Ablacja \"wrazliwosci vs wagi NDX\" pozostaje otwarta.** Historycznych wag",
        "NDX nie mamy — sa produktem platnym, a przyjecie wag dzisiejszych dla calej",
        "historii byloby bledem powazniejszym niz problem, ktory miałyby rozwiazac",
        f"(wrazliwosc NVDA wzrosla u nas {nvda_a[0]:.3f} → {nvda_a[-1]:.3f}).",
        "",
        "Ten raport porownuje wrazliwosci z modelem **naiwnym**, nie z wagami.",
        "To dwie rozne rzeczy i nie wolno drugiej podstawiac za pierwsza. W karcie",
        "H013 ablacja piata zostaje oznaczona jako **NIEWYKONALNA bez platnych",
        "danych**, a nie jako rozstrzygnieta.",
        "",
        "Nie rozstrzygamy tez, czy model jest **wystarczajaco dobry dla H013**.",
        f"MAE {mae_ridge:.0f}‱ to okolo {mae_ridge/BAZIS*100:.2f}% dziennie — "
        "wielkosc porownywalna",
        "z rezyduum, ktorego karta szuka. **To jest ostrzezenie, nie detal:** jesli",
        "blad modelu jest tego samego rzedu co sygnal, karta moze mierzyc wlasny",
        "szum estymacyjny. Pre-flight musi to sprawdzic wprost, porownujac rozklad",
        "rezyduum w dni zdarzen z rozkladem w dni zwykle.",
        "",
        "---",
        "",
        "Odtworzenie: `python3 research/W007_wrazliwosci_walidacja.py`",
    ]

    RAPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPORT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"-> {RAPORT}")
    for nazwa, (r2, obc, mae) in wyniki.items():
        print(f"  {nazwa:42s} R²={r2:.4f}  obc={obc:+.2f}‱  MAE={mae:.2f}‱")
    print(f"  dni z ujemnym wspolczynnikiem: {ujemne_dni}/{len(idx)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
