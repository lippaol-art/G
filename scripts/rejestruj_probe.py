#!/usr/bin/env python3
"""Rejestracja proby w globalnym liczniku — PLAN.pdf rozdz. 6.5.

PO CO OPRZYRZADOWANIE DO PLIKU, KTORY MA SZESC POL.

`validation/trial_counter.json` jest najbardziej konsekwencjonalnym artefaktem
projektu: wchodzi wprost do mianownika DSR. Zawyzenie licznika obniza wlasny
werdykt niepotrzebnie; ZANIZENIE certyfikuje strategie, ktora na certyfikat nie
zasluguje — i tego drugiego bledu nie widac w zadnym wyniku. Dopoki licznik
wynosi 0, recznie edytowany JSON jest bezpieczny. Od proby nr 1 przestaje byc,
bo kazda kolejna edycja odbywa sie pod presja wyniku, ktory wlasnie zobaczylismy.

Ten skrypt zamienia dyscypline w mechanizm, ZANIM padnie pierwsza proba.

CZTERY ODMOWY. Skrypt PRZERYWA, gdy:
  1. drzewo robocze jest brudne — zapisany SHA nie identyfikowalby wtedy kodu,
     ktory da sie wynik odtworzyc; byloby to odniesienie do stanu, ktorego
     nie ma w historii,
  2. `--sr-dzienny` wyglada na SR ROCZNY (patrz `PROG_SR_DZIENNY`),
  3. karta przekroczylaby limit 10 wariantow,
  4. partia przekroczylaby limit 40 wariantow.

Uruchomienie:
    python3 scripts/rejestruj_probe.py --karta H017 --sr-dzienny 0.031 \
        --opis "wariant bazowy, prog 0.6" --raport reports/H017_proba1.md
    python3 scripts/rejestruj_probe.py --karta B06 --sr-dzienny 0.010 \
        --opis "benchmark z literatury" --benchmark      # NIE zuzywa proby
    python3 scripts/rejestruj_probe.py --pokaz                # sam stan
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

KORZEN = Path(__file__).resolve().parent.parent
LICZNIK = KORZEN / "validation" / "trial_counter.json"

#: SR DZIENNY, nie roczny — najczestszy blad implementacji DSR (poprawka A2-4
#: z audytu 2). SR dzienny 0.5 to po annualizacji ~7.9, czyli wartosc, ktorej
#: nie ma na tym rynku. Taka liczba prawie na pewno oznacza, ze ktos wstawil
#: SR roczny, a wtedy sigma_SR wg FST liczy sie z zupelnie zlej skali.
PROG_SR_DZIENNY = 0.5


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(KORZEN), *args],
                          capture_output=True, text=True, check=True).stdout.strip()


def stan_drzewa() -> str:
    """Zwraca pusty napis, gdy drzewo czyste; inaczej liste zmian."""
    return _git("status", "--porcelain")


def wczytaj() -> dict:
    return json.loads(LICZNIK.read_text(encoding="utf-8"))


def zapisz(dane: dict) -> None:
    """Zapis ATOMOWY. Przerwanie w polowie zapisu zostawiloby licznik
    nieczytelny, a jest to jedyny egzemplarz tej informacji."""
    obok = LICZNIK.with_suffix(".json.nowy")
    obok.write_text(json.dumps(dane, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")
    obok.replace(LICZNIK)


def pokaz(dane: dict) -> None:
    r = dane["_rules"]
    print(f"licznik prob (total_trials) : {dane['total_trials']}")
    print(f"limit na hipoteze           : {r['max_variants_per_hypothesis']}")
    print(f"limit na partie             : {r['max_variants_per_batch']}")
    print(f"SR-y prob zapisane          : {len(dane['trial_sharpes_daily'])}")
    if dane["by_hypothesis"]:
        print("\nwedlug kart:")
        for k, v in sorted(dane["by_hypothesis"].items()):
            print(f"  {k:<8} {v}")
    else:
        print("\nzadna karta nie zuzyla jeszcze proby")
    if dane["history"]:
        print(f"\nostatni wpis: {dane['history'][-1]['utc']} "
              f"{dane['history'][-1]['karta']}")


def main() -> int:
    p = argparse.ArgumentParser(description="Rejestracja proby w liczniku DSR")
    p.add_argument("--karta", help="identyfikator karty, np. H017")
    p.add_argument("--sr-dzienny", type=float,
                   help="Sharpe DZIENNY tej proby (nie roczny!)")
    p.add_argument("--opis", help="co dokladnie testowano — jednym zdaniem")
    p.add_argument("--raport", help="sciezka raportu z ta proba")
    p.add_argument("--benchmark", action="store_true",
                   help="uruchomienie z parametrami z literatury: NIE zuzywa proby")
    p.add_argument("--pokaz", action="store_true", help="tylko stan licznika")
    args = p.parse_args()

    dane = wczytaj()
    if args.pokaz:
        pokaz(dane)
        return 0

    brakuje = [n for n, v in (("--karta", args.karta), ("--opis", args.opis),
                              ("--sr-dzienny", args.sr_dzienny)) if v is None]
    if brakuje:
        sys.exit(f"STOP: brakuje {', '.join(brakuje)}. Proba bez opisu i SR jest "
                 "wpisem bez wartosci dowodowej.")

    # --- odmowa 1: brudne drzewo ------------------------------------------
    zmiany = stan_drzewa()
    if zmiany:
        print(zmiany)
        sys.exit("\nSTOP: drzewo robocze nie jest czyste. SHA zapisany przy probie "
                 "ma wskazywac kod, z ktorego wynik da sie ODTWORZYC — przy "
                 "niezacommitowanych zmianach wskazywalby stan, ktorego nie ma "
                 "w historii. Zacommituj i uruchom ponownie.")

    # --- odmowa 2: SR roczny podany jako dzienny --------------------------
    if abs(args.sr_dzienny) > PROG_SR_DZIENNY:
        sys.exit(f"STOP: |SR| = {abs(args.sr_dzienny):.3f} przekracza "
                 f"{PROG_SR_DZIENNY} i wyglada na SR ROCZNY. DSR wymaga SR "
                 "DZIENNEGO (poprawka A2-4). Po annualizacji ta liczba dalaby "
                 f"~{args.sr_dzienny * (252 ** 0.5):.1f} — sprawdz skale.")

    r = dane["_rules"]
    zuzyte = int(dane["by_hypothesis"].get(args.karta, 0))

    if args.benchmark:
        if not r["benchmarks_excluded"]:
            sys.exit("STOP: `benchmarks_excluded` jest False, wiec benchmark "
                     "zuzywa probe — nie wolno go rejestrowac tym trybem.")
    else:
        # --- odmowa 3: limit na karte -------------------------------------
        if zuzyte + 1 > r["max_variants_per_hypothesis"]:
            sys.exit(f"STOP: karta {args.karta} zuzyla juz {zuzyte} z "
                     f"{r['max_variants_per_hypothesis']} wariantow. Limit nie "
                     "jest preferencja — przy 30 wariantach certyfikacji nie "
                     "przechodzi nawet strategia o Sharpe 1.5 (tabela 6.5).")
        # --- odmowa 4: limit na partie ------------------------------------
        if dane["total_trials"] + 1 > r["max_variants_per_batch"]:
            sys.exit(f"STOP: partia zuzyla {dane['total_trials']} z "
                     f"{r['max_variants_per_batch']} prob. Zamknij partie "
                     "i podsumuj ja, zanim otworzysz nastepna.")

    wpis = {
        "utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "karta": args.karta,
        "opis": args.opis,
        "sr_dzienny": args.sr_dzienny,
        "benchmark": bool(args.benchmark),
        "commit": _git("rev-parse", "HEAD"),
        "raport": args.raport,
    }
    dane["history"].append(wpis)

    if args.benchmark:
        # Benchmark nie jest proba selekcji: uruchamiany raz, z parametrami
        # z literatury, bez optymalizacji. Nie wchodzi ani do licznika, ani
        # do rozrzutu SR-ow, z ktorego liczy sie sigma_SR wg FST.
        print("BENCHMARK — licznik prob i rozrzut SR bez zmian.")
    else:
        dane["total_trials"] += 1
        dane["by_hypothesis"][args.karta] = zuzyte + 1
        dane["trial_sharpes_daily"].append(args.sr_dzienny)

    zapisz(dane)
    print(f"\nzapisano: {args.karta}  SR_d={args.sr_dzienny:+.4f}  "
          f"commit {wpis['commit'][:12]}")
    print(f"-> {LICZNIK}\n")
    pokaz(dane)
    print("\nZacommituj licznik razem z raportem tej proby.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
