#!/usr/bin/env python3
"""Zakup 22 sesji RTH `mbo` — D5-B2. Specyfikacja: docs/D5_ETAP4_SPEC.md.

DZIEN PO DNIU, ZE WZNOWIENIEM, DO `PROJECT_G_DATA_ROOT`.

OSIEM WARUNKOW ODMOWY, jedna numeracja — ta sama w docstringu i w kazdym
komunikacie `STOP (warunek N)`; jej odpowiednik w dokumentacji to
`docs/URUCHOMIENIE_LOKALNE.md` §8. Skrypt PRZERYWA, gdy:

  1. wolne miejsce na starcie jest mniejsze niz `MIN_WOLNE_GB`,
  2. suma wycen 22 sesji przekroczy `LIMIT_USD`,
  3. zapytanie lub okna sesji roznia sie od zapisanych w manifescie
     poprzedniego uruchomienia (ochrona wznowienia przed zmiana specyfikacji),
  4. sesja `SESJA_D5C` mialaby zostac kupiona ponownie — bez jawnego
     `--kup-ponownie-d5c`,
  5. wolne miejsce spadnie ponizej `REZERWA_GB` w trakcie pobierania,
  6. pobrana sesja nie przejdzie kontroli kompletnosci,
  7. plik `SESJA_D5C` ma SHA-256 inny niz `data/manifest_d5c.json` — czyli ma
     poprawna liczbe rekordow, ale NIE jest tym plikiem, na ktorym policzono
     audyt Etapu 3,
  8. liczba rekordow w metadanych rozjechala sie z zapisana w manifescie —
     kazdy juz oplacony plik wyglada wtedy na niekompletny i skrypt kupilby
     caly miesiac drugi raz. Jawna furtka: `--akceptuj-rozjazd`, ktora
     ARCHIWIZUJE stary manifest zamiast go nadpisywac.

UWAGA NA DWIE ROZNE LISTY. Powyzsza numeracja opisuje ODMOWY SKRYPTU. Lista
w `URUCHOMIENIE_LOKALNE.md` §7 to co innego — osiem WARUNKOW ZGODY wlasciciela
na zakup, z wlasna numeracja, spelnianych czesciowo poza skryptem (CI zielone,
zgodnosc lokalnego D5-C). Nie mieszac ich ze soba.

CZEGO SKRYPT NIE ROBI, CHOC MOZNA BY TAK PRZECZYTAC.
Niekompletny plik ISTNIEJACY PRZED URUCHOMIENIEM **nie** przerywa pracy:
zostaje skasowany i pobrany raz jeszcze, co KOSZTUJE cene tej sesji. Tak ma
byc — inaczej jedna obcieta sesja blokowalaby caly miesiac. Odmowa (warunek 6)
dotyczy sesji niekompletnej PO pobraniu, bo to znaczy, ze cos jest nie tak
z zapytaniem i dalsze wydawanie pieniedzy nie ma sensu.

  WYJATEK OD TEGO KASOWANIA — plik zgodny z liczba rekordow z MANIFESTU.
  Po zmianie normalizacji GLBX.MDP3 (08.08.2026) biezaca wycena podaje dla
  naszych pieciu sesji WIECEJ rekordow, niz maja pliki na dysku, a starej
  wersji nie da sie juz pobrac. Bez tego wyjatku `--akceptuj-rozjazd`
  kasowalby jedyny istniejacy egzemplarz starej normalizacji i kupowal te
  same doby drugi raz. `kompletny()` przyjmuje wiec DWIE dopuszczalne liczby:
  biezaca i oplacona. Druga linia obrony stoi przy samym `unlink()`.

CZEGO NIE ROBI — I TO JEST CELOWE.
Nie ponawia pobierania po bledzie 504. Pobieranie jest PLATNE i tworzy plik;
slepe ponowienie grozi podwojnym naliczeniem i cichym zostawieniem obcietej
sesji, ktora parsuje sie bez bledu. Po awarii skrypt konczy prace, wypisuje
stan i zostawia decyzje czlowiekowi.

WZNOWIENIE NIE JEST DARMOWE DLA SESJI PRZERWANEJ W LOCIE. Sesje juz KOMPLETNE
sa pomijane bez kosztu. Sesja, ktorej pobieranie przerwano, kosztuje DWA RAZY:
raz za dane faktycznie przeslane przed zerwaniem, drugi raz za pelne pobranie
przy wznowieniu.

  Databento (Rob, 11.08.2026): *"If a request was broken and only partially
  sent, you'll be charged for the partial data sent."*

  KOREKTA: pisalem tu wczesniej, ze dostawca liczy "za zrealizowane zapytanie,
  nie za odebrane bajty". To bylo BLEDNE — rozliczenie idzie po danych
  faktycznie przeslanych. Regula postepowania sie nie zmienia (nie przerywaj),
  ale jej uzasadnienie tak: strata to nadmiarowa czesc, nie cala sesja.

Precedens: D5-B, sesja 2026-07-07, pozycja "duplikacja" w `data/KOSZTY.md`.

Metadane sa darmowe i dzielone na kawalki (`engine/databento_io.py`), bo dla
MBO pojedyncze zapytanie o cala sesje trafia w 60-sekundowy limit bramy.

Uruchomienie:
    python3 scripts/fetch_d5b2_month.py --wycena   # sama wycena, bez zakupu
    python3 scripts/fetch_d5b2_month.py            # wycena + zakup
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import databento as db

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.databento_io import (  # noqa: E402
    ODSTEPY_DLUGIE,
    metadane_dzielone,
)
from engine.paths import raw_dir, wolne_gb  # noqa: E402

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

ZAPYTANIE = dict(dataset="GLBX.MDP3", symbols=["MNQU6"],
                 stype_in="raw_symbol", schema="mbo")

#: 22 sesje RTH lipca 2026. Lista JAWNA, nie generowana z kalendarza —
#: zakres jest czescia zamrozonej specyfikacji i nie moze sie zmienic
#: przez poprawke w innym module.
SESJE = [f"2026-07-{d:02d}" for d in
         (1, 2, 3, 6, 7, 8, 9, 10, 13, 14, 15, 16, 17, 20, 21, 22, 23, 24,
          27, 28, 29, 30)]

#: Zamrozony w `docs/D5_ETAP4_SPEC.md` §7 przed zakupem.
LIMIT_USD = 82.00
#: Ponizej tego zapasu nie zaczynamy i nie kontynuujemy.
REZERWA_GB = 20.0
#: Warunek 1: minimum wolnego miejsca na starcie.
MIN_WOLNE_GB = 100.0

#: Przelom normalizacji GLBX.MDP3, potwierdzony przez dostawce 10-11.08.2026.
#: Databento: *"The old data is not available anymore in our API."* — starej
#: wersji NIE DA SIE juz pobrac za zadna cene, a obu wersji NIE WIDAC w samych
#: danych. Bez znacznika w manifescie kolejna sesja zmiesza je na slepo.
#: Granica jest PRZEDZIALEM, nie punktem: ostatnie pobranie ze stara
#: normalizacja to 2026-08-06T22:05:38Z, pierwsza wycena z nowa 2026-08-08
#: 12:15Z. Miedzy nimi nie zgadujemy — zwracamy NIEUSTALONA.
NORMALIZACJA_OSTATNIA_STARA = dt.datetime(2026, 8, 6, 22, 5, 38, tzinfo=dt.UTC)
NORMALIZACJA_PIERWSZA_NOWA = dt.datetime(2026, 8, 8, 12, 15, tzinfo=dt.UTC)

#: Sesja kupiona w D5-C. Nazwana stala, bo odwoluja sie do niej trzy rozne
#: kontrole i literal w trzech miejscach rozjechalby sie przy pierwszej zmianie.
SESJA_D5C = "2026-07-30"

#: PIEC sesji pobranych PRZED przelomem normalizacji. Lista jest tu, a nie
#: w dokumentacji, bo dwa razy z rzedu zgubila sie w niej sesja 2026-07-06 —
#: raz w mailu do dostawcy ("We hold four"), raz w liscie plikow DO KOPII
#: ZAPASOWEJ. Ta druga pomylka ma skutek fizyczny: 07-06 zostalby na jednym
#: dysku, a starej normalizacji nie da sie juz pobrac. Straznik
#: `TestKopiaZapasowa` w tests/test_guards.py porownuje z ta stala.
SESJE_STARA_NORMALIZACJA = ("2026-07-01", "2026-07-02", "2026-07-03",
                            "2026-07-06", SESJA_D5C)

KATALOG = "d5b2_mbo"
#: Sesja kupiona wczesniej w ramach D5-C — lezy W INNYM KATALOGU, pod ta sama
#: nazwa pliku. Bez tego wpisu skrypt jej nie widzi i proponuje zakup 22 sesji
#: zamiast 21, czyli TRZECIE naliczenie tej samej doby (3,5961 USD).
#: Wykryte przy wycenie, zanim cokolwiek kupiono.
KATALOG_D5C = "d5c_mbo"
MANIFEST = "manifest_d5b2.json"
#: Cache wyceny. Wycena to 572 wywolania metadanych (22 sesje x 13 kawalkow
#: x 2 zapytania) i jedno nieudane kasowalo dotad CALA prace — realnie zdarzyl
#: sie 503 na 6. kawalku PIERWSZEJ sesji. Cache sprawia, ze ponowne
#: uruchomienie dopytuje tylko o to, czego jeszcze nie ma.
CACHE_WYCENY = "wycena_cache.json"
#: Po tylu godzinach wpis w cache jest ignorowany i wyceniany od nowa.
#: Regula wlasciciela brzmi "wycena bezposrednio przed pobraniem, nie sprzed
#: kilku dni" — cache ma ratowac PRZERWANY przebieg, nie zastepowac wyceny.
WAZNOSC_WYCENY_H = 12
#: Manifest kanoniczny D5-C — sledzony w repo, zrodlo SHA-256 pierwotnego zakupu.
KANONICZNY_D5C = Path("data/manifest_d5c.json")


def okno(sesja: str) -> tuple[str, str]:
    """RTH WYPROWADZONE ZE STREFY ET — nigdy ze stalej UTC."""
    y, m, d = map(int, sesja.split("-"))
    a = dt.datetime(y, m, d, 9, 30, tzinfo=ET).astimezone(UTC)
    b = dt.datetime(y, m, d, 16, 0, tzinfo=ET).astimezone(UTC)
    return a.strftime("%Y-%m-%dT%H:%M"), b.strftime("%Y-%m-%dT%H:%M")


def nazwa_pliku(sesja: str) -> str:
    return f"mnq_mbo_rth_{sesja}.dbn.zst"


def sciezka_docelowa(sesja: str) -> Path:
    """Dokad POBIERAMY. Zawsze wlasny katalog — nigdy cudzy.

    Rozdzielenie od `sciezka_istniejaca` jest celowe i pilnuje go test.
    Gdyby pobieranie moglo trafic do `d5c_mbo/`, niekompletne pobranie
    skasowaloby kanoniczny plik D5-C, na ktorym opiera sie caly audyt Etapu 3.
    """
    return raw_dir(KATALOG, nazwa_pliku(sesja))


def sciezka_istniejaca(sesja: str) -> Path:
    """Gdzie plik LEZY, jesli w ogole lezy.

    Sesja 2026-07-30 zostala kupiona w ramach D5-C i zapisana w `d5c_mbo/`
    pod ta sama nazwa. Szukanie wylacznie we wlasnym katalogu znaczyloby, ze
    skrypt jej nie widzi i proponuje ja kupic po raz trzeci.
    """
    for katalog in (KATALOG, KATALOG_D5C):
        p = raw_dir(katalog, nazwa_pliku(sesja))
        if p.exists():
            return p
    return sciezka_docelowa(sesja)


def sciezka_manifestu() -> Path:
    return raw_dir().parent / "manifests" / MANIFEST


def sciezka_cache() -> Path:
    return raw_dir().parent / "manifests" / CACHE_WYCENY


def klucz_wyceny(a: str, b: str) -> str:
    """Klucz zawiera CALE zapytanie, nie samo okno.

    Gdyby zawieral tylko daty, zmiana symbolu albo schematu podstawilaby
    ceny z innego zapytania — i to bez sladu, bo liczby wygladalyby sensownie.
    """
    return (f"{ZAPYTANIE['dataset']}|{','.join(ZAPYTANIE['symbols'])}"
            f"|{ZAPYTANIE['stype_in']}|{ZAPYTANIE['schema']}|{a}|{b}")


def wczytaj_cache() -> dict[str, dict]:
    """Wpisy MLODSZE niz `WAZNOSC_WYCENY_H`. Starsze sa po cichu odrzucane.

    Cache ratuje PRZERWANY przebieg, nie zastepuje wyceny. Regula wlasciciela
    brzmi "wycena bezposrednio przed pobraniem" i limit wieku jest po to,
    zeby cache jej nie obchodzil.
    """
    p = sciezka_cache()
    if not p.exists():
        return {}
    try:
        dane = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}                      # uszkodzony cache to brak cache
    teraz = dt.datetime.now(dt.UTC)
    swieze = {}
    for k, v in dane.items():
        try:
            wiek = (teraz - dt.datetime.fromisoformat(v["utc"])).total_seconds()
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= wiek < WAZNOSC_WYCENY_H * 3600:
            v["wiek_h"] = wiek / 3600
            swieze[k] = v
    return swieze


def zapisz_cache(cache: dict[str, dict]) -> None:
    p = sciezka_cache()
    p.parent.mkdir(parents=True, exist_ok=True)
    czyste = {k: {i: j for i, j in v.items() if i != "wiek_h"}
              for k, v in cache.items()}
    p.write_text(json.dumps(czyste, indent=1), encoding="utf-8", newline="\n")


def sha_pliku(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for kawalek in iter(lambda: f.read(1 << 20), b""):
            h.update(kawalek)
    return h.hexdigest()


def sprawdz_manifest(plan: list[dict]) -> str:
    """WARUNEK 3 — wznowienie musi dotyczyc TEGO SAMEGO zakupu.

    Manifest poprzedniego uruchomienia zapisuje zapytanie i okna wszystkich
    sesji. Jesli ktos zmieni symbol, schemat albo granice RTH i uruchomi skrypt
    ponownie, czesc plikow na dysku pochodzi ze starej definicji, a czesc
    z nowej — i nic w danych tego nie zdradzi. Miesiac zlozony z dwoch roznych
    zapytan wyglada dokladnie jak miesiac poprawny.

    Zwraca komunikat diagnostyczny; przerywa przy niezgodnosci.
    """
    cel = sciezka_manifestu()
    if not cel.exists():
        return "manifest: brak (pierwsze uruchomienie)"
    try:
        stary = json.loads(cel.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        # Bez tego leci traceback tuz przed zakupem za kilkadziesiat USD.
        # Nie zgadujemy, ze "pewnie pierwsze uruchomienie" — manifest jest
        # jedynym zapisem tego, za co juz zaplacono.
        sys.exit(f"STOP (warunek 3): nie moge odczytac {cel} "
                 f"({type(e).__name__}). Manifest jest jedynym zapisem "
                 "poprzedniego zakupu — napraw go albo usun SWIADOMIE, "
                 "wiedzac, ze tracisz historie tego, za co zaplacono.")

    if stary.get("zapytanie") != ZAPYTANIE:
        sys.exit(f"STOP (warunek 3): zapytanie rozni sie od zapisanego w "
                 f"{cel}.\n  manifest: {stary.get('zapytanie')}\n"
                 f"  teraz   : {ZAPYTANIE}\n"
                 "Pliki na dysku pochodza z INNEJ definicji. Usun je swiadomie "
                 "albo przywroc poprzednie zapytanie.")

    okna_stare = {w["sesja"]: (w["start_utc"], w["end_utc"])
                  for w in stary.get("plan", [])}
    rozne = [w["sesja"] for w in plan
             if w["sesja"] in okna_stare
             and okna_stare[w["sesja"]] != (w["start_utc"], w["end_utc"])]
    if rozne:
        sys.exit(f"STOP (warunek 3): okna sesji roznia sie od manifestu dla "
                 f"{len(rozne)} sesji: {rozne[:5]}. Granice RTH sa czescia "
                 "zamrozonej specyfikacji — nie mieszamy dwoch definicji "
                 "w jednym miesiacu.")
    return f"manifest: zgodny ({len(okna_stare)} sesji)"


def sprawdz_sesje_d5c(do_pobrania: list[dict], pozwol: bool) -> None:
    """WARUNEK 4 — sesja z D5-C nie moze zostac kupiona po raz TRZECI.

    Ta doba byla juz naliczona dwukrotnie (`data/KOSZTY.md`, pozycja
    duplikacja). Jesli trafia do listy zakupowej, znaczy to, ze pliku nie ma
    albo jest uszkodzony — i jedno, i drugie wymaga decyzji czlowieka,
    a nie cichego dokupienia za 3,5961 USD.
    """
    if not any(w["sesja"] == SESJA_D5C for w in do_pobrania):
        return
    if pozwol:
        print(f"\n  UWAGA: {SESJA_D5C} zostanie kupiona PONOWNIE na jawne "
              "zadanie (--kup-ponownie-d5c). Bedzie to TRZECIE naliczenie tej "
              "doby — dopisz je do data/KOSZTY.md.", flush=True)
        return
    sys.exit(
        f"\nSTOP (warunek 4): {SESJA_D5C} trafila na liste do pobrania.\n"
        f"  Ta doba byla juz kupiona dwa razy (D5-B i D5-C).\n"
        f"  Szukalem w: {raw_dir(KATALOG, nazwa_pliku(SESJA_D5C))}\n"
        f"          i : {raw_dir(KATALOG_D5C, nazwa_pliku(SESJA_D5C))}\n"
        "  Sprawdz, czy plik istnieje i czy nie jest obciety.\n"
        "\n"
        "  UWAGA PRZED UZYCIEM --kup-ponownie-d5c: jesli ta sesja trafila tu\n"
        "  dlatego, ze jej plik pochodzi ze STAREJ normalizacji (sprzed\n"
        "  2026-08-08), to flaga NIE jest wlasciwa odpowiedzia. Plik jest\n"
        "  kompletny w swojej epoce, a starej wersji nie da sie juz pobrac —\n"
        "  patrz docs/D5_DRYF_METADANYCH.md §5f. Flaga sluzy wylacznie\n"
        "  swiadomemu TRZECIEMU zakupowi tej doby.")


def rekordy_z_manifestu() -> dict[str, int]:
    """Liczby rekordow ZAPISANE przy poprzednim zakupie — to, za co zaplacono."""
    cel = sciezka_manifestu()
    if not cel.exists():
        return {}
    try:
        stary = json.loads(cel.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {w["sesja"]: int(w["rekordow"]) for w in stary.get("plan", [])
            if "rekordow" in w}


def liczby_oplacone() -> dict[str, int]:
    """Liczby rekordow plikow, ktore MAMY I ZA KTORE ZAPLACONO.

    NIE to samo co `rekordy_z_manifestu()`. Tamta czyta `plan[]`, czyli
    OCZEKIWANIA z ostatniej wyceny — i wlasnie dlatego nie nadaje sie tutaj:
    **bieg zakupowy nadpisuje `plan[]` nowymi liczbami**, a zapis manifestu
    wykonuje sie takze po `break` (brak miejsca, blad pobierania, warunek 6).

    Skutek, gdyby zostawic tu `rekordy_z_manifestu()`: po PIERWSZYM biegu —
    choćby przerwanym — "oplacone" staje sie rowne biezacej wycenie, wiec piec
    starych plikow znow wypada z obu galezi `kompletny()`, a obrona przy
    `unlink()` porownuje z nowa liczba i nie zadziala. Obie ochrony gina
    dokladnie w biegu, w ktorym sa najbardziej potrzebne — wznowieniowym.
    Zarzut recenzji P2, potwierdzony w zrodle.

    Zrodla, w kolejnosci pierwszenstwa:

    1. `wyniki[]` z wpisami `kompletny: true` — to zapis pliku, ktory realnie
       pobrano i zweryfikowano. `przeniesione_wyniki()` przenosi te wpisy przez
       kolejne biegi, wiec przezywaja nadpisanie `plan[]`,
    2. `plan[]` — fallback na PIERWSZY bieg, zanim jakiekolwiek `wyniki`
       powstana,
    3. `data/manifest_d5c.json` dla `SESJA_D5C` — sledzony w repo i nietykany
       przez bieg zakupowy, wiec dla tej doby jest zrodlem najtwardszym.

    Bierzemy wylacznie wpisy `kompletny: true`. Wpis nieudanego pobrania niesie
    liczbe OCZEKIWANA, nie liczbe pliku na dysku — dopuszczenie go nic by nie
    zepsulo, ale "zaplacono za plik o tylu rekordach" ma znaczyc dokladnie to.
    """
    out: dict[str, int] = {}
    cel = sciezka_manifestu()
    if cel.exists():
        try:
            stary = json.loads(cel.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            stary = {}
        for w in stary.get("plan", []):
            if "rekordow" in w:
                out[w["sesja"]] = int(w["rekordow"])
        # `wyniki` NADPISUJE `plan` — opisuje plik, nie oczekiwanie.
        for w in stary.get("wyniki", []):
            if w.get("kompletny") and "rekordow" in w:
                out[w["sesja"]] = int(w["rekordow"])
    if KANONICZNY_D5C.exists():
        try:
            d5c = json.loads(KANONICZNY_D5C.read_text(encoding="utf-8"))
            if "rekordow_wg_metadata" in d5c:
                out[SESJA_D5C] = int(d5c["rekordow_wg_metadata"])
        except (json.JSONDecodeError, OSError):
            pass
    return out


def archiwizuj_manifest() -> Path | None:
    """Odklada kopie manifestu ze znacznikiem czasu. NIE nadpisuje niczego.

    Przyjecie nowych liczb rekordow kasuje jedyny zapis tego, za co juz
    zaplacono. Archiwum sprawia, ze decyzja jest odwracalna i zostawia slad.
    """
    cel = sciezka_manifestu()
    if not cel.exists():
        return None
    stempel = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    kopia = cel.with_name(f"{cel.stem}_przed_{stempel}{cel.suffix}")
    kopia.write_bytes(cel.read_bytes())
    return kopia


def sprawdz_dryf_rekordow(plan: list[dict], zapisane: dict[str, int],
                          akceptuj: bool = False) -> str:
    """WARUNEK 8 — dostawca nie moze zmienic danych w trakcie zakupu.

    DLACZEGO TO JEST ODMOWA, A NIE OSTRZEZENIE.

    `kompletny()` porownuje plik z liczba rekordow z BIEZACEJ wyceny. Jesli
    dostawca zrewiduje dane, kazdy JUZ OPLACONY plik zaczyna wygladac na
    niekompletny — i skrypt kupilby caly miesiac po raz drugi, nie mowiac
    o tym ani slowa. Zdarzylo sie realnie 08.08.2026: wszystkie 22 sesje
    urosly o 1,67-3,06% (mediana 2,66%) miedzy dwoma uruchomieniami,
    a laczna wycena z 78,6044 na 80,6729 USD.

    Kontynuowanie oznaczaloby tez zlozenie miesiaca z DWOCH WERSJI danych
    dostawcy — czesc plikow sprzed rewizji, czesc po. W danych nie widac tego
    w zaden sposob; wynik wygladalby normalnie.
    """
    rozne = [(w["sesja"], zapisane[w["sesja"]], w["rekordow"])
             for w in plan
             if w["sesja"] in zapisane and zapisane[w["sesja"]] != w["rekordow"]]
    if not rozne:
        return f"rekordy: zgodne z manifestem ({len(zapisane)} sesji)"

    linie = [f"    {s}: manifest {a:>12,} -> teraz {b:>12,} "
             f"({100 * (b - a) / a:+.2f}%)" for s, a, b in rozne[:8]]

    if akceptuj:
        # JAWNA, ODNOTOWANA DROGA PRZYJECIA NOWYCH LICZB. Bez niej jedynym
        # sposobem bylaby reczna edycja albo skasowanie manifestu — czyli
        # obejscie straznika poza protokolem, bez sladu i bez testu.
        kopia = archiwizuj_manifest()
        stara = sum(zapisane.get(w["sesja"], 0) for w in plan)
        nowa = sum(w["rekordow"] for w in plan)
        print(f"\n  AKCEPTACJA ROZJAZDU (--akceptuj-rozjazd) dla {len(rozne)} "
              f"z {len(plan)} sesji:")
        print("\n".join(linie), flush=True)
        print(f"  rekordow razem : {stara:,} -> {nowa:,} "
              f"({100 * (nowa - stara) / stara:+.2f}%)")
        print(f"  stary manifest : {kopia if kopia else 'brak — nie bylo czego archiwizowac'}")
        print("  Dopisz powod tej decyzji do data/KOSZTY.md — przyjecie nowych "
              "liczb zwykle oznacza ponowne naliczenie.", flush=True)
        return f"rozjazd PRZYJETY jawnie dla {len(rozne)} sesji"

    sys.exit(
        f"\nSTOP (warunek 8): dostawca zmienil dane {len(rozne)} z "
        f"{len(plan)} sesji.\n" + "\n".join(linie)
        + (f"\n    ... i {len(rozne) - 8} wiecej" if len(rozne) > 8 else "")
        + "\n\n  To NIE jest uszkodzenie Twoich plikow — one zgadzaja sie"
          "\n  z liczbami, za ktore zaplacono. Zmienily sie METADANE po stronie"
          "\n  Databento, wiec kazdy oplacony plik wyglada teraz na niekompletny."
          "\n\n  Bez tej odmowy skrypt kupilby caly miesiac PO RAZ DRUGI."
          "\n  Nie kupuj, dopoki nie wiadomo, co dostawca zmienil:"
          "\n  patrz docs/D5_DRYF_METADANYCH.md.")


def sprawdz_sha_d5c(p: Path) -> str:
    """Kontrola MOCNIEJSZA niz liczba rekordow.

    Zgodna liczba rekordow mowi tylko, ze plik ma tyle rekordow, ile trzeba.
    SHA-256 mowi, ze to jest DOKLADNIE ten plik, na ktorym policzono audyt
    Etapu 3 — 842 757 zdarzen, 0 niewyjasnionych. Bez tego moglibysmy liczyc
    miesiac na pliku o poprawnej dlugosci i innej zawartosci.
    """
    if not KANONICZNY_D5C.exists():
        return "SHA: brak manifestu kanonicznego — pomijam"
    oczekiwany = json.loads(KANONICZNY_D5C.read_text(encoding="utf-8")).get("sha256")
    if not oczekiwany:
        return "SHA: manifest kanoniczny bez pola sha256 — pomijam"
    faktyczny = sha_pliku(p)
    if faktyczny != oczekiwany:
        sys.exit(f"\nSTOP (warunek 7): {SESJA_D5C} ma SHA-256 inny niz kanoniczny.\n"
                 f"  plik      : {p}\n  faktyczny : {faktyczny}\n"
                 f"  kanoniczny: {oczekiwany}\n"
                 "Liczba rekordow sie zgadza, ale to NIE jest ten plik, na "
                 "ktorym policzono audyt D5-C. Nie licz na nim miesiaca.")
    return f"SHA: zgodny z {KANONICZNY_D5C}"


def przeniesione_wyniki(pomijane: list[str]) -> list[dict]:
    """Wpisy z POPRZEDNIEGO manifestu dla sesji, ktorych ten bieg nie pobiera.

    Bez tego manifest opisuje wylacznie biezacy bieg, a `kompletnych_przed`
    to gole daty. Nastepny bieg zakupowy — a taki bedzie, bo zostalo 17 sesji —
    nadpisalby manifest tak, ze `sha256`, `pobrano_utc` i `normalizacja` PIECIU
    sesji ze starej normalizacji zniknelyby z aktywnego pliku. Zostalyby tylko
    w kopii archiwalnej, czyli tam, gdzie nikt ich nie szuka.

    To nie jest hipotetyczne: starej normalizacji **nie da sie juz pobrac**
    (Databento, 11.08), a obu wersji nie widac w danych. Znacznik w manifescie
    jest jedynym nosnikiem tej informacji — musi wiec przezyc nadpisanie.

    BACKFILL: wpisy sprzed wprowadzenia pola `normalizacja` dostaja je
    wyliczone z wlasnego `pobrano_utc`, a gdy i tego brak — z `pobrano_utc`
    calego manifestu. Gdy brak obu, zostaje "NIEUSTALONA"; nie zgadujemy.
    """
    cel = sciezka_manifestu()
    if not cel.exists():
        return []
    try:
        stary = json.loads(cel.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    manifest_utc = stary.get("pobrano_utc")
    szukane = set(pomijane)
    out: list[dict] = []
    for w in stary.get("wyniki", []):
        if w.get("sesja") not in szukane:
            continue
        w = dict(w)
        if not w.get("normalizacja"):
            znacznik = w.get("pobrano_utc") or manifest_utc
            try:
                w["normalizacja"] = epoka_normalizacji(
                    dt.datetime.fromisoformat(znacznik))
                w.setdefault("pobrano_utc", znacznik)
            except (TypeError, ValueError):
                w["normalizacja"] = "NIEUSTALONA"
        w["z_poprzedniego_biegu"] = True
        out.append(w)
    return out


def epoka_normalizacji(kiedy: dt.datetime) -> str:
    """W ktorej wersji normalizacji GLBX.MDP3 jest plik pobrany o `kiedy`.

    Po co to w ogole istnieje: dwie wersje serwowania roznia sie rekordami
    `action=N` w zdarzeniach wielopakietowych, ale **w danych nie widac, ktora
    to wersja** — plik nie niesie tej informacji. Dostawca potwierdzil przy tym,
    ze starej wersji nie da sie juz pobrac. Znacznik w manifescie jest wiec
    jedynym sposobem, zeby ktokolwiek pozniej wiedzial, co ma na dysku.

    Zwraca NIEUSTALONA dla znacznikow w przedziale przelomu. To nie jest
    ostroznosc na wyrost: zgadniecie tutaj daje plik opisany jako jednorodny,
    ktory jednorodny nie jest, a blad wyjdzie dopiero w wynikach badania.
    """
    if kiedy <= NORMALIZACJA_OSTATNIA_STARA:
        return "przed-2026-08-08"
    if kiedy >= NORMALIZACJA_PIERWSZA_NOWA:
        return "po-2026-08-08"
    return "NIEUSTALONA"


def kompletny(p: Path, oczekiwane: int,
              oplacone: int | None = None) -> tuple[bool, str]:
    """Czy plik jest kompletny. ISTNIENIE NIE WYSTARCZA.

    Ta regula powstala po tym, jak przerwany transfer zostawil obcieta sesje,
    ktora parsowala sie BEZ BLEDU. Sprawdzamy: obecnosc, niezerowy rozmiar,
    parsowalnosc i zgodnosc liczby rekordow z `metadata.get_record_count`.

    `oplacone` — liczba rekordow ZAPISANA W MANIFESCIE, czyli to, za co juz
    zaplacono. Plik zgodny z ta liczba jest **kompletny w swojej epoce
    normalizacji** i NIE WOLNO go ani kupowac ponownie, ani kasowac.

    PO CO TEN DRUGI PARAMETR — sytuacja, ktora bez niego konczy sie utrata
    danych i podwojna platnoscia. Databento zmienilo 08.08.2026 normalizacje
    GLBX.MDP3: te same zapytania zwracaja dzis WIECEJ rekordow, a starej wersji
    **nie da sie juz pobrac**. Nasze piec plikow zgadza sie z liczbami sprzed
    zmiany. Gdyby porownywac je wylacznie z biezaca wycena, kazdy wygladalby
    na niekompletny, wiec skrypt kasowalby je (`out.unlink()`) i kupowal
    ponownie — niszczac jedyny istniejacy egzemplarz starej normalizacji
    i placac drugi raz za to, co juz mamy.
    """
    if not p.exists():
        return False, "brak pliku"
    if p.stat().st_size == 0:
        return False, "plik pusty"
    try:
        n = sum(1 for _ in db.DBNStore.from_file(p))
    except Exception as e:                                    # noqa: BLE001
        return False, f"nie parsuje sie: {type(e).__name__}"
    if n == oczekiwane:
        return True, "kompletny"
    if oplacone is not None and n == oplacone:
        return True, (f"kompletny wg manifestu ({n:,} rek.) — plik ze STAREJ "
                      "normalizacji, oplacony i nieodtwarzalny")
    return False, f"rekordow {n:,} != oczekiwanych {oczekiwane:,}"


def main() -> int:
    p = argparse.ArgumentParser(description="Zakup 22 sesji MBO dla D5-B2")
    p.add_argument("--wycena", action="store_true", help="tylko wycena")
    p.add_argument("--kup-ponownie-d5c", action="store_true",
                   help=f"pozwol kupic {SESJA_D5C} TRZECI raz (warunek 4)")
    p.add_argument("--akceptuj-rozjazd", action="store_true",
                   help="przyjmij nowe liczby rekordow mimo rozjazdu "
                        "z manifestem (warunek 8); archiwizuje stary manifest")
    args = p.parse_args()

    if args.wycena and args.akceptuj_rozjazd:
        # Archiwizacja manifestu w trybie, ktory niczego nie kupuje, jest bez
        # celu — a zostawia w katalogu kopie sugerujaca, ze decyzja zapadla.
        sys.exit("STOP: --akceptuj-rozjazd nie ma sensu z --wycena. Tryb wyceny "
                 "niczego nie kupuje, a flaga zarchiwizowalaby manifest bez "
                 "powodu, zostawiajac slad nieistniejacej decyzji.")

    c = db.Historical(os.environ["DATABENTO_API_KEY"])
    kat = raw_dir(KATALOG)
    kat.mkdir(parents=True, exist_ok=True)

    wolne_start = wolne_gb(kat)
    print(f"katalog : {kat}")
    print(f"wolne   : {wolne_start:.1f} GB (wymagane min. {MIN_WOLNE_GB})\n")
    if wolne_start < MIN_WOLNE_GB:
        sys.exit(f"STOP (warunek 1): {wolne_start:.1f} GB < {MIN_WOLNE_GB} GB "
                 "wymaganego minimum wolnego miejsca.")

    # ---------------------------------------------------------- wycena ----
    print("Wycena 22 sesji (metadane darmowe, dzielone na kawalki)...\n",
          flush=True)
    cache = wczytaj_cache()
    if cache:
        print(f"  (cache wyceny: {len(cache)} sesji mlodszych niz "
              f"{WAZNOSC_WYCENY_H} h — nie odpytuje ich ponownie)\n", flush=True)
    z_cache = 0

    plan = []
    suma = 0.0          # suma DOKLADNA, przed zaokragleniem pozycji
    for s in SESJE:
        a, b = okno(s)
        wpis = cache.get(klucz_wyceny(a, b))
        if wpis is not None:
            k, n = float(wpis["koszt"]), int(wpis["rekordow"])
            z_cache += 1
            print(f"  {s}  {k:7.4f} USD  {n:>12,} rek.  "
                  f"[cache {wpis['wiek_h']:.1f} h]", flush=True)
        else:
            bez = {k2: v for k2, v in ZAPYTANIE.items()}
            k = metadane_dzielone(c.metadata.get_cost, start=a, end=b,
                                  opis=f"koszt {s}",
                                  odstepy=ODSTEPY_DLUGIE, **bez)
            n = int(metadane_dzielone(c.metadata.get_record_count,
                                      start=a, end=b, opis=f"rekordy {s}",
                                      odstepy=ODSTEPY_DLUGIE, **bez))
            cache[klucz_wyceny(a, b)] = {
                "koszt": k, "rekordow": n,
                "utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds")}
            # Zapis po KAZDEJ sesji, nie na koncu. Awaria na 6. kawalku
            # pierwszej sesji skasowala kiedys cala wycene 22 sesji.
            zapisz_cache(cache)
            print(f"  {s}  {k:7.4f} USD  {n:>12,} rek.", flush=True)
        plan.append(dict(sesja=s, start_utc=a, end_utc=b,
                         koszt_usd=round(k, 4), koszt_dokladny=k, rekordow=n))
        suma += k

    print(f"\nRAZEM 22 sesje: {suma:.4f} USD   (limit {LIMIT_USD:.2f})")
    if z_cache:
        print(f"  z tego {z_cache} sesji z cache (maks. {WAZNOSC_WYCENY_H} h), "
              f"{len(SESJE) - z_cache} wycenionych teraz")
    if suma > LIMIT_USD:
        sys.exit(f"STOP (warunek 2): {suma:.4f} > {LIMIT_USD:.2f} USD — zakup "
                 "NIEWYKONANY. Zakresu ani listy sesji NIE skracamy "
                 "(specyfikacja zamrozona).")

    print(sprawdz_manifest(plan))
    print(sprawdz_dryf_rekordow(plan, rekordy_z_manifestu(),
                                akceptuj=args.akceptuj_rozjazd))

    # ------------------------------------------------ stan przed zakupem --
    # Liczby rekordow, za ktore JUZ ZAPLACONO. Plik zgodny z ta liczba jest
    # kompletny w swojej epoce normalizacji — patrz `kompletny()`.
    # NIE `rekordy_z_manifestu()`: tamta czyta `plan[]`, ktory bieg zakupowy
    # nadpisuje nowymi liczbami, wiec ochrona ginelaby przy wznowieniu.
    oplacone = liczby_oplacone()

    juz_mamy, do_pobrania, koszt_do_zaplaty = [], [], 0.0
    for w in plan:
        p = sciezka_istniejaca(w["sesja"])
        ok, powod = kompletny(p, w["rekordow"], oplacone.get(w["sesja"]))
        if ok:
            juz_mamy.append(w["sesja"])
            komunikat = f"  MAM {w['sesja']}: {powod} ({p.parent.name})"
            if w["sesja"] == SESJA_D5C:
                komunikat += f"; {sprawdz_sha_d5c(p)}"
            print(f"{komunikat} — pomijam, oszczednosc {w['koszt_usd']:.4f} USD")
        else:
            do_pobrania.append(w)
            # Sumujemy wartosci DOKLADNE, nie zaokraglone pozycje. Suma 21
            # zaokragleń rozni sie tu od prawdy o 0,0001 USD — bez znaczenia
            # dla kwoty, ale liczba w naglowku ma byc ta sama, ktora rozliczy
            # dostawca, a nie ta, ktora wyszla z formatowania wydruku.
            koszt_do_zaplaty += w["koszt_dokladny"]
            if p.exists():
                print(f"  UWAGA {w['sesja']}: plik istnieje, ale {powod}")

    print(f"\nkompletnych juz na dysku : {len(juz_mamy)}")
    print(f"do pobrania              : {len(do_pobrania)}")
    print(f"koszt do zaplaty teraz   : {koszt_do_zaplaty:.4f} USD")

    sprawdz_sesje_d5c(do_pobrania, args.kup_ponownie_d5c)

    if args.wycena:
        print("\nTryb wyceny — nic nie pobrano.")
        return 0
    if not do_pobrania:
        print("\nWszystkie sesje kompletne — nie ma czego pobierac.")
        return 0

    # ---------------------------------------------------------- zakup ----
    print("\n" + "=" * 64, flush=True)
    wyniki = []
    for i, w in enumerate(do_pobrania, start=1):
        s = w["sesja"]
        out = sciezka_docelowa(s)

        wolne = wolne_gb(kat)
        if wolne < REZERWA_GB:
            print(f"\nSTOP (warunek 5): wolne miejsce {wolne:.1f} GB < "
                  f"rezerwy {REZERWA_GB} GB. Przerwano PRZED sesja {s}.")
            break

        # Plik niekompletny usuwamy dopiero tutaj, swiadomie i z komunikatem.
        if out.exists():
            # DRUGA LINIA OBRONY. Po poprawce w `kompletny()` plik zgodny
            # z manifestem nie powinien tu w ogole trafic — ale kasowanie jest
            # NIEODWRACALNE, a starej normalizacji nie da sie odtworzyc za
            # zadna cene. Wolimy przerwac zakup niz skasowac jedyny egzemplarz.
            ile = sum(1 for _ in db.DBNStore.from_file(out))
            if ile == oplacone.get(s):
                sys.exit(
                    f"\nSTOP: {s} ma {ile:,} rekordow — dokladnie tyle, za ile "
                    "juz ZAPLACONO (manifest).\n"
                    "  Ten plik jest kompletny w swojej epoce normalizacji "
                    "i NIE WOLNO go skasowac:\n"
                    "  starej normalizacji GLBX.MDP3 nie da sie juz pobrac.\n"
                    "  Zatrzymuje zakup — to blad logiki kwalifikacji, "
                    "nie stan danych.")
            print(f"  {s}: usuwam niekompletny plik przed ponownym pobraniem",
                  flush=True)
            out.unlink()

        print(f"[{i}/{len(do_pobrania)}] {s}  pobieranie "
              f"({w['koszt_usd']:.4f} USD)...", flush=True)
        try:
            c.timeseries.get_range(**ZAPYTANIE, start=w["start_utc"],
                                   end=w["end_utc"], path=str(out))
        except Exception as e:                                # noqa: BLE001
            # ZADNEGO AUTOMATYCZNEGO PONOWIENIA — pobieranie jest platne.
            print(f"\nBLAD podczas pobierania {s}: {type(e).__name__}: {e}")
            print(f"  plik istnieje: {out.exists()}"
                  + (f", rozmiar {out.stat().st_size / 1e6:.1f} MB"
                     if out.exists() else ""))
            print("\n  NIE ponawiam automatycznie. Sprawdz stan pliku, a potem")
            print("  uruchom skrypt ponownie — sesje kompletne zostana pominiete")
            print("  bez kosztu, a ta bedzie pobrana raz jeszcze.")
            break

        raw = out.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        bajtow = len(raw)
        del raw

        ok, powod = kompletny(out, w["rekordow"])
        teraz = dt.datetime.now(dt.UTC)
        wyniki.append(dict(**w, plik=out.name, sciezka=str(out),
                           bajtow=bajtow, sha256=sha, kompletny=ok,
                           status=powod,
                           pobrano_utc=teraz.isoformat(timespec="seconds"),
                           normalizacja=epoka_normalizacji(teraz)))
        print(f"      {bajtow / 1e9:.3f} GB  {'OK' if ok else 'NIEKOMPLETNY'}"
              f"  {sha[:16]}...", flush=True)
        if not ok:
            print(f"\nSTOP (warunek 6): {s} niekompletny po pobraniu "
                  f"({powod}). Nie kontynuuje — sprawdz zanim wydasz wiecej.")
            break

    # -------------------------------------------------------- manifest ----
    cel = sciezka_manifestu()
    cel.parent.mkdir(parents=True, exist_ok=True)
    cel.write_text(json.dumps(dict(
        etap="D5-B2", zapytanie=ZAPYTANIE,
        rth="09:30-16:00 America/New_York (UTC wyprowadzone ze strefy)",
        limit_usd=LIMIT_USD, wycena_22_sesji_usd=round(suma, 4),
        sesji_planowanych=len(SESJE),
        kompletnych_przed=juz_mamy,
        pobranych_teraz=[w["sesja"] for w in wyniki if w["kompletny"]],
        plan=plan, wyniki=przeniesione_wyniki(juz_mamy) + wyniki,
        wolne_gb_przed=round(wolne_start, 2),
        wolne_gb_po=round(wolne_gb(kat), 2),
        pobrano_utc=dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        normalizacja=epoka_normalizacji(dt.datetime.now(dt.UTC)),
        databento=db.__version__,
    ), indent=1), encoding="utf-8", newline="\n")

    udane = sum(1 for w in wyniki if w["kompletny"])
    print("\n" + "=" * 64)
    print(f"  pobrano kompletnych : {udane} z {len(do_pobrania)}")
    # `koszt_dokladny`, nie `koszt_usd` — ta sama podstawa co naglowek
    # `koszt do zaplaty teraz`. Dwie sumy tej samej rzeczy roznily sie
    # o 0,0001 USD tylko dlatego, ze jedna sumowala pozycje zaokraglone.
    print(f"  wydano teraz        : "
          f"{sum(w['koszt_dokladny'] for w in wyniki if w['kompletny']):.4f} USD")
    print(f"  wolne po            : {wolne_gb(kat):.1f} GB")
    print(f"-> {cel}")
    return 0 if udane == len(do_pobrania) else 1


if __name__ == "__main__":
    raise SystemExit(main())
