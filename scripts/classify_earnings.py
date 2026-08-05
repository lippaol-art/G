#!/usr/bin/env python3
"""Klasyfikacja publikacji 8-K item 2.02 wg TRESCI komunikatu — audyt zamykajacy H013.

POWOD. Pierwotna karta H013 mowila o **kwartalnych wynikach finansowych osmiu
megacapow publikowanych po zamknieciu sesji**: 8 spolek x 4 kwartaly x 7 lat.
Kalendarz EDGAR zawiera 261 zdarzen, w tym publikacje o produkcji i dostawach
Tesli, publikacje przed otwarciem i inne ujawnienia operacyjne. To nie jest ta
sama proba, na ktorej karta byla zaprojektowana.

CO KLASYFIKUJEMY I CZYM. Nagłowkiem komunikatu prasowego z zalacznika EX-99 —
czyli **trescia dokumentu**, nigdy reakcja ceny. Detektor cenowy nie ma tu wstepu
z tego samego powodu co w `engine/earnings.py`: wybieranie zdarzen po wielkosci
badanej reakcji skazilo by probe selekcja.

Reguly zadeklarowane przed uruchomieniem:

  KWARTALNE — naglowek mowi o wynikach finansowych za kwartal lub rok
  DOSTAWY   — naglowek mowi o produkcji i dostawach, a NIE mowi o wynikach
              finansowych (Tesla publikuje to jako osobne zdarzenie na poczatku
              kwartalu, kilkanascie dni przed wlasciwym raportem finansowym)
  INNE      — pozostale ujawnienia operacyjne

ROZDZIELENIE DWOCH DOKUMENTOW TESLI JEST NIETRYWIALNE i wymagalo obejrzenia
prawdziwych tytulow. Oba zawieraja markery, ktore naiwna regula uznalaby za
przeciwne:

  dostawy:  "Tesla Vehicle Production & Deliveries and Date for Financial
             Results & Webcast for Fourth Quarter 2023"
             -> zawiera "Financial Results", ale tylko jako ZAPOWIEDZ DATY
                przyszlej publikacji

  wyniki:   "Q4 and FY 2023 Update" + sekcja Highlights, w ktorej wymieniona
             jest produkcja i dostawy
             -> zawiera slowa o dostawach, choc jest pelnym raportem

Stad regula z jawnym wykluczeniem: dokument jest DOSTAWAMI, gdy tytul mowi
o produkcji lub dostawach pojazdow **i jednoczesnie nie jest kwartalnym
"Update"**. Reguly rozdzielaja te dokumenty **po tresci tytulu**, nigdy po dacie
ani po reakcji rynku.

Wyjscie: data/clean/earnings_rodzaj.csv
"""

from __future__ import annotations

import csv
import gzip
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

WEJSCIE = Path("data/clean/earnings.csv")
WYJSCIE = Path("data/clean/earnings_rodzaj.csv")
CACHE = Path("data/raw/edgar_naglowki.json")

UA = os.environ.get("SEC_USER_AGENT", "Projekt-G badania naukowe kontakt-przez-github")
PRZERWA = 0.15
PROBY, BACKOFF = 4, 2.0
ZNAKI_NAGLOWKA = 2500        # poczatek komunikatu wystarcza — tam jest tytul

DOSTAWY, KWARTALNE, INNE = "DOSTAWY", "KWARTALNE", "INNE"

#: Tytul komunikatu o dostawach zmienial sie w czasie i wzorzec musi objac obie
#: postacie: "Vehicle Production & Deliveries" (2019-2024) oraz "Production,
#: Deliveries & Deployments" (od IV kw. 2024) — z przecinkiem zamiast spojnika.
_WZ_DOSTAWY = re.compile(
    r"(production\s*[,&]?\s*(and\s+)?deliver|deliver\w*\s*[,&]?\s*(and\s+)?production|"
    r"vehicle\s+production|vehicle\s+deliver)", re.I)
#: Tesla tytuluje raport finansowy "Second Quarter 2019 Update" / "Q4 2023 Update",
#: bez slowa "results" — stad osobna galaz na "update". Bez niej 23 publikacje
#: kwartalne Tesli wpadaly do kosza INNE.
_WZ_KWARTALNE = re.compile(
    r"(financial\s+results|reports?\s+[\w\s]{0,30}results|quarterly\s+results|"
    r"results\s+for\s+(the\s+)?(first|second|third|fourth|fiscal)|"
    r"(first|second|third|fourth)\s+quarter[\w\s,]{0,30}(results|update)|"
    r"q[1-4][\s-]*\d{4}\s+(update|results|financial|earnings)|earnings\s+release|"
    r"q[1-4]\s+and\s+fy\s*\d{4}\s+update|"
    r"announces?\s+[\w\s]{0,30}(results|earnings)|"
    r"(first|second|third|fourth)\s+quarter\s+(and|fiscal|of)|"
    r"full\s+year[\w\s]{0,20}(results|update))", re.I)


def pobierz(url: str) -> str:
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
            if e.code == 404:
                return ""
            ostatni = e
        except (urllib.error.URLError, TimeoutError) as e:
            ostatni = e
        time.sleep(BACKOFF**proba)
    raise SystemExit(f"Nie udalo sie pobrac {url}: {ostatni}")


def tekst(surowy_html: str) -> str:
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", surowy_html)
    t = re.sub(r"<[^>]+>", " ", t)
    return html.unescape(re.sub(r"\s+", " ", t)).strip()


def naglowek(cik: int, accession: str) -> str:
    """Poczatek komunikatu prasowego z zalacznika EX-99 danego zlozenia."""
    nod = accession.replace("-", "")
    baza = f"https://www.sec.gov/Archives/edgar/data/{cik}/{nod}"
    indeks = pobierz(f"{baza}/{accession}-index.htm")
    time.sleep(PRZERWA)
    # Zalacznik rozpoznajemy po KOLUMNIE TYPU w tabeli indeksu, nie po nazwie pliku.
    # Nazwy plikow sa dowolne: Apple 2019 nazwal go `a8-kexhibit991q320196292019.htm`,
    # ktorego zaden wzorzec na "ex-99" nie zlapie. Typ w tabeli jest znormalizowany.
    ex: list[str] = []
    for wiersz in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", indeks):
        if not re.search(r"EX-?99", wiersz, re.I):
            continue
        m = re.search(r'href="([^"]+\.(?:htm|txt))"', wiersz, re.I)
        if m:
            ex.append(m.group(1))
    if not ex:
        return ""
    url = ex[0].replace("/ix?doc=", "")
    if not url.startswith("http"):
        url = "https://www.sec.gov" + url
    t = tekst(pobierz(url))
    time.sleep(PRZERWA)
    return t[:ZNAKI_NAGLOWKA]


#: Kwartalny raport Tesli nosi tytul "Update", nie "results" — i to jest jedyny
#: pewny znacznik odrozniajacy go od komunikatu o dostawach, ktory tez wspomina
#: o "Financial Results" (zapowiadajac ich date).
_WZ_UPDATE = re.compile(
    r"(q[1-4]\s+(and\s+fy\s*)?\d{4}\s+update|"
    r"(first|second|third|fourth)\s+quarter[\w\s,]{0,20}update|"
    r"fy\s*\d{4}\s+update)", re.I)


#: Regula decyduje z TYTULU, nie z calego poczatku dokumentu — i to nie jest
#: optymalizacja, tylko konieczosc. Komunikat Tesli o dostawach zawiera ~1700
#: znakow dalej link do webcastu przyszlego raportu: "Q4 & FY 2022 Update :
#: http://ir.tesla...". Przy szerszym oknie kazdy komunikat o dostawach
#: wygladal jak raport kwartalny.
DL_TYTULU = 400


def klasyfikuj(tekst_naglowka: str) -> str:
    """DOSTAWY tylko wtedy, gdy TYTUL nie jest kwartalnym raportem.

    Uzasadnienie wykluczenia i szerokosci okna — docstring modulu i komentarz
    przy `DL_TYTULU`.
    """
    tytul = tekst_naglowka[:DL_TYTULU]
    if _WZ_DOSTAWY.search(tytul) and not _WZ_UPDATE.search(tytul):
        return DOSTAWY
    if _WZ_KWARTALNE.search(tytul) or _WZ_KWARTALNE.search(tekst_naglowka):
        return KWARTALNE
    return INNE


def main() -> int:
    if not WEJSCIE.exists():
        sys.exit(f"Brak {WEJSCIE} — uruchom scripts/build_earnings.py")
    wiersze = list(csv.DictReader(WEJSCIE.open(encoding="utf-8", newline="\n")))

    cache: dict[str, str] = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    brak = [r for r in wiersze if r["accession"] not in cache]
    if brak:
        print(f"Pobieram naglowki komunikatow: {len(brak)} (w cache {len(cache)})")
    for i, r in enumerate(brak, 1):
        cache[r["accession"]] = naglowek(int(r["cik"]), r["accession"])
        if i % 25 == 0:
            print(f"  {i}/{len(brak)}")
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8", newline="\n")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8", newline="\n")

    for r in wiersze:
        r["rodzaj"] = klasyfikuj(cache.get(r["accession"], ""))
        r["naglowek"] = re.sub(r"\s+", " ", cache.get(r["accession"], ""))[:120]

    pola = [*wiersze[0].keys()]
    with WYJSCIE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pola)
        w.writeheader()
        w.writerows(wiersze)

    c = Counter(r["rodzaj"] for r in wiersze)
    print(f"-> {WYJSCIE}")
    for k, n in c.most_common():
        print(f"   {k:10s} {n}")
    inne = [r for r in wiersze if r["rodzaj"] == INNE]
    print(f"   do przejrzenia recznie (INNE): {len(inne)}")
    for r in inne[:12]:
        print(f"     {r['symbol']} {r['akceptacja_et'][:10]} | {r['naglowek'][:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
