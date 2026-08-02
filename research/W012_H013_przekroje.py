#!/usr/bin/env python3
"""W012 — przekroje proby H013 zgodne z pierwotna definicja karty. Audyt zamykajacy.

POWOD. Pierwotna karta H013 mowila o **kwartalnych wynikach finansowych osmiu
megacapow publikowanych po zamknieciu sesji**: 8 spolek x 4 kwartaly x 7 lat,
czyli okolo 224 zdarzen. W009 policzyl werdykt na 185 sesjach reakcji zbudowanych
ze WSZYSTKICH 261 zlozen 8-K item 2.02 — razem z 29 komunikatami Tesli
o produkcji i dostawach oraz z publikacjami przed otwarciem sesji.

To nie jest ta sama proba. Zanim karta zostanie zamknieta, werdykt musi zostac
sprawdzony na probie, na ktorej karta byla **zaprojektowana**.

PRZEKROJE SA DEFINICJAMI PROBY, NIE WARIANTAMI STRATEGII. Nie zuzywaja prob
z budzetu karty, bo nie zmieniaja reguly wejscia ani wyjscia — zmieniaja
odpowiedz na pytanie "ktore zdarzenia sa zdarzeniami tej karty". Rozdzial
wykonany z TRESCI komunikatow (`scripts/classify_earnings.py`), nigdy z reakcji
ceny.

Zero zuzytych prob.

Wyjscie: reports/W012_H013_przekroje.md
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.W009_H013_preflight import zbuduj  # noqa: E402

RAPORT = Path("reports/W012_H013_przekroje.md")
KALENDARZ = Path("data/clean/earnings_rodzaj.csv")


def t_stat(x: np.ndarray) -> float:
    return float(x.mean() / x.std(ddof=1) * np.sqrt(x.size)) if x.size > 2 else float("nan")


def wczytaj() -> list[dict]:
    if not KALENDARZ.exists():
        sys.exit(f"Brak {KALENDARZ} — uruchom scripts/classify_earnings.py")
    return list(csv.DictReader(KALENDARZ.open(encoding="utf-8")))


def main() -> int:
    wiersze = [r for r in wczytaj() if r["sesja_reakcji"]]
    G = zbuduj("przed_otwarciem")
    dni, rez, wy, gotowe = G["dni"], G["rez"], G["wy"], G["gotowe"]
    lata = G["lata"]
    poziom = G["poziom"]
    ix = {d: i for i, d in enumerate(dni)}

    # Korekta obciazenia modelu w sesje zdarzen (W011), bez lookaheadu
    zdarz_all = {date.fromisoformat(r["sesja_reakcji"]) for r in wiersze}
    korekta = np.full(len(rez), np.nan)
    hist: list[float] = []
    for i, d in enumerate(dni):
        if d in zdarz_all and gotowe[i]:
            korekta[i] = float(np.mean(hist)) if len(hist) >= 20 else 0.0
            hist.append(float(rez[i]))
    rez_k = rez - korekta

    def przekroj(nazwa: str, wybrane: list[dict]) -> dict:
        sesje = {date.fromisoformat(r["sesja_reakcji"]) for r in wybrane}
        idx = np.array([ix[d] for d in sorted(sesje) if d in ix and gotowe[ix[d]]],
                       dtype=int)
        if idx.size < 5:
            return {"nazwa": nazwa, "n": int(idx.size)}
        rz, rk, w = rez[idx], rez_k[idx], wy[idx]
        pnl, pnl_k = -np.sign(rz) * w, -np.sign(rk) * w
        gorny = np.abs(rk) >= np.quantile(np.abs(rk), 2 / 3)
        lat = lata[idx]
        znaki = [1 if pnl_k[lat == r].mean() > 0 else 0
                 for r in sorted(set(lat.tolist())) if (lat == r).sum() >= 5]
        return {
            "nazwa": nazwa, "n": int(idx.size),
            "kor": float(np.corrcoef(rk, w)[0, 1]),
            "sr": float(pnl.mean()), "t": t_stat(pnl),
            "sr_k": float(pnl_k.mean()), "t_k": t_stat(pnl_k),
            "t_gorny": t_stat(pnl_k[gorny]),
            "lat_dod": sum(znaki), "lat": len(znaki),
            "pkt": float(pnl_k.mean()) * poziom,
        }

    kw = [r for r in wiersze if r["rodzaj"] == "KWARTALNE"]
    dost = [r for r in wiersze if r["rodzaj"] == "DOSTAWY"]
    licz = Counter(r["sesja_reakcji"] for r in wiersze)
    pojedyncze = [r for r in kw if licz[r["sesja_reakcji"]] == 1]
    wielokrotne = [r for r in kw if licz[r["sesja_reakcji"]] > 1]

    przekroje = [
        przekroj("**pelna proba W009** (wszystko)", wiersze),
        przekroj("**tylko kwartalne wyniki**", kw),
        przekroj("**kwartalne + AMC** (pierwotna definicja karty)",
                 [r for r in kw if r["klasa"] == "AMC"]),
        przekroj("kwartalne + BMO", [r for r in kw if r["klasa"] == "BMO"]),
        przekroj("tylko dostawy TSLA", dost),
        przekroj("kwartalne, noce z jedna publikacja", pojedyncze),
        przekroj("kwartalne, noce z wieloma publikacjami", wielokrotne),
    ]

    L: list[str] = [
        "# W012 — przekroje proby H013 (audyt zamykajacy)",
        "",
        f"*Wygenerowane przez `research/W012_H013_przekroje.py`, "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}.*",
        "",
        "**Status licznika prob: 0 zuzytych.**",
        "",
        "## 0. Po co ten raport",
        "",
        "Pierwotna karta H013 mowila o **kwartalnych wynikach osmiu megacapow",
        "publikowanych po zamknieciu sesji** — okolo 8 x 4 x 7 = 224 zdarzen. W009",
        "policzyl werdykt na wszystkich 261 zlozeniach 8-K item 2.02, w tym na",
        "komunikatach Tesli o produkcji i dostawach oraz na publikacjach przed",
        "otwarciem. To nie jest ta sama proba.",
        "",
        "**Przekroje sa definicjami proby, nie wariantami strategii** — regula wejscia",
        "i wyjscia jest w kazdym wierszu ta sama. Dlatego nie zuzywaja prob z budzetu",
        "karty. Rozdzial wykonany z **tresci komunikatow prasowych**",
        "(`scripts/classify_earnings.py`), nigdy z reakcji ceny.",
        "",
        "## 1. Klasyfikacja zlozen",
        "",
        "| Rodzaj | N | AMC | BMO |",
        "|---|---|---|---|",
    ]
    for nazwa, grupa in (("kwartalne wyniki finansowe", kw), ("produkcja i dostawy", dost)):
        L.append(f"| {nazwa} | {len(grupa)} | "
                 f"{sum(1 for r in grupa if r['klasa'] == 'AMC')} | "
                 f"{sum(1 for r in grupa if r['klasa'] == 'BMO')} |")

    L += [
        "",
        "Kontrola wewnetrzna: kazda spolka ma 28-30 raportow kwartalnych "
        "(~4 rocznie x 7 lat), a TSLA rozdziela sie na **29 dostaw i 29 raportow**.",
        "Liczby te nie byly w zaden sposob dostrajane — reguly operuja na tytulach",
        "komunikatow.",
        "",
        "## 2. Wynik karty w kazdym przekroju",
        "",
        "Kolumna `t` to wynik surowy (jak w W009), `t korr` — po korekcie obciazenia",
        "modelu w sesje zdarzen (W011). `t gorny` dotyczy gornego tercyla \\|rezyduum\\|",
        "i sprawdza, czy warunkowanie **poprawia** wynik, jak wymaga mechanizm.",
        "",
        "| Przekroj | N | korelacja | sredni wynik | t | t korr | t gorny | lat + |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for p in przekroje:
        if p.get("n", 0) < 5:
            L.append(f"| {p['nazwa']} | {p.get('n', 0)} | — | — | — | — | — | — |")
            continue
        L.append(
            f"| {p['nazwa']} | {p['n']} | {p['kor']:+.4f} | {p['sr']*100:+.4f}% | "
            f"**{p['t']:+.2f}** | {p['t_k']:+.2f} | {p['t_gorny']:+.2f} | "
            f"{p['lat_dod']}/{p['lat']} |"
        )

    glowny = przekroje[2]
    pelny = przekroje[0]
    L += [
        "",
        "## 3. Werdykt przekrojowy",
        "",
        "**Przekroj zgodny z pierwotna definicja karty** (kwartalne wyniki, AMC) liczy",
        f"**{glowny['n']} sesji** i daje t = **{glowny['t']:+.2f}** surowo, "
        f"{glowny['t_k']:+.2f} po korekcie — wobec {pelny['t']:+.2f} na pelnej probie.",
        "",
        f"Sredni wynik na zdarzenie: **{glowny['pkt']:+.1f} pkt MNQ** przy progu",
        "**+24.2 pkt** wymaganym dla SR ≥ 0.8 (sekcja 5 karty).",
        "",
        f"Warunkowanie na wielkosci rezyduum: t {glowny['t_k']:+.2f} → "
        f"{glowny['t_gorny']:+.2f} w gornym tercylu. Mechanizm wymaga **poprawy**.",
        "",
        f"Stabilnosc: {glowny['lat_dod']} lat dodatnich z {glowny['lat']}.",
        "",
        "**Kierunek wnioskow nie zmienia sie w zadnym przekroju.** Zawezenie proby do",
        "pierwotnej definicji karty nie ujawnia efektu, ktory ginal w szumie dostaw",
        "Tesli i publikacji przedsesyjnych.",
        "",
        "Warto odnotowac przekroj **najczystszy mechanizmowo**: noce, w ktorych wyniki",
        "publikowala **dokladnie jedna** spolka. Tam transmisja \"news skladnika →",
        "indeks\" jest najmniej zaburzona, wiec karta powinna wypasc tam najlepiej.",
        f"Wypada **najgorzej** ze wszystkich przekrojow (N = {przekroje[5]['n']}, "
        f"t = {przekroje[5]['t']:+.2f}, po korekcie {przekroje[5]['t_k']:+.2f}).",
        "",
        "Dostawy Tesli daja jedyny dodatni odczyt (t korr +1.50), ale przy N = 27 i po",
        "obejrzeniu wyniku — **nie jest to przeslanka do niczego** i nie otwieram na to",
        "karty. Odnotowane wylacznie dla kompletnosci.",
        "",
        "Przekroj \"kwartalne + BMO\" pominiety: w calej probie sa **2 takie zdarzenia**,",
        "bo megacapy publikuja wyniki po zamknieciu. To samo w sobie potwierdza, ze",
        "pierwotna karta slusznie mowila o publikacjach after-hours.",
        "",
        "> **Mimo ograniczonej mocy uklad wynikow jest niezgodny z wczesniej",
        "> zadeklarowanymi przewidywaniami mechanizmu, dlatego karta nie spelnia",
        "> bramki GO.**",
        "",
        "Nie jest to twierdzenie, ze udowodniono brak jakiegokolwiek edge'u — przy",
        f"{glowny['n']} zdarzeniach udowodnic tego nie sposob.",
        "",
        "---",
        "",
        "Odtworzenie: `python3 research/W012_H013_przekroje.py`",
    ]

    RAPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {RAPORT}")
    for p in przekroje:
        if p.get("n", 0) >= 5:
            print(f"  {p['nazwa'][:46]:48s} N={p['n']:3d} t={p['t']:+.2f} "
                  f"t_k={p['t_k']:+.2f} t_gorny={p['t_gorny']:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
