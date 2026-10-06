"""D5-B2 — bramka identyfikowalnosci na kanonicznej jednostce. Czysta logika.

Specyfikacja nadrzedna: PLAN.pdf rozdz. 5.6 (bramka przed badaniem), 6 i 7
(aparat statystyczny). Specyfikacja szczegolowa, ZAMROZONA przed zakupem:
`docs/D5_ETAP4_SPEC.md` §1–§6, z uzupelnieniem ex ante §12. Model i progi
skopiowane 1:1 z `docs/D5_ETAP2_SPEC.md` §6–§8 i z ich jedynej dotychczasowej
implementacji, `scripts/audit_d5_etap2.py`. Zmienila sie WYLACZNIE jednostka
zdarzenia: zamiast `(ts_event, sequence, side)` — kanoniczna akcja agresywna
z `engine.mbo_events.rekonstruuj`.

CZEGO TEN MODUL NIE LICZY: przyszlych zwrotow, P&L, trwalosci znaku, Sharpe'a,
zadnego progu wejscia. Kazda zmienna pochodzi z TEGO SAMEGO okna 60 s.
**Licznik prob pozostaje 0.**

Bez I/O i bez `databento` — strumien rekordow podaje skrypt
`scripts/d5b2_bramka.py`. Dzieki temu kazda regula jest sprawdzalna testem na
recznie zbudowanych rekordach, bez danych rynkowych.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

import numpy as np

from engine.guards import assert_imbalance, assert_udzial, assert_vif
from engine.mbo_events import RekordMBO, rekonstruuj

# ------------------------------------------------- stale ZAMROZONE w spec ---
#: Okno obserwacji, §2 — 60 s wyrownane do pelnych minut wg `ts_recv`.
MIN_NS = 60_000_000_000
#: §5 warunki 1–3: prog VIF.
PROG_VIF = 5.0
#: §5 warunek 3: odsetek kompletnych sesji z VIF ponizej progu.
UDZIAL_SESJI = 0.75
#: §5 warunki 4 i 6: maksymalny udzial jednej pory dnia / jednej sesji
#: w zmiennosci `I_count`.
MAX_KONC = 0.20
#: §5 warunek 5: najslabsza sesja musi miec >= 20% okien po slabszej stronie.
MIN_STRONA = 0.20
#: Kubelek pory dnia — jak w implementacji Etapu 2 (13 kubelkow w RTH).
KUBELEK_MIN = 30
#: Dzienny VIF liczony tylko dla sesji z co najmniej tyloma oknami —
#: jak w implementacji Etapu 2 (`m.height < 50: continue`).
MIN_OKIEN_DZIENNY = 50
#: §2.3 i §6: sesja skrocona — w probie, ale poza wymogiem kompletnosci (war. 3).
SESJA_SKROCONA = "2026-07-03"

#: Cena niezdefiniowana w DBN (`UNDEF_PRICE`). Niesie ja m.in. wypelniacz `N`
#: nowej normalizacji. Rekord `T` z taka cena bylby anomalia danych.
UNDEF_PRICE = 2**63 - 1

#: Warunki, ktorych NIEspelnienie przy spelnionym warunku 1 oznacza, ze
#: identyfikacja pochodzi z roznic MIEDZY sesjami albo z PORY DNIA — §5 spec,
#: zdanie o `INCONCLUSIVE`. Mapowanie zapisane ex ante w §12.2.
WARUNKI_ZRODLA_IDENTYFIKACJI = frozenset({2, 3, 4, 6})


# ------------------------------------------------------------ akumulacja ----
@dataclass
class StatyOkna:
    """Wszystko, co jedno okno 60 s wnosi do bramki i do kontroli barow."""

    # rekordy `T` (wszystkie, takze strona N) — bar i momentum, §4
    t_n: int = 0
    t_wolumen: int = 0
    t_high: int = 0
    t_low: int = 0
    _klucz_pierwszy: tuple[int, int] | None = None
    _klucz_ostatni: tuple[int, int] | None = None
    t_open: int = 0
    t_close: int = 0
    # kontrole B i C — rekordy `T` po stronie agresora (bez strony N)
    t_buy: int = 0
    t_sell: int = 0
    v_buy: int = 0
    v_sell: int = 0
    # glowna A — kanoniczne akcje agresywne przypisane do TEGO okna, §1–§3
    n_buy: int = 0
    n_sell: int = 0
    n_none: int = 0

    def dodaj_trade(self, ts: int, seq: int, cena: int, rozmiar: int,
                    strona: str) -> None:
        """Rekord `T` o `ts_recv` w tym oknie.

        KOLEJNOSC `(ts_recv, sequence)` — §4 spec: `P_first`, `P_last` to cena
        pierwszego i ostatniego wypelnienia w tej kolejnosci. Liczymy ja
        jawnie, zamiast ufac kolejnosci pliku. Remis na `(ts, seq)` jest
        mozliwy (jedna wiadomosc CME niesie kilka transakcji) i wtedy rozstrzyga
        kolejnosc w pliku: pierwszy wygrywa przy `<`, ostatni przy `>=`.
        """
        klucz = (ts, seq)
        if self.t_n == 0:
            self.t_high = self.t_low = cena
            self._klucz_pierwszy = self._klucz_ostatni = klucz
            self.t_open = self.t_close = cena
        else:
            self.t_high = max(self.t_high, cena)
            self.t_low = min(self.t_low, cena)
            assert self._klucz_pierwszy is not None
            assert self._klucz_ostatni is not None
            if klucz < self._klucz_pierwszy:
                self._klucz_pierwszy, self.t_open = klucz, cena
            if klucz >= self._klucz_ostatni:
                self._klucz_ostatni, self.t_close = klucz, cena
        self.t_n += 1
        self.t_wolumen += rozmiar
        if strona == "B":
            self.t_buy += 1
            self.v_buy += rozmiar
        elif strona == "A":
            self.t_sell += 1
            self.v_sell += rozmiar

    def jako_slownik(self) -> dict[str, int]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


@dataclass
class WynikSesji:
    """Okna jednej sesji plus kontrola przebiegu. Nic wiecej nie wychodzi."""

    okna: dict[int, StatyOkna]
    kontrola: dict[str, int] = field(default_factory=dict)


class _Strumien:
    """Jeden przebieg po rekordach: filtr RTH, statystyki `T`, kontrole.

    Iterator, a nie lista — sesja ma do ~63 mln rekordow (§8 spec: przetwarzanie
    sesja po sesji, nigdy caly miesiac w pamieci).
    """

    def __init__(self, strumien: Iterable[tuple[RekordMBO, int]],
                 rth: tuple[int, int], okna: dict[int, StatyOkna],
                 k: dict[str, int]) -> None:
        self._it = iter(strumien)
        self._lo, self._hi = rth
        self._okna = okna
        self._k = k
        self._poprzedni_ts: int | None = None

    def __iter__(self) -> Iterator[RekordMBO]:
        return self

    def __next__(self) -> RekordMBO:
        k = self._k
        while True:
            r, seq = next(self._it)
            k["rekordow"] += 1
            ts = r.ts_recv
            if not (self._lo <= ts < self._hi):
                k["poza_rth"] += 1
                continue
            k["rekordow_rth"] += 1
            if self._poprzedni_ts is not None and ts < self._poprzedni_ts:
                k["ts_recv_wstecz"] += 1
            self._poprzedni_ts = ts
            if r.action == "T":
                k["trade"] += 1
                if not 0 < r.price < UNDEF_PRICE:
                    k["trade_cena_niezdefiniowana"] += 1
                else:
                    minuta = ts // MIN_NS
                    st = self._okna.get(minuta)
                    if st is None:
                        st = self._okna[minuta] = StatyOkna()
                    st.dodaj_trade(ts, seq, r.price, r.size, r.side)
            return r


def przetworz_sesje(strumien: Iterable[tuple[RekordMBO, int]],
                    rth: tuple[int, int]) -> WynikSesji:
    """Jedna sesja: okna 60 s z rekordow MBO podanych w kolejnosci pliku.

    `strumien` — pary `(RekordMBO, sequence)`. `sequence` jest potrzebne
    WYLACZNIE do kolejnosci `(ts_recv, sequence)` przy cenach okna (§4);
    rekonstrukcja akcji go nie uzywa, bo dostawca potwierdzil, ze nie jest
    identyfikatorem zdarzenia (D5-B INCONCLUSIVE).

    `rth` — granice `ts_recv` w ns, [poczatek, koniec). Rekordy spoza sa liczone
    i pomijane.
    """
    okna: dict[int, StatyOkna] = {}
    k: dict[str, int] = dict.fromkeys(
        ("rekordow", "rekordow_rth", "poza_rth", "ts_recv_wstecz", "trade",
         "trade_cena_niezdefiniowana", "akcji", "akcji_strona_N",
         "suma_n_trade", "n4_niezgodnych", "n4_niezgodnych_brzeg",
         "akcji_poza_rth"), 0)
    lo, hi = rth
    pierwsza, ostatnia = lo // MIN_NS, (hi - 1) // MIN_NS

    for a in rekonstruuj(_Strumien(strumien, rth, okna, k)):
        k["akcji"] += 1
        k["suma_n_trade"] += a.n_trade
        minuta = a.minuta                    # §1.5, §2.1: ts_recv OSTATNIEGO rekordu
        if not pierwsza <= minuta <= ostatnia:
            k["akcji_poza_rth"] += 1
            continue
        # N4 z dry runu: suma pasywnych Fill == rozmiar akcji. Na brzegach RTH
        # filtr ucina czesc rekordow akcji, wiec rozjazd jest tam mozliwy
        # i raportowany osobno. Wewnatrz sesji — raportowany jako anomalia.
        if a.rozmiar_pasywnych != a.rozmiar:
            if minuta in (pierwsza, ostatnia):
                k["n4_niezgodnych_brzeg"] += 1
            else:
                k["n4_niezgodnych"] += 1
        st = okna.get(minuta)
        if st is None:
            # Akcja moze zakonczyc sie w minucie bez wlasnego rekordu `T`
            # (ostatni rekord to `Fill`). Okno istnieje wtedy tylko po stronie A;
            # bez `T` nie ma ceny, wiec obserwacja i tak wypadnie jako brakujaca.
            st = okna[minuta] = StatyOkna()
        if a.side == "B":
            st.n_buy += 1
        elif a.side == "A":
            st.n_sell += 1
        else:
            # Etap 2 §4: strona NONE raportowana osobno, wykluczona ze znaku.
            st.n_none += 1
            k["akcji_strona_N"] += 1
    return WynikSesji(okna=okna, kontrola=k)


# ------------------------------------------------------------- obserwacje ---
def obserwacje(wynik: WynikSesji, rth_poczatek: int) -> dict[str, np.ndarray]:
    """Okna, ktore SA obserwacjami — §2.2: brakujace nie sa zerami.

    Okno jest obserwacja, gdy ma jednoczesnie: cene (>= 1 rekord `T`), strone
    dla kontroli B/C (>= 1 `T` z B lub A) i strone dla glownej A (>= 1 akcja
    B lub A). To jest `inner join` trzech tabel z implementacji Etapu 2.
    """
    wiersze = []
    for minuta in sorted(wynik.okna):
        s = wynik.okna[minuta]
        if s.t_n == 0 or (s.t_buy + s.t_sell) == 0 or (s.n_buy + s.n_sell) == 0:
            continue
        wiersze.append((minuta, s))

    n = len(wiersze)
    out = {
        "minuta": np.fromiter((m for m, _ in wiersze), dtype=np.int64, count=n),
        # R6: liczniki jako int64 ZE ZNAKIEM przed odejmowaniem.
        "n_buy": np.fromiter((s.n_buy for _, s in wiersze), dtype=np.int64, count=n),
        "n_sell": np.fromiter((s.n_sell for _, s in wiersze), dtype=np.int64, count=n),
        "t_buy": np.fromiter((s.t_buy for _, s in wiersze), dtype=np.int64, count=n),
        "t_sell": np.fromiter((s.t_sell for _, s in wiersze), dtype=np.int64, count=n),
        "v_buy": np.fromiter((s.v_buy for _, s in wiersze), dtype=np.int64, count=n),
        "v_sell": np.fromiter((s.v_sell for _, s in wiersze), dtype=np.int64, count=n),
        "wolumen": np.fromiter((s.t_wolumen for _, s in wiersze), dtype=np.int64, count=n),
        "p_first": np.fromiter((s.t_open for _, s in wiersze), dtype=np.int64, count=n),
        "p_last": np.fromiter((s.t_close for _, s in wiersze), dtype=np.int64, count=n),
    }
    out["A_count"] = (out["n_buy"] - out["n_sell"]) / (out["n_buy"] + out["n_sell"])
    out["B_fill"] = (out["t_buy"] - out["t_sell"]) / (out["t_buy"] + out["t_sell"])
    vs = out["v_buy"] + out["v_sell"]
    with np.errstate(invalid="ignore", divide="ignore"):
        out["C_volume"] = np.where(vs > 0, (out["v_buy"] - out["v_sell"]) / np.maximum(vs, 1),
                                   np.nan)
    # §4: m = log(P_last / P_first) — w TYM SAMYM oknie, bez przyszlosci.
    out["m"] = np.log(out["p_last"].astype(float) / out["p_first"].astype(float))
    # kubelek pory dnia: minuty od otwarcia RTH // 30 (0..12 w sesji pelnej)
    out["kubelek"] = (out["minuta"] - rth_poczatek // MIN_NS) // KUBELEK_MIN
    # R5: nierownowagi z konstrukcji w [-1, +1]. Pusta sesja (np. same okna
    # brakujace) nie ma czego sprawdzac — `min()` na pustej tablicy rzuca.
    if n:
        assert_imbalance(out["A_count"], nazwa="A_count")
        assert_imbalance(out["B_fill"], nazwa="B_fill")
        c = out["C_volume"][np.isfinite(out["C_volume"])]
        if c.size:
            assert_imbalance(c, nazwa="C_volume")
    return out


# ------------------------------------------------------- kontrola barow §6.5 -
def porownaj_bary(okna: dict[int, StatyOkna],
                  dostawca: dict[int, tuple[int, int, int, int, int]]) -> dict[str, int]:
    """Rekonstrukcja `ohlcv-1m` z rekordow `T` wobec barow dostawcy.

    `dostawca` — minuta -> (open, high, low, close, volume), ceny w jednostkach
    DBN (1e-9). Zgodnosc musi byc DOKLADNA: Etap 1 ustalil 1380/1380 barow
    identycznych na `ts_recv`, wiec kazdy rozjazd jest informacja o danych.
    """
    nasze = {m: s for m, s in okna.items() if s.t_n > 0}
    wspolne = sorted(set(nasze) & set(dostawca))
    wynik = {"wspolnych": len(wspolne),
             "tylko_nasze": len(set(nasze) - set(dostawca)),
             "tylko_dostawcy": len(set(dostawca) - set(nasze)),
             "open": 0, "high": 0, "low": 0, "close": 0, "volume": 0}
    for m in wspolne:
        s, (o, h, lo, c, v) = nasze[m], dostawca[m]
        wynik["open"] += s.t_open != o
        wynik["high"] += s.t_high != h
        wynik["low"] += s.t_low != lo
        wynik["close"] += s.t_close != c
        wynik["volume"] += s.t_wolumen != v
    wynik["niezgodnych"] = (wynik["tylko_nasze"] + wynik["tylko_dostawcy"]
                            + wynik["open"] + wynik["high"] + wynik["low"]
                            + wynik["close"] + wynik["volume"])
    return wynik


# ------------------------------------------------------------------- VIF ----
def _r2(y: np.ndarray, X: np.ndarray) -> float:
    """R^2 regresji Z WYRAZEM WOLNYM — identycznie jak w Etapie 2."""
    Xa = np.c_[np.ones(len(y)), X]
    beta, *_ = np.linalg.lstsq(Xa, y, rcond=None)
    r = y - Xa @ beta
    return float(1 - r.var() / y.var()) if y.var() > 0 else float("nan")


def vif(y: np.ndarray, X: np.ndarray) -> float:
    """VIF = 1 / (1 - R^2). NaN, gdy `y` jest stale — wtedy NIE jest < progu."""
    r2 = _r2(y, X)
    return float("nan") if np.isnan(r2) else 1.0 / max(1.0 - r2, 1e-12)


def regresory(o: dict[str, np.ndarray], pory: bool) -> np.ndarray:
    """§4: m + |m| + m^2 + sign(m) + log(1 + volume) [+ efekty pory dnia]."""
    m = o["m"]
    X = np.c_[m, np.abs(m), m ** 2, np.sign(m),
              np.log1p(o["wolumen"].astype(float))]
    if pory:
        k = o["kubelek"]
        for v in np.unique(k)[1:]:          # jeden kubelek jako baza
            X = np.c_[X, (k == v).astype(float)]
    return X


def _polacz(czesci: list[dict[str, np.ndarray]]) -> dict[str, np.ndarray]:
    return {k: np.concatenate([c[k] for c in czesci]) for k in czesci[0]}


def _koncentracja(y: np.ndarray, grupy: np.ndarray) -> float:
    """Najwiekszy udzial jednej grupy w sumie kwadratow odchylen od sredniej."""
    sr = y.mean()
    ss = np.array([((y[grupy == g] - sr) ** 2).sum() for g in np.unique(grupy)])
    return float(ss.max() / ss.sum()) if ss.sum() > 0 else float("nan")


# --------------------------------------------------------------- werdykt ----
def werdykt(warunki: dict[int, bool], abc_zgodne: bool) -> tuple[str, str]:
    """Werdykt z szesciu warunkow §5 — mapowanie zapisane ex ante w §12.2.

    GO            — wszystkie szesc ORAZ A/B/C zgodne co do pooled VIF
                    (`docs/D5_ETAP2_SPEC.md` §4a: „A daje GO, B/C nie" ->
                    INCONCLUSIVE),
    INCONCLUSIVE  — (a) wszystkie szesc, ale A/B/C niezgodne, albo
                    (b) warunek 1 spelniony, a wszystkie niespelnione naleza do
                    {2, 3, 4, 6}: identyfikacja pochodzi z roznic miedzy
                    sesjami (2, 3, 6) albo z pory dnia (4) — §5 spec,
    NO-GO         — kazdy inny uklad, w tym niespelniony warunek 1 albo 5.
    """
    if set(warunki) != {1, 2, 3, 4, 5, 6}:
        raise ValueError(f"oczekiwano warunkow 1-6, jest {sorted(warunki)}")
    niespelnione = {n for n, ok in warunki.items() if not ok}
    if not niespelnione:
        if abc_zgodne:
            return "D5-B2 GO", "wszystkie szesc warunkow i A/B/C zgodne"
        return "D5-B2 INCONCLUSIVE", "szesc warunkow spelnionych, ale A/B/C niezgodne"
    if warunki[1] and niespelnione <= WARUNKI_ZRODLA_IDENTYFIKACJI:
        return ("D5-B2 INCONCLUSIVE",
                "pooled VIF < 5, ale identyfikacja z roznic miedzy sesjami "
                f"albo z pory dnia (niespelnione: {sorted(niespelnione)})")
    return "D5-B2 NO-GO", f"niespelnione warunki: {sorted(niespelnione)}"


def ocen(sesje: dict[str, dict[str, np.ndarray]]) -> dict:
    """Szesc warunkow §5 na obserwacjach wszystkich sesji.

    `sesje` — nazwa sesji -> wynik `obserwacje()`. Sesja skrocona zostaje
    w probie (§2.3), ale nie liczy sie do wymogu kompletnosci (§6).
    """
    nazwy = sorted(s for s in sesje if len(sesje[s]["m"]))
    if not nazwy:
        raise ValueError("brak obserwacji w zadnej sesji")
    o = _polacz([sesje[s] for s in nazwy])
    etykiety = np.concatenate([np.full(len(sesje[s]["m"]), s) for s in nazwy])

    wyniki: dict[str, dict] = {}
    for kol in ("A_count", "B_fill", "C_volume"):
        maska = np.isfinite(o[kol])
        ok = {k: v[maska] for k, v in o.items()}
        et = etykiety[maska]
        y = ok[kol]
        r2p = _r2(y, regresory(ok, pory=True))
        r2b = _r2(y, regresory(ok, pory=False))
        vif_p = float("nan") if np.isnan(r2p) else 1 / max(1 - r2p, 1e-12)
        vif_b = float("nan") if np.isnan(r2b) else 1 / max(1 - r2b, 1e-12)
        dz: dict[str, float] = {}
        for s in nazwy:
            if s == SESJA_SKROCONA:
                continue
            m = et == s
            if m.sum() < MIN_OKIEN_DZIENNY:
                continue
            sub = {k: v[m] for k, v in ok.items()}
            dz[s] = vif(sub[kol], regresory(sub, pory=True))
        tab = np.array([v for v in dz.values() if np.isfinite(v)])
        if np.isfinite(vif_p):
            assert_vif([vif_p], nazwa=f"pooled VIF {kol}")
        if np.isfinite(vif_b):
            assert_vif([vif_b], nazwa=f"pooled VIF bez pory {kol}")
        if tab.size:
            assert_vif(tab, nazwa=f"dzienny VIF {kol}")
        dzienne = np.array(list(dz.values()))
        konc = _koncentracja(y, et)
        wyniki[kol] = {
            "pooled_vif": vif_p, "pooled_r2": r2p,
            "pooled_vif_bez_pory": vif_b, "pooled_r2_bez_pory": r2b,
            "dzienne_vif": dz,
            "mediana_dzienna": float(np.median(dzienne)) if dzienne.size else float("nan"),
            "p10": float(np.percentile(dzienne, 10)) if dzienne.size else float("nan"),
            "p90": float(np.percentile(dzienne, 90)) if dzienne.size else float("nan"),
            # NaN (stale I w sesji) NIE jest ponizej progu.
            "udzial_ponizej": float(np.mean(dzienne < PROG_VIF)) if dzienne.size else 0.0,
            "sesji_dziennych": int(dzienne.size),
            "max_koncentracja_sesji": konc,
            "okien": int(len(y)),
        }

    y = o["A_count"]
    konc_pory = _koncentracja(y, o["kubelek"])
    assert_udzial([konc_pory, wyniki["A_count"]["max_koncentracja_sesji"]],
                  nazwa="koncentracja zmiennosci A")
    strony = {}
    for s in nazwy:
        i_s = sesje[s]["A_count"]
        strony[s] = {"dod": float((i_s > 0).mean()), "uje": float((i_s < 0).mean())}
    min_strona = min(min(v["dod"], v["uje"]) for v in strony.values())
    assert_udzial([min_strona], nazwa="najslabsza strona agresji")

    a = wyniki["A_count"]
    warunki = {
        1: bool(a["pooled_vif"] < PROG_VIF),
        2: bool(a["mediana_dzienna"] < PROG_VIF),
        3: bool(a["udzial_ponizej"] >= UDZIAL_SESJI),
        4: bool(konc_pory <= MAX_KONC),
        5: bool(min_strona >= MIN_STRONA),
        6: bool(a["max_koncentracja_sesji"] <= MAX_KONC),
    }
    przechodzi = {k: bool(wyniki[k]["pooled_vif"] < PROG_VIF)
                  for k in ("A_count", "B_fill", "C_volume")}
    abc_zgodne = len(set(przechodzi.values())) == 1
    w, powod = werdykt(warunki, abc_zgodne)
    return {
        "werdykt": w, "powod": powod, "warunki": warunki,
        "abc_pooled_ponizej_progu": przechodzi, "abc_zgodne": abc_zgodne,
        "wyniki": wyniki, "koncentracja_pory_dnia": konc_pory,
        "min_strona_sesji": min_strona, "strony_sesji": strony,
        "okien_na_sesje": {s: int(len(sesje[s]["m"])) for s in sorted(sesje)},
        "udzial_dodatnich": float((y > 0).mean()),
        "udzial_ujemnych": float((y < 0).mean()),
        "udzial_zerowych": float((y == 0).mean()),
    }
