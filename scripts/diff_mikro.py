#!/usr/bin/env python3
"""Mikro-diff 30 minut MBO — rozstrzyga wariant A vs B'. PLATNE (~0,08 USD).

PO CO. Test 2 (`diag_dryf.py`) pokazal, ze nasz plik 2026-07-03 ma w oknie
13:30-14:30 o 27 781 rekordow MNIEJ niz podaje dzis API, przy PELNYM pokryciu
czasowym. Liczebnosci powiedzialy juz wszystko, co mogly. Zostaje pytanie,
na ktore odpowiada wylacznie porownanie TRESCI:

  wariant A  — brakuje REALNYCH ZDARZEN, ktorych u nas nie ma
               -> pliki niepelne, trzeba je odkupic,
  wariant B' — te same zdarzenia w INNEJ REPREZENTACJI (inny podzial
               komunikatow, inne typy rekordow)
               -> nie kupujemy nic, ale nadal nie wolno mieszac.

WARUNKI ZGODY WLASCICIELA (R1) — wszystkie egzekwowane w kodzie:
  1. `get_cost` PRZED pobraniem; STOP bez pytania, gdy koszt przekroczy
     limit WLASNY DLA TEGO OKNA (`OKNA[...]['limit']`),
  2. zakres WYLACZNIE z zamrozonego rejestru `OKNA` — nie da sie podac
     dowolnego przedzialu z linii polecen. Start kazdego okna jest identyczny
     ze startem naszego pliku, wiec syntetyczny snapshot ksiegi wypada w tym
     samym miejscu po obu stronach i SKRACA SIE w porownaniu,
  3. zapis do OSOBNEGO katalogu diagnostycznego; `d5b2_mbo/`, `d5c_mbo/`
     i manifesty pozostaja NIETKNIETE,
  4. wpis do `data/KOSZTY.md` NIEZALEZNIE od wyniku,
  5. wynik jako meldunek z liczbami, zanim cokolwiek dalej.

DLACZEGO TEN SKRYPT MUSI BIEC LOKALNIE. Porownywany plik lezy w
`PROJECT_G_DATA_ROOT`, na maszynie wlasciciela. Srodowisko zdalne go nie ma.

Uruchomienie:
    python scripts/diff_mikro.py --wycena   # sam koszt, nic nie pobiera
    python scripts/diff_mikro.py            # wycena + pobranie + diff
    python scripts/diff_mikro.py --flagi    # histogram flag, LOKALNIE i DARMO
    python scripts/diff_mikro.py --rekonstrukcja        # akcje, LOKALNIE i DARMO
    python scripts/diff_mikro.py --sesja 2026-07-06     # drugie okno (§5e)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import NamedTuple

import databento as db

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.mbo_events import rekonstruuj, z_dbn  # noqa: E402
from engine.paths import raw_dir  # noqa: E402

UTC = dt.UTC

ZAPYTANIE = dict(dataset="GLBX.MDP3", symbols=["MNQU6"],
                 stype_in="raw_symbol", schema="mbo")
#: REJESTR DOZWOLONYCH OKIEN. Parametryzacja przez `--sesja`, ale WYLACZNIE
#: po kluczach tego slownika — dowolnego przedzialu nie da sie podac z linii
#: polecen. To jest ta sama ochrona co wczesniejsze zaszycie jednego okna na
#: stale (warunek 2 zgody R1), tylko rozszerzona o drugi pomiar; luzniejsza
#: wersja pozwalalaby przypadkiem zapytac o cala sesje za ~3 USD.
#:
#: Kazde okno ma WLASNY twardy limit kosztu, bo rozmiary sesji roznia sie
#: dziesieciokrotnie i jeden wspolny limit bylby albo bezuzyteczny, albo
#: blokujacy.
OKNA = {
    # Pierwszy mikro-diff, wykonany 09.08 za 0,0789 USD. Zmierzone
    # ~840 392 rek. x 9,388e-8; limit z zapasem na kolejny skok +2,6%.
    "2026-07-03": {"od": "13:30", "do": "14:00", "limit": 0.10},
    # Drugi mikro-diff (D5_DRYF §5e) — NIEURUCHOMIONY, wymaga zgody R1.
    # Sesja pelnowymiarowa: 07-03 to polowka, a rekordy `N` powstaja
    # w zdarzeniach wielopakietowych klastrujacych sie na otwarciach.
    # 32 910 056 rek. w calej sesji; 30 min otwarcia modelowo ~0,3-0,5 USD.
    "2026-07-06": {"od": "13:30", "do": "14:00", "limit": 1.00},
}


class Okno(NamedTuple):
    """Jedno zamrozone okno diagnostyczne wraz z wlasnym limitem kosztu."""

    sesja: str
    start_utc: str
    end_utc: str
    limit_usd: float

    @property
    def nazwa_pliku(self) -> str:
        znacznik = f"{self.start_utc[-5:]}_{self.end_utc[-5:]}".replace(":", "")
        return f"mikro_{self.sesja}_{znacznik}.dbn.zst"


def wybierz_okno(sesja: str) -> Okno:
    """Okno z rejestru albo TWARDA ODMOWA. Nie ma trzeciej mozliwosci."""
    if sesja not in OKNA:
        sys.exit(f"STOP (warunek 2): okno {sesja} nie jest w zamrozonym "
                 f"rejestrze. Dozwolone: {', '.join(sorted(OKNA))}. "
                 "Rejestr rozszerza sie commitem PRZED biegiem, nie flaga.")
    w = OKNA[sesja]
    return Okno(sesja, f"{sesja}T{w['od']}", f"{sesja}T{w['do']}",
                float(w["limit"]))


#: Domyslne okno — pierwszy mikro-diff, zeby stare wywolania dzialaly bez zmian.
SESJA_DOMYSLNA = "2026-07-03"

#: Warunek 3 zgody: katalog NIE nalezy do zadnego zakupu badawczego.
KATALOG_DIAG = "diag_mikro"
#: Nasz plik do porownania — czytany TYLKO do odczytu.
KATALOGI_NASZE = ("d5b2_mbo", "d5c_mbo")

#: Bity pola `flags` w DBN. Nazwy i wartosci wg specyfikacji Databento.
#: F_LAST jest tu jedynym, ktory ma konsekwencje badawcze: audyt D5-C liczy
#: koperty zdarzen wlasnie po tym bicie (842 757 kopert, 0 niewyjasnionych).
BITY_FLAG = ((128, "F_LAST"), (64, "F_TOB"), (32, "F_SNAPSHOT"),
             (16, "F_MBP"), (8, "F_BAD_TS_RECV"), (4, "F_MAYBE_BAD_BOOK"))


def nasz_plik(o: Okno) -> Path:
    for kat in KATALOGI_NASZE:
        p = raw_dir(kat, f"mnq_mbo_rth_{o.sesja}.dbn.zst")
        if p.exists():
            return p
    sys.exit(f"STOP: nie znalazlem naszego pliku {o.sesja} w "
             f"{KATALOGI_NASZE}. Bez niego nie ma czego porownywac.")


def granice_ns(o: Okno) -> tuple[int, int]:
    """Okno w nanosekundach — jedno miejsce, w ktorym parsuje sie znaczniki."""
    def na_ns(s: str) -> int:
        return int(dt.datetime.fromisoformat(s)
                   .replace(tzinfo=UTC).timestamp() * 1e9)
    return na_ns(o.start_utc), na_ns(o.end_utc)


def klucz(r) -> tuple:
    """Tozsamosc rekordu MBO: co musi sie zgadzac, zeby uznac go za TEN SAM.

    `ts_recv` + `order_id` + `action` + `side` + `price` + `size`. Celowo BEZ
    `sequence` — to numer wiadomosci CME, a nie identyfikator zdarzenia
    (potwierdzone oficjalnie przez Databento, `docs/D5_PYTANIE_DATABENTO.md`).
    Gdyby wejsc z `sequence` do klucza, KAZDA zmiana pakowania komunikatow
    wygladalaby jak inne zdarzenie — czyli test z gory dawalby wariant A.
    """
    return (getattr(r, "ts_recv", None), getattr(r, "order_id", None),
            getattr(r, "action", None), getattr(r, "side", None),
            getattr(r, "price", None), getattr(r, "size", None))


def wczytaj(p: Path, od_ns: int, do_ns: int) -> tuple[Counter, Counter]:
    """Zwraca licznik kluczy i licznik typow akcji w oknie."""
    klucze: Counter = Counter()
    typy: Counter = Counter()
    for r in db.DBNStore.from_file(p):
        ts = getattr(r, "ts_recv", None)
        if ts is None or not (od_ns <= ts < do_ns):
            continue
        klucze[klucz(r)] += 1
        typy[str(getattr(r, "action", "?"))] += 1
    return klucze, typy


def flagi_wg_akcji(p: Path, od_ns: int, do_ns: int) -> dict[str, Counter]:
    """Rozklad pola `flags` w rozbiciu na typ akcji, w oknie [od_ns, do_ns).

    Pierwotnie pytanie brzmialo: czy rekordy `action=N` niosa `F_LAST`.
    Pomiar 09.08 odpowiedzial "wszystkie" — i pokazal, ze **to pytanie bylo
    zle postawione**. Laczna liczba kopert jest po obu stronach identyczna
    (698 358), a nadwyzka `F_LAST` po naszej stronie na A, C i M sumuje sie
    dokladnie do liczby rekordow `N`. Bit zostal PRZENIESIONY, nie dodany.

    Histogram nie potrafi odroznic granicy przeniesionej (skutek zerowy) od
    wstawionej w srodek ciagu (skutek powazny), bo nie widzi KOLEJNOSCI.
    Rozstrzyga to dopiero `--rekonstrukcja`.
    """
    wynik: dict[str, Counter] = {}
    for r in db.DBNStore.from_file(p):
        ts = getattr(r, "ts_recv", None)
        if ts is None or not (od_ns <= ts < do_ns):
            continue
        akcja = str(getattr(r, "action", "?"))
        wynik.setdefault(akcja, Counter())[int(getattr(r, "flags", 0))] += 1
    return wynik


def opis_flag(wartosc: int) -> str:
    nazwy = [n for bit, n in BITY_FLAG if wartosc & bit]
    reszta = wartosc & ~sum(bit for bit, _ in BITY_FLAG)
    if reszta:
        nazwy.append(f"+{reszta}")
    return "|".join(nazwy) if nazwy else "(brak bitow)"


def raport_flag(o: Okno) -> int:
    """Tryb LOKALNY i DARMOWY — czyta tylko pliki, ktore juz sa na dysku.

    Wolno go uruchamiac bez zgody R1, bo nie dotyka sieci i nie wywoluje nawet
    `get_cost`. Klucz API nie jest potrzebny.
    """
    plik_mikro = raw_dir(KATALOG_DIAG, o.nazwa_pliku)
    if not plik_mikro.exists():
        sys.exit(f"STOP: brak {plik_mikro}. Ten tryb NIE pobiera danych — "
                 "uruchom najpierw pelny mikro-diff.")
    plik_nasz = nasz_plik(o)

    od_ns, do_ns = granice_ns(o)

    print(f"zakres : {o.start_utc} .. {o.end_utc} UTC")
    print("czytam swiezy wycinek...", flush=True)
    serw = flagi_wg_akcji(plik_mikro, od_ns, do_ns)
    print("czytam nasz plik (kilka minut — to setki MB)...", flush=True)
    nasz = flagi_wg_akcji(plik_nasz, od_ns, do_ns)

    print("\n" + "=" * 70)
    print("FLAGI W ROZBICIU NA TYP AKCJI")
    for akcja in sorted(set(serw) | set(nasz)):
        print(f"\n  action={akcja}")
        s, n = serw.get(akcja, Counter()), nasz.get(akcja, Counter())
        for w in sorted(set(s) | set(n)):
            print(f"    flags={w:>4} {opis_flag(w):<28} "
                  f"dostawca {s.get(w, 0):>9,}   my {n.get(w, 0):>9,}")

    print("\n" + "=" * 70)
    print("LICZBA KOPERT — czy granice zdarzen w ogole sie zmienily?")
    n_z_last = sum(ile for w, ile in serw.get("N", Counter()).items()
                   if w & 128)
    n_ogolem = sum(serw.get("N", Counter()).values())
    last_serw = sum(ile for c in serw.values() for w, ile in c.items() if w & 128)
    last_nasz = sum(ile for c in nasz.values() for w, ile in c.items() if w & 128)
    print(f"  rekordow action=N u dostawcy      : {n_ogolem:>10,}")
    print(f"  z nich z bitem F_LAST             : {n_z_last:>10,}")
    print(f"  kopert (F_LAST) razem u dostawcy  : {last_serw:>10,}")
    print(f"  kopert (F_LAST) razem u nas       : {last_nasz:>10,}")

    # Bilans przeniesienia: o ile WIECEJ F_LAST niosa u nas rekordy realne.
    nadwyzka = {a: sum(i for w, i in nasz.get(a, Counter()).items() if w & 128)
                - sum(i for w, i in serw.get(a, Counter()).items() if w & 128)
                for a in sorted(set(serw) | set(nasz)) if a != "N"}
    razem = sum(v for v in nadwyzka.values() if v > 0)
    print("\n  nadwyzka F_LAST po NASZEJ stronie, wg akcji:")
    for a, v in nadwyzka.items():
        if v:
            print(f"    {a} : {v:>+10,}")
    print(f"    {'razem':<2}: {razem:>+10,}   (rekordow N: {n_ogolem:,})")
    print()

    if last_serw != last_nasz:
        print(f"  -> LICZBA KOPERT SIE ROZNI o {last_serw - last_nasz:+,}.")
        print("     Granice zdarzen NIE sa te same — audyt D5-C wymaga")
        print("     powtorzenia niezaleznie od reszty tej diagnostyki.")
    elif n_z_last and razem == n_ogolem:
        print("  -> Bit F_LAST zostal PRZENIESIONY, nie dodany: liczba kopert")
        print("     identyczna, a nadwyzka na rekordach realnych sumuje sie")
        print("     dokladnie do liczby rekordow N. Koperta zamyka sie teraz")
        print("     osobnym wypelniaczem zamiast ostatniego rekordu realnego.")
        print()
        print("     TO NIE JEST JESZCZE WERDYKT. Histogram nie widzi KOLEJNOSCI,")
        print("     a granica przeniesiona (skutek zerowy) i wstawiona w srodek")
        print("     ciagu (skutek powazny) daja tu te same liczby. Rozstrzyga:")
        print("         python scripts/diff_mikro.py --rekonstrukcja")
    else:
        print("  -> Liczba kopert zgodna, ale bilans przeniesienia sie NIE")
        print(f"     domyka ({razem:,} vs {n_ogolem:,} rekordow N). Nie zgaduj")
        print("     mechanizmu — uruchom --rekonstrukcja i porownaj akcje.")
    return 0


def raport_rekonstrukcji(o: Okno) -> int:
    """Test KONCOWY: te same akcje agresywne z obu plikow, czy nie?

    Histogramy odpowiadaja na pytania o liczebnosc. To pytanie jest inne:
    czy **jednostka obserwacji D5-B2** — akcja agresywna per Trade — wychodzi
    z obu wersji danych identyczna. Jesli tak, audyt D5-C stoi, bo policzono go
    dokladnie na tej jednostce. Jesli nie, wynik `842 757 zdarzen` opisuje
    wersje danych, ktorej dostawca juz nie serwuje.

    To jest jedyny test, ktory patrzy na KOLEJNOSC rekordow, a nie na ich
    rozklad. Lokalny i darmowy.
    """
    plik_mikro = raw_dir(KATALOG_DIAG, o.nazwa_pliku)
    if not plik_mikro.exists():
        sys.exit(f"STOP: brak {plik_mikro}. Ten tryb NIE pobiera danych.")
    plik_nasz = nasz_plik(o)

    od_ns, do_ns = granice_ns(o)
    okno = (od_ns, do_ns)

    def akcje(p: Path) -> list[tuple]:
        store = db.DBNStore.from_file(p)
        return [(a.order_id, a.side, a.n_trade, a.rozmiar, a.n_pasywnych,
                 a.rozmiar_pasywnych, a.n_wlasnych, a.ts_recv_pierwszy,
                 a.ts_recv_ostatni, a.poziomy, a.minuta)
                for a in rekonstruuj(z_dbn(store, tylko_rth=okno))]

    print(f"zakres : {o.start_utc} .. {o.end_utc} UTC")
    print("rekonstruuje ze swiezego wycinka...", flush=True)
    a_serw = akcje(plik_mikro)
    print("rekonstruuje z naszego pliku (kilka minut)...", flush=True)
    a_nasz = akcje(plik_nasz)

    print("\n" + "=" * 70)
    print("AKCJE AGRESYWNE — JEDNOSTKA OBSERWACJI D5-B2")
    print(f"  akcji ze swiezego wycinka : {len(a_serw):>10,}")
    print(f"  akcji z naszego pliku     : {len(a_nasz):>10,}")
    print(f"  suma Trade  swiezy / nasz : {sum(x[2] for x in a_serw):>10,}"
          f" / {sum(x[2] for x in a_nasz):,}")
    print(f"  suma rozmiaru swiezy/nasz : {sum(x[3] for x in a_serw):>10,}"
          f" / {sum(x[3] for x in a_nasz):,}")
    print()

    # Celowo POMIJAMY pole `koperta`: numer koperty to indeks porzadkowy,
    # a nie cecha zdarzenia. Rownosc pozostalych jedenastu pol znaczy, ze
    # jednostka obserwacji jest ta sama — i tylko to jest tu pytaniem.
    if a_serw == a_nasz:
        print("  -> IDENTYCZNE, akcja po akcji, we wszystkich polach.")
        print("     AUDYT D5-C STOI. Przeniesienie bitu F_LAST na wypelniacz")
        print("     nie zmienia jednostki obserwacji.")
        return 0

    rozne = [i for i, (x, z) in enumerate(zip(a_serw, a_nasz, strict=False))
             if x != z]
    print(f"  -> ROZNICA. Pierwsza na pozycji {rozne[0] if rozne else len(a_serw)}"
          f", roznych pozycji: {len(rozne):,}")
    for i in (rozne or [0])[:3]:
        print(f"     [{i}] swiezy: {a_serw[i]}")
        print(f"     [{i}] nasz  : {a_nasz[i]}")
    print("     AUDYT D5-C WYMAGA POWTORZENIA.")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Mikro-diff 30 min MBO (PLATNE)")
    ap.add_argument("--wycena", action="store_true",
                    help="tylko koszt, bez pobierania")
    ap.add_argument("--flagi", action="store_true",
                    help="histogram flag na juz pobranych plikach — "
                         "lokalnie, bez sieci, bez kosztu")
    ap.add_argument("--rekonstrukcja", action="store_true",
                    help="porownanie akcji agresywnych z obu plikow — "
                         "rozstrzyga los audytu D5-C, lokalnie i darmo")
    ap.add_argument("--sesja", default=SESJA_DOMYSLNA,
                    help="okno z zamrozonego rejestru OKNA; dowolnego "
                         f"przedzialu podac sie NIE DA. Domyslnie {SESJA_DOMYSLNA}")
    args = ap.parse_args()
    o = wybierz_okno(args.sesja)

    if args.flagi:
        return raport_flag(o)
    if args.rekonstrukcja:
        return raport_rekonstrukcji(o)

    plik_nasz = nasz_plik(o)
    print(f"nasz plik   : {plik_nasz}")
    print(f"zakres      : {o.start_utc} .. {o.end_utc} UTC")
    print(f"limit kosztu: {o.limit_usd:.2f} USD (warunek 1 zgody)\n", flush=True)

    c = db.Historical(os.environ["DATABENTO_API_KEY"])

    # --- WARUNEK 1: wycena PRZED pobraniem -------------------------------
    koszt = c.metadata.get_cost(**ZAPYTANIE, start=o.start_utc, end=o.end_utc)
    rekordow = c.metadata.get_record_count(**ZAPYTANIE, start=o.start_utc,
                                           end=o.end_utc)
    print(f"koszt wg API : {koszt:.4f} USD")
    print(f"rekordow     : {rekordow:,}", flush=True)
    if koszt > o.limit_usd:
        sys.exit(f"\nSTOP (warunek 1): {koszt:.4f} > {o.limit_usd:.2f} USD. "
                 "Zgoda wlasciciela obejmowala kwote do limitu — nie pobieram.")

    if args.wycena:
        print("\nTryb wyceny — nic nie pobrano.")
        return 0

    # --- WARUNEK 3: osobny katalog, cudze nietkniete ----------------------
    kat = raw_dir(KATALOG_DIAG)
    kat.mkdir(parents=True, exist_ok=True)
    out = kat / o.nazwa_pliku
    if out.exists():
        print(f"\n{out} juz istnieje — uzywam bez ponownego pobrania "
              "(zero dodatkowego kosztu).", flush=True)
    else:
        print("\npobieranie 30 minut...", flush=True)
        c.timeseries.get_range(**ZAPYTANIE, start=o.start_utc, end=o.end_utc,
                               path=str(out))
        print(f"  -> {out}  ({out.stat().st_size / 1e6:.1f} MB)", flush=True)

    # --- porownanie tresci -------------------------------------------------
    od_ns, do_ns = granice_ns(o)

    print("\nczytam swiezy wycinek...", flush=True)
    serw_k, serw_t = wczytaj(out, od_ns, do_ns)
    print("czytam nasz plik...", flush=True)
    nasz_k, nasz_t = wczytaj(plik_nasz, od_ns, do_ns)

    wspolne = sum((serw_k & nasz_k).values())
    tylko_serw = serw_k - nasz_k
    tylko_nasz = nasz_k - serw_k
    n_serw, n_nasz = sum(serw_k.values()), sum(nasz_k.values())

    print("\n" + "=" * 70)
    print("MIKRO-DIFF — TRESC, nie liczebnosc")
    print(f"  rekordow u dostawcy (dzis)  : {n_serw:>10,}")
    print(f"  rekordow u nas              : {n_nasz:>10,}")
    print(f"  WSPOLNYCH (ten sam klucz)   : {wspolne:>10,}")
    print(f"  TYLKO u dostawcy            : {sum(tylko_serw.values()):>10,}")
    print(f"  TYLKO u nas                 : {sum(tylko_nasz.values()):>10,}")

    print("\n  typy akcji — dostawca vs my:")
    for t in sorted(set(serw_t) | set(nasz_t)):
        print(f"    {t:>4} : {serw_t.get(t, 0):>10,}  vs {nasz_t.get(t, 0):>10,}"
              f"   ({serw_t.get(t, 0) - nasz_t.get(t, 0):+,})")

    if tylko_serw:
        print("\n  przyklady rekordow TYLKO u dostawcy (do 5):")
        for k, ile in list(tylko_serw.items())[:5]:
            ts = dt.datetime.fromtimestamp(k[0] / 1e9, UTC) if k[0] else None
            print(f"    ts={ts} order_id={k[1]} action={k[2]} side={k[3]} "
                  f"px={k[4]} sz={k[5]}  x{ile}")

    print("\n" + "=" * 70)
    print("JAK CZYTAC")
    print("  duzo TYLKO u dostawcy, malo/zero TYLKO u nas")
    print("      -> WARIANT A: brakuje nam realnych zdarzen, pliki niepelne,")
    print("  porownywalne liczby po obu stronach, rozne typy/podzial")
    print("      -> WARIANT B': te same zdarzenia, inna reprezentacja.")
    print("\n  Zakaz mieszania plikow z obu okresow obowiazuje TAK CZY INACZEJ.")
    print("  Wpisz koszt do data/KOSZTY.md niezaleznie od wyniku (warunek 4).")

    wynik = {
        "sesja": o.sesja, "zakres_utc": [o.start_utc, o.end_utc],
        "koszt_usd": round(float(koszt), 4), "rekordow_wg_api": int(rekordow),
        "rekordow_dostawca": n_serw, "rekordow_nasze": n_nasz,
        "wspolnych": wspolne,
        "tylko_dostawca": sum(tylko_serw.values()),
        "tylko_nasze": sum(tylko_nasz.values()),
        "typy_dostawca": dict(serw_t), "typy_nasze": dict(nasz_t),
        "utc": dt.datetime.now(UTC).isoformat(timespec="seconds"),
    }
    raport = Path("reports/D5_mikro_diff.json")
    raport.parent.mkdir(exist_ok=True)
    raport.write_text(json.dumps(wynik, indent=1), encoding="utf-8",
                      newline="\n")
    print(f"\n-> {raport}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
