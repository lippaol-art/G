#!/usr/bin/env python3
"""D5-C — audyt jednodniowej probki MBO. Specyfikacja: docs/D5_ETAP3_SPEC.md.

JEDNO PYTANIE: czy z `mbo` da sie kanonicznie odtworzyc pojedyncze zdarzenia
dopasowania (matching events)?

NIE LICZY: przyszlych zwrotow, trwalosci znaku, VIF, Sharpe'a, P&L, optymalnego
progu, najlepszego horyzontu ani skutecznosci strategii. **Zero zuzytych prob.**
D5-C jest audytem POMIARU, nie testem przewagi.

PRZETWARZANIE STRUMIENIOWE — WYMOG, NIE PREFERENCJA.
Plik ma 38,3 mln rekordow. Nie powstaje pelna zdekompresowana kopia i nie ma
momentu, w ktorym wszystkie rekordy sa naraz w ramce. Iterujemy po `DBNStore`,
utrzymujac wylacznie liczniki i kompaktowe tablice `array('q')` — 8 bajtow na
identyfikator zamiast ~28 bajtow obiektu Pythona.

Uruchomienie:
    python3 scripts/audit_d5_etap3.py
    python3 scripts/audit_d5_etap3.py --limit 2000000   # szybki przebieg
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from array import array
from collections import Counter, defaultdict
from pathlib import Path

import databento as db
import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.paths import raw_dir  # noqa: E402

PLIK_MBO = raw_dir("d5c_mbo", "mnq_mbo_rth_2026-07-30.dbn.zst")
PLIK_TRADES = Path("data/raw/mnq_trades_2026-07-30.dbn.zst")
F_LAST = 128


class Stan:
    """Liczniki jednego przebiegu strumieniowego."""

    def __init__(self) -> None:
        self.n = 0
        self.akcje: Counter = Counter()
        self.flagi: Counter = Counter()
        self.strony_T: Counter = Counter()

        # --- zdarzenia rozgraniczone przez F_LAST
        self.zdarzen = 0
        self.rekordow_w_zdarzeniu: Counter = Counter()
        self.T_w_zdarzeniu: Counter = Counter()
        self.zdarzen_z_T = 0
        self.zdarzen_z_dokladnie_1T = 0
        self.zdarzen_z_T_bez_F = 0

        # --- Q4: order_id agresora na rekordzie Trade
        self.T_z_order_id = 0
        self.T_bez_order_id = 0

        # --- Q6: suma pasywnych Fill vs rozmiar Trade
        self.zgodne_sumy = 0
        self.niezgodne_sumy = 0
        self.zdarzen_z_fill_agresora = 0
        self.przyklady_niezgodne: list[dict] = []

        # --- Q7: rekonstrukcja schematu `trades`
        self.T_ts_recv = array("q")
        self.T_price = array("q")
        self.T_size = array("q")

        # --- Q8: relacja do grupowania po (ts_event, sequence)
        self.T_ts_event = array("q")
        self.T_sequence = array("q")
        self.T_zdarzenie = array("q")     # indeks zdarzenia F_LAST

        # --- Q9: czy Fill odwoluje sie do zlecen sprzed okna
        self.add_ids = array("q")
        self.fill_ids = array("q")


def przetworz(st: Stan, bufor: list) -> None:
    """Domkniecie jednego zdarzenia (rekordy do F_LAST wlacznie)."""
    st.zdarzen += 1
    st.rekordow_w_zdarzeniu[min(len(bufor), 20)] += 1

    trade = [r for r in bufor if r[0] == "T"]
    fill = [r for r in bufor if r[0] == "F"]
    st.T_w_zdarzeniu[min(len(trade), 10)] += 1
    if not trade:
        return
    st.zdarzen_z_T += 1
    if len(trade) == 1:
        st.zdarzen_z_dokladnie_1T += 1
        if not fill:
            st.zdarzen_z_T_bez_F += 1
        else:
            # Q6 — NIEZMIENNIK POPRAWIONY PO DIAGNOSTYCE.
            # Naiwna suma WSZYSTKICH Fill nie dziala, bo `Fill` dostaje takze
            # zlecenie AGRESORA, nie tylko pasywne. Rozpoznajemy je po tym, ze
            # `order_id` jest identyczny z `order_id` rekordu `Trade`.
            # Wlasciwy niezmiennik: suma Fill PASYWNYCH == rozmiar Trade.
            oid_agresora = trade[0][2]
            pasywne = [r for r in fill if r[2] != oid_agresora]
            wlasne = [r for r in fill if r[2] == oid_agresora]
            if wlasne:
                st.zdarzen_z_fill_agresora += 1
            suma_p = sum(r[3] for r in pasywne)
            if suma_p == trade[0][3]:
                st.zgodne_sumy += 1
            else:
                st.niezgodne_sumy += 1
                if len(st.przyklady_niezgodne) < 5:
                    st.przyklady_niezgodne.append(
                        dict(trade_size=trade[0][3], suma_pasywnych=suma_p,
                             n_pasywnych=len(pasywne), n_wlasnych=len(wlasne),
                             ts_recv=trade[0][1]))


def przebieg(limit: int | None) -> Stan:
    st = Stan()
    store = db.DBNStore.from_file(PLIK_MBO)
    zrodlo = itertools.islice(store, limit) if limit else store

    bufor: list[tuple] = []
    for r in zrodlo:
        st.n += 1
        akcja = r.action if isinstance(r.action, str) else r.action.value
        flagi = int(r.flags)
        st.akcje[akcja] += 1
        st.flagi[flagi] += 1

        oid = int(r.order_id)
        if akcja == "A":
            st.add_ids.append(oid)
        elif akcja == "F":
            st.fill_ids.append(oid)
        elif akcja == "T":
            strona = r.side if isinstance(r.side, str) else r.side.value
            st.strony_T[strona] += 1
            if oid:
                st.T_z_order_id += 1
            else:
                st.T_bez_order_id += 1
            st.T_ts_recv.append(int(r.ts_recv))
            st.T_price.append(int(r.price))
            st.T_size.append(int(r.size))
            st.T_ts_event.append(int(r.ts_event))
            st.T_sequence.append(int(r.sequence))
            st.T_zdarzenie.append(st.zdarzen)

        bufor.append((akcja, int(r.ts_recv), oid, int(r.size)))
        if flagi & F_LAST:
            przetworz(st, bufor)
            bufor = []

    if bufor:                      # ogon bez F_LAST — sam w sobie jest wynikiem
        przetworz(st, bufor)
    return st



# ---------------------------------------------------------------------------
# PELNY PODZIAL ZDARZEN Z TRANSAKCJA — mianownik musi sie zgadzac co do sztuki
# ---------------------------------------------------------------------------
#
# PO CO. Niezmiennik Q6 badal tylko zdarzenia z DOKLADNIE JEDNYM rekordem
# `Trade` (767 588), podczas gdy zdarzen z transakcja jest 842 757. Roznica
# 75 169 zostala w pierwszej wersji raportu bez wyjasnienia — a metryka
# z niezapisanym mianownikiem jest dokladnie tym rodzajem pulapki, przed ktorym
# ostrzega wniosek W003.
#
# Kategorie ponizej sa ROZLACZNE i WYCZERPUJACE: ich suma musi rownac sie
# liczbie zdarzen z transakcja. Adnotacje (Fill agresora, wplyw braku
# snapshotu) sa ortogonalne i liczone osobno, bo moga wystapic w kazdej
# kategorii.
#
# Wymaga DWOCH przebiegow: pierwszy zbiera identyfikatory zlecen zlozonych
# w oknie, drugi klasyfikuje zdarzenia. Kazdy ~45 s.

KATEGORIE = (
    "1T_pasywne_zgodne",
    "1T_pasywne_niezgodne",
    "1T_bez_pasywnych",
    "wieleT_zgodne",
    "wieleT_niezgodne",
    "wieleT_bez_pasywnych",
    "inne",
)


def _dodane_order_id() -> np.ndarray:
    """Przebieg 1: identyfikatory zlecen ZLOZONYCH w oknie obserwacji."""
    ids = array("q")
    for r in db.DBNStore.from_file(PLIK_MBO):
        a = r.action if isinstance(r.action, str) else r.action.value
        if a == "A":
            ids.append(int(r.order_id))
    return np.unique(np.array(ids, dtype="int64"))


def pelny_podzial() -> dict:
    """Przebieg 2: rozlaczna klasyfikacja wszystkich zdarzen z transakcja."""
    dodane = _dodane_order_id()
    kat: Counter = Counter()
    adn = Counter()
    agresorow_w_zdarzeniu: Counter = Counter()
    zdarzen_z_T = 0

    bufor: list[tuple] = []

    def domknij(buf: list[tuple]) -> None:
        nonlocal zdarzen_z_T
        trade = [x for x in buf if x[0] == "T"]
        if not trade:
            return
        zdarzen_z_T += 1
        oid_agr = {x[2] for x in trade}
        agresorow_w_zdarzeniu[min(len(oid_agr), 5)] += 1

        fill = [x for x in buf if x[0] == "F"]
        wlasne = [x for x in fill if x[2] in oid_agr]
        pasywne = [x for x in fill if x[2] not in oid_agr]
        if wlasne:
            adn["z_fill_agresora"] += 1
        if pasywne and not np.isin([x[2] for x in pasywne], dodane).all():
            adn["dotkniete_brakiem_snapshotu"] += 1

        suma_t = sum(x[3] for x in trade)
        suma_p = sum(x[3] for x in pasywne)
        jeden = len(trade) == 1
        if not pasywne:
            kat["1T_bez_pasywnych" if jeden else "wieleT_bez_pasywnych"] += 1
        elif suma_p == suma_t:
            kat["1T_pasywne_zgodne" if jeden else "wieleT_zgodne"] += 1
        else:
            kat["1T_pasywne_niezgodne" if jeden else "wieleT_niezgodne"] += 1

    for r in db.DBNStore.from_file(PLIK_MBO):
        a = r.action if isinstance(r.action, str) else r.action.value
        bufor.append((a, int(r.ts_recv), int(r.order_id), int(r.size)))
        if int(r.flags) & F_LAST:
            domknij(bufor)
            bufor = []
    if bufor:
        domknij(bufor)

    suma_kat = sum(kat.values())
    return dict(zdarzen_z_T=zdarzen_z_T, kategorie=dict(kat),
                suma_kategorii=suma_kat,
                niewyjasnione=zdarzen_z_T - suma_kat,
                adnotacje=dict(adn),
                agresorow_w_zdarzeniu=dict(agresorow_w_zdarzeniu))


def sekcja(tytul: str) -> None:
    print(f"\n{'=' * 68}\n  {tytul}\n{'=' * 68}")


def main() -> int:
    p = argparse.ArgumentParser(description="D5-C — audyt probki MBO")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()

    if not PLIK_MBO.exists():
        sys.exit(f"BRAK PLIKU: {PLIK_MBO}")

    print(f"plik: {PLIK_MBO}  ({PLIK_MBO.stat().st_size / 1e9:.3f} GB)")
    st = przebieg(args.limit)
    w: dict = {"rekordow": st.n, "limit": args.limit}

    sekcja("Q1  Czy F_LAST jest rzeczywiscie dostepne")
    z_last = sum(v for k, v in st.flagi.items() if k & F_LAST)
    print(f"  rekordow z F_LAST : {z_last:,} / {st.n:,} ({100 * z_last / st.n:.2f}%)")
    print(f"  rozklad flag      : {dict(sorted(st.flagi.items()))}")
    print(f"  rozklad akcji     : {dict(st.akcje)}")
    w["Q1"] = dict(z_flaga_last=z_last, flagi=dict(st.flagi), akcje=dict(st.akcje))

    sekcja("Q2  Jak F_LAST wyznacza granice zdarzenia")
    print(f"  zdarzen (grup do F_LAST wlacznie) : {st.zdarzen:,}")
    print(f"  srednio rekordow na zdarzenie     : {st.n / st.zdarzen:.3f}")
    print("  rozklad dlugosci zdarzenia (20 = 20+):")
    for k in sorted(st.rekordow_w_zdarzeniu)[:8]:
        print(f"    {k:>3} rek. : {st.rekordow_w_zdarzeniu[k]:>10,}")
    w["Q2"] = dict(zdarzen=st.zdarzen,
                   rozklad_dlugosci=dict(st.rekordow_w_zdarzeniu))

    sekcja("Q3  Jak lacza sie rekordy Trade i Fill")
    print(f"  zdarzen zawierajacych Trade   : {st.zdarzen_z_T:,}")
    print(f"  w tym dokladnie jeden Trade   : {st.zdarzen_z_dokladnie_1T:,} "
          f"({100 * st.zdarzen_z_dokladnie_1T / max(st.zdarzen_z_T, 1):.2f}%)")
    print(f"  zdarzen z Trade, ale bez Fill : {st.zdarzen_z_T_bez_F:,}")
    print(f"  rozklad liczby Trade w zdarzeniu: {dict(sorted(st.T_w_zdarzeniu.items()))}")
    w["Q3"] = dict(zdarzen_z_T=st.zdarzen_z_T,
                   dokladnie_1T=st.zdarzen_z_dokladnie_1T,
                   T_bez_F=st.zdarzen_z_T_bez_F,
                   rozklad_T=dict(st.T_w_zdarzeniu))

    sekcja("Q4  Czy Trade zawiera order_id agresora")
    razem_T = st.T_z_order_id + st.T_bez_order_id
    print(f"  rekordow Trade          : {razem_T:,}")
    print(f"  z niezerowym order_id   : {st.T_z_order_id:,} "
          f"({100 * st.T_z_order_id / max(razem_T, 1):.2f}%)")
    print(f"  z order_id == 0         : {st.T_bez_order_id:,}")
    w["Q4"] = dict(trade=razem_T, z_order_id=st.T_z_order_id,
                   bez_order_id=st.T_bez_order_id)

    sekcja("Q5  Czy zdarzenie dopasowania jest jednoznaczne")
    jedn = st.zdarzen_z_dokladnie_1T / max(st.zdarzen_z_T, 1)
    print(f"  zdarzen z dokladnie jednym Trade: {100 * jedn:.3f}%")
    print(f"  zdarzen z >1 Trade             : "
          f"{st.zdarzen_z_T - st.zdarzen_z_dokladnie_1T:,}")
    w["Q5"] = dict(udzial_jednoznacznych=jedn)

    sekcja("Q6  Czy suma pasywnych Fill zgadza sie z Trade")
    razem6 = st.zgodne_sumy + st.niezgodne_sumy
    print(f"  zdarzen sprawdzonych  : {razem6:,}")
    print(f"  suma Fill == size Trade: {st.zgodne_sumy:,} "
          f"({100 * st.zgodne_sumy / max(razem6, 1):.3f}%)")
    print(f"  niezgodnych           : {st.niezgodne_sumy:,}")
    print(f"  zdarzen, w ktorych Fill dostal TEZ agresor: "
          f"{st.zdarzen_z_fill_agresora:,} "
          f"({100 * st.zdarzen_z_fill_agresora / max(razem6, 1):.2f}%)")
    for x in st.przyklady_niezgodne:
        print(f"    przyklad: {x}")
    w["Q6"] = dict(sprawdzonych=razem6, zgodne=st.zgodne_sumy,
                   niezgodne=st.niezgodne_sumy,
                   z_fill_agresora=st.zdarzen_z_fill_agresora,
                   przyklady=st.przyklady_niezgodne)

    sekcja("Q6b  PELNY PODZIAL zdarzen z transakcja — mianownik")
    if args.limit:
        print("  POMINIETE — przebieg czesciowy (--limit)")
        w["Q6b"] = {"pominiete": "przebieg czesciowy"}
    else:
        pod = pelny_podzial()
        print(f"  zdarzen z transakcja      : {pod['zdarzen_z_T']:,}")
        for k in KATEGORIE:
            v = pod["kategorie"].get(k, 0)
            print(f"    {k:<24} : {v:>9,}")
        print(f"  suma kategorii            : {pod['suma_kategorii']:,}")
        print(f"  NIEWYJASNIONE             : {pod['niewyjasnione']:,}")
        print("  adnotacje (ortogonalne, moga sie nakladac):")
        for k, v in sorted(pod["adnotacje"].items()):
            print(f"    {k:<24} : {v:>9,}")
        print(f"  agresorow w zdarzeniu     : {pod['agresorow_w_zdarzeniu']}")
        w["Q6b"] = pod

    sekcja("Q7  Czy z MBO da sie odtworzyc posiadany schemat `trades`")
    if args.limit:
        print("  POMINIETE — przebieg czesciowy (--limit)")
        w["Q7"] = {"pominiete": "przebieg czesciowy"}
    else:
        tr = pl.from_pandas(
            db.DBNStore.from_file(PLIK_TRADES).to_df().reset_index())
        mbo = pl.DataFrame({
            "ts_recv": np.array(st.T_ts_recv, dtype="int64"),
            "price": np.array(st.T_price, dtype="int64"),
            "size": np.array(st.T_size, dtype="int64"),
        })
        lo, hi = mbo["ts_recv"].min(), mbo["ts_recv"].max()
        tr = tr.with_columns(
            pl.col("ts_recv").dt.epoch("ns").alias("ts_ns")
        ).filter((pl.col("ts_ns") >= lo) & (pl.col("ts_ns") <= hi))
        print(f"  Trade z MBO            : {mbo.height:,}")
        print(f"  rekordow w `trades`    : {tr.height:,}")
        print(f"  suma size MBO / trades : {int(mbo['size'].sum()):,} / "
              f"{int(tr['size'].sum()):,}")
        zgodne = (mbo.height == tr.height
                  and int(mbo["size"].sum()) == int(tr["size"].sum()))
        print(f"  liczba i wolumen zgodne: {'TAK' if zgodne else 'NIE'}")
        w["Q7"] = dict(trade_mbo=mbo.height, trades=tr.height,
                       size_mbo=int(mbo["size"].sum()),
                       size_trades=int(tr["size"].sum()), zgodne=zgodne)

    sekcja("Q8  Relacja MBO vs grupowanie po (ts_event, sequence)")
    te = np.array(st.T_ts_event, dtype="int64")
    sq = np.array(st.T_sequence, dtype="int64")
    ev = np.array(st.T_zdarzenie, dtype="int64")
    par = len({(int(x), int(y)) for x, y in zip(te, sq, strict=True)})
    zd_z_T = len(set(ev.tolist()))
    # ile par (ts_event, sequence) rozciaga sie na WIECEJ NIZ JEDNO zdarzenie
    mapa: dict[tuple[int, int], set[int]] = defaultdict(set)
    for x, y, e in zip(te, sq, ev, strict=True):
        mapa[(int(x), int(y))].add(int(e))
    rozjazd = sum(1 for v in mapa.values() if len(v) > 1)
    print(f"  rekordow Trade                     : {len(te):,}")
    print(f"  unikalnych par (ts_event, sequence): {par:,}")
    print(f"  zdarzen F_LAST zawierajacych Trade : {zd_z_T:,}")
    print(f"  par rozciagnietych na >1 zdarzenie : {rozjazd:,} "
          f"({100 * rozjazd / max(par, 1):.3f}%)")
    w["Q8"] = dict(trade=len(te), par_ts_event_sequence=par,
                   zdarzen_z_T=zd_z_T, par_na_wiele_zdarzen=rozjazd)

    sekcja("Q9  Czy brak snapshotu uniemozliwia ktorekolwiek z powyzszych")
    dodane = np.unique(np.array(st.add_ids, dtype="int64"))
    fille = np.array(st.fill_ids, dtype="int64")
    znane = np.isin(fille, dodane)
    print(f"  zlecen ADD w oknie          : {len(dodane):,} unikalnych")
    print(f"  rekordow FILL               : {len(fille):,}")
    print(f"  FILL do zlecen z tego okna  : {int(znane.sum()):,} "
          f"({100 * znane.mean():.2f}%)")
    print(f"  FILL do zlecen sprzed okna  : {int((~znane).sum()):,} "
          f"({100 * (~znane).mean():.2f}%)")
    w["Q9"] = dict(add_unikalnych=len(dodane), fill=len(fille),
                   fill_znane=int(znane.sum()), fill_nieznane=int((~znane).sum()))

    Path("reports").mkdir(exist_ok=True)
    Path("reports/D5_etap3_wyniki.json").write_text(
        json.dumps(w, indent=1, default=str), encoding="utf-8")
    print("\n-> reports/D5_etap3_wyniki.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
