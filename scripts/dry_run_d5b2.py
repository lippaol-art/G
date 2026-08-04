#!/usr/bin/env python3
"""D5-B2 — jednodniowy dry run rekonstrukcji. Specyfikacja: docs/D5_ETAP4_SPEC.md.

CO SPRAWDZA: wylacznie STRUKTURE rekonstrukcji akcji agresywnych na posiadanej
sesji 2026-07-30, PRZED zakupem pozostalych 21 sesji.

CZEGO NIE LICZY: VIF, przyszlego przeplywu, przyszlych zwrotow, P&L, trwalosci
znaku, zadnego progu ani metryki wynikowej. **Zero zuzytych prob.**

Osiem niezmiennikow strukturalnych:
  N1  liczba rekordow Trade rozliczona bez zgubienia i bez podwojnego przypisania
  N2  kazda akcja trafia do DOKLADNIE jednego okna
  N3  strona akcji zgodna z rekordami Trade, ktore ja tworza
  N4  suma pasywnych Fill == rozmiar akcji
  N5  akcja przecinajaca minute trafia w calosci do minuty ostatniego ts_recv
  N6  akcja nie przekracza granicy koperty F_LAST
  N7  okna minutowe kompletne wzgledem sesji RTH
  N8  wynik deterministyczny

Uruchomienie:
    python3 scripts/dry_run_d5b2.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

import databento as db

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.mbo_events import F_LAST, rekonstruuj, z_dbn  # noqa: E402
from engine.paths import raw_dir  # noqa: E402

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
SESJA = "2026-07-30"
PLIK = raw_dir("d5c_mbo", f"mnq_mbo_rth_{SESJA}.dbn.zst")
MIN_NS = 60_000_000_000
OKIEN_RTH = 390          # 09:30-16:00 w sesji pelnej


def granice_ns() -> tuple[int, int]:
    """RTH WYPROWADZONE ZE STREFY ET, w nanosekundach epoki."""
    y, m, d = map(int, SESJA.split("-"))
    a = dt.datetime(y, m, d, 9, 30, tzinfo=ET).astimezone(UTC)
    b = dt.datetime(y, m, d, 16, 0, tzinfo=ET).astimezone(UTC)
    return int(a.timestamp()) * 10**9, int(b.timestamp()) * 10**9


def przebieg(gr: tuple[int, int]) -> tuple[list, dict]:
    """Jeden przebieg: akcje + kontrola surowych rekordow."""
    kontrola = Counter()
    strony_trade: dict[int, set[str]] = {}

    def zrodlo():
        for r in z_dbn(db.DBNStore.from_file(PLIK), tylko_rth=gr):
            kontrola["rekordow"] += 1
            if r.action == "T":
                kontrola["trade"] += 1
            elif r.action == "F":
                kontrola["fill"] += 1
            if r.flags & F_LAST:
                kontrola["koperty"] += 1
            yield r

    akcje = []
    for a in rekonstruuj(zrodlo()):
        akcje.append(a)
        strony_trade.setdefault(id(a), set()).add(a.side)
    return akcje, dict(kontrola)


def main() -> int:
    if not PLIK.exists():
        sys.exit(f"BRAK PLIKU: {PLIK}")
    gr = granice_ns()
    print(f"sesja {SESJA}, RTH {gr[0]} .. {gr[1]} ns\nplik: {PLIK}\n", flush=True)

    akcje, kontrola = przebieg(gr)
    print(f"rekordow w RTH : {kontrola['rekordow']:,}")
    print(f"  Trade        : {kontrola['trade']:,}")
    print(f"  Fill         : {kontrola['fill']:,}")
    print(f"  kopert F_LAST: {kontrola['koperty']:,}")
    print(f"AKCJI AGRESYWNYCH: {len(akcje):,}\n", flush=True)

    bledy: list[str] = []
    wyniki: dict = {"sesja": SESJA, "akcji": len(akcje), "kontrola": kontrola}

    # N1 — rozliczenie rekordow Trade
    suma_trade = sum(a.n_trade for a in akcje)
    ok1 = suma_trade == kontrola["trade"]
    print(f"N1  suma n_trade po akcjach : {suma_trade:,} "
          f"{'==' if ok1 else '!='} rekordow Trade {kontrola['trade']:,}")
    if not ok1:
        bledy.append(f"N1: {suma_trade} != {kontrola['trade']}")
    wyniki["N1"] = dict(suma_trade=suma_trade, rekordow_trade=kontrola["trade"],
                        ok=ok1)

    # N2 — dokladnie jedno okno na akcje
    okna = Counter(a.minuta for a in akcje)
    ok2 = sum(okna.values()) == len(akcje)
    print(f"N2  akcji przypisanych do okien: {sum(okna.values()):,} "
          f"{'==' if ok2 else '!='} akcji {len(akcje):,}")
    if not ok2:
        bledy.append("N2: liczba przypisan != liczba akcji")
    wyniki["N2"] = dict(przypisan=sum(okna.values()), ok=ok2)

    # N3 — strona zgodna i zawsze jednoznaczna
    zle_strony = [a for a in akcje if a.side not in ("B", "A")]
    print(f"N3  akcji o stronie spoza (B, A): {len(zle_strony):,}")
    if zle_strony:
        bledy.append(f"N3: {len(zle_strony)} akcji o niejednoznacznej stronie")
    wyniki["N3"] = dict(zle=len(zle_strony), ok=not zle_strony)

    # N4 — suma pasywnych == rozmiar akcji
    niezgodne = [a for a in akcje if a.rozmiar_pasywnych != a.rozmiar]
    print(f"N4  akcji z suma pasywnych != rozmiar: {len(niezgodne):,} "
          f"z {len(akcje):,}")
    if niezgodne:
        for a in niezgodne[:3]:
            print(f"      przyklad: rozmiar={a.rozmiar} "
                  f"pasywne={a.rozmiar_pasywnych} n_trade={a.n_trade} "
                  f"wlasnych={a.n_wlasnych}")
        bledy.append(f"N4: {len(niezgodne)} akcji niezgodnych")
    wyniki["N4"] = dict(niezgodne=len(niezgodne), ok=not niezgodne)

    # N5 — akcje przecinajace minute
    przecinajace = [a for a in akcje
                    if a.ts_recv_pierwszy // MIN_NS != a.ts_recv_ostatni // MIN_NS]
    zle5 = [a for a in przecinajace if a.minuta != a.ts_recv_ostatni // MIN_NS]
    print(f"N5  akcji przecinajacych minute: {len(przecinajace):,}  "
          f"zle przypisanych: {len(zle5):,}")
    if zle5:
        bledy.append(f"N5: {len(zle5)} akcji przypisanych nie do ostatniej minuty")
    wyniki["N5"] = dict(przecinajacych=len(przecinajace), zle=len(zle5),
                        ok=not zle5)

    # N6 — akcja nie przekracza koperty
    kopert_uzytych = len({a.koperta for a in akcje})
    print(f"N6  kopert z akcja: {kopert_uzytych:,} "
          f"(kopert lacznie {kontrola['koperty']:,})")
    ok6 = kopert_uzytych <= kontrola["koperty"]
    if not ok6:
        bledy.append("N6: wiecej kopert z akcja niz kopert")
    wyniki["N6"] = dict(kopert_z_akcja=kopert_uzytych, ok=ok6)

    # N7 — kompletnosc okien
    lo, hi = gr[0] // MIN_NS, gr[1] // MIN_NS
    oczekiwane = set(range(lo, hi))
    puste = sorted(oczekiwane - set(okna))
    poza = sorted(set(okna) - oczekiwane)
    print(f"N7  okien oczekiwanych: {len(oczekiwane)}  z akcjami: {len(okna)}  "
          f"pustych: {len(puste)}  poza RTH: {len(poza)}")
    if len(oczekiwane) != OKIEN_RTH:
        bledy.append(f"N7: {len(oczekiwane)} okien zamiast {OKIEN_RTH}")
    if poza:
        bledy.append(f"N7: {len(poza)} okien poza RTH")
    wyniki["N7"] = dict(oczekiwanych=len(oczekiwane), z_akcjami=len(okna),
                        pustych=len(puste), poza_rth=len(poza),
                        ok=not poza and len(oczekiwane) == OKIEN_RTH)

    # N8 — determinizm
    akcje2, _ = przebieg(gr)
    ok8 = (len(akcje) == len(akcje2) and all(
        (a.order_id, a.side, a.n_trade, a.rozmiar, a.rozmiar_pasywnych,
         a.ts_recv_ostatni, a.minuta) ==
        (b.order_id, b.side, b.n_trade, b.rozmiar, b.rozmiar_pasywnych,
         b.ts_recv_ostatni, b.minuta)
        for a, b in zip(akcje, akcje2, strict=True)))
    print(f"N8  dwa przebiegi identyczne: {'TAK' if ok8 else 'NIE'}")
    if not ok8:
        bledy.append("N8: przebiegi rozne")
    wyniki["N8"] = dict(ok=ok8)

    # --- statystyki opisowe (NIE metryki wynikowe)
    strony = Counter(a.side for a in akcje)
    n_trade = Counter(min(a.n_trade, 5) for a in akcje)
    print(f"\nstrony akcji     : {dict(strony)}")
    print(f"rekordow Trade w akcji (5 = 5+): {dict(sorted(n_trade.items()))}")
    print(f"akcji na okno    : min {min(okna.values())}  "
          f"mediana {sorted(okna.values())[len(okna) // 2]}  "
          f"max {max(okna.values())}")
    wyniki["opis"] = dict(strony=dict(strony), n_trade=dict(n_trade))

    print("\n" + "=" * 64)
    if bledy:
        for b in bledy:
            print(f"  BLAD  {b}")
        print("\n  DRY RUN NIEUDANY — nie kupujemy miesiaca")
    else:
        print("  WSZYSTKIE OSIEM NIEZMIENNIKOW SPELNIONE")
    print("=" * 64)

    wyniki["bledy"] = bledy
    Path("reports").mkdir(exist_ok=True)
    Path("reports/D5_b2_dry_run.json").write_text(
        json.dumps(wyniki, indent=1, default=str), encoding="utf-8")
    print("\n-> reports/D5_b2_dry_run.json")
    return 1 if bledy else 0


if __name__ == "__main__":
    raise SystemExit(main())
