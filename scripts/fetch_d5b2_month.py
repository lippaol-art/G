#!/usr/bin/env python3
"""Zakup 22 sesji RTH `mbo` — D5-B2. Specyfikacja: docs/D5_ETAP4_SPEC.md.

DZIEN PO DNIU, ZE WZNOWIENIEM, DO `PROJECT_G_DATA_ROOT`.

SIEDEM WARUNKOW ODMOWY. Skrypt PRZERYWA, gdy:
  1. suma wycen przekroczy `LIMIT_USD`,
  2. zabraknie miejsca na dysku,
  3. wolne miejsce spadnie ponizej rezerwy w trakcie,
  4. istniejacy plik nie przejdzie kontroli kompletnosci,
  5. zakres zapytania rozni sie od zapisanego w manifescie,
  6. parser zglosi brak oczekiwanych rekordow,
  7. sesja 2026-07-30 mialaby zostac kupiona ponownie.

CZEGO NIE ROBI — I TO JEST CELOWE.
Nie ponawia pobierania po bledzie 504. Pobieranie jest PLATNE i tworzy plik;
slepe ponowienie grozi podwojnym naliczeniem i cichym zostawieniem obcietej
sesji, ktora parsuje sie bez bledu. Po awarii skrypt konczy prace, wypisuje
stan i zostawia decyzje czlowiekowi. Wznowienie to ponowne uruchomienie —
sesje juz kompletne zostana pominiete bez kosztu.

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

from engine.databento_io import metadane_dzielone  # noqa: E402
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
#: Warunek 4 z listy zgody: minimum wolnego miejsca na starcie.
MIN_WOLNE_GB = 100.0

KATALOG = "d5b2_mbo"
#: Sesja kupiona wczesniej w ramach D5-C — lezy W INNYM KATALOGU, pod ta sama
#: nazwa pliku. Bez tego wpisu skrypt jej nie widzi i proponuje zakup 22 sesji
#: zamiast 21, czyli TRZECIE naliczenie tej samej doby (3,5961 USD).
#: Wykryte przy wycenie, zanim cokolwiek kupiono.
KATALOG_D5C = "d5c_mbo"
MANIFEST = "manifest_d5b2.json"


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


def kompletny(p: Path, oczekiwane: int) -> tuple[bool, str]:
    """Czy plik jest kompletny. ISTNIENIE NIE WYSTARCZA.

    Ta regula powstala po tym, jak przerwany transfer zostawil obcieta sesje,
    ktora parsowala sie BEZ BLEDU. Sprawdzamy: obecnosc, niezerowy rozmiar,
    parsowalnosc i zgodnosc liczby rekordow z `metadata.get_record_count`.
    """
    if not p.exists():
        return False, "brak pliku"
    if p.stat().st_size == 0:
        return False, "plik pusty"
    try:
        n = sum(1 for _ in db.DBNStore.from_file(p))
    except Exception as e:                                    # noqa: BLE001
        return False, f"nie parsuje sie: {type(e).__name__}"
    if n != oczekiwane:
        return False, f"rekordow {n:,} != oczekiwanych {oczekiwane:,}"
    return True, "kompletny"


def main() -> int:
    p = argparse.ArgumentParser(description="Zakup 22 sesji MBO dla D5-B2")
    p.add_argument("--wycena", action="store_true", help="tylko wycena")
    args = p.parse_args()

    c = db.Historical(os.environ["DATABENTO_API_KEY"])
    kat = raw_dir(KATALOG)
    kat.mkdir(parents=True, exist_ok=True)

    wolne_start = wolne_gb(kat)
    print(f"katalog : {kat}")
    print(f"wolne   : {wolne_start:.1f} GB (wymagane min. {MIN_WOLNE_GB})\n")
    if wolne_start < MIN_WOLNE_GB:
        sys.exit(f"STOP: {wolne_start:.1f} GB < {MIN_WOLNE_GB} GB wymaganego "
                 "minimum. Warunek 4 zgody na zakup niespelniony.")

    # ---------------------------------------------------------- wycena ----
    print("Wycena 22 sesji (metadane darmowe, dzielone na kawalki)...\n",
          flush=True)
    plan = []
    suma = 0.0
    for s in SESJE:
        a, b = okno(s)
        bez = {k: v for k, v in ZAPYTANIE.items()}
        k = metadane_dzielone(c.metadata.get_cost, start=a, end=b,
                              opis=f"koszt {s}", **bez)
        n = int(metadane_dzielone(c.metadata.get_record_count, start=a, end=b,
                                  opis=f"rekordy {s}", **bez))
        plan.append(dict(sesja=s, start_utc=a, end_utc=b,
                         koszt_usd=round(k, 4), rekordow=n))
        suma += k
        print(f"  {s}  {k:7.4f} USD  {n:>12,} rek.", flush=True)

    print(f"\nRAZEM 22 sesje: {suma:.4f} USD   (limit {LIMIT_USD:.2f})")
    if suma > LIMIT_USD:
        sys.exit(f"STOP: {suma:.4f} > {LIMIT_USD:.2f} USD — zakup NIEWYKONANY. "
                 "Zakresu ani listy sesji NIE skracamy (specyfikacja zamrozona).")

    # ------------------------------------------------ stan przed zakupem --
    juz_mamy, do_pobrania, koszt_do_zaplaty = [], [], 0.0
    for w in plan:
        p = sciezka_istniejaca(w["sesja"])
        ok, powod = kompletny(p, w["rekordow"])
        if ok:
            juz_mamy.append(w["sesja"])
            print(f"  MAM {w['sesja']}: {powod} ({p.parent.name}) — pomijam, "
                  f"oszczednosc {w['koszt_usd']:.4f} USD")
        else:
            do_pobrania.append(w)
            koszt_do_zaplaty += w["koszt_usd"]
            if p.exists():
                print(f"  UWAGA {w['sesja']}: plik istnieje, ale {powod}")

    print(f"\nkompletnych juz na dysku : {len(juz_mamy)}")
    print(f"do pobrania              : {len(do_pobrania)}")
    print(f"koszt do zaplaty teraz   : {koszt_do_zaplaty:.4f} USD")

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
            print(f"\nSTOP: wolne miejsce {wolne:.1f} GB < rezerwy "
                  f"{REZERWA_GB} GB. Przerwano PRZED sesja {s}.")
            break

        # Plik niekompletny usuwamy dopiero tutaj, swiadomie i z komunikatem.
        if out.exists():
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
        wyniki.append(dict(**w, plik=out.name, sciezka=str(out),
                           bajtow=bajtow, sha256=sha, kompletny=ok,
                           status=powod))
        print(f"      {bajtow / 1e9:.3f} GB  {'OK' if ok else 'NIEKOMPLETNY'}"
              f"  {sha[:16]}...", flush=True)
        if not ok:
            print(f"\nSTOP: {s} niekompletny po pobraniu ({powod}). "
                  "Nie kontynuuje — sprawdz zanim wydasz wiecej.")
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
        plan=plan, wyniki=wyniki,
        wolne_gb_przed=round(wolne_start, 2),
        wolne_gb_po=round(wolne_gb(kat), 2),
        pobrano_utc=dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        databento=db.__version__,
    ), indent=1), encoding="utf-8", newline="\n")

    udane = sum(1 for w in wyniki if w["kompletny"])
    print("\n" + "=" * 64)
    print(f"  pobrano kompletnych : {udane} z {len(do_pobrania)}")
    print(f"  wydano teraz        : "
          f"{sum(w['koszt_usd'] for w in wyniki if w['kompletny']):.4f} USD")
    print(f"  wolne po            : {wolne_gb(kat):.1f} GB")
    print(f"-> {cel}")
    return 0 if udane == len(do_pobrania) else 1


if __name__ == "__main__":
    raise SystemExit(main())
