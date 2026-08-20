#!/usr/bin/env python3
"""Diagnostyka read-only: czy ochrona starych plikow przezyje bieg zakupowy.

CZEGO TEN SKRYPT NIE ROBI: nie laczy sie z siecia, nie czyta
`DATABENTO_API_KEY`, nie zapisuje ani nie kasuje zadnego pliku. Czyta manifest
i drukuje. Import `fetch_d5b2_month` jest bezpieczny — klucz odczytywany jest
dopiero w `main()`, po `parse_args()`.

PO CO: piec plikow ze STAREJ normalizacji GLBX.MDP3 jest **nieodtwarzalnych**
(vendor: „The old data is not available anymore in our API"). Bieg zakupowy
uruchamiany z `--akceptuj-rozjazd` przechodzi sciezka, na ktorej plik uznany za
niekompletny trafia pod `out.unlink()`. `liczby_oplacone()` jest jedyna rzecza,
ktora te piec plikow ratuje — a ratuje je tylko wtedy, gdy liczba pochodzi
z `wyniki[]`. Liczby z `plan[]` sa nadpisywane przez pierwszy bieg zakupowy,
wiec ochrona oparta na nich ginie dokladnie w biegu wznowieniowym.

Ten skrypt odpowiada na jedno pytanie: **skad pochodzi liczba dla kazdej
z piaciu starych sesji** — i czy to zrodlo przezyje bieg.

Uruchomienie (z katalogu repo, venv aktywny lub nie — zaleznosci nie sa
potrzebne poza standardowa biblioteka i importem modulu):

    python scripts/diag_wyniki.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.fetch_d5b2_month import (  # noqa: E402
    KANONICZNY_D5C,
    SESJA_D5C,
    SESJE_STARA_NORMALIZACJA,
    liczby_oplacone,
    sciezka_manifestu,
)

#: Liczby, ktore recenzja podala jako oczekiwane dla czterech sesji lipcowych.
#: Trzymane tu wylacznie do wydrukowania obok stanu faktycznego — skrypt nie
#: uzywa ich do zadnej decyzji, zeby nie zastapic pomiaru oczekiwaniem.
OCZEKIWANE_WG_RECENZJI = {
    "2026-07-01": 39_297_265,
    "2026-07-02": 61_279_315,
    "2026-07-03": 2_660_629,
    "2026-07-06": 32_369_900,
}


def main() -> int:
    cel = sciezka_manifestu()
    print(f"manifest : {cel}")
    if not cel.exists():
        print("\nBRAK MANIFESTU — nie ma zadnej zapisanej liczby rekordow, wiec")
        print("nie ma tez z czym porownac plikow na dysku. `kompletny()` uzna je")
        print("za niekompletne, a obrona przy `unlink()` nie ma na czym stanac.")
        print("WERDYKT: BLOKADA. Nie uruchamiaj zakupu.")
        return 1

    stary = json.loads(cel.read_text(encoding="utf-8"))
    plan = {w["sesja"]: int(w["rekordow"]) for w in stary.get("plan", [])
            if "rekordow" in w}
    wyniki = {w["sesja"]: w for w in stary.get("wyniki", [])}
    oplacone = liczby_oplacone()

    print(f"plan[]   : {len(plan)} sesji")
    print(f"wyniki[] : {len(wyniki)} wpisow")
    print(f"kanoniczny D5-C: {'jest' if KANONICZNY_D5C.exists() else 'BRAK'}"
          f"  ({KANONICZNY_D5C})\n")

    naglowek = (f"{'sesja':<12} {'w wyniki[]':<12} {'kompletny':<10} "
                f"{'liczba oplacona':>16}  zrodlo")
    print(naglowek)
    print("-" * len(naglowek))

    braki: list[str] = []
    do_syntezy: list[str] = []
    for sesja in SESJE_STARA_NORMALIZACJA:
        w = wyniki.get(sesja)
        ma_wynik = "tak" if w is not None else "NIE"
        komplet = "-" if w is None else ("tak" if w.get("kompletny") else "NIE")
        liczba = oplacone.get(sesja)

        # Kolejnosc taka sama jak w `liczby_oplacone()`: kanoniczny D5-C bije
        # wszystko, potem `wyniki[]` z `kompletny: true`, na koncu `plan[]`.
        if sesja == SESJA_D5C and KANONICZNY_D5C.exists():
            zrodlo = "manifest_d5c.json (w repo — PRZEZYJE)"
        elif w is not None and w.get("kompletny"):
            zrodlo = "wyniki[] (PRZEZYJE bieg zakupowy)"
        elif sesja in plan:
            zrodlo = "plan[] — ulotny, ale synteza go utrwali"
            do_syntezy.append(sesja)
        else:
            zrodlo = "BRAK LICZBY — plik bez zadnej ochrony"
            braki.append(sesja)

        print(f"{sesja:<12} {ma_wynik:<12} {komplet:<10} "
              f"{liczba if liczba is not None else '—':>16}  {zrodlo}")

    print("\nporownanie z liczbami z recenzji (tylko informacyjnie):")
    for sesja, ocz in OCZEKIWANE_WG_RECENZJI.items():
        mam = oplacone.get(sesja)
        if mam is None:
            stan = "BRAK LICZBY"
        elif mam == ocz:
            stan = "zgodne"
        else:
            stan = f"ROZNI SIE (oczekiwano {ocz:,})"
        print(f"  {sesja}: {mam if mam is not None else '—':>12}  {stan}")

    print()
    if braki:
        print("WERDYKT: BLOKADA. Sesje bez zadnej liczby: " + ", ".join(braki))
        print("Nie ma z czym porownac pliku, wiec ani `kompletny()`, ani obrona")
        print("przy `unlink()` nie maja na czym stanac. Nie uruchamiaj zakupu.")
        return 1

    if do_syntezy:
        print("WERDYKT: mozna uruchomic zakup. Ochrona w BIEGU jest pelna,")
        print("a trwalosc zalatwia synteza przy zapisie manifestu.")
        print("Sesje stojace jeszcze na `plan[]`: " + ", ".join(do_syntezy))
        print()
        print("Dlaczego to wystarcza — dwa kroki, oba w tym samym biegu:")
        print("  1. `liczby_oplacone()` czyta STARY manifest PRZED petla zakupu,")
        print("     wiec w tym biegu liczby z `plan[]` sa jeszcze poprawne,")
        print("  2. `syntetyzuj_wyniki()` przy zapisie manifestu przenosi je")
        print("     do `wyniki[]` — czyli ze zrodla ulotnego do trwalego,")
        print("     w tym samym zapisie, ktory nadpisuje `plan[]`.")
        print("Po tym biegu ta sama komenda pokaze juz `wyniki[]`.")
        return 0

    print("WERDYKT: ochrona trwala dla wszystkich piaciu starych sesji.")
    print("Zadna z liczb nie stoi na `plan[]` — nie ma nawet czego syntetyzowac.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
