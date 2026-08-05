#!/usr/bin/env python3
"""W011 — walidacja OOS modelu NOCNEGO uzytego w W009.  Audyt zamykajacy H013.

POWOD POWSTANIA.

W009 odrzucil karte H013 na podstawie rezyduum z modelu nocnego. Jakosc tego
modelu nie zostala jednak nigdzie zmierzona out-of-sample. W007 mierzyl **inny
obiekt**:

    W007:  QQQ  ~ 8 megacapow            zwroty RTH close-to-close
    W009:  NQ   ~ 8 megacapow + ES + SOXX zwroty NOCNE

To nie jest ten sam estymator ani ten sam problem. Jedyna liczba, ktora W009
podal o jakosci modelu — redukcja odchylenia rezyduum o 82% — jest statystyka
**in-sample** z okna kroczacego i nie mowi nic o wartosci predykcyjnej.

Odrzucenie karty na podstawie rezyduum, ktorego jakosci sie nie zmierzylo, jest
tym samym bledem co publikowanie R² in-sample jako walidacji (W007) — tyle ze
w druga strone. Ten raport go naprawia.

**Nie po to, zeby ratowac H013.** Po to, zeby ustalic, czy rezyduum uzyte do jej
odrzucenia jest sensownym rezyduum. Jesli model nocny okaze sie zly, werdykt
W009 trzeba bedzie uniewaznic i policzyc od nowa — niezaleznie od tego, w ktora
strone poszedlby wynik.

MODEL JEST IMPORTOWANY, NIE ODTWARZANY. `zbuduj()` z W009 zwraca macierz X
i wektor y; ten skrypt liczy na nich, wiec walidowany jest dokladnie ten obiekt,
ktory posluzyl do werdyktu.

Zero zuzytych prob.

Wyjscie: reports/W011_model_nocny_oos.md
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.ndx_sensitivity import MIN_OKNO, OKNO_DNI, RIDGE_LAMBDA  # noqa: E402
from research.W009_H013_preflight import _ridge, zbuduj  # noqa: E402

RAPORT = Path("reports/W011_model_nocny_oos.md")
BAZIS = 10_000.0        # dziesietne punkty bazowe (‱)


def statystyki(y: np.ndarray, p: np.ndarray) -> tuple[float, float, float]:
    r2 = 1.0 - float(((y - p) ** 2).sum()) / float(((y - y.mean()) ** 2).sum())
    return r2, float((p - y).mean()) * BAZIS, float(np.abs(y - p).mean()) * BAZIS


def main() -> int:
    G = zbuduj("przed_otwarciem")
    y, X, kol = G["y"], G["X"], G["kol"]
    idx_kontroli = G["idx_kontroli"]
    dni, jest = G["dni"], G["jest"]

    idx = np.arange(MIN_OKNO, len(y))
    lata = np.array([dni[i].year for i in idx])
    y_true = y[idx]

    # --- trzy modele, wszystkie bez lookaheadu -------------------------------
    p_pelny, p_kontrole, p_naiwny = [], [], []
    for i in idx:
        a, b = max(0, i - OKNO_DNI), i
        p_pelny.append(float(X[i] @ _ridge(X[a:b], y[a:b], RIDGE_LAMBDA)))
        p_kontrole.append(float(X[i][idx_kontroli]
                                @ _ridge(X[a:b][:, idx_kontroli], y[a:b], RIDGE_LAMBDA)))
        # naiwny: srednia zwrotow skladnikow przeskalowana stala z okna
        sk = [k for k in range(len(kol)) if kol[k] not in ("ES", "SOXX")]
        sr = X[a:b][:, sk].mean(axis=1)
        k = float(sr @ y[a:b] / (sr @ sr)) if float(sr @ sr) > 0 else 0.0
        p_naiwny.append(k * float(X[i][sk].mean()))
    P = {"pelny (skladniki + ES + SOXX)": np.array(p_pelny),
         "tylko ES + SOXX": np.array(p_kontrole),
         "naiwny (rowne wagi skladnikow)": np.array(p_naiwny)}

    L: list[str] = [
        "# W011 — walidacja OOS modelu nocnego (audyt zamykajacy H013)",
        "",
        f"*Wygenerowane przez `research/W011_model_nocny_oos.py`, "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}. "
        f"N = {len(idx)} predykcji, {dni[idx[0]]} → {dni[idx[-1]]}.*",
        "",
        "**Status licznika prob: 0 zuzytych.**",
        "",
        "## 0. Po co ten raport",
        "",
        "W009 odrzucil H013 na podstawie rezyduum modelu nocnego, ale jakosci tego",
        "modelu nie zmierzyl OOS. Jedyna podana liczba — redukcja odchylenia o 82% —",
        "jest statystyka **in-sample**. W007 walidowal **inny obiekt**: QQQ na zwrotach",
        "RTH wobec osmiu spolek, bez ES i SOXX.",
        "",
        "Model jest tu **importowany z W009**, nie odtwarzany: `zbuduj()` zwraca te sama",
        "macierz X i ten sam wektor y, ktore posluzyly do werdyktu.",
        "",
        "## 1. Wynik out-of-sample",
        "",
        "Predykcja dnia t z okna konczacego sie w t−1, okno "
        f"{OKNO_DNI} sesji, przez cala historie.",
        "",
        "| Model | OOS R² | Obciazenie | MAE |",
        "|---|---|---|---|",
    ]
    wyn = {}
    for nazwa, p in P.items():
        r2, obc, mae = statystyki(y_true, p)
        wyn[nazwa] = (r2, obc, mae)
        L.append(f"| {nazwa} | {r2:.4f} | {obc:+.2f}‱ | {mae:.2f}‱ |")

    L += [
        "",
        f"sd zwrotu nocnego NQ: {y_true.std(ddof=1)*100:.3f}% "
        f"({y_true.std(ddof=1)*BAZIS:.0f}‱).",
        "",
        "## 2. Kalibracja",
        "",
        "Regresja `zrealizowane = α + γ · przewidziane`. Model dobrze skalibrowany ma",
        "**γ ≈ 1** i **α ≈ 0**. γ < 1 oznacza, ze model **przestrzeliwuje** — a wtedy",
        "rezyduum ma skladowa systematyczna, ktora karta H013 czytalaby jako sygnal.",
        "",
        "| Model | γ (nachylenie) | α (wyraz wolny) |",
        "|---|---|---|",
    ]
    for nazwa, p in P.items():
        gam, alfa = np.polyfit(p, y_true, 1)
        L.append(f"| {nazwa} | **{gam:.3f}** | {alfa*BAZIS:+.2f}‱ |")

    gam_p, alfa_p = np.polyfit(P["pelny (skladniki + ES + SOXX)"], y_true, 1)
    L += [
        "",
        "## 3. Rozklad roczny — z naciskiem na 2026",
        "",
        "W007 znalazl w modelu DZIENNYM silne obciazenie w 2026 (−8.59‱ wobec +0.30‱",
        "na calej probie). Pytanie, czy model nocny ma ten sam problem, jest kluczowe:",
        "**jesli tak, rezyduum W009 ma w koncowce probki przesuniecie pochodzace",
        "z modelu, a nie z rynku.**",
        "",
        "| Rok | N | OOS R² | Obciazenie | MAE | γ |",
        "|---|---|---|---|---|---|",
    ]
    p_gl = P["pelny (skladniki + ES + SOXX)"]
    per_rok = {}
    for rok in sorted(set(lata.tolist())):
        m = lata == rok
        if m.sum() < 20:
            continue
        r2r, obcr, maer = statystyki(y_true[m], p_gl[m])
        gr = float(np.polyfit(p_gl[m], y_true[m], 1)[0])
        per_rok[rok] = (r2r, obcr, maer, gr, int(m.sum()))
        L.append(f"| {rok} | {int(m.sum())} | {r2r:.4f} | {obcr:+.2f}‱ | "
                 f"{maer:.2f}‱ | {gr:.3f} |")

    najg = min(per_rok, key=lambda r: per_rok[r][0])
    obc_2026 = per_rok.get(2026, (0, 0, 0, 0, 0))[1]
    obc_all = wyn["pelny (skladniki + ES + SOXX)"][1]

    # --- obciazenie w sesje zdarzen kontra pozostale ------------------------
    jest_idx = jest[idx]
    L += [
        "",
        "## 4. Czy obciazenie rozni sie w sesje zdarzen",
        "",
        "Gdyby model byl obciazony akurat w sesje publikacji wynikow, rezyduum W009",
        "mialoby stale przesuniecie **dokladnie tam, gdzie karta patrzy**.",
        "",
        "| Grupa | N | OOS R² | Obciazenie | MAE |",
        "|---|---|---|---|---|",
    ]
    for nazwa, m in (("sesje zdarzen", jest_idx), ("pozostale sesje", ~jest_idx)):
        r2g, obcg, maeg = statystyki(y_true[m], p_gl[m])
        L.append(f"| {nazwa} | {int(m.sum())} | {r2g:.4f} | {obcg:+.2f}‱ | {maeg:.2f}‱ |")

    r2_zd = statystyki(y_true[jest_idx], p_gl[jest_idx])[0]
    obc_zd = statystyki(y_true[jest_idx], p_gl[jest_idx])[1]
    mae_zd = statystyki(y_true[jest_idx], p_gl[jest_idx])[2]

    # --- czy korekta obciazenia zmienia werdykt W009 ------------------------
    rez, wy, maska = G["rez"], G["wy"], G["maska"]
    lata_pelne = G["lata"]
    # Korekta bez lookaheadu: srednia rezyduum z WCZESNIEJSZYCH sesji zdarzen.
    # Nie wolno uzyc sredniej z calej proby — to bylaby informacja z przyszlosci.
    korekta = np.full(len(rez), np.nan)
    hist: list[float] = []
    for i in range(len(rez)):
        if maska[i]:
            korekta[i] = float(np.mean(hist)) if len(hist) >= 20 else 0.0
            hist.append(float(rez[i]))
    rez_k = rez - korekta

    m = maska & np.isfinite(rez_k)
    pnl_s = (-np.sign(rez) * wy)[m]
    pnl_k = (-np.sign(rez_k) * wy)[m]
    rz, rk = rez[m], rez_k[m]

    def t_(x: np.ndarray) -> float:
        return float(x.mean() / x.std(ddof=1) * np.sqrt(x.size))

    L += [
        "",
        "## 5. Czy korekta obciazenia zmienia werdykt W009",
        "",
        f"Obciazenie w sesje zdarzen ({obc_zd:+.2f}‱) jest rzedu **20% odchylenia",
        "rezyduum** (153‱ na sesjach zdarzen wg W009). Przesuwa wiec **znak** rezyduum",
        "w jedna strone — a znak jest sygnalem karty. W009 naliczyl 106 rezyduow",
        "ujemnych wobec 79 dodatnich; przy symetrii oczekiwaloby sie ~93/93.",
        "",
        "**Czesc \"asymetrii stron\" z przewidywania 4 W009 jest wiec artefaktem modelu,",
        "nie wlasnoscia rynku.** Ponizej te same statystyki po korekcie obciazenia",
        "sredniem z WCZESNIEJSZYCH sesji zdarzen (bez lookaheadu).",
        "",
        "| Miara | Rezyduum surowe | Rezyduum skorygowane |",
        "|---|---|---|",
        f"| Rezyduow ujemnych / dodatnich | {int((rz<0).sum())} / {int((rz>0).sum())} | "
        f"{int((rk<0).sum())} / {int((rk>0).sum())} |",
        f"| korelacja(rezyduum, zwrot po otwarciu) | "
        f"{np.corrcoef(rz, wy[m])[0,1]:+.4f} | {np.corrcoef(rk, wy[m])[0,1]:+.4f} |",
        f"| sredni wynik fade'u | {pnl_s.mean()*100:+.4f}% | {pnl_k.mean()*100:+.4f}% |",
        f"| **t** | **{t_(pnl_s):+.2f}** | **{t_(pnl_k):+.2f}** |",
        "",
        "| Warunek | t (surowe) | t (skorygowane) |",
        "|---|---|---|",
    ]
    for q, nazwa in ((0.0, "wszystkie zdarzenia"), (2 / 3, "gorny tercyl \\|rezyduum\\|"),
                     (0.9, "gorny decyl \\|rezyduum\\|")):
        ms = np.abs(rz) >= np.quantile(np.abs(rz), q)
        mk = np.abs(rk) >= np.quantile(np.abs(rk), q)
        L.append(f"| {nazwa} | {t_(pnl_s[ms]):+.2f} | {t_(pnl_k[mk]):+.2f} |")

    L += [
        "",
        "| Strona | N (skor.) | Sredni wynik | t |",
        "|---|---|---|---|",
    ]
    for nazwa, mm in (("dodatnie rezyduum", rk > 0), ("ujemne rezyduum", rk < 0)):
        L.append(f"| {nazwa} | {int(mm.sum())} | {pnl_k[mm].mean()*100:+.4f}% | "
                 f"{t_(pnl_k[mm]):+.2f} |")

    inne_m = G["gotowe"] & ~G["jest"]
    L += [
        "",
        "### Skad bierze sie ta \"asymetria\" — prostsze wyjasnienie",
        "",
        "Po korekcie obie strony daja wynik o podobnej wielkosci i przeciwnym znaku,",
        "co wyglada na mechanizm dzialajacy tylko w jedna strone. Nie jest to jednak",
        "wlasnosc rezyduum, tylko **dryfu kierunkowego w poranki po publikacjach**:",
        "",
        "| Grupa sesji | N | Zwrot 09:31→10:30 | t |",
        "|---|---|---|---|",
        f"| sesje zdarzen | {int(m.sum())} | {wy[m].mean()*100:+.4f}% | "
        f"{t_(wy[m]):+.2f} |",
        f"| pozostale sesje | {int(inne_m.sum())} | {wy[inne_m].mean()*100:+.4f}% | "
        f"{t_(wy[inne_m]):+.2f} |",
        "",
        "W poranki reakcji na wyniki NQ dryfuje w dol, w pozostale — lekko w gore.",
        "Sygnal karty (`−sign(rezyduum)`) jedynie **rozcina ten dryf** zmienna, ktora",
        "niesie malo informacji: strona, ktora \"gra z dryfem\", wychodzi na plus,",
        "druga na minus. To nie jest domykanie sie rezyduum.",
        "",
        "**Uwaga: to nie jest nowa karta.** Dryf ma t = −1.39 przy 185 obserwacjach,",
        "czyli jest nieistotny, i zostal znaleziony **po** obejrzeniu wyniku. Zapisuje",
        "go jako obserwacje do ewentualnego przyszlego ID, nie jako hipoteze do testu.",
    ]

    lata_m = lata_pelne[m]
    L += [
        "",
        "### Rozklad roczny w postaci bezwzglednej",
        "",
        "Poprzednia wersja podawala **udzial procentowy roku w wyniku**, co przy ujemnym",
        "wyniku calkowitym jest mylace: rok stratny wychodzil `+118%`, a zyskowny `−77%`.",
        "Ponizej to samo bez ilorazow.",
        "",
        "| Rok | N | Suma (pkt) | Srednia (%) | Znak |",
        "|---|---|---|---|---|",
    ]
    poziom = G["poziom"]
    for rok in sorted(set(lata_m.tolist())):
        mm = lata_m == rok
        x = pnl_k[mm]
        L.append(f"| {rok} | {int(mm.sum())} | {x.sum()*poziom:+.0f} | "
                 f"{x.mean()*100:+.4f} | {'+' if x.mean() > 0 else '−'} |")
    dod = sum(1 for r in sorted(set(lata_m.tolist())) if pnl_k[lata_m == r].mean() > 0)
    sr_lat = [pnl_k[lata_m == r].mean() * 100 for r in sorted(set(lata_m.tolist()))]
    L += [
        "",
        f"Lat dodatnich: **{dod} z {len(sr_lat)}**. Rozstep srednich rocznych: "
        f"od {min(sr_lat):+.4f}% do {max(sr_lat):+.4f}%.",
        "",
        "## 6. Werdykt audytu",
        "",
        "| Pytanie | Odpowiedz |",
        "|---|---|",
        f"| Czy model nocny ma wartosc predykcyjna OOS? | R² = "
        f"{wyn['pelny (skladniki + ES + SOXX)'][0]:.4f} |",
        f"| Czy skladniki wnosza cos ponad ES+SOXX? | "
        f"{wyn['tylko ES + SOXX'][0]:.4f} → "
        f"{wyn['pelny (skladniki + ES + SOXX)'][0]:.4f} |",
        f"| Czy model jest skalibrowany? | γ = {gam_p:.3f}, α = {alfa_p*BAZIS:+.2f}‱ |",
        f"| Czy jest obciazony na calej probie? | {obc_all:+.2f}‱ przy MAE "
        f"{wyn['pelny (skladniki + ES + SOXX)'][2]:.2f}‱ |",
        f"| Czy jest obciazony w sesje zdarzen? | {obc_zd:+.2f}‱ przy MAE "
        f"{mae_zd:.2f}‱, R² {r2_zd:.4f} |",
        f"| Najgorszy rok | {najg} (R² {per_rok[najg][0]:.4f}, "
        f"obciazenie {per_rok[najg][1]:+.2f}‱) |",
        f"| Obciazenie 2026 | {obc_2026:+.2f}‱ |",
        "",
        "### Co audyt ustalil",
        "",
        "**Model nocny jest dobry i lepszy od dziennego.** OOS R² "
        f"{wyn['pelny (skladniki + ES + SOXX)'][0]:.4f} wobec 0.9436 dla modelu dziennego",
        f"z W007, MAE {wyn['pelny (skladniki + ES + SOXX)'][2]:.2f}‱, kalibracja "
        f"γ = {gam_p:.3f}. Nie ma tez problemu z 2026, ktory miał model dzienny",
        f"({obc_2026:+.2f}‱ wobec −8.59‱ tam). **Rezyduum uzyte do odrzucenia karty",
        "jest sensownym rezyduum** — i to jest glowna odpowiedz tego audytu.",
        "",
        "**Skladniki wnosza duzo — do MODELU.** Sam ES+SOXX daje MAE "
        f"{wyn['tylko ES + SOXX'][2]:.2f}‱; dolozenie osmiu spolek schodzi do "
        f"{wyn['pelny (skladniki + ES + SOXX)'][2]:.2f}‱, czyli o "
        f"{(1-wyn['pelny (skladniki + ES + SOXX)'][2]/wyn['tylko ES + SOXX'][2]):.0%}.",
        "To **nie jest sprzeczne** z przewidywaniem 6 z W009, ktore mowilo o czyms innym:",
        "ze rezyduum tych skladnikow nie daje sygnalu handlowego lepszego niz sama luka.",
        "Oba zdania sa prawdziwe i trzeba je trzymac osobno — modelowanie ruchu indeksu",
        "to nie to samo co handlowanie odchylenia od modelu.",
        "",
        "**Znaleziono realna usterke W009.** Model jest obciazony w sesje zdarzen",
        f"({obc_zd:+.2f}‱ wobec −0.21‱ w pozostale), co przesuwalo znak rezyduum",
        "i wytwarzalo pozorna asymetrie stron (106/79). Po korekcie bez lookaheadu",
        "jest 93/92. **Przewidywanie 4 z W009 zawiodlo czesciowo z powodu wewnetrznego",
        "dla modelu, nie wlasnosci rynku** — i tak trzeba je odtad opisywac.",
        "",
        "**Werdykt karty sie nie zmienia.** Po korekcie wynik fade'u idzie ku zeru",
        f"(t {t_(pnl_s):+.2f} → {t_(pnl_k):+.2f}), warunkowanie nadal dziala na opak",
        "(t maleje wraz z wielkoscia rezyduum, nie rosnie), a znak wyniku nadal odwraca",
        "sie miedzy 2022 a 2023. Zadna z tych trzech rzeczy nie byla artefaktem",
        "obciazenia.",
        "",
        "### Sformulowanie werdyktu",
        "",
        "Poprzednia wersja W009 twierdzila, ze „sprzecznosci wewnetrzne nie sa kwestia",
        "mocy testu\". **To bylo za mocne.** Mala proba sama w sobie potrafi wytworzyc",
        "niestabilnosc znakow, pozorna asymetrie i skrajne wyniki w decylu liczacym",
        "19 obserwacji.",
        "",
        "> Poprawne sformulowanie: **mimo ograniczonej mocy uklad wynikow jest",
        "> niezgodny z wczesniej zadeklarowanymi przewidywaniami mechanizmu, dlatego",
        "> karta nie spelnia bramki GO.**",
        "",
        "To wystarcza do odrzucenia karty bez twierdzenia, ze udowodniono statystycznie",
        "brak jakiegokolwiek edge'u. Nie udowodniono i przy tej probie udowodnic sie",
        "nie da.",
        "",
        "---",
        "",
        "Odtworzenie: `python3 research/W011_model_nocny_oos.py`",
    ]

    RAPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPORT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"-> {RAPORT}")
    for nazwa, (r2, obc, mae) in wyn.items():
        print(f"  {nazwa:34s} R²={r2:.4f}  obc={obc:+.2f}‱  MAE={mae:.2f}‱")
    print(f"  kalibracja gamma={gam_p:.3f} alfa={alfa_p*BAZIS:+.2f}‱")
    print(f"  zdarzenia: R²={r2_zd:.4f} obc={obc_zd:+.2f}‱")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
