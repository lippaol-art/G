#!/usr/bin/env python3
"""Zakup jednodniowej probki `mbo` — D5-C. Specyfikacja: docs/D5_ETAP3_SPEC.md.

Sesja 2026-07-30, MNQU6, RTH 09:30-16:00 America/New_York.

TRZY ZABEZPIECZENIA, KAZDE Z POWODU:

1. PONOWNA WYCENA BEZPOSREDNIO PRZED POBRANIEM. Limit dotyczy kwoty zmierzonej
   teraz, nie zapisanej wczoraj. Moje ekstrapolacje kosztu mylily sie w tym
   projekcie dwukrotnie — o 21% i o 40%.

2. KONTROLA WOLNEGO MIEJSCA PRZED I PO. Przerwany transfer na pelnym dysku
   zostawia obcieta sesje, ktora parsuje sie bez bledu. Awaryjne zatrzymanie
   przy zapasie ponizej REZERWA_GB.

3. PLIK NIE JEST USUWANY PRZED ZAPISANIEM MANIFESTU. Hash i liczba rekordow
   powstaja zanim cokolwiek moze plik ruszyc.

Uruchomienie:
    python3 scripts/fetch_d5c.py --wycena   # sama wycena, bez zakupu
    python3 scripts/fetch_d5c.py            # wycena + zakup
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

SESJA = "2026-07-30"
ZAPYTANIE = dict(dataset="GLBX.MDP3", symbols=["MNQU6"],
                 stype_in="raw_symbol", schema="mbo")

#: Zamrozony w `docs/D5_ETAP3_SPEC.md` przed zakupem.
LIMIT_USD = 4.00
#: Awaryjne zatrzymanie: ponizej tego zapasu nie zaczynamy i nie kontynuujemy.
REZERWA_GB = 8.0

#: Manifest PIERWOTNEGO zakupu — sledzony przez golden baseline, NIETYKALNY.
KANONICZNY = Path("data/manifest_d5c.json")


def sciezka_manifestu_lokalnego() -> Path:
    """Manifest ponownego pobrania — POZA repozytorium.

    Trafia pod `PROJECT_G_DATA_ROOT`, zeby lokalny smoke test nie ruszal
    `hash_danych`. Gdy zmiennej nie ma, ladujemy obok danych surowych, i tak
    objetych `.gitignore`.
    """
    return raw_dir().parent / "manifests" / "manifest_d5c_local.json"


def okno() -> tuple[str, str]:
    """RTH WYPROWADZONE ZE STREFY ET — nigdy ze stalej UTC."""
    y, m, d = map(int, SESJA.split("-"))
    a = dt.datetime(y, m, d, 9, 30, tzinfo=ET).astimezone(UTC)
    b = dt.datetime(y, m, d, 16, 0, tzinfo=ET).astimezone(UTC)
    return a.strftime("%Y-%m-%dT%H:%M"), b.strftime("%Y-%m-%dT%H:%M")


def main() -> int:
    p = argparse.ArgumentParser(description="Zakup probki MBO dla D5-C")
    p.add_argument("--wycena", action="store_true", help="tylko wycena")
    args = p.parse_args()

    c = db.Historical(os.environ["DATABENTO_API_KEY"])
    a, b = okno()
    q = dict(**ZAPYTANIE, start=a, end=b)

    # ZAPYTANIA DZIELONE, NIE POJEDYNCZE. Dla MBO pytanie o cala sesje RTH
    # (38,3 mln rekordow) trwa 54-60 s przy 60-sekundowym limicie bramy —
    # to loteria, nie awaria przejsciowa. Podzial na kawalki po 30 min daje
    # czasy 2,5-37 s, a suma jest zweryfikowana empirycznie co do rekordu
    # i co do czwartego miejsca po przecinku. Szczegoly: engine/databento_io.py.
    bez_czasu = {k: v for k, v in q.items() if k not in ("start", "end")}
    koszt = metadane_dzielone(c.metadata.get_cost, start=a, end=b,
                              opis="koszt", **bez_czasu)
    rekordow = int(metadane_dzielone(c.metadata.get_record_count, start=a, end=b,
                                     opis="rekordy", **bez_czasu))
    rozmiar = int(metadane_dzielone(c.metadata.get_billable_size, start=a, end=b,
                                    opis="rozmiar", **bez_czasu))
    print(f"okno UTC : {a} .. {b}")
    print(f"koszt    : {koszt:.4f} USD  (limit {LIMIT_USD:.2f})")
    print(f"rekordow : {rekordow:,}")
    print(f"rozmiar  : {rozmiar / 1e9:.3f} GB rozliczeniowo", flush=True)

    if koszt > LIMIT_USD:
        sys.exit(f"STOP: {koszt:.4f} > {LIMIT_USD:.2f} USD — zakup NIEWYKONANY. "
                 "Okna ani dnia NIE skracamy (specyfikacja zamrozona).")

    kat = raw_dir("d5c_mbo")
    wolne_przed = wolne_gb(kat)
    print(f"wolne    : {wolne_przed:.1f} GB w {kat}", flush=True)
    # Zapas liczony po rozmiarze ROZLICZENIOWYM, ktory jest gorna granica —
    # plik `.dbn.zst` bedzie mniejszy, wiec kontrola jest konserwatywna.
    if wolne_przed - rozmiar / 1e9 < REZERWA_GB:
        sys.exit(f"STOP: po pobraniu zostaloby < {REZERWA_GB} GB. "
                 "Przenies etap na dysk lokalny (PROJECT_G_DATA_ROOT).")

    if args.wycena:
        print("\nTryb wyceny — nic nie pobrano.")
        return 0

    kat.mkdir(parents=True, exist_ok=True)
    out = kat / f"mnq_mbo_rth_{SESJA}.dbn.zst"
    if out.exists():
        sys.exit(f"STOP: {out} juz istnieje — usun swiadomie albo zmien nazwe.")

    print("\npobieranie...", flush=True)
    c.timeseries.get_range(**q, path=str(out))

    raw = out.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    bajtow = len(raw)
    del raw   # nie trzymamy 2 GB w pamieci dluzej niz na policzenie hasha

    manifest = dict(
        etap="D5-C", sesja=SESJA, zapytanie=ZAPYTANIE,
        rth="09:30-16:00 America/New_York (UTC wyprowadzone ze strefy)",
        start_utc=a, end_utc=b,
        limit_usd=LIMIT_USD,
        koszt_usd=round(koszt, 4),
        rekordow_wg_metadata=rekordow,
        rozmiar_rozliczeniowy_b=rozmiar,
        plik=out.name,
        sciezka=str(out),
        bajtow_na_dysku=bajtow,
        sha256=sha,
        wolne_gb_przed=round(wolne_przed, 2),
        wolne_gb_po=round(wolne_gb(kat), 2),
        pobrano_utc=dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        databento=db.__version__,
    )

    # MANIFEST KANONICZNY JEST NIETYKALNY.
    # `data/manifest_d5c.json` dokumentuje PIERWOTNY zakup i jest sledzony
    # przez golden baseline. Nadpisanie go lokalna sciezka Windows, nowa data
    # pobrania i nowym stanem wolnego miejsca ruszyloby `hash_danych` mimo
    # BAJTOWO IDENTYCZNYCH danych — dokladnie ta klasa falszywej roznicy,
    # ktora juz raz zatrzymala bramke (konwersja koncow linii na Windows).
    if KANONICZNY.exists():
        odniesienie = json.loads(KANONICZNY.read_text(encoding="utf-8"))
        zgodny = odniesienie.get("sha256") == sha
        cel = sciezka_manifestu_lokalnego()
        cel.parent.mkdir(parents=True, exist_ok=True)
        manifest["ponowne_pobranie"] = True
        manifest["sha256_kanoniczny"] = odniesienie.get("sha256")
        manifest["zgodny_z_kanonicznym"] = zgodny
        cel.write_text(json.dumps(manifest, indent=1), encoding="utf-8", newline="\n")
        gdzie = cel
    else:
        KANONICZNY.write_text(json.dumps(manifest, indent=1), encoding="utf-8", newline="\n")
        zgodny = True
        gdzie = KANONICZNY

    print(f"\n-> {out}  ({bajtow / 1e9:.3f} GB na dysku)")
    print(f"   SHA-256 : {sha}")
    print(f"   koszt   : {manifest['koszt_usd']} USD")
    print(f"   wolne po: {manifest['wolne_gb_po']:.1f} GB")
    print(f"-> {gdzie}")

    if KANONICZNY.exists() and not zgodny:
        print(f"\n   SHA-256 kanoniczny: {manifest['sha256_kanoniczny']}")
        sys.exit("STOP: pobrany plik ROZNI SIE od zapisanego w manifescie "
                 "kanonicznym. Nie uzywaj go do odtworzenia D5-C, dopoki "
                 "roznica nie zostanie wyjasniona.")
    if KANONICZNY.exists():
        print("   zgodny z manifestem kanonicznym: TAK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
