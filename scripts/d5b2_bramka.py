#!/usr/bin/env python3
"""D5-B2 — bramka GO/NO-GO na miesiacu MBO. Spec: docs/D5_ETAP4_SPEC.md.

Logika w `engine/d5b2.py` (testowana na recznych przypadkach). Ten skrypt robi
wylacznie I/O: czyta pliki MBO, sprawdza kompletnosc sesji (§6 spec, §12.3
uzupelnienia), podaje strumien rekordow do logiki i drukuje wynik.

CZEGO NIE LICZY: przyszlych zwrotow, P&L, trwalosci znaku. **Licznik prob 0.**

BRAMKA JEST JEDNORAZOWA. Progi i mapowanie werdyktu sa zamrozone w spec i w
testach (`tests/test_d5b2.py`). Wyniku nie wolno "poprawiac" zmiana definicji
po jego zobaczeniu — reguly R2 i §5 spec.

Uruchomienie (na komputerze z danymi, venv aktywny):

    python scripts/d5b2_bramka.py --sesja 2026-07-03   # proba generalna: jedna
                                                       # sesja, kontrole, BEZ werdyktu
    python scripts/d5b2_bramka.py                      # pelny bieg (~100 min)

Pelny bieg jest WZNAWIALNY: okna kazdej sesji trafiaja do cache poza repo
(`<PROJECT_G_DATA_ROOT>/pochodne/d5b2_okna/`). Przerwany bieg (Ctrl+C) po
ponownym uruchomieniu pomija sesje juz policzone. `--od-nowa` ignoruje cache.

Kody wyjscia: 0 — werdykt wydany; 2 — STOP na kontroli danych, werdyktu brak.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from zoneinfo import ZoneInfo

import databento as db
import numpy as np
import polars as pl

KORZEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORZEN))

from engine.d5b2 import (  # noqa: E402
    StatyOkna,
    WynikSesji,
    obserwacje,
    ocen,
    porownaj_bary,
    przetworz_sesje,
    regresory,
    vif,
)
from engine.mbo_events import RekordMBO  # noqa: E402
from engine.paths import data_root  # noqa: E402
from scripts.fetch_d5b2_month import (  # noqa: E402
    KANONICZNY_D5C,
    SESJA_D5C,
    SESJE,
    SESJE_STARA_NORMALIZACJA,
    okno,
    sciezka_istniejaca,
    sciezka_manifestu,
)

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
BARY = KORZEN / "data" / "clean" / "mnq_1m_cont.parquet"
KONTRAKT = "MNQU6"
RAPORT = KORZEN / "reports" / "D5_b2_wyniki.json"
SCHEMAT_CACHE = 1


# ------------------------------------------------------------- pomocnicze ---
def granice_ns(sesja: str) -> tuple[int, int]:
    """RTH WYPROWADZONE ZE STREFY ET, w ns epoki — §2 spec."""
    y, m, d = map(int, sesja.split("-"))
    a = dt.datetime(y, m, d, 9, 30, tzinfo=ET).astimezone(UTC)
    b = dt.datetime(y, m, d, 16, 0, tzinfo=ET).astimezone(UTC)
    return int(a.timestamp()) * 10**9, int(b.timestamp()) * 10**9


def sha256_pliku(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for kawalek in iter(lambda: f.read(1 << 22), b""):
            h.update(kawalek)
    return h.hexdigest()


def wersja_kodu() -> str:
    """Zmiana logiki uniewaznia cache — inaczej stary wynik udawalby nowy."""
    h = hashlib.sha256()
    for p in ("engine/d5b2.py", "engine/mbo_events.py"):
        h.update((KORZEN / p).read_bytes())
    return h.hexdigest()[:16]


def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=KORZEN,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "nieznany"


def _pokaz(p: Path) -> str:
    """Sciezka do wydruku. NIGDY wyjatek — to ostatnia linia ~100-minutowego
    biegu; `relative_to` rzucal, gdy raport lezal poza repozytorium."""
    try:
        return str(p.relative_to(KORZEN))
    except ValueError:
        return str(p)


def _bez_nan(x):
    """JSON bez NaN — `null` zamiast nieprawidlowego literalu."""
    if isinstance(x, dict):
        return {str(k): _bez_nan(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_bez_nan(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if math.isnan(float(x)) else float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


# ------------------------------------------------------------ zrodla danych -
def strumien(p: Path, licznik: Counter) -> Iterator[tuple[RekordMBO, int]]:
    """Rekordy pliku DBN jako `(RekordMBO, sequence)`, w kolejnosci pliku.

    Liczy WSZYSTKIE rekordy (kontrola 2 §6 porownuje z ta sama liczba, co
    downloader) i instrumenty (plik ma zawierac wylacznie MNQU6).
    """
    for r in db.DBNStore.from_file(p):
        licznik["wszystkich"] += 1
        if not hasattr(r, "order_id"):
            licznik["nie_mbo"] += 1
            continue
        licznik[f"instrument_{int(r.instrument_id)}"] += 1
        akcja = r.action if isinstance(r.action, str) else r.action.value
        strona = r.side if isinstance(r.side, str) else r.side.value
        yield (RekordMBO(ts_recv=int(r.ts_recv), action=akcja, side=strona,
                         price=int(r.price), size=int(r.size),
                         order_id=int(r.order_id), flags=int(r.flags)),
               int(r.sequence))


def bary_dostawcy() -> dict[str, dict[int, tuple[int, int, int, int, int]]]:
    """Bary `ohlcv-1m` dostawcy dla MNQU6, ceny w jednostkach DBN (1e-9).

    Dla lipca 2026 offset back-adjustu MNQU6 wynosi 0 (ostatni kontrakt), wiec
    `open..close` to ceny surowe — sprawdzane ponizej, nie zakladane.
    """
    d = (pl.read_parquet(BARY)
         .filter(pl.col("contract") == KONTRAKT)
         .filter(pl.col("ts_utc") >= dt.datetime(2026, 7, 1, tzinfo=UTC)))
    if not (d["close"] == d["px_raw"]).all():
        sys.exit("STOP: bary MNQU6 w data/clean nie sa surowe (close != px_raw).")
    out: dict[str, dict[int, tuple[int, int, int, int, int]]] = {}
    for s in SESJE:
        lo, hi = granice_ns(s)
        sub = d.filter((pl.col("ts_utc") >= dt.datetime.fromtimestamp(lo / 1e9, UTC))
                       & (pl.col("ts_utc") < dt.datetime.fromtimestamp(hi / 1e9, UTC)))
        # Klucz minuty na CALKOWITYCH sekundach. `int(t.timestamp() * 1e9)`
        # byloby bledem: przy ~1,78e18 float ma rozdzielczosc 256 ns, wiec bar
        # dokladnie na granicy minuty mogl wypasc minute wczesniej.
        out[s] = {
            int(t.timestamp()) // 60: (round(o * 1e9), round(h * 1e9),
                                                round(lo_ * 1e9), round(c * 1e9), int(v))
            for t, o, h, lo_, c, v in sub.select(
                "ts_utc", "open", "high", "low", "close", "volume").iter_rows()}
    return out


def oczekiwania() -> dict[str, dict]:
    """Z manifestu: liczba rekordow i SHA kazdej sesji oraz jej wpis planu.

    Liczba rekordow WYLACZNIE z wpisow `wyniki[]` z `kompletny: true` — to
    zapis pliku, nie oczekiwanie wyceny. Dla 07-30 rezerwowo manifest D5-C.
    """
    cel = sciezka_manifestu()
    if not cel.exists():
        sys.exit(f"STOP: brak manifestu {cel}")
    man = json.loads(cel.read_text(encoding="utf-8"))
    plan = {w["sesja"]: w for w in man.get("plan", [])}
    out: dict[str, dict] = {s: {"plan": plan.get(s)} for s in SESJE}
    for w in man.get("wyniki", []):
        if w.get("kompletny") and w.get("sesja") in out:
            out[w["sesja"]].update(rekordow=int(w["rekordow"]),
                                   sha256=w.get("sha256"),
                                   pochodzenie=w.get("pochodzenie"))
    d5c = json.loads(KANONICZNY_D5C.read_text(encoding="utf-8"))
    e = out[SESJA_D5C]
    e.setdefault("rekordow", int(d5c["rekordow_wg_metadata"]))
    if not e.get("sha256"):
        e["sha256"] = d5c["sha256"]
    return out


# ----------------------------------------------------------------- cache ----
def _sciezka_cache(s: str) -> Path:
    return data_root() / "pochodne" / "d5b2_okna" / f"{s}.json"


def _klucz_cache(p: Path, rth: tuple[int, int], wersja: str) -> dict:
    st = p.stat()
    return {"schemat": SCHEMAT_CACHE, "plik": p.name, "bajtow": st.st_size,
            "mtime_ns": st.st_mtime_ns, "wersja_kodu": wersja, "rth": list(rth)}


def wczytaj_cache(s: str, klucz: dict) -> tuple[WynikSesji, Counter] | None:
    c = _sciezka_cache(s)
    if not c.exists():
        return None
    try:
        z = json.loads(c.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if z.get("klucz") != klucz:
        return None
    okna = {int(m): StatyOkna(**v) for m, v in z["okna"].items()}
    return WynikSesji(okna=okna, kontrola=z["kontrola"]), Counter(z["licznik"])


def zapisz_cache(s: str, klucz: dict, w: WynikSesji, licznik: Counter) -> None:
    c = _sciezka_cache(s)
    c.parent.mkdir(parents=True, exist_ok=True)
    tmp = c.with_suffix(".tmp")
    tmp.write_text(json.dumps({
        "klucz": klucz, "kontrola": w.kontrola, "licznik": dict(licznik),
        "okna": {str(m): v.jako_slownik() for m, v in w.okna.items()}}),
        encoding="utf-8")
    tmp.replace(c)          # atomowo — przerwany zapis nie zostawia polowy pliku


# ------------------------------------------------------------- jedna sesja --
def przelicz(p: Path, rth: tuple[int, int]) -> tuple[WynikSesji, Counter]:
    licznik: Counter = Counter()
    return przetworz_sesje(strumien(p, licznik), rth), licznik


def kontrole_sesji(s: str, p: Path, w: WynikSesji, licznik: Counter, sha: str,
                   ocz: dict, bary: dict) -> tuple[list[str], dict]:
    """§6 spec (z uzupelnieniem §12.3) + niezmienniki rekonstrukcji.

    Zwraca (powody STOP, slownik do raportu). Pusta lista = sesja kompletna.
    """
    stop: list[str] = []
    k = w.kontrola
    # 2. liczba rekordow
    if ocz.get("rekordow") is None:
        stop.append("brak liczby rekordow w manifescie (wyniki[] kompletny)")
    elif licznik["wszystkich"] != ocz["rekordow"]:
        stop.append(f"rekordow {licznik['wszystkich']:,} != manifest {ocz['rekordow']:,}")
    # 3. SHA-256
    if ocz.get("sha256"):
        sha_zrodlo = "manifest"
        if sha != ocz["sha256"]:
            stop.append("SHA-256 rozny od manifestu")
    else:
        sha_zrodlo = "zapisany_teraz"     # §12.3 — cztery stare sesje
    # 4. koszt i dokladny zakres UTC
    plan = ocz.get("plan") or {}
    a, b = okno(s)
    if plan.get("koszt_usd") is None:
        stop.append("brak kosztu w planie manifestu")
    if (plan.get("start_utc"), plan.get("end_utc")) != (a, b):
        stop.append(f"zakres UTC w manifescie {plan.get('start_utc')}..{plan.get('end_utc')} "
                    f"!= RTH {a}..{b}")
    # 5. rekonstrukcja ohlcv-1m == bary dostawcy
    porown = porownaj_bary(w.okna, bary[s])
    if porown["niezgodnych"]:
        stop.append(f"rekonstrukcja ohlcv-1m: {porown['niezgodnych']} niezgodnosci "
                    "z barami dostawcy")
    # niezmienniki
    instrumenty = [x for x in licznik if x.startswith("instrument_")]
    if len(instrumenty) != 1:
        stop.append(f"instrumentow w pliku: {len(instrumenty)} (oczekiwany 1)")
    if k["suma_n_trade"] != k["trade"]:
        stop.append(f"N1: suma n_trade {k['suma_n_trade']} != Trade {k['trade']}")
    if k["akcji_poza_rth"]:
        stop.append(f"{k['akcji_poza_rth']} akcji poza RTH")
    if k["trade_cena_niezdefiniowana"]:
        stop.append(f"{k['trade_cena_niezdefiniowana']} rekordow Trade bez ceny")
    raport = {"sha256": sha, "sha_zrodlo": sha_zrodlo, "bary": porown,
              "rekordow_w_pliku": licznik["wszystkich"],
              "rekordow_manifest": ocz.get("rekordow"),
              "pochodzenie_wpisu": ocz.get("pochodzenie"),
              "normalizacja": ("stara" if s in SESJE_STARA_NORMALIZACJA else "nowa"),
              "kontrola": k, "stop": stop}
    return stop, raport


# ------------------------------------------------------------------- main ---
def main() -> int:
    ap = argparse.ArgumentParser(description="D5-B2 — bramka GO/NO-GO")
    ap.add_argument("--sesja", help="tylko jedna sesja: kontrole, BEZ werdyktu")
    ap.add_argument("--od-nowa", action="store_true", help="ignoruj cache okien")
    args = ap.parse_args()

    sesje = [args.sesja] if args.sesja else list(SESJE)
    if args.sesja and args.sesja not in SESJE:
        sys.exit(f"STOP: {args.sesja} nie nalezy do 22 zamrozonych sesji.")
    wersja = wersja_kodu()
    print(f"D5-B2 bramka   kod {wersja}   git {git_sha()}   sesji {len(sesje)}\n",
          flush=True)
    ocz = oczekiwania()
    bary = bary_dostawcy()

    raport_sesji: dict[str, dict] = {}
    obs: dict[str, dict] = {}
    stopy: dict[str, list[str]] = {}
    t0 = time.monotonic()
    for i, s in enumerate(sesje, start=1):
        p = sciezka_istniejaca(s)
        if not p.exists():
            stopy[s] = [f"brak pliku {p}"]
            print(f"[{i:2}/{len(sesje)}] {s}  BRAK PLIKU {p}", flush=True)
            continue
        rth = granice_ns(s)
        t1 = time.monotonic()
        sha = sha256_pliku(p)
        klucz = _klucz_cache(p, rth, wersja)
        z = None if args.od_nowa else wczytaj_cache(s, klucz)
        try:
            w, licznik = z if z else przelicz(p, rth)
        except Exception as e:                       # noqa: BLE001
            # 1. §6: plik musi sie sparsowac
            stopy[s] = [f"plik nie parsuje sie: {type(e).__name__}: {e}"]
            print(f"[{i:2}/{len(sesje)}] {s}  BLAD PARSOWANIA: {e}", flush=True)
            continue
        if not z:
            zapisz_cache(s, klucz, w, licznik)
        stop, rap = kontrole_sesji(s, p, w, licznik, sha, ocz[s], bary)
        o = obserwacje(w, rth[0])
        rap["okien"] = int(len(o["m"]))
        rap["z_cache"] = bool(z)
        raport_sesji[s] = rap
        obs[s] = o
        if stop:
            stopy[s] = stop
        k = w.kontrola
        uplyw = time.monotonic() - t0
        print(f"[{i:2}/{len(sesje)}] {s}  {rap['normalizacja']:5}  "
              f"rek. {licznik['wszystkich']:>11,}  akcji {k['akcji']:>9,}  "
              f"okien {rap['okien']:>3}  bary {rap['bary']['wspolnych']:>3}/"
              f"{rap['bary']['niezgodnych']} niezg.  "
              f"{'cache' if z else f'{time.monotonic() - t1:5.0f} s'}  "
              f"{'OK' if not stop else 'STOP'}   [{uplyw / 60:5.1f} min]", flush=True)
        for powod in stop:
            print(f"      STOP: {powod}")

    # DETERMINIZM (Etap 2 §4 niezmienniki 6–7): najmniejsza sesja liczona drugi
    # raz od zera i porownana z wynikiem uzytym w bramce (tak samo z cache).
    kontrolna = "2026-07-03"
    if kontrolna in raport_sesji:
        w2, _ = przelicz(sciezka_istniejaca(kontrolna), granice_ns(kontrolna))
        o2 = obserwacje(w2, granice_ns(kontrolna)[0])
        zgodne = all(np.array_equal(o2[k], obs[kontrolna][k], equal_nan=True)
                     for k in o2)
        print(f"\ndeterminizm ({kontrolna} drugi raz od zera): "
              f"{'IDENTYCZNY' if zgodne else 'ROZNY'}")
        if not zgodne:
            stopy.setdefault(kontrolna, []).append("niedeterministyczny wynik")

    meta = {"wersja_kodu": wersja, "git": git_sha(),
            "utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            "databento": db.__version__, "sesji": len(sesje)}

    if args.sesja:
        print("\nTryb jednej sesji — BEZ werdyktu (proba generalna).")
        return 2 if stopy else 0

    RAPORT.parent.mkdir(exist_ok=True)
    if stopy:
        print("\n" + "=" * 64)
        print("  STOP NA KONTROLI DANYCH — WERDYKTU BRAK. Nic nie jest stracone:")
        print("  sesje policzone sa w cache, a bramka nie zostala uzyta.")
        for s, pw in stopy.items():
            for x in pw:
                print(f"    {s}: {x}")
        print("=" * 64)
        RAPORT.write_text(json.dumps(_bez_nan({
            "werdykt": None, "stop": stopy, "sesje": raport_sesji, "meta": meta}),
            indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
        print(f"\n-> {_pokaz(RAPORT)}")
        return 2

    wynik = ocen(obs)

    # OPISOWE, NIE wchodzi do werdyktu (§12.4): pooled VIF A osobno dla sesji
    # starej i nowej normalizacji. Miesiac jest niejednorodny i ta liczba ma
    # byc widoczna — ale bramka liczy sie na calosci, jak w spec.
    opis = {}
    for etykieta, grupa in (("stara", [s for s in obs if s in SESJE_STARA_NORMALIZACJA]),
                            ("nowa", [s for s in obs if s not in SESJE_STARA_NORMALIZACJA])):
        cz = [obs[s] for s in grupa if len(obs[s]["m"])]
        if cz:
            sk = {k: np.concatenate([c[k] for c in cz]) for k in cz[0]}
            opis[etykieta] = {"sesji": len(cz), "okien": int(len(sk["m"])),
                              "pooled_vif_A": vif(sk["A_count"], regresory(sk, pory=True))}

    a = wynik["wyniki"]["A_count"]
    print("\n=== TEST IDENTYFIKOWALNOSCI (A = I_count, GLOWNA) ===")
    print(f"  okien lacznie {a['okien']:,}   sesji {len(obs)}   "
          f"sesji z dziennym VIF {a['sesji_dziennych']}")
    for kol, nazwa in (("A_count", "A  I_count (GLOWNA)"), ("B_fill", "B  po Trade"),
                       ("C_volume", "C  I_volume")):
        x = wynik["wyniki"][kol]
        print(f"\n  {nazwa}")
        print(f"    pooled VIF (z pora dnia) : {x['pooled_vif']:9.3f}   R²={x['pooled_r2']:.4f}")
        print(f"    pooled VIF (bez pory)    : {x['pooled_vif_bez_pory']:9.3f}")
        print(f"    dzienny VIF: mediana {x['mediana_dzienna']:7.3f}  p10 {x['p10']:7.3f}  "
              f"p90 {x['p90']:7.3f}   ponizej 5: {100 * x['udzial_ponizej']:.1f}%")
        print(f"    max udzial jednej sesji w zmiennosci: {100 * x['max_koncentracja_sesji']:.2f}%")
    print(f"\n  strony: I>0 {100 * wynik['udzial_dodatnich']:.1f}%  "
          f"I<0 {100 * wynik['udzial_ujemnych']:.1f}%  I=0 {100 * wynik['udzial_zerowych']:.1f}%")
    print(f"  najslabsza sesja — mniejsza strona: {100 * wynik['min_strona_sesji']:.1f}% okien")
    print(f"  max udzial jednego kubelka 30-min: {100 * wynik['koncentracja_pory_dnia']:.2f}%")
    print("\n  opisowe (NIE wchodzi do werdyktu): pooled VIF A wg normalizacji")
    for e, v in opis.items():
        print(f"    {e:5}  sesji {v['sesji']:2}  okien {v['okien']:5}  VIF {v['pooled_vif_A']:.3f}")

    nazwy = {1: "pooled VIF < 5", 2: "mediana dziennego VIF < 5",
             3: ">= 75% kompletnych sesji z VIF < 5", 4: "zadna pora dnia > 20% zmiennosci",
             5: "najslabsza sesja >= 20% okien po slabszej stronie",
             6: "zadna sesja > 20% zmiennosci"}
    print("\n" + "=" * 64)
    for n, ok in wynik["warunki"].items():
        print(f"  {'OK ' if ok else 'NIE'}  {n}. {nazwy[n]}")
    print(f"  {'OK ' if wynik['abc_zgodne'] else 'NIE'}  A/B/C zgodne co do pooled VIF")
    print(f"\n  WERDYKT: {wynik['werdykt']}")
    print(f"  powod  : {wynik['powod']}")
    print("=" * 64)

    RAPORT.write_text(json.dumps(_bez_nan({
        **wynik, "opis_normalizacji": opis, "sesje": raport_sesji, "meta": meta}),
        indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"\n-> {_pokaz(RAPORT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
