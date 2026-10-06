#!/usr/bin/env python3
"""Audyt odejmowania kolumn bez znaku — waski, celowany, nie refaktor.

DLACZEGO ISTNIEJE. Ta sama klasa bledu wystapila w projekcie DWA razy:
  * Etap 1 D5 — roznica wolumenow,
  * Etap 2 D5 — `n_buy - n_sell`, `f_buy - f_sell`, `v_buy - v_sell`,
    co dalo falszywy werdykt `NO-GO` (wartosci rzedu 1,8e19 zamiast ujemnych).

Sama dokumentacja nie wystarczyla. Ten skrypt szuka miejsc, w ktorych wynik
agregacji polars (`.sum()`, `.len()`, `.count()`, porownanie logiczne) trafia
do odejmowania BEZ jawnego rzutowania na typ ze znakiem.

REGULA PROJEKTU: kazda roznica, ktora semantycznie moze byc ujemna, musi byc
rzutowana na typ ze znakiem PRZED odejmowaniem.

Skrypt zglasza kandydatow do przejrzenia — nie kazde trafienie jest bledem
(odejmowanie liczb zmiennoprzecinkowych z numpy jest bezpieczne). Wyjscie
sluzy do recznej oceny, a nie do automatycznej poprawki.

Uruchomienie:
    python3 scripts/audit_typy_bez_znaku.py
"""

from __future__ import annotations

import ast
from pathlib import Path

KATALOGI = ("engine", "validation", "research", "scripts")

#: Wywolania, ktorych wynik w polars jest BEZ ZNAKU (UInt32/UInt64).
AGREGATY_BEZ_ZNAKU = {"len", "count", "n_unique"}
#: `.sum()` jest bez znaku, gdy sumuje kolumne bez znaku albo maske logiczna.
AGREGATY_WARUNKOWE = {"sum"}
#: Rzutowania, ktore neutralizuja ryzyko.
BEZPIECZNE = ("cast", "Int8", "Int16", "Int32", "Int64", "Float32", "Float64",
              "astype", "float", "int(")


def _zrodlo(w: ast.AST, linie: list[str]) -> str:
    try:
        return ast.get_source_segment("\n".join(linie), w) or ""
    except Exception:
        return ""


def _indeksowanie_kolumny(w: ast.AST) -> bool:
    """Forma `df["kolumna"]` — DRUGI slepy punkt, znaleziony w audycie.

    Detekcja po `pl.col(` przepuszczala `z["volume"] - z["v"]`, czyli
    dokladnie zapis, w ktorym wystapil blad Etapu 1. Indeksowanie napisem
    jest rownie grozne, bo zwraca `Series` o tym samym typie bez znaku.
    """
    return (isinstance(w, ast.Subscript)
            and isinstance(w.slice, ast.Constant)
            and isinstance(w.slice.value, str))


def _polars_wyrazenie(tekst: str) -> bool:
    return "pl.col(" in tekst or "pl.len(" in tekst


def _agregat(tekst: str) -> bool:
    if any(f".{a}()" in tekst for a in AGREGATY_BEZ_ZNAKU | AGREGATY_WARUNKOWE):
        return True
    return "pl.len()" in tekst


def _bezpieczne(tekst: str) -> bool:
    return any(b in tekst for b in BEZPIECZNE)


def skanuj(path: Path) -> list[tuple[int, str]]:
    tekst = path.read_text(encoding="utf-8")
    linie = tekst.splitlines()
    try:
        drzewo = ast.parse(tekst)
    except SyntaxError:
        return []
    trafienia = []
    for w in ast.walk(drzewo):
        if not (isinstance(w, ast.BinOp) and isinstance(w.op, ast.Sub)):
            continue
        lewy = _zrodlo(w.left, linie)
        prawy = _zrodlo(w.right, linie)
        calosc = f"{lewy} - {prawy}"
        # ZAKRES SKANU JEST SZERSZY NIZ "WIDOCZNY AGREGAT" — I TO JEST SEDNO.
        # Pierwsza wersja wymagala, zeby `.sum()`/`.len()` wystapilo w TYM
        # SAMYM wyrazeniu. Taki warunek przepuszczal dokladnie ten blad,
        # ktory dal falszywy werdykt `NO-GO`:
        #     (pl.col("n_buy") - pl.col("n_sell")) / (...)
        # bo brak znaku przyszedl z agregacji wykonanej PIETRO WYZEJ, przy
        # tworzeniu kolumn. Zadna analiza jednego wyrazenia tego nie zobaczy.
        # Dlatego zglaszamy KAZDE odejmowanie kolumn polars bez rzutowania,
        # godzac sie na falszywe alarmy — sa tansze niz drugi taki werdykt.
        indeksowane = (_indeksowanie_kolumny(w.left)
                       or _indeksowanie_kolumny(w.right))
        if not (_polars_wyrazenie(calosc) or indeksowane):
            continue
        if _bezpieczne(calosc):
            continue
        trafienia.append((w.lineno, " ".join(calosc.split())[:150]))
    return trafienia


def main() -> int:
    razem = 0
    for kat in KATALOGI:
        d = Path(kat)
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.py")):
            if "__pycache__" in p.parts or p.name == Path(__file__).name:
                continue
            for lineno, frag in skanuj(p):
                print(f"{p}:{lineno}: {frag}")
                razem += 1
    print(f"\nkandydatow do przejrzenia: {razem}")
    if razem:
        print("Kazdy wymaga RECZNEJ oceny: czy roznica moze byc ujemna?")
        print("Jesli tak — rzutowanie na Int64 PRZY AGREGACJI, nie przy odejmowaniu.")
    return 1 if razem else 0


if __name__ == "__main__":
    raise SystemExit(main())
