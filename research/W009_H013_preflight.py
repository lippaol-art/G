#!/usr/bin/env python3
"""W009 — pre-flight H013: rezydualny repricing po wynikach megacapow.  PLAN rozdz. 8.4.

MODUL PELNI PODWOJNA ROLE — NIE PRZENOSIC (decyzja wlasciciela, poz. N4).

Po pierwsze jest ZAMROZONYM EKSPERYMENTEM Gen1: to ten plik, dokladnie
w tej postaci, wyprodukowal werdykt NO-GO dla karty H013. Jego wartoscia
dowodowa jest nienaruszalnosc.

Po drugie jest de facto BIBLIOTEKA: `research/W011` i `research/W012`
importuja z niego `zbuduj()`, zeby walidowac i przekrajac DOKLADNIE ten
sam model, a nie jego kopie. To bylo celowe — W007 sparzylo sie na tym,
ze walidowalo model o innej konstrukcji niz mierzony.

Wyciagniecie `zbuduj()` do wspolnego modulu rozbiloby dowod na dwa pliki
dla korzysci czysto estetycznej. Adnotacja zamiast przeniesienia.

TO JEST PUNKT GO/NO-GO KARTY. Zero zuzytych prob — badanie rozkladow, nie backtest.
Zadnych stopow, zadnych progow, zadnej optymalizacji. Szesc przewidywan mechanizmu
zadeklarowanych z gory i raportowanych **wszystkie**, takze niekorzystne.

KONSTRUKCJA — JEDNO OKNO DLA AMC I BMO.

Karta pyta, czy kontrakt na indeks wycenil juz to, co zrobily skladniki, zanim
otworzy sie sesja kasowa. Naturalnym oknem jest wiec **noc**: od zamkniecia RTH
poprzedniej sesji do ostatniego notowania przed otwarciem sesji reakcji.

Okno to obejmuje oba rodzaje publikacji, i to bez zadnej gimnastyki:

    AMC opublikowane wieczorem dnia D  -> wpada w okno D -> D'
    BMO opublikowane rano dnia D'      -> takze wpada w okno D -> D'

Dzieki temu nie dzielimy proby na dwa rezimy pomiarowe.

DLACZEGO NIE OKNO 16:00-17:00 Z SEKCJI 6 KARTY. W008 zmierzyl, ze pojedynczy odczyt
o 17:00 ma **przeciwny znak** niz stan przed otwarciem w 16% zdarzen — kurs potrafi
przejsc cala amplitude reakcji i wrocic. Sygnalem karty jest znak rezyduum, wiec
takie okno opisuje stan, ktorego w momencie wejscia juz nie ma.

Kryterium wyboru zadeklarowane PRZED policzeniem czegokolwiek i **niezalezne od
P&L** (regula R2): okno ma opisywac stan skladnika w momencie wejscia w pozycje.
Ostatnie notowanie przed otwarciem RTH spelnia to z definicji i nie jest
lookaheadem — ta cena jest dostepna, zanim karta zawrze transakcje. Okno 16:00-17:00
raportujemy jako kontrole odpornosci, nie jako wariant do wyboru po wyniku.

ESTYMACJA WRAZLIWOSCI NA TYM SAMYM RODZAJU OKNA. Wspolczynniki sa dopasowywane na
zwrotach NOCNYCH, nie dziennych. Stosowanie wrazliwosci z sesji dziennej do ruchu
nocnego zakladalo by, ze transmisja jest w obu rezimach identyczna — a to jest
zalozenie, nie fakt, i akurat tego zalozenia karta nie potrzebuje.

Regresja kroczaca 250 sesji konczaca sie PRZED sesja zdarzenia obejmuje w jednym
rownaniu skladniki oraz kontrole ES i SOXX:

    r_NQ,noc = Σ sᵢ·rᵢ,noc + β_ES·r_ES,noc + β_SOX·r_SOXX,noc + rezyduum

Wspolne rozwiazanie jest tu wlasciwsze niz odejmowanie po kolei: przy odejmowaniu
sekwencyjnym czlon ES pochlanialby czesc wplywu skladnikow, bo ES i megacapy sa
skorelowane.

Wyjscie: reports/W009_H013_preflight.md
"""

from __future__ import annotations

import csv
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.costs import POINT_VALUE  # noqa: E402
from engine.ndx_sensitivity import MEGACAPY, MIN_OKNO, OKNO_DNI, RIDGE_LAMBDA  # noqa: E402

RAPORT = Path("reports/W009_H013_preflight.md")
KALENDARZ = Path("data/clean/earnings.csv")
K6 = Path("data/clean/k6")
KONTROLE = ("SOXX",)
KOSZT_RT = 2.20          # jedna noga, PLAN rozdz. 3.2


def akcje_nocne(symbol: str, okno: str = "przed_otwarciem") -> pl.DataFrame:
    """Zwrot skladnika w zadanym oknie, indeksowany sesja reakcji.

    `okno="przed_otwarciem"` — od zamkniecia RTH poprzedniej sesji do ostatniego
    notowania przedsesyjnego sesji reakcji. Okno glowne (kryterium z W008).

    `okno="do_17"` — od zamkniecia RTH poprzedniej sesji do 16:59 tamtego dnia,
    czyli wersja z sekcji 6 karty. Kontrola odpornosci.
    """
    d = pl.scan_parquet(K6 / f"{symbol.lower()}_1m.parquet")
    godzina = pl.col("ts_utc").dt.convert_time_zone("America/New_York").dt.hour()
    rth = (d.filter(pl.col("segment") == "rth").sort("ts_utc")
            .group_by("trade_date").agg(c_rth=pl.col("close").last(), n_rth=pl.len()))
    pre = (d.filter(pl.col("segment") == "premarket").sort("ts_utc")
            .group_by("trade_date").agg(c_pre=pl.col("close").last()))
    ah17 = (d.filter((pl.col("segment") == "afterhours") & (godzina == 16)).sort("ts_utc")
             .group_by("trade_date").agg(c_17=pl.col("close").last()))
    j = (rth.join(pre, on="trade_date", how="left").join(ah17, on="trade_date", how="left")
            .filter(pl.col("n_rth") >= 60).sort("trade_date").collect())
    # brak notowan w oknie -> okno konczy sie na ostatniej znanej cenie
    j = j.with_columns(pl.col("c_pre").fill_null(pl.col("c_rth")),
                       pl.col("c_17").fill_null(pl.col("c_rth")))
    koniec = (pl.col("c_pre") if okno == "przed_otwarciem"
              else pl.col("c_17").shift(1))
    return j.with_columns(
        (koniec.log() - pl.col("c_rth").log().shift(1)).alias(symbol)
    ).select("trade_date", symbol)


def futures_kotwice(symbol: str) -> pl.DataFrame:
    """Ceny w stalych momentach doby ET. Na serii SKORYGOWANEJ (PLAN rozdz. 4.3).

    Pracujemy na dacie kalendarzowej ET, a nie na `trade_date` kontraktu, bo sesja
    terminowa zaczyna sie o 18:00 poprzedniego dnia. Mieszanie tych dwoch pojec
    jest w tym miejscu najlatwiejszym sposobem na cichy blad o jedna sesje.
    """
    d = pl.scan_parquet(f"data/clean/{symbol.lower()}_1m_cont.parquet")
    et = pl.col("ts_utc").dt.convert_time_zone("America/New_York")
    # RZUTOWANIE NA Int32 JEST KONIECZNE, NIE KOSMETYCZNE. `dt.hour()` zwraca Int8,
    # wiec `hour * 60` przepelnia sie CICHO: zakres wychodzi [-128, 127] zamiast
    # [0, 1439] i wszystkie filtry godzinowe zaczynaja dzialac na smieciach,
    # nie rzucajac zadnego bledu.
    d = d.with_columns(
        et.dt.date().alias("dzien"),
        (et.dt.hour().cast(pl.Int32) * 60 + et.dt.minute().cast(pl.Int32)).alias("hm"),
        (pl.col("open") + (pl.col("px_adj") - pl.col("close"))).alias("o_adj"),
    ).sort("ts_utc")
    return (
        d.group_by("dzien").agg(
            p_zamk=pl.col("px_adj").filter(pl.col("hm") <= 15 * 60 + 59).last(),
            p_przed=pl.col("px_adj").filter(pl.col("hm") <= 9 * 60 + 29).last(),
            p_17=pl.col("px_adj").filter(pl.col("hm") <= 16 * 60 + 59).last(),
            p_wejscie=pl.col("o_adj").filter(pl.col("hm") == 9 * 60 + 31).last(),
            p_1030=pl.col("px_adj").filter(pl.col("hm") <= 10 * 60 + 30).last(),
            p_kon=pl.col("px_adj").filter(pl.col("hm") <= 15 * 60 + 59).last(),
        ).sort("dzien").collect()
    )


def sesje_zdarzen() -> tuple[set[date], dict[date, list[str]]]:
    """Sesje reakcji z kalendarza EDGAR wraz z lista spolek publikujacych."""
    if not KALENDARZ.exists():
        sys.exit(f"Brak {KALENDARZ} — uruchom scripts/build_earnings.py")
    kto: dict[date, list[str]] = {}
    with KALENDARZ.open(encoding="utf-8", newline="\n") as f:
        for r in csv.DictReader(f):
            if not r["sesja_reakcji"]:
                continue
            kto.setdefault(date.fromisoformat(r["sesja_reakcji"]), []).append(r["symbol"])
    return set(kto), kto


def _ridge(X: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    G = X.T @ X
    skala = float(np.trace(G)) / X.shape[1]
    return np.linalg.solve(G + lam * skala * np.eye(X.shape[1]), X.T @ y)


def t_stat(x: np.ndarray) -> float:
    return float(x.mean() / x.std(ddof=1) * np.sqrt(x.size)) if x.size > 1 else float("nan")


def zbuduj(okno: str) -> dict:
    """Caly rachunek dla jednego okna pomiaru. Zwraca slownik wielkosci."""
    tab = akcje_nocne(MEGACAPY[0], okno)
    for s in (*MEGACAPY[1:], *KONTROLE):
        tab = tab.join(akcje_nocne(s, okno), on="trade_date", how="inner")
    tab = tab.drop_nulls().sort("trade_date")

    for sym in ("NQ", "ES"):
        f = futures_kotwice(sym).rename({c: f"{sym}_{c}" for c in
                                         ("p_zamk", "p_przed", "p_17",
                                          "p_wejscie", "p_1030", "p_kon")})
        tab = tab.join(f, left_on="trade_date", right_on="dzien", how="left")

    def koniec_okna(sym: str) -> pl.Expr:
        return (pl.col(f"{sym}_p_przed") if okno == "przed_otwarciem"
                else pl.col(f"{sym}_p_17").shift(1))

    tab = tab.with_columns(
        (koniec_okna("NQ").log() - pl.col("NQ_p_zamk").log().shift(1)).alias("r_NQ"),
        (koniec_okna("ES").log() - pl.col("ES_p_zamk").log().shift(1)).alias("r_ES"),
        # wyniki po wejsciu — mierzone od ceny wejscia, nie od otwarcia
        (pl.col("NQ_p_1030").log() - pl.col("NQ_p_wejscie").log()).alias("wy_1030"),
        (pl.col("NQ_p_kon").log() - pl.col("NQ_p_wejscie").log()).alias("wy_kon"),
    ).drop_nulls(["r_NQ", "r_ES", "wy_1030", "wy_kon"])

    dni = tab["trade_date"].to_list()
    y = tab["r_NQ"].to_numpy()
    X = np.column_stack([tab[s].to_numpy() for s in (*MEGACAPY, *KONTROLE)]
                        + [tab["r_ES"].to_numpy()])
    kol = [*MEGACAPY, *KONTROLE, "ES"]

    rez = np.full(len(y), np.nan)
    rez_bez_skladnikow = np.full(len(y), np.nan)   # model tylko z ES i SOXX
    idx_kontroli = [kol.index("ES"), kol.index("SOXX")]
    for i in range(MIN_OKNO, len(y)):
        a, b = max(0, i - OKNO_DNI), i
        beta = _ridge(X[a:b], y[a:b], RIDGE_LAMBDA)
        rez[i] = y[i] - float(X[i] @ beta)
        bk = _ridge(X[a:b][:, idx_kontroli], y[a:b], RIDGE_LAMBDA)
        rez_bez_skladnikow[i] = y[i] - float(X[i][idx_kontroli] @ bk)

    zdarzenia, _ = sesje_zdarzen()
    jest = np.array([d in zdarzenia for d in dni], dtype=bool)
    gotowe = np.isfinite(rez)
    return {
        "tab": tab, "dni": dni, "y": y, "rez": rez,
        # X i kol wychodza na zewnatrz, zeby W011 walidowal DOKLADNIE ten model,
        # ktory posluzyl do werdyktu — a nie jego rekonstrukcje
        "X": X, "kol": kol, "idx_kontroli": idx_kontroli,
        "rez_bez": rez_bez_skladnikow,
        "jest": jest, "gotowe": gotowe, "maska": jest & gotowe,
        "wy": tab["wy_1030"].to_numpy(), "wy_kon": tab["wy_kon"].to_numpy(),
        "lata": np.array([d.year for d in dni]),
        "poziom": float(np.nanmedian(tab["NQ_p_wejscie"].to_numpy())),
    }


def main() -> int:
    brak = [s for s in (*MEGACAPY, *KONTROLE) if not (K6 / f"{s.lower()}_1m.parquet").exists()]
    if brak:
        sys.exit(f"Brak danych K6: {', '.join(brak)}")

    G = zbuduj("przed_otwarciem")
    y, rez = G["y"], G["rez"]
    rez_bez_skladnikow = G["rez_bez"]
    jest, gotowe, maska = G["jest"], G["gotowe"], G["maska"]
    wy, wy_kon, lata, poziom = G["wy"], G["wy_kon"], G["lata"], G["poziom"]
    n = int(maska.sum())
    if n == 0:
        sys.exit("Brak sesji zdarzen z policzonym rezyduum")

    # sygnal karty: przeciwny do znaku rezyduum
    pnl = -np.sign(rez) * wy
    pnl_kon = -np.sign(rez) * wy_kon

    L: list[str] = [
        "# W009 — pre-flight H013 (rezydualny repricing po wynikach megacapow)",
        "",
        f"*Wygenerowane przez `research/W009_H013_preflight.py`, "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}. "
        f"{n} sesji zdarzen z {int(gotowe.sum())} sesji z policzonym rezyduum.*",
        "",
        "**Status licznika prob: 0 zuzytych.** Zadnych stopow, progow ani optymalizacji.",
        "",
        "Szesc przewidywan mechanizmu, zadeklarowanych z gory. Raportowane sa",
        "**wszystkie**, takze niekorzystne.",
        "",
        "## 0. Konstrukcja",
        "",
        "| Element | Wybor | Uzasadnienie |",
        "|---|---|---|",
        "| Okno pomiaru | zamkniecie RTH → ostatnie notowanie przed 09:30 | obejmuje AMC i BMO "
        "jednym oknem; opisuje stan w momencie wejscia (W008) |",
        "| Wrazliwosci | estymowane na zwrotach **nocnych** | stosowanie wspolczynnikow "
        "z sesji dziennej zakladaloby identyczna transmisje w obu rezimach |",
        f"| Okno regresji | {OKNO_DNI} sesji, konczace sie **przed** sesja zdarzenia | zakaz "
        "lookaheadu |",
        "| Kontrole | ES i SOXX **w tym samym rownaniu** | odejmowanie sekwencyjne "
        "kazaloby ES pochlonac czesc wplywu skladnikow |",
        "| Wejscie | otwarcie bara 09:31 sesji reakcji | zasada 2 silnika |",
        "| Wyjscie | koniec segmentu `rth_open` (10:30) | bez stopa — to nie backtest |",
        "",
        "## 1. Przewidywanie 1 — rezyduum istnieje i ma sensowna skale",
        "",
        "| Wielkosc | Sesje zdarzen | Pozostale sesje |",
        "|---|---|---|",
    ]
    inne = gotowe & ~jest
    for nazwa, v in (("sd ruchu nocnego NQ", y), ("sd rezyduum", rez)):
        L.append(f"| {nazwa} | {np.nanstd(v[maska], ddof=1)*100:.3f}% | "
                 f"{np.nanstd(v[inne], ddof=1)*100:.3f}% |")
    red = 1 - float(np.nanstd(rez[maska], ddof=1) / np.nanstd(y[maska], ddof=1))
    L += [
        f"| redukcja szumu przez model | **{red:.0%}** | "
        f"{1-float(np.nanstd(rez[inne],ddof=1)/np.nanstd(y[inne],ddof=1)):.0%} |",
        "",
        "Rezyduum istnieje i jest wyraznie wezsze niz sam ruch nocny — model tlumaczy",
        f"{red:.0%} zmiennosci w sesje zdarzen. Warunek 1 z sekcji 2 karty **spelniony**,",
        "co bylo spodziewane; karta nigdy na nim nie stala.",
        "",
        "## 2. Przewidywanie 2 — rezyduum ma strukture (NA TYM KARTA STOI)",
        "",
        "Jesli kontrakt nie doszacowal ruchu skladnikow, roznica powinna domykac sie",
        "po otwarciu. Znak: **dodatnie rezyduum = NQ za wysoko wzgledem skladnikow**,",
        "wiec mechanizm przewiduje **ujemny** zwrot po otwarciu.",
        "",
        "| Miara | Wartosc |",
        "|---|---|",
        f"| korelacja(rezyduum, zwrot 09:31→10:30) | **{np.corrcoef(rez[maska], wy[maska])[0,1]:+.4f}** |",
        f"| korelacja(rezyduum, zwrot 09:31→koniec) | {np.corrcoef(rez[maska], wy_kon[maska])[0,1]:+.4f} |",
        f"| sredni wynik fade'u (09:31→10:30) | {pnl[maska].mean()*100:+.4f}% |",
        f"| **t** | **{t_stat(pnl[maska]):+.2f}** |",
        f"| sredni wynik fade'u (09:31→koniec) | {pnl_kon[maska].mean()*100:+.4f}% |",
        f"| t | {t_stat(pnl_kon[maska]):+.2f} |",
        "",
    ]

    # --- przewidywanie 3: zaleznosc od wielkosci rezyduum --------------------
    L += [
        "## 3. Przewidywanie 3 — efekt rosnie z wielkoscia rezyduum",
        "",
        "Jesli nie rosnie, mierzymy cos innego niz niedowycenienie. **Tak uplo H014.**",
        "",
        "| Warunek | *f* wsrod zdarzen | N | Sredni wynik | t | pkt MNQ |",
        "|---|---|---|---|---|---|",
    ]
    ar = np.abs(rez[maska])
    p_masked = pnl[maska]
    for q, nazwa in ((0.0, "wszystkie zdarzenia"), (1 / 3, "gorne 2/3"),
                     (2 / 3, "gorny tercyl"), (0.9, "gorny decyl")):
        prog = np.quantile(ar, q)
        m = ar >= prog
        x = p_masked[m]
        L.append(f"| {nazwa} | {m.mean():.2f} | {m.sum()} | {x.mean()*100:+.4f}% | "
                 f"**{t_stat(x):+.2f}** | {x.mean()*poziom:+.1f} |")

    # --- przewidywanie 4: symetria ------------------------------------------
    L += [
        "",
        "## 4. Przewidywanie 4 — symetria stron",
        "",
        "Mechanizm arytmetyczny nie ma powodu dzialac tylko w jedna strone.",
        "**Asymetria bez wyjasnienia zabila H005.**",
        "",
        "| Strona rezyduum | N | Sredni wynik | t |",
        "|---|---|---|---|",
    ]
    r_masked = rez[maska]
    for nazwa, m in (("dodatnie (NQ za wysoko)", r_masked > 0),
                     ("ujemne (NQ za nisko)", r_masked < 0)):
        x = p_masked[m]
        L.append(f"| {nazwa} | {m.sum()} | {x.mean()*100:+.4f}% | **{t_stat(x):+.2f}** |")

    # --- przewidywanie 5: stabilnosc roczna ---------------------------------
    L += [
        "",
        "## 5. Przewidywanie 5 — stabilnosc roczna",
        "",
        "Zaden rok nie moze dawac ponad 40% wyniku. **Tak uplo H005** (52% z jednego roku).",
        "",
        "Raportujemy **sumy i srednie bezwzgledne, nie udzialy procentowe**. Przy ujemnym",
        "wyniku calkowitym udzialy sa mylace: rok stratny wychodzi wtedy `+118%`,",
        "a zyskowny `−77%`, co czyta sie dokladnie odwrotnie do tego, co sie stalo.",
        "",
        "| Rok | N | Suma (pkt MNQ) | Sredni wynik | t | Znak |",
        "|---|---|---|---|---|---|",
    ]
    lata_m = lata[maska]
    udzialy = {}
    for rok in sorted(set(lata_m.tolist())):
        m = lata_m == rok
        x = p_masked[m]
        udzialy[rok] = float(x.mean())
        L.append(f"| {rok} | {int(m.sum())} | {x.sum()*poziom:+.0f} | "
                 f"{x.mean()*100:+.4f}% | {t_stat(x):+.2f} | "
                 f"{'+' if x.mean() > 0 else '−'} |")
    dodatnie_lata = sum(1 for r in udzialy if p_masked[lata_m == r].mean() > 0)

    # --- przewidywanie 6: kontrola pozornosci -------------------------------
    pnl_bez = -np.sign(rez_bez_skladnikow) * wy
    pnl_luka = -np.sign(y) * wy
    L += [
        "",
        f"Lat dodatnich: **{dodatnie_lata} z {len(udzialy)}**. "
        f"Rozstep srednich rocznych: od {min(udzialy.values())*100:+.4f}% "
        f"do {max(udzialy.values())*100:+.4f}% — **zmiana znaku, nie koncentracja**.",
        "",
        "## 6. Przewidywanie 6 — kontrola pozornosci",
        "",
        "Czy skladniki cokolwiek wnosza? Porownanie z modelem bez nich i z sama luka NQ.",
        "Jesli wyniki sa zblizone, karta redukuje sie do **B04** i schodzi do benchmarkow.",
        "",
        "| Model rezyduum | Sredni wynik | t |",
        "|---|---|---|",
        f"| **pelny (skladniki + ES + SOXX)** | {p_masked.mean()*100:+.4f}% | "
        f"**{t_stat(p_masked):+.2f}** |",
        f"| tylko ES + SOXX (bez skladnikow) | {pnl_bez[maska].mean()*100:+.4f}% | "
        f"{t_stat(pnl_bez[maska]):+.2f} |",
        f"| sama luka nocna NQ (odpowiednik B04) | {pnl_luka[maska].mean()*100:+.4f}% | "
        f"{t_stat(pnl_luka[maska]):+.2f} |",
        "",
        "## 7. Ekonomia — prog z sekcji 5 karty",
        "",
        "| Wielkosc | Wartosc |",
        "|---|---|",
        f"| Sredni wynik brutto na zdarzenie | {p_masked.mean()*poziom:+.1f} pkt MNQ |",
        f"| W USD (mnoznik {POINT_VALUE}) | {p_masked.mean()*poziom*POINT_VALUE:+.2f} |",
        f"| Koszt round-turn | −{KOSZT_RT:.2f} USD |",
        f"| **Netto na zdarzenie** | "
        f"**{p_masked.mean()*poziom*POINT_VALUE - KOSZT_RT:+.2f} USD** |",
        "| Prog SR ≥ 0.8 z karty | +24.2 pkt |",
        "| Prog DSR ≥ 0.95 z karty | +34.4 pkt |",
        "",
    ]

    # --- kontrola odpornosci: okno 16:00-17:00 ------------------------------
    K = zbuduj("do_17")
    m17 = K["maska"]
    p17 = (-np.sign(K["rez"]) * K["wy"])[m17]
    L += [
        "## 8. Kontrola odpornosci — okno 16:00-17:00 z sekcji 6 karty",
        "",
        "Raportowane, zeby bylo widac, ze wybor okna nie zostal zrobiony pod wynik.",
        "Kryterium wyboru bylo pomiarowe i zadeklarowane przed liczeniem (W008).",
        "",
        "| Okno | N | Sredni wynik | t |",
        "|---|---|---|---|",
        f"| **przed otwarciem (glowne)** | {n} | {p_masked.mean()*100:+.4f}% | "
        f"**{t_stat(p_masked):+.2f}** |",
        f"| 16:00-17:00 (sekcja 6 karty) | {int(m17.sum())} | {p17.mean()*100:+.4f}% | "
        f"{t_stat(p17):+.2f} |",
        "",
        "Oba okna daja ten sam ZNAK, a oryginalne okno z karty wypada dla karty",
        f"**gorzej** (t = {t_stat(p17):+.2f} wobec {t_stat(p_masked):+.2f}). Wybor okna",
        "nie jest wiec przyczyna negatywnego wyniku — przeciwnie, okno wybrane",
        "kryterium pomiarowym jest dla karty **lagodniejsze** niz to, ktore karta",
        "sama deklarowala.",
        "",
        "## 9. Moc testu — czego ten pre-flight NIE wyklucza",
        "",
    ]
    sd_pnl = float(p_masked.std(ddof=1))
    wymagany = 0.00105                        # +0.105% na zdarzenie, sekcja 5 karty
    n_potrzebne = ((1.96 + 0.84) * sd_pnl / wymagany) ** 2
    ci_dol = p_masked.mean() - 1.96 * sd_pnl / np.sqrt(n)
    ci_gora = p_masked.mean() + 1.96 * sd_pnl / np.sqrt(n)
    L += [
        "| Wielkosc | Wartosc |",
        "|---|---|",
        f"| sd wyniku na zdarzenie | {sd_pnl*100:.3f}% |",
        f"| 95% CI sredniego wyniku | [{ci_dol*100:+.4f}%, {ci_gora*100:+.4f}%] |",
        "| Wymagany edge (SR ≥ 0.8) | +0.105% |",
        f"| N potrzebne przy mocy 80% | **{n_potrzebne:.0f} zdarzen** |",
        f"| N dostepne | **{n}** |",
        "",
        "**Uczciwie: przy tej probie nie da sie odrzucic edge'u dokladnie tej",
        "wielkosci, ktorej karta potrzebuje** — gorny koniec przedzialu ufnosci",
        f"({ci_gora*100:+.4f}%) lezy blisko progu. Gdyby jedynym wynikiem byl brak",
        "istotnosci, werdykt brzmialby \"nierozstrzygniete\", jak w W001.",
        "",
        "**Ale to nie jest jedyny wynik.** Uklad wynikow jest niezgodny z wczesniej",
        "zadeklarowanymi przewidywaniami mechanizmu: warunkowanie na wielkosci",
        "rezyduum pogarsza wynik, strony sa asymetryczne, a znak efektu odwraca sie",
        "w polowie probki.",
        "",
        "> **Mimo ograniczonej mocy uklad wynikow jest niezgodny z wczesniej",
        "> zadeklarowanymi przewidywaniami mechanizmu, dlatego karta nie spelnia",
        "> bramki GO.**",
        "",
        "Swiadomie NIE twierdze, ze te niezgodnosci sa niezalezne od mocy testu.",
        "Mala proba sama w sobie potrafi wytworzyc niestabilnosc znakow, pozorna",
        "asymetrie i skrajny odczyt w decylu liczacym 19 obserwacji. Do odrzucenia",
        "karty wystarcza, ze przewidywania sie nie potwierdzily — nie trzeba do tego",
        "twierdzic, ze udowodniono brak jakiegokolwiek edge'u. Nie udowodniono.",
        "",
        "**Ta sama lekcja co W004: kontrole z mechanizmu odrzucaja wczesniej",
        "i pewniej niz kontrole statystyczne.**",
        "",
        "**Audyt zamykajacy:** [W011](W011_model_nocny_oos.md) waliduje OOS dokladnie",
        "ten model, ktory posluzyl do werdyktu, i znajduje w nim obciazenie w sesje",
        "zdarzen (+3.05‱), przez ktore czesc asymetrii z przewidywania 4 jest",
        "artefaktem modelu. [W012](W012_H013_przekroje.md) powtarza rachunek na probie",
        "zgodnej z pierwotna definicja karty (kwartalne wyniki, AMC, N = 157).",
        "**Kierunek wnioskow nie zmienia sie w zadnym z tych sprawdzen.**",
        "",
    ]

    # --- werdykt -------------------------------------------------------------
    t_glowne = t_stat(p_masked)
    kor = float(np.corrcoef(rez[maska], wy[maska])[0, 1])
    kor_kon = float(np.corrcoef(rez[maska], wy_kon[maska])[0, 1])
    t_decyl = t_stat(p_masked[np.abs(r_masked) >= np.quantile(np.abs(r_masked), 0.9)])
    t_dod = t_stat(p_masked[r_masked > 0])
    t_ujem = t_stat(p_masked[r_masked < 0])
    rozstep = (min(udzialy.values()) * 100, max(udzialy.values()) * 100)
    L += [
        "## 10. Werdykt: **NO-GO**",
        "",
        "| # | Przewidywanie | Wynik | Ocena |",
        "|---|---|---|---|",
        f"| 1 | Rezyduum istnieje i ma skale | redukcja szumu {red:.0%}, "
        f"sd {np.nanstd(rez[maska],ddof=1)*100:.3f}% | **spelnione** |",
        f"| 2 | Rezyduum sie domyka | korelacja {kor:+.4f} (10:30), {kor_kon:+.4f} "
        f"(koniec); t = {t_glowne:+.2f} | **zawiedzione** |",
        f"| 3 | Efekt rosnie z wielkoscia rezyduum | t: {t_glowne:+.2f} → {t_decyl:+.2f} "
        "w gornym decylu — **pogorszenie** | **zawiedzione** |",
        f"| 4 | Symetria stron | dodatnie t = {t_dod:+.2f}, ujemne t = {t_ujem:+.2f} "
        "— przeciwne znaki | **zawiedzione** |",
        f"| 5 | Stabilnosc roczna | {dodatnie_lata}/{len(udzialy)} lat dodatnich, "
        f"srednie roczne od {rozstep[0]:+.3f}% do {rozstep[1]:+.3f}% | **zawiedzione** |",
        f"| 6 | Skladniki cos wnosza | pelny model t = {t_glowne:+.2f}, "
        f"sama luka NQ t = {t_stat(pnl_luka[maska]):+.2f} | **zawiedzione** |",
        "",
        "**Piec z szesciu przewidywan zawiedzionych. Jedyne spelnione to warunek 1,",
        "o ktorym karta sama pisala, ze nigdy na nim nie stala** — sekcja 2 karty",
        "mowi wprost: warunek 3 jest tym, na czym karta stoi lub upada.",
        "",
        "### Co jest tu rozstrzygajace",
        "",
        "Nie sam brak istotnosci — ten bylby kwestia mocy. Rozstrzygajace sa **trzy",
        "sprzecznosci wewnetrzne**, kazda niezalezna od pozostalych:",
        "",
        "1. **Warunkowanie dziala na opak.** Im wieksze rezyduum, tym gorszy wynik",
        f"   ({t_glowne:+.2f} → {t_decyl:+.2f}). Gdyby mechanizm mowil prawde, byloby",
        "   odwrotnie: wieksze niedowycenienie to wieksza okazja. Dokladnie tak upadlo",
        "   H014 i ten punkt jest tam opisany jako rozstrzygajacy.",
        "",
        "2. **Znak odwraca sie w polowie probki.** Lata 2019-2022 daja srednio",
        "   ujemny wynik fade'u, lata 2023-2026 dodatni. To nie jest koncentracja",
        "   (jak w H005), tylko **zmiana kierunku** — najmocniejszy dowod, ze stalego",
        "   mechanizmu nie ma.",
        "",
        "3. **Skladniki nie wnosza nic.** Model bez nich i sama luka nocna NQ daja",
        "   wyniki tego samego rzedu, tyle ze z przeciwnym znakiem. Czlon Σsᵢrᵢ —",
        "   caly powod istnienia tej karty — nie jest zrodlem zadnej informacji",
        "   ponad to, co widac w samej luce.",
        "",
        "### Konsekwencje",
        "",
        "| Co | Decyzja |",
        "|---|---|",
        "| **H013** | **REJECTED (pre-flight)**, 0 z 8 prob zuzytych |",
        "| **H016** | traci nosiciela — pozostaje w stanie oczekiwania (sekcja 7 karty) |",
        "| Kalendarz EDGAR | zostaje w repo, jest poprawny i darmowy |",
        "| `engine/ndx_sensitivity` | zostaje, model jest zwalidowany OOS (W007) |",
        "| Dane K6 za $7.82 | wydane; kupione **przed** pre-flightem, bo bez nich "
        "pre-flight bylby niewykonalny |",
        "",
        "Ostatni wiersz wart jest odnotowania bez owijania: to pierwszy raz w tym",
        "projekcie, gdy pre-flight kosztowal pieniadze, a nie tylko czas. Kwota jest",
        "mala, ale zasada z reguly R1 zadziala tak samo przy wiekszej — **zakup danych",
        "nie jest inwestycja w karte, tylko w mozliwosc jej sprawdzenia.**",
        "",
        "---",
        "",
        "Odtworzenie: `python3 research/W009_H013_preflight.py`",
    ]

    RAPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPORT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"-> {RAPORT}")
    print(f"   N zdarzen {n}, korelacja {kor:+.4f}, t {t_glowne:+.2f}, "
          f"srednio {p_masked.mean()*poziom:+.1f} pkt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
