#!/usr/bin/env python3
"""Budowa kalendarza wynikow z SEC EDGAR — PLAN.pdf rozdz. 4.5.

Pobiera 8-K item 2.02 dla osmiu megacapow, klasyfikuje BMO/AMC/srodsesyjne wzgledem
ZAOBSERWOWANYCH granic sesji i przypisuje sesje reakcji.

Zrodlo jest darmowe i autorytatywne — zero kosztu, zero skazenia proby selekcja.
Uzasadnienie podzialu rol miedzy kalendarz a detektor: docstring `engine/earnings.py`.

Granice sesji bierzemy z `data/clean/k6/qqq_1m.parquet`, bo QQQ handluje sie
w kazdej sesji naszego zakresu, a dane mowia wprost, ktore dni byly sesjami
i o ktorej sie konczyly. Zadnej tablicy swiat ani zalozen o dniach skroconych.

Wyjscie: data/clean/earnings.csv + reports/earnings_calendar.md
"""

from __future__ import annotations

import csv
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.earnings import (  # noqa: E402
    AMC,
    BMO,
    CIK,
    ET,
    POZA_SESJA,
    SRODSESYJNE,
    Publikacja,
    klasyfikuj,
    parsuj_akceptacje,
    parsuj_submissions,
    sesja_reakcji,
    url_indeksu,
)

WYJSCIE = Path("data/clean/earnings.csv")
RAPORT = Path("reports/earnings_calendar.md")
QQQ = Path("data/clean/k6/qqq_1m.parquet")
#: Cache czasow akceptacji. W data/raw/, czyli poza repozytorium — przyspiesza
#: ponowne przebiegi, ale wynik nie zalezy od jego obecnosci.
CACHE = Path("data/raw/edgar_akceptacje.json")

BAZA = "https://data.sec.gov/submissions"
#: SEC wymaga deklaracji kontaktu w User-Agent. Trzymamy go w zmiennej srodowiskowej,
#: zeby adres e-mail wlasciciela nie trafil do repozytorium.
UA = os.environ.get("SEC_USER_AGENT", "Projekt-G badania naukowe kontakt-przez-github")
PRZERWA = 0.15          # SEC dopuszcza 10 zapytan/s; trzymamy sie znacznie nizej
PROBY, BACKOFF = 4, 2.0


def pobierz(url: str) -> dict:
    """GET z ponowieniami. Odmowa polityki (403/407) NIE jest ponawiana."""
    ostatni: Exception | None = None
    for proba in range(PROBY):
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept-Encoding": "gzip"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                surowe = r.read()
                # SEC zaleca gzip, a urllib nie rozpakowuje sam — trzeba jawnie,
                # inaczej dostajemy UnicodeDecodeError na pierwszym bajcie naglowka
                if r.headers.get("Content-Encoding") == "gzip":
                    surowe = gzip.decompress(surowe)
                return json.loads(surowe.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (403, 407):
                raise SystemExit(
                    f"HTTP {e.code} dla {url} — odmowa polityki egress lub blokada SEC. "
                    "Zglos, nie ponawiaj (patrz /root/.ccr/README.md)."
                ) from e
            if e.code == 404:
                raise
            ostatni = e
        except (urllib.error.URLError, TimeoutError) as e:
            ostatni = e
        czekaj = BACKOFF**proba
        print(f"  ponawiam za {czekaj:.0f}s ({ostatni})")
        time.sleep(czekaj)
    raise SystemExit(f"Nie udalo sie pobrac {url}: {ostatni}")


def pobierz_tekst(url: str) -> str:
    """GET zwracajacy tekst — dla stron indeksu zlozen."""
    ostatni: Exception | None = None
    for proba in range(PROBY):
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept-Encoding": "gzip"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                surowe = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    surowe = gzip.decompress(surowe)
                return surowe.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 407):
                raise SystemExit(
                    f"HTTP {e.code} dla {url} — odmowa polityki egress lub blokada SEC. "
                    "Zglos, nie ponawiaj (patrz /root/.ccr/README.md)."
                ) from e
            ostatni = e
        except (urllib.error.URLError, TimeoutError) as e:
            ostatni = e
        time.sleep(BACKOFF**proba)
    raise SystemExit(f"Nie udalo sie pobrac {url}: {ostatni}")


def publikacje_spolki(symbol: str) -> list[Publikacja]:
    """Wszystkie 8-K 2.02 spolki — z pliku biezacego i z plikow historycznych."""
    dane = pobierz(f"{BAZA}/CIK{CIK[symbol]:010d}.json")
    time.sleep(PRZERWA)
    wynik = parsuj_submissions(dane["filings"]["recent"], symbol)
    for plik in dane["filings"].get("files", []):
        stare = pobierz(f"{BAZA}/{plik['name']}")
        time.sleep(PRZERWA)
        wynik += parsuj_submissions(stare, symbol)
    return wynik


def wczytaj_cache() -> dict[str, str]:
    """Accession -> czas ET jako ISO. Cache tylko przyspiesza ponowne przebiegi."""
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def czasy_akceptacji(publikacje: list[Publikacja]) -> dict[str, datetime]:
    """Autorytatywne czasy ET ze stron indeksu — patrz docstring engine/earnings.py."""
    cache = wczytaj_cache()
    znane = {k: datetime.fromisoformat(v) for k, v in cache.items()}
    brakujace = [p for p in publikacje if p.accession not in znane]
    if brakujace:
        print(f"Pobieram czasy akceptacji ze stron indeksu: {len(brakujace)} "
              f"(w cache {len(znane)})")
    for i, p in enumerate(brakujace, 1):
        html = pobierz_tekst(url_indeksu(p.cik, p.accession))
        t = parsuj_akceptacje(html)
        if t is None:
            print(f"  UWAGA: brak pola 'Accepted' dla {p.symbol} {p.accession}")
            continue
        znane[p.accession] = t
        time.sleep(PRZERWA)
        if i % 25 == 0:
            print(f"  {i}/{len(brakujace)}")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(
        json.dumps({k: v.isoformat() for k, v in znane.items()}, indent=1),
        encoding="utf-8",
    )
    return znane


def granice_sesji() -> dict:
    """trade_date -> (pierwszy, ostatni bar RTH) w ET, prosto z danych."""
    d = (
        pl.scan_parquet(QQQ)
        .filter(pl.col("segment") == "rth")
        .group_by("trade_date")
        .agg(o=pl.col("ts_utc").min(), c=pl.col("ts_utc").max(), n=pl.len())
        .filter(pl.col("n") >= 60)
        .collect()
    )
    return {
        r["trade_date"]: (r["o"].astimezone(ET), r["c"].astimezone(ET))
        for r in d.iter_rows(named=True)
    }


def main() -> int:
    if not QQQ.exists():
        sys.exit(f"Brak {QQQ} — kalendarz wymaga granic sesji z danych. Patrz HANDOFF.md")

    sesje_granice = granice_sesji()
    sesje = frozenset(sesje_granice)
    pierwsza, ostatnia = min(sesje), max(sesje)
    print(f"Sesji w danych: {len(sesje)} ({pierwsza} → {ostatnia})")

    # Wstepne zawezenie po DACIE ZLOZENIA (z marginesem doby), zeby nie pobierac
    # stron indeksu dla kilkuset zlozen spoza naszego zakresu. Margines jest
    # potrzebny, bo data zlozenia i data przyjecia moga sie roznic o dobe.
    margines = timedelta(days=2)
    wszystkie: list[Publikacja] = []
    for symbol in CIK:
        p = publikacje_spolki(symbol)
        w_zakresie = [x for x in p
                      if pierwsza - margines <= x.data_zlozenia <= ostatnia + margines]
        print(f"  {symbol:6s} 8-K 2.02: {len(p):4d} wszystkich, "
              f"{len(w_zakresie):3d} w zakresie dat")
        wszystkie += w_zakresie

    czasy = czasy_akceptacji(wszystkie)

    gotowe: list[Publikacja] = []
    bez_czasu: list[Publikacja] = []
    for p in wszystkie:
        t = czasy.get(p.accession)
        if t is None:
            bez_czasu.append(p)
            continue
        dzien = t.date()
        if not (pierwsza <= dzien <= ostatnia):
            continue
        o, c = sesje_granice.get(dzien, (None, None))
        klasa = klasyfikuj(t, o, c)
        gotowe.append(
            Publikacja(
                symbol=p.symbol, cik=p.cik, accession=p.accession,
                data_zlozenia=p.data_zlozenia, okres=p.okres,
                znacznik_json=p.znacznik_json, akceptacja_et=t, klasa=klasa,
                sesja_reakcji=sesja_reakcji(dzien, klasa, sesje),
            )
        )
    gotowe.sort(key=lambda x: (x.akceptacja_et, x.symbol))  # type: ignore[arg-type,return-value]
    if bez_czasu:
        print(f"UWAGA: {len(bez_czasu)} zlozen bez czasu akceptacji — pominiete")

    WYJSCIE.parent.mkdir(parents=True, exist_ok=True)
    with WYJSCIE.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "cik", "accession", "okres", "data_zlozenia",
                    "akceptacja_et", "klasa", "sesja_reakcji", "znacznik_json",
                    "json_zgodny"])
        for p in gotowe:
            assert p.akceptacja_et is not None
            w.writerow([
                p.symbol, p.cik, p.accession, p.okres, p.data_zlozenia.isoformat(),
                p.akceptacja_et.strftime("%Y-%m-%d %H:%M:%S"),
                p.klasa,
                p.sesja_reakcji.isoformat() if p.sesja_reakcji else "",
                p.znacznik_json,
                "tak" if p.json_zgodny else "NIE",
            ])

    def et(p: Publikacja) -> datetime:
        assert p.akceptacja_et is not None
        return p.akceptacja_et

    klasy = Counter(p.klasa for p in gotowe)
    bez_sesji = [p for p in gotowe if p.sesja_reakcji is None]
    uzyteczne = [p for p in gotowe if p.klasa in (AMC, BMO, POZA_SESJA)
                 and p.sesja_reakcji is not None]
    godziny = Counter(et(p).strftime("%H:%M") for p in gotowe if p.klasa == AMC)
    per_spolka = Counter(p.symbol for p in gotowe)
    per_rok: Counter = Counter(et(p).year for p in gotowe)
    niezgodne = [p for p in gotowe if p.json_zgodny is False]
    niezgodne_spolki = Counter(p.symbol for p in niezgodne)
    tsla_bmo = sum(1 for p in gotowe if p.symbol == "TSLA" and p.klasa == BMO)

    L: list[str] = [
        "# Kalendarz publikacji wynikow — SEC EDGAR 8-K item 2.02",
        "",
        f"*Wygenerowane przez `scripts/build_earnings.py`, "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}. "
        f"Zakres: {pierwsza} → {ostatnia}, {len(sesje)} sesji.*",
        "",
        f"**{len(gotowe)} publikacji** osmiu megacapow. Zrodlo darmowe i autorytatywne;",
        "proba **nie jest** wybierana po wielkosci reakcji rynku — uzasadnienie",
        "w docstringu `engine/earnings.py`.",
        "",
        "## 1. Rozklad wzgledem sesji",
        "",
        "| Klasa | N | Udzial | Sesja reakcji |",
        "|---|---|---|---|",
        f"| **AMC** (po zamknieciu) | {klasy[AMC]} | {klasy[AMC]/len(gotowe):.1%} | nastepna |",
        f"| **BMO** (przed otwarciem) | {klasy[BMO]} | {klasy[BMO]/len(gotowe):.1%} | ta sama |",
        f"| POZA_SESJA (weekend/swieto) | {klasy[POZA_SESJA]} | "
        f"{klasy[POZA_SESJA]/len(gotowe):.1%} | najblizsza |",
        f"| SRODSESYJNE | {klasy[SRODSESYJNE]} | {klasy[SRODSESYJNE]/len(gotowe):.1%} | "
        "**wykluczone z proby podstawowej** |",
        "",
        f"Zdarzen uzytecznych dla H013: **{len(uzyteczne)}**.",
        "",
        "Klasyfikacja liczona wzgledem **zaobserwowanych granic sesji tego konkretnego",
        "dnia**, nie stalych 09:30-16:00 — dzieki temu dni skrocone (13:00 ET) sa",
        "obsluzone bez tablicy wyjatkow: publikacja o 13:30 w wigilie jest AMC,",
        "a nie srodsesyjna.",
        "",
        "## 2. Pulapka strefy czasowej — wykryta i ominieta",
        "",
        f"**Dla {len(niezgodne)} z {len(gotowe)} publikacji pole `acceptanceDateTime`",
        "z API `submissions` NIE jest tym, na co wyglada.** Konczy sie litera Z, ale",
        "dla czesci spolek zawiera czas wschodni bez konwersji:",
        "",
        "| Spolka | Publikacji z bledna strefa |",
        "|---|---|",
    ]
    for s, n in sorted(niezgodne_spolki.items(), key=lambda x: -x[1]):
        L.append(f"| {s} | {n} |")
    L += [
        "",
        "Przyjecie tego pola za dobra monete przesunelo by te zdarzenia o cztery",
        "godziny wstecz — z okolic 16:0x ET (po zamknieciu) na 12:0x ET (srodek sesji).",
        "Karta H013 zaklasyfikowalaby je jako srodsesyjne i **odrzucila**, albo — gorzej",
        "— liczylaby rezyduum z okna, w ktorym publikacji jeszcze nie bylo.",
        "**Zaden wyjatek by nie poleciał.**",
        "",
        "Dlatego czas przyjecia bierzemy ze **strony indeksu zlozenia** (pole",
        "\"Accepted\", zawsze ET, zgodne co do sekundy z naglowkiem",
        "ACCEPTANCE-DATETIME pelnego zlozenia). API `submissions` mowi nam, ktore",
        "zlozenia istnieja — nie mowi, kiedy zostaly przyjete.",
        "",
        "### Godzina publikacji AMC",
        "",
        "| Godzina ET | N |",
        "|---|---|",
    ]
    for g, n in sorted(godziny.items())[:12]:
        L.append(f"| {g} | {n} |")
    L += [
        "",
        "Koncentracja tuz po 16:00 ET jest kontrola poprawnosci: publikacje wynikow",
        "megacapow wychodza kilka-kilkanascie minut po zamknieciu sesji kasowej.",
        "",
        "## 3. Pokrycie",
        "",
        "| Spolka | N publikacji | Oczekiwane (~4/rok) |",
        "|---|---|---|",
    ]
    lat = (ostatnia - pierwsza).days / 365.25
    for s in CIK:
        L.append(f"| {s} | {per_spolka[s]} | {4*lat:.0f} |")
    L += [
        "",
        "| Rok | N |",
        "|---|---|",
    ]
    for rok in sorted(per_rok):
        L.append(f"| {rok} | {per_rok[rok]} |")

    L += [
        "",
        "## 4. Zastrzezenia — znane ograniczenia tej proby",
        "",
        "**Komunikat prasowy to nie konferencja wynikowa.** EDGAR datuje zlozenie 8-K,",
        "czyli moment publikacji liczb. Konferencja zaczyna sie zwykle okolo godziny",
        "pozniej i potrafi **odwrocic** reakcje na sam komunikat. Kalendarz tego nie",
        "rozdziela i nie udaje, ze rozdziela.",
        "",
        "**Nie kazdy 8-K 2.02 to wyniki kwartalne.** Pozycja 2.02 obejmuje kazde",
        "ujawnienie wynikow operacyjnych, wiec trafiaja tu takze korekty i komunikaty",
        "posrednie. Nie filtrujemy ich po wielkosci reakcji — to bylby dokladnie ten",
        "selection bias, ktorego caly ten modul unika. Odchylenia od ~4/rok w tabeli",
        "wyzej sa wiec spodziewane i **nie sa** defektem danych.",
        "",
        f"**TSLA jest tu przypadkiem osobnym: {per_spolka['TSLA']} publikacji zamiast",
        f"~{4*lat:.0f}, w tym {tsla_bmo} przed otwarciem sesji.** Tesla sklada 8-K 2.02",
        "takze dla kwartalnych danych o produkcji i dostawach — osobnego zdarzenia,",
        "wychodzacego rano na poczatku kwartalu, kilkanascie dni przed wlasciwym",
        "raportem finansowym. Sa to prawdziwe publikacje wynikow operacyjnych i zostaja",
        "w probie, ale **karta H013 musi je raportowac osobno**: mechanizm transmisji",
        "moze dzialac inaczej dla danych o dostawach niz dla rachunku zyskow i strat,",
        "a przy jednej spolce dajacej dwa razy wiecej zdarzen niz pozostale roznica",
        "ta nie rozmyje sie w sredniej.",
        "",
    ]
    if bez_sesji:
        L += [
            f"**{len(bez_sesji)} publikacji bez sesji reakcji** — na koncu probki nie ma",
            "juz kolejnej sesji w naszych danych. Odrzucane jawnie, nie przypisywane",
            "do zlej daty:",
            "",
        ]
        L += [f"- {p.symbol} {et(p):%Y-%m-%d %H:%M} ET ({p.klasa})"
              for p in bez_sesji[:10]]
        L.append("")
    L += [
        "---",
        "",
        f"Dane: `{WYJSCIE}`. Odtworzenie: `python3 scripts/build_earnings.py`",
    ]

    RAPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPORT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"-> {WYJSCIE} ({len(gotowe)} publikacji)")
    print(f"-> {RAPORT}")
    print(f"   AMC {klasy[AMC]}, BMO {klasy[BMO]}, poza sesja {klasy[POZA_SESJA]}, "
          f"srodsesyjne {klasy[SRODSESYJNE]}; uzytecznych {len(uzyteczne)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
