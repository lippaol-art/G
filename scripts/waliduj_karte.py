#!/usr/bin/env python3
"""Linter kart hipotez — bramka zamrozenia. PLAN.pdf rozdz. 8.4.

PO CO LINTER DO DOKUMENTU PISANEGO PRZEZ CZLOWIEKA.

`engine/guards.py` pilnuje niezmiennikow DANYCH. Ten skrypt pilnuje niezmiennikow
PROCESU — i jest potrzebny z tego samego powodu: brak tych pol nie boli w chwili
pisania karty, tylko po wydaniu prob, kiedy okazuje sie, ze karty nie da sie
sfalsyfikowac albo ze nie wiadomo, wobec czego mierzyc przewage.

Kazde sprawdzane pole odpowiada bledowi, ktory ten projekt juz popelnil:

  * PRZYMUSZONY UCZESTNIK — bez nazwania, KTO musi handlowac niezaleznie od ceny,
    karta opisuje korelacje, nie mechanizm. Tak upadla wiekszosc Gen1.
  * ROZNICA WOBEC BENCHMARKU — reguła "dwa znane warunki = oryginalnosc" byla
    bledna (audyt 3). Oryginalnosc wymaga innego MECHANIZMU, nie innych parametrow.
  * WARUNEK NEGATYWNY — karta, ktorej nic nie obala, nie jest hipoteza.
  * PLAN N / MOCY — wyprowadzenie N≈380 bylo rachunkiem istotnosci, nie mocy;
    podloga to N≥400, cel 800+ (poprawka A2-6).
  * CZESTOTLIWOSC OKAZJI — bez niej nie wiadomo, ile LAT trwaloby zebranie N.
  * LICZBA WARIANTOW ≤10 — przy 30 certyfikacji nie przechodzi nawet Sharpe 1.5.
  * SHA ZAMROZENIA — bez niego nie da sie dowiesc, ze specyfikacja poprzedzala wynik.
  * RECENZJE — poziom P2 protokolu wspolpracy wymaga odpowiedzi na kazdy zarzut
    PRZED zamrozeniem (`docs/PROTOKOL_WSPOLPRACY.md`).

ZAKRES OBOWIAZYWANIA. Bramka dotyczy kart **od H017 w gore**. Karty Gen1 powstaly
przed linterem i NIE sa nim objete wstecznie: ich wyniki maja pozostac odtwarzalne,
a nie zgodne z pozniejszym formularzem. Przerabianie zamknietych kart pod nowy
formularz byloby zmienianiem historii, nie poprawianiem procesu.

Uruchomienie:
    python3 scripts/waliduj_karte.py hypotheses/H017.md
    python3 scripts/waliduj_karte.py hypotheses/H017.md --przed-zamrozeniem
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

#: (nazwa pola, wzorzec naglowka/etykiety, komunikat czego brakuje)
#: Wzorce sa CELOWO luzne co do numeracji sekcji — karta ma spelniac wymagania
#: merytoryczne, a nie odtwarzac uklad numerow z szablonu.
WYMAGANE: tuple[tuple[str, str, str], ...] = (
    ("mechanizm",
     r"przymuszony\s+uczestnik",
     "nazwij PRZYMUSZONEGO UCZESTNIKA: kto musi handlowac niezaleznie od ceny "
     "i dlaczego nie moze przestac"),
    # NIE samo slowo "benchmark": pada mimochodem w prozie prawie kazdej karty
    # i przepuszczaloby karty, ktore zadnego benchmarku nie wskazuja. Wymagamy
    # postaci naglowka albo etykiety z dwukropkiem.
    ("benchmark",
     r"(^#{1,6}[^\n]*benchmark|benchmark\w*\s*[:\-—])",
     "wskaz najblizszy publiczny benchmark (B00/B0x lub pozycja z literatury) "
     "jako osobna sekcje albo etykiete `Benchmark:` — wzmianka w prozie "
     "nie wystarcza"),
    ("roznica",
     r"r[oó][zż]nica\s+mechanizmu",
     "nazwij ROZNICE MECHANIZMU wobec benchmarku — nie roznice parametrow"),
    ("warunek_negatywny",
     r"(co\s+by\s+t[eę]\s+kart[eę]\s+sfalsyfikowa|warunek\s+negatywny|"
     r"co\s+j[aą]\s+obala)",
     "dopisz WARUNEK NEGATYWNY: co konkretnie obala te hipoteze"),
    ("plan_n",
     r"(plan\s+N|liczno[sś][cć]\s+pr[oó]by|moc\s+testu|N\s*[≥>=])",
     "dopisz PLAN N / MOCY (podloga N>=400 albo jawne uzasadnienie odstepstwa)"),
    ("czestotliwosc",
     r"(cz[eę]stotliwo[sś][cć]|okazji\s*/\s*rok|zdarze[nń]\s+rocznie|"
     r"okazji\s+rocznie)",
     "podaj CZESTOTLIWOSC OKAZJI na rok — bez niej nie wiadomo, ile lat "
     "trwaloby zebranie N"),
    ("warianty",
     r"wariant",
     "wymien WARIANTY zadeklarowane z gory (maks. 10)"),
    ("recenzje",
     r"recenzje",
     "dodaj sekcje `Recenzje` z odpowiedzia na kazdy zarzut (protokol P2)"),
)

WZORZEC_SHA = re.compile(
    r"SHA\s+zamro[żz]enia\s*[:|]\s*[`*]*\s*(PENDING|[0-9a-f]{7,40})",
    re.IGNORECASE)

#: Limit z tabeli wykonalnosci DSR (PLAN rozdz. 6.5), nie preferencja stylu.
MAX_WARIANTOW = 10
#: Podloga liczebnosci proby po dodaniu czlonu mocy testu (poprawka A2-6).
MIN_N = 400


#: Minimalna dlugosc tresci sekcji, po odarciu ze znakow skladni Markdown.
MIN_TRESCI = 40


def _sekcja_niepusta(tekst: str, wzorzec: str) -> bool:
    """Czy KTORAKOLWIEK sekcja pasujaca do wzorca ma faktyczna tresc.

    DWIE PULAPKI, KTORE TA FUNKCJA MUSI OMIJAC — obie wykryte przez testy,
    nie przez lekture:

    1. Sam naglowek nie wystarcza. Pusta sekcja `## Warunek negatywny`
       spelnialaby kontrole obecnosci, nie wnoszac nic. Dlatego wymagamy
       tresci — ale liczonej WYLACZNIE do najblizszego naglowka. Bez tego
       ciecia pusta sekcja "pozyczalaby" tresc od nastepnej i przechodzila.

    2. Pierwsze trafienie nie musi byc tym wlasciwym. Slowo moze wystapic
       mimochodem w innej sekcji, wiec sprawdzamy WSZYSTKIE wystapienia
       i wystarczy, ze jedno ma wlasna tresc.
    """
    for m in re.finditer(wzorzec, tekst, re.IGNORECASE | re.MULTILINE):
        ogon = tekst[m.end():]
        koniec = re.search(r"\n#{1,6}\s", ogon)
        if koniec:
            ogon = ogon[:koniec.start()]
        tresc = re.sub(r"[\s#*_`|:\-]+", " ", ogon).strip()
        if len(tresc) >= MIN_TRESCI:
            return True
    return False


def liczba_wariantow(tekst: str) -> int | None:
    """Wyluskuje zadeklarowana liczbe wariantow, jesli karta ja podaje."""
    m = re.search(r"wszystkie\s+(\d+)\s+zadeklarowane", tekst, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s+wariant[oó]w", tekst, re.IGNORECASE)
    return int(m.group(1)) if m else None


def waliduj(sciezka: Path, przed_zamrozeniem: bool = False) -> list[str]:
    """Zwraca liste brakow. Pusta lista == karta gotowa do zamrozenia."""
    if not sciezka.exists():
        return [f"nie ma pliku {sciezka}"]
    tekst = sciezka.read_text(encoding="utf-8")
    braki: list[str] = []

    for _, wzorzec, komunikat in WYMAGANE:
        if not _sekcja_niepusta(tekst, wzorzec):
            braki.append(komunikat)

    n = liczba_wariantow(tekst)
    if n is not None and n > MAX_WARIANTOW:
        braki.append(f"zadeklarowano {n} wariantow, limit to {MAX_WARIANTOW} "
                     "(przy 30 certyfikacji nie przechodzi nawet Sharpe 1.5)")

    m = WZORZEC_SHA.search(tekst)
    if m is None:
        braki.append("brak pola `SHA zamrozenia` (dopuszczalne `PENDING` przed "
                     "zamrozeniem)")
    elif m.group(1).upper() == "PENDING" and not przed_zamrozeniem:
        braki.append("`SHA zamrozenia: PENDING` — karta NIE jest zamrozona; "
                     "uruchom z --przed-zamrozeniem, jesli to stan zamierzony")
    return braki


def main() -> int:
    p = argparse.ArgumentParser(description="Linter kart hipotez")
    p.add_argument("karta", type=Path, help="sciezka do karty, np. hypotheses/H017.md")
    p.add_argument("--przed-zamrozeniem", action="store_true",
                   help="dopusc `SHA zamrozenia: PENDING`")
    args = p.parse_args()

    braki = waliduj(args.karta, args.przed_zamrozeniem)
    if not braki:
        print(f"{args.karta}: OK — karta spelnia wymagania zamrozenia.")
        return 0

    print(f"{args.karta}: {len(braki)} brak(ow)\n")
    for i, b in enumerate(braki, start=1):
        print(f"  {i}. {b}")
    print("\nKarta NIE moze zostac zamrozona (regula 10 z HANDOFF).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
