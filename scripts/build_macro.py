#!/usr/bin/env python3
"""Budowa kalendarza makro — PLAN.pdf rozdz. 4.5, karta H003.

CPI, PPI i Employment Situation z harmonogramow BLS; komunikaty FOMC z kalendarza
Fedu, z godzina odczytana ze strony samego komunikatu. Uzasadnienie konstrukcji
i wykluczen: docstring `engine/macro.py`.

Wyjscie: data/clean/macro_events.csv + reports/macro_calendar.md
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.macro import (  # noqa: E402
    ET,
    FOMC,
    OPOZNIENIE_KONFERENCJI,
    Zdarzenie,
    parsuj_godzine_komunikatu,
    parsuj_harmonogram_bls,
    parsuj_posiedzenia_fomc,
    sesja_reakcji,
)

WYJSCIE = Path("data/clean/macro_events.csv")
RAPORT = Path("reports/macro_calendar.md")
MANIFEST = Path("data/manifest_macro.md")
CACHE = Path("data/raw/macro_strony.json")
MNQ = Path("data/clean/mnq_1m_cont.parquet")

LATA = range(2019, 2027)
UA = os.environ.get("SEC_USER_AGENT", "Projekt-G badania naukowe kontakt-przez-github")
PRZERWA, PROBY, BACKOFF = 0.3, 4, 2.0

BLS_ROK = "https://www.bls.gov/schedule/{rok}/home.htm"
FED_BIEZ = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FED_HIST = "https://www.federalreserve.gov/monetarypolicy/fomchistorical{rok}.htm"
FED_KOMUNIKAT = "https://www.federalreserve.gov/newsevents/pressreleases/monetary{d}a.htm"


def _pobierz_sieci(url: str) -> str:
    ostatni: Exception | None = None
    for proba in range(PROBY):
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept-Encoding": "gzip"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                b = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    b = gzip.decompress(b)
                return b.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 407):
                raise SystemExit(
                    f"HTTP {e.code} dla {url} — odmowa polityki egress. "
                    "Zglos, nie ponawiaj (patrz /root/.ccr/README.md)."
                ) from e
            if e.code == 404:
                return ""
            ostatni = e
        except (urllib.error.URLError, TimeoutError) as e:
            ostatni = e
        time.sleep(BACKOFF**proba)
    raise SystemExit(f"Nie udalo sie pobrac {url}: {ostatni}")


_cache: dict[str, str] = {}


def pobierz(url: str) -> str:
    if url in _cache:
        return _cache[url]
    _cache[url] = _pobierz_sieci(url)
    time.sleep(PRZERWA)
    return _cache[url]


def wczytaj_cache() -> None:
    if CACHE.exists():
        _cache.update(json.loads(CACHE.read_text(encoding="utf-8")))


def zapisz_cache() -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(_cache), encoding="utf-8")


#: Prog liczby barow RTH uznajacy dzien za sesje. NIE 300 — dzien skrocony
#: (wigilia, 3 lipca, dzien po Swiecie Dziekczynienia) ma okolo 210 barow i przy
#: progu 300 wypadal z kalendarza jako "brak sesji". Kosztowalo to publikacje NFP
#: z 03.07.2025, ktora jest zwyklym, handlowalnym zdarzeniem.
MIN_BAROW_SESJI = 60
PELNA_SESJA = 300


def sesje_mnq() -> tuple[frozenset[date], frozenset[date]]:
    """(dni sesyjne, dni skrocone) z naszych danych — zadnej tablicy swiat."""
    if not MNQ.exists():
        sys.exit(f"Brak {MNQ} — kalendarz wymaga dni sesyjnych z danych.")
    d = (pl.scan_parquet(MNQ).filter(pl.col("segment").is_in(
        ["rth_open", "midday", "afternoon", "close"]))
        .group_by("trade_date").agg(n=pl.len())
        .filter(pl.col("n") >= MIN_BAROW_SESJI).collect())
    wszystkie = frozenset(d["trade_date"].to_list())
    krotkie = frozenset(d.filter(pl.col("n") < PELNA_SESJA)["trade_date"].to_list())
    return wszystkie, krotkie


#: Okna wymagane przez karte H003 (sekcja 0.2), w minutach wzgledem publikacji.
OKNO_ROWNOWAGI, OKNO_IMPULSU, OKNO_OUTCOME = (-60, 0), (0, 5), (5, 25)
#: Ile procent minut okna musi miec bar, zeby zdarzenie uznac za mierzalne.
#: Bar powstaje tylko wtedy, gdy byla transakcja, wiec 100% bylo by za ostre;
#: 80% wyklucza okna, w ktorych zakres rownowagi liczylby sie z kilku wydrukow.
POKRYCIE_MIN = 0.80


def dostepnosc_barow(zdarzenia: list[Zdarzenie]) -> dict[tuple[str, date], tuple[int, int, int]]:
    """Liczba barow MNQ w trzech oknach kazdego zdarzenia.

    KRYTERIUM UZYTECZNOSCI KARTY, zastepujace warunek istnienia sesji RTH.
    Karta dla publikacji BLS dziala miedzy 07:30 a 08:55 ET i sesji kasowej
    nie potrzebuje. Zmierzone: CME otwiera skrocona sesje Globex w Wielki
    Piatek, gdy wypada NFP — trzy takie publikacje maja komplet barow, a filtr
    RTH wyrzucal je bez powodu.
    """
    d = (pl.scan_parquet(MNQ)
         .with_columns(pl.col("ts_utc").dt.convert_time_zone("America/New_York")
                       .alias("et")).collect())
    znaczniki = d["et"].to_list()
    import bisect
    posort = znaczniki  # parquet jest juz posortowany po ts_utc
    out: dict[tuple[str, date], tuple[int, int, int]] = {}
    for z in zdarzenia:
        t = z.planowany_et
        okna = []
        for a, b in (OKNO_ROWNOWAGI, OKNO_IMPULSU, OKNO_OUTCOME):
            lo = bisect.bisect_left(posort, t + timedelta(minutes=a))
            hi = bisect.bisect_left(posort, t + timedelta(minutes=b))
            okna.append(hi - lo)
        out[(z.typ, z.data)] = (okna[0], okna[1], okna[2])
    return out


def zbierz_bls() -> list[Zdarzenie]:
    out: list[Zdarzenie] = []
    for rok in LATA:
        h = pobierz(BLS_ROK.format(rok=rok))
        z = parsuj_harmonogram_bls(h, rok)
        print(f"  BLS {rok}: {len(z)} publikacji")
        out += z
    return out


def zbierz_fomc() -> tuple[list[Zdarzenie], list[Zdarzenie]]:
    """Zwraca (posiedzenia planowe, dzialania nadzwyczajne)."""
    strony = [pobierz(FED_BIEZ)]
    for rok in LATA:
        h = pobierz(FED_HIST.format(rok=rok))
        if h:
            strony.append(h)

    planowe: set[date] = set()
    komunikaty: set[date] = set()
    konferencje: set[date] = set()
    for h in strony:
        planowe |= parsuj_posiedzenia_fomc(h)
        komunikaty |= {datetime.strptime(x, "%Y%m%d").date()
                       for x in re.findall(r"monetary(\d{8})a\.htm", h)}
        konferencje |= {datetime.strptime(x, "%Y%m%d").date()
                        for x in re.findall(r"fomcpresconf(\d{8})", h)}
    komunikaty = {d for d in komunikaty if LATA.start <= d.year <= LATA.stop - 1}

    zwykle: list[Zdarzenie] = []
    nadzwyczajne: list[Zdarzenie] = []
    for d in sorted(komunikaty):
        h = pobierz(FED_KOMUNIKAT.format(d=d.strftime("%Y%m%d")))
        g = parsuj_godzine_komunikatu(h)
        if g is None:
            print(f"  UWAGA: brak godziny w komunikacie {d} — pomijam")
            continue
        znacznik = datetime(d.year, d.month, d.day, g.hour, g.minute, tzinfo=ET)
        ma_konf = d in konferencje
        z = Zdarzenie(
            typ=FOMC, planowany_et=znacznik, data=d, zrodlo="Federal Reserve",
            ma_drugi_etap=ma_konf,
            drugi_etap_et=(znacznik + timedelta(minutes=OPOZNIENIE_KONFERENCJI)
                           if ma_konf else None),
            okres=d.isoformat(),
            uwagi="" if d in planowe else "poza planowym posiedzeniem",
        )
        (zwykle if d in planowe else nadzwyczajne).append(z)
    return zwykle, nadzwyczajne


def main() -> int:
    wczytaj_cache()
    sesje, krotkie = sesje_mnq()
    pierwsza, ostatnia = min(sesje), max(sesje)
    print(f"Sesji MNQ: {len(sesje)} ({pierwsza} → {ostatnia})")

    bls = zbierz_bls()
    fomc, nadzw = zbierz_fomc()
    zapisz_cache()
    print(f"  FOMC: {len(fomc)} posiedzen planowych, {len(nadzw)} dzialan nadzwyczajnych")

    wszystkie = [z for z in (*bls, *fomc, *nadzw)
                 if pierwsza <= z.data <= ostatnia]
    gotowe = [
        Zdarzenie(typ=z.typ, planowany_et=z.planowany_et, data=z.data, zrodlo=z.zrodlo,
                  sesja_reakcji=sesja_reakcji(z.data, sesje), ma_drugi_etap=z.ma_drugi_etap,
                  drugi_etap_et=z.drugi_etap_et, okres=z.okres,
                  uwagi="; ".join(x for x in (z.uwagi,
                       "dzien skrocony" if z.data in krotkie else "") if x))
        for z in wszystkie
    ]
    gotowe.sort(key=lambda z: (z.planowany_et, z.typ))

    dost = dostepnosc_barow(gotowe)
    WYM = (int(60 * POKRYCIE_MIN), int(5 * POKRYCIE_MIN), int(20 * POKRYCIE_MIN))

    def mierzalne(z: Zdarzenie) -> bool:
        n = dost[(z.typ, z.data)]
        return all(a >= b for a, b in zip(n, WYM, strict=True))

    bez_sesji = [z for z in gotowe if not mierzalne(z)]
    podstawowe = [z for z in gotowe
                  if "poza planowym" not in z.uwagi and mierzalne(z)]
    krotkie_zd = [z for z in podstawowe if "skrocony" in z.uwagi]

    WYJSCIE.parent.mkdir(parents=True, exist_ok=True)
    with WYJSCIE.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["event_type", "scheduled_timestamp_et", "scheduled_timestamp_utc",
                    "actual_date", "source", "session_date", "has_second_stage",
                    "second_stage_timestamp_et", "second_stage_timestamp_utc",
                    "bars_pre", "bars_impulse", "bars_outcome", "bars_ok",
                    "reference_period", "notes"])
        for z in gotowe:
            w.writerow([
                z.typ, z.planowany_et.isoformat(),
                z.planowany_et.astimezone(UTC).isoformat(),
                z.data.isoformat(), z.zrodlo,
                z.sesja_reakcji.isoformat() if z.sesja_reakcji else "",
                "tak" if z.ma_drugi_etap else "nie",
                z.drugi_etap_et.isoformat() if z.drugi_etap_et else "",
                z.drugi_etap_et.astimezone(UTC).isoformat() if z.drugi_etap_et else "",
                *dost[(z.typ, z.data)], "tak" if mierzalne(z) else "nie",
                z.okres, z.uwagi,
            ])

    per_typ = Counter(z.typ for z in podstawowe)
    per_rok: Counter = Counter(z.data.year for z in podstawowe)
    godziny = Counter(z.planowany_et.strftime("%H:%M") for z in podstawowe)
    lat = (ostatnia - pierwsza).days / 365.25

    L: list[str] = [
        "# Kalendarz publikacji makro — BLS i Federal Reserve",
        "",
        f"*Wygenerowane przez `scripts/build_macro.py`, "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}. "
        f"Zakres {pierwsza} → {ostatnia}.*",
        "",
        f"**{len(podstawowe)} zdarzen w probie podstawowej** "
        f"({len(gotowe)} w kalendarzu lacznie).",
        "",
        "Zrodla urzedowe i darmowe; **godzina pochodzi z dokumentu, nie z konwencji**.",
        "Harmonogram BLS podaje ja w osobnej kolumnie, strona komunikatu FOMC we frazie",
        "\"For release at 2:00 p.m.\". Uzasadnienie: docstring `engine/macro.py`.",
        "",
        "## 1. Pokrycie",
        "",
        "| Typ | N | Oczekiwane | Zrodlo |",
        "|---|---|---|---|",
        f"| CPI | {per_typ['CPI']} | {12*lat:.0f} | BLS |",
        f"| PPI | {per_typ['PPI']} | {12*lat:.0f} | BLS |",
        f"| NFP | {per_typ['NFP']} | {12*lat:.0f} | BLS |",
        f"| FOMC (komunikat) | {per_typ['FOMC']} | {8*lat:.0f} | Federal Reserve |",
        "",
        "| Rok | CPI | PPI | NFP | FOMC |",
        "|---|---|---|---|---|",
    ]
    for rok in sorted(per_rok):
        c = Counter(z.typ for z in podstawowe if z.data.year == rok)
        L.append(f"| {rok} | {c['CPI']} | {c['PPI']} | {c['NFP']} | {c['FOMC']} |")

    L += [
        "",
        "## 2. Godziny publikacji",
        "",
        "| Godzina ET | N |",
        "|---|---|",
    ]
    for g, n in sorted(godziny.items()):
        L.append(f"| {g} | {n} |")
    L += [
        "",
        "Stalosc godzin jest **kontrola strefy czasowej**: publikacje maja stala godzine",
        "**scienna**, a nie staly offset UTC. Konwersja przez `America/New_York` obsluguje",
        "zmiane czasu sama; recznie wpisany offset bylby bledny przez pol roku.",
        "",
        "## 3. Dwa etapy posiedzenia FOMC",
        "",
    ]
    z_konf = [z for z in podstawowe if z.ma_drugi_etap]
    L += [
        f"**{len(z_konf)} z {per_typ['FOMC']} posiedzen ma konferencje prasowa** okolo",
        f"{OPOZNIENIE_KONFERENCJI} minut po komunikacie.",
        "",
        "Ma to bezposrednia konsekwencje dla H003: okno 5-60 minut po komunikacie",
        "**obejmuje w calosci konferencje**, wiec mierzyloby mieszanke dwoch zdarzen",
        "informacyjnych. Karta mierzy wynik **przed konferencja**, a decyzja zapadla",
        "przed policzeniem czegokolwiek.",
        "",
        "## 4. Dzialania nadzwyczajne — wykluczone z proby podstawowej",
        "",
    ]
    if nadzw:
        L += [
            f"**{len(nadzw)} komunikatow poza harmonogramem posiedzen.** Wykluczone",
            "z proby podstawowej **z mechanizmu, nie z danych**: karta bada rynek, ktory",
            "kompresuje sie przed ZNANYM terminem publikacji, a dzialanie nadzwyczajne",
            "jest z definicji nieoczekiwane — okna rownowagi w sensie karty nie ma.",
            "",
            "| Data | Konferencja prasowa |",
            "|---|---|",
        ]
        L += [f"| {z.data} | {'tak' if z.ma_drugi_etap else 'nie'} |" for z in nadzw]
        L += [
            "",
            "**Uwaga na pulapke:** obecnosc konferencji prasowej NIE odroznia posiedzen",
            "planowych od nadzwyczajnych — marcowe ciecia awaryjne 2020 mialy konferencje.",
            "Rozroznienie bierzemy z listy posiedzen na kalendarzu Fedu.",
            "",
        ]
    else:
        L += ["Brak — wszystkie komunikaty odpowiadaja posiedzeniom planowym.", ""]

    L += ["## 5. Kontrola jakosci", "", "| Kontrola | Wynik |", "|---|---|"]
    dupy = [k for k, v in Counter((z.typ, z.data) for z in gotowe).items() if v > 1]
    kolizje = [k for k, v in Counter(
        (z.data, z.planowany_et.hour) for z in podstawowe).items() if v > 1]
    L += [
        f"| Duplikaty (typ, data) | {len(dupy)} |",
        f"| Zdarzenia w dniu bez sesji | {len(bez_sesji)} |",
        f"| Kolizje: dwie publikacje tego samego dnia i o tej samej godzinie | {len(kolizje)} |",
        f"| Godziny inne niz 08:30 / 14:00 | "
        f"{sum(n for g, n in godziny.items() if g not in ('08:30', '14:00'))} |",
        f"| Zdarzenia w dniu SKROCONYM (zostaja w probie, oznaczone) | {len(krotkie_zd)} |",
    ]
    if bez_sesji:
        L += ["", "Zdarzenia w dniu bez sesji (raportowane, nie usuwane):", ""]
        L += [f"- {z.typ} {z.data} {z.planowany_et:%H:%M} ET" for z in bez_sesji[:15]]
    if kolizje:
        L += ["", "**Kolizje wymagaja uwagi w H003:** dwie publikacje o 08:30 tego samego",
              "dnia to jedno zdarzenie rynkowe, nie dwa. Karta musi je scalic albo",
              "wykluczyc — decyzja przed testem.", "",
              "| Data | Godzina | Typy |", "|---|---|---|"]
        for (d, g) in sorted(kolizje)[:20]:
            typy = ",".join(sorted(z.typ for z in podstawowe
                                   if z.data == d and z.planowany_et.hour == g))
            L.append(f"| {d} | {g}:00 | {typy} |")

    L += [
        "",
        "---",
        "",
        f"Dane: `{WYJSCIE}`. Odtworzenie: `python3 scripts/build_macro.py`",
    ]
    RAPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPORT.write_text("\n".join(L) + "\n", encoding="utf-8")

    # Manifest zrodel. Strony BLS i Fedu sa zmienne w czasie, wiec sam CSV nie
    # wystarcza do odtworzenia — trzeba wiedziec, z jakiego snapshotu powstal.
    M = [
        "# Manifest kalendarza makro",
        "",
        f"*Pobrane {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}.*",
        "",
        f"Wynik: `{WYJSCIE}`, SHA-256 "
        f"`{hashlib.sha256(WYJSCIE.read_bytes()).hexdigest()}`",
        "",
        "| Zrodlo | Bajtow | SHA-256 |",
        "|---|---|---|",
    ]
    for url in sorted(_cache):
        tresc = _cache[url].encode("utf-8")
        M.append(f"| `{url}` | {len(tresc)} | `{hashlib.sha256(tresc).hexdigest()[:32]}…` |")
    M += [
        "",
        "Strony puste (HTTP 404) sa w tabeli celowo — brak strony historycznej dla",
        "danego roku jest informacja o strukturze zrodla, nie bledem.",
        "",
        f"Odtworzenie: `python3 {Path(__file__).name if False else 'scripts/build_macro.py'}`",
    ]
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text("\n".join(M) + "\n", encoding="utf-8")
    print(f"-> {MANIFEST}")

    print(f"-> {WYJSCIE} ({len(gotowe)} zdarzen, {len(podstawowe)} w probie podstawowej)")
    print(f"-> {RAPORT}")
    print(f"   {dict(per_typ)}; bez sesji {len(bez_sesji)}, kolizji {len(kolizje)}, "
          f"duplikatow {len(dupy)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
