#!/usr/bin/env python3
"""W016 — pre-flight H017: czy przewaga agresorow w minucie t zapowiada t+1.

Specyfikacja: `hypotheses/H017.md`, zamrozona w commicie `efa4a8f` PRZED
napisaniem tego kodu. Ten kod wykonuje sekcje 9 (P1–P6) i 10 (ablacje) karty
i NIE MOZE niczego do nich dodawac ani z nich ujmowac.

**Zero zuzytych prob.** Pre-flight bada rozklady na zbiorze deweloperskim
(lipiec 2026), nie uruchamia zadnego wariantu z sekcji 8 karty.

Dane: `data/clean/d5b2_okna/` — tabele minutowe bramki D5-B2. Obserwacje
budowane ta sama funkcja co w bramce (`engine.d5b2.obserwacje`), wiec definicja
okna jest identyczna z ta, na ktorej wydano `D5-B2 GO`.

Uruchomienie:
    python research/W016_H017_preflight.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

KORZEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORZEN))

from engine.d5b2 import StatyOkna, WynikSesji, obserwacje  # noqa: E402

KATALOG = KORZEN / "data" / "clean" / "d5b2_okna"
RAPORT_MD = KORZEN / "reports" / "W016_H017_preflight.md"
RAPORT_JSON = KORZEN / "reports" / "W016_H017_preflight.json"
ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

# ------------------------------------------- progi ZAMROZONE w karcie §5, §9 -
KOSZT_PKT = 1.10          # 2,20 USD RT / 2 USD za punkt
KOSZT_STRESS_PKT = 2.20   # stress-test x2 — raportowany, nie rozstrzyga
P1_MIN_SESJI = 18         # z 22
P2_MIN_T = 2.0
P3_MIN_KROKOW = 3         # z 4
P6_MIN_SESJI = 15         # z 22
SESJE_STARE = frozenset({"2026-07-01", "2026-07-02", "2026-07-03",
                         "2026-07-06", "2026-07-30"})


# --------------------------------------------------------------- dane --------
def rth_poczatek_ns(sesja: str) -> int:
    y, m, d = map(int, sesja.split("-"))
    a = dt.datetime(y, m, d, 9, 30, tzinfo=ET).astimezone(UTC)
    return int(a.timestamp()) * 10**9


def wczytaj(katalog: Path = KATALOG) -> dict[str, dict[str, np.ndarray]]:
    """Obserwacje bramki per sesja — ta sama definicja okna co w D5-B2."""
    out = {}
    for p in sorted(katalog.glob("*.json")):
        z = json.loads(p.read_text(encoding="utf-8"))
        okna = {int(m): StatyOkna(**v) for m, v in z["okna"].items()}
        out[p.stem] = obserwacje(WynikSesji(okna=okna), rth_poczatek_ns(p.stem))
    return out


def trojki(o: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Pary (t -> t+1) z karty §6: t, t+1, t+2 to KOLEJNE minuty z obserwacja.

    Δ_{t+1} = P_first(t+2) − P_first(t+1): wejscie po pierwszej transakcji
    minuty nastepnej, wyjscie po pierwszej transakcji minuty po niej. Nic
    z minuty t nie wchodzi do Δ, a nic z t+1 i t+2 nie wchodzi do I_t ani m_t.
    """
    mi = o["minuta"]
    n = len(mi)
    if n < 3:
        return {k: np.array([]) for k in ("I", "I_nast", "B", "C", "m", "delta", "minuta")}
    i = np.arange(n - 2)
    ok = (mi[i + 1] == mi[i] + 1) & (mi[i + 2] == mi[i] + 2)
    i = i[ok]
    return {
        "I": o["A_count"][i],
        "I_nast": o["A_count"][i + 1],
        "B": o["B_fill"][i],
        "C": o["C_volume"][i],
        "m": (o["p_last"][i] - o["p_first"][i]) / 1e9,
        "delta": (o["p_first"][i + 2] - o["p_first"][i + 1]) / 1e9,
        "minuta": mi[i],
    }


# ---------------------------------------------------------- statystyka -------
def ols_klastry(y: np.ndarray, X: np.ndarray, grupy: np.ndarray
                ) -> tuple[np.ndarray, np.ndarray]:
    """OLS z bledami standardowymi grupowanymi (CR1). `X` BEZ wyrazu wolnego.

    Zwraca (beta, se) z wyrazem wolnym na pozycji 0. CR1 = sandwich z korekta
    G/(G−1)·(N−1)/(N−K) — standard (Stata `cluster`). Przy 22 grupach to jest
    przyblizenie, nie dokladna wartosc; karta to wie i daje prog t >= 2.
    """
    Xa = np.c_[np.ones(len(y)), X]
    n, k = Xa.shape
    xtx_inv = np.linalg.inv(Xa.T @ Xa)
    beta = xtx_inv @ Xa.T @ y
    u = y - Xa @ beta
    meat = np.zeros((k, k))
    ug = np.unique(grupy)
    for g in ug:
        s = Xa[grupy == g].T @ u[grupy == g]
        meat += np.outer(s, s)
    G = len(ug)
    c = (G / (G - 1)) * ((n - 1) / (n - k)) if G > 1 else 1.0
    V = c * xtx_inv @ meat @ xtx_inv
    return beta, np.sqrt(np.diag(V))


def ols_beta(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    Xa = np.c_[np.ones(len(y)), X]
    return np.linalg.lstsq(Xa, y, rcond=None)[0]


def kwintyle(x: np.ndarray, sesja_idx: np.ndarray, minuta: np.ndarray) -> np.ndarray:
    """Etykiety 0..4: sortowanie po (x, sesja, minuta), piec grup rownej liczby.

    Karta §6: deterministycznie, takze przy remisach — `I_count` ma wiele
    powtarzajacych sie wartosci (np. 0, ±1/3), a podzial po progach wartosci
    dawalby grupy o nierownej licznosci zaleznej od remisow.
    """
    kolejnosc = np.lexsort((minuta, sesja_idx, x))
    etykiety = np.empty(len(x), dtype=int)
    for q, idx in enumerate(np.array_split(kolejnosc, 5)):
        etykiety[idx] = q
    return etykiety


def werdykt(p: dict[str, bool]) -> tuple[str, str]:
    """Tabela kategorii z karty §9 — kolejnosc wierszy jest kolejnoscia regul."""
    if not p["P1"]:
        return "REJECTED (pre-flight)", "BRAK — brak trwalosci znaku, mechanizm nie istnieje"
    if not p["P2"]:
        return ("REJECTED (pre-flight)",
                "MECHANIZM — przeplyw trwa, cena nie (propagator)")
    if not (p["P3"] and p["P4"] and p["P6"]):
        return "REJECTED (pre-flight)", "MECHANIZM — efekt pozorny lub niestabilny"
    if not p["P5"]:
        return "REJECTED (pre-flight)", "KOSZTY"
    return "PASSED (pre-flight)", "wszystkie P1–P6 spelnione — na lipcu nic nie certyfikuje"


# ------------------------------------------------------------- analiza -------
def _polacz(sesje: dict[str, dict[str, np.ndarray]]):
    nazwy = sorted(sesje)
    cz = {s: trojki(sesje[s]) for s in nazwy}
    nazwy = [s for s in nazwy if len(cz[s]["I"])]
    d = {k: np.concatenate([cz[s][k] for s in nazwy]) for k in cz[nazwy[0]]}
    d["sesja"] = np.concatenate([np.full(len(cz[s]["I"]), s) for s in nazwy])
    d["sesja_idx"] = np.concatenate([np.full(len(cz[s]["I"]), i)
                                     for i, s in enumerate(nazwy)])
    return nazwy, d


def _efekt(y, x, m, grupy, z_m: bool = True) -> dict:
    X = np.c_[x, m] if z_m else x[:, None]
    b, se = ols_klastry(y, X, grupy)
    return {"wsp": float(b[1]), "se": float(se[1]), "t": float(b[1] / se[1])}


def _kwintyle_srednie(y, x, sesja_idx, minuta) -> list[float]:
    q = kwintyle(x, sesja_idx, minuta)
    return [float(y[q == k].mean()) for k in range(5)]


def analizuj(sesje: dict[str, dict[str, np.ndarray]]) -> dict:
    nazwy, d = _polacz(sesje)
    dt_ = d["delta"] - d["delta"].mean()          # Δ̃ — karta §6
    g = d["sesja_idx"]

    # P1 — trwalosc znaku
    kor_pula = float(np.corrcoef(d["I"], d["I_nast"])[0, 1])
    kor_sesje = {s: float(np.corrcoef(d["I"][d["sesja"] == s],
                                      d["I_nast"][d["sesja"] == s])[0, 1])
                 for s in nazwy}
    n_dod_p1 = sum(v > 0 for v in kor_sesje.values())

    # P2 — przyrost ponad momentum
    p2 = _efekt(dt_, d["I"], d["m"], g)

    # P3, P4, P5 — kwintyle I_t
    sr = _kwintyle_srednie(dt_, d["I"], g, d["minuta"])
    kroki = int(sum(b > a for a, b in zip(sr, sr[1:], strict=False)))
    rozpietosc = (sr[4] - sr[0]) / 2

    # P6 — stabilnosc
    wsp_sesje = {}
    for s in nazwy:
        mk = d["sesja"] == s
        wsp_sesje[s] = float(ols_beta(dt_[mk], np.c_[d["I"][mk], d["m"][mk]])[1])
    n_dod_p6 = sum(v > 0 for v in wsp_sesje.values())
    jackknife = {}
    for s in nazwy:
        mk = d["sesja"] != s
        jackknife[s] = float(ols_beta(dt_[mk], np.c_[d["I"][mk], d["m"][mk]])[1])

    p = {
        "P1": bool(kor_pula > 0 and n_dod_p1 >= P1_MIN_SESJI),
        "P2": bool(p2["wsp"] > 0 and p2["t"] >= P2_MIN_T),
        "P3": bool(kroki >= P3_MIN_KROKOW and sr[4] > sr[0]),
        "P4": bool(sr[4] > 0 and sr[0] < 0),
        "P5": bool(rozpietosc >= KOSZT_PKT),
        "P6": bool(n_dod_p6 >= P6_MIN_SESJI and all(v > 0 for v in jackknife.values())),
    }
    status, kategoria = werdykt(p)

    # ablacje §10 — raportowane, nie zmieniaja werdyktu
    def _rozp(x: np.ndarray) -> float:
        s = _kwintyle_srednie(dt_, x, g, d["minuta"])
        return float((s[4] - s[0]) / 2)

    ablacje = {
        "1_C_wolumen": {**_efekt(dt_, d["C"], d["m"], g), "rozpietosc": _rozp(d["C"])},
        "2_B_trade": {**_efekt(dt_, d["B"], d["m"], g), "rozpietosc": _rozp(d["B"])},
        "3_bez_m": _efekt(dt_, d["I"], d["m"], g, z_m=False),
        "4_samo_m": _efekt(dt_, d["m"], d["m"], g, z_m=False),
    }
    # opisowe: normalizacja
    opis_norm = {}
    for etyk, maska in (("stara", np.isin(d["sesja"], list(SESJE_STARE))),
                        ("nowa", ~np.isin(d["sesja"], list(SESJE_STARE)))):
        if maska.sum():
            opis_norm[etyk] = {"par": int(maska.sum()),
                               **_efekt(dt_[maska], d["I"][maska], d["m"][maska], g[maska])}

    return {
        "status": status, "kategoria": kategoria, "przewidywania": p,
        "par": int(len(dt_)), "sesji": len(nazwy),
        "srednia_delta_pkt": float(d["delta"].mean()),
        "sd_delta_pkt": float(d["delta"].std()),
        "P1": {"korelacja_pula": kor_pula, "sesji_dodatnich": n_dod_p1,
               "korelacje_sesji": kor_sesje},
        "P2": p2,
        "P3_P4_P5": {"srednie_kwintyli_pkt": sr, "krokow_rosnacych": kroki,
                     "rozpietosc_pkt": rozpietosc,
                     "przechodzi_stress_x2": bool(rozpietosc >= KOSZT_STRESS_PKT)},
        "P6": {"sesji_dodatnich": n_dod_p6, "wsp_sesji": wsp_sesje,
               "jackknife_min": min(jackknife.values()),
               "jackknife_max": max(jackknife.values())},
        "ablacje": ablacje, "opis_normalizacji": opis_norm,
    }


# --------------------------------------------------------------- raport ------
def _f(x: float, n: int = 3) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def raport_md(w: dict) -> str:
    p = w["przewidywania"]
    k = w["P3_P4_P5"]
    a = w["ablacje"]
    ok = {True: "✅", False: "❌"}
    lin = [
        "# W016 — pre-flight H017: kontynuacja przepływu agresywnego",
        "",
        "Karta: [`hypotheses/H017.md`](../hypotheses/H017.md), zamrożona w "
        "`efa4a8f` przed napisaniem tego kodu. Kod: "
        "`research/W016_H017_preflight.py`. Dane: `data/clean/d5b2_okna/` "
        "(lipiec 2026 — **zbiór deweloperski**).",
        "",
        f"**Werdykt: `{w['status']}` — {w['kategoria']}.**",
        "",
        f"Par (t → t+1): **{w['par']:,}**".replace(",", " ")
        + f" w **{w['sesji']}** sesjach. Ruch Δ: średnia "
        f"{_f(w['srednia_delta_pkt'], 2)} pkt, odchylenie "
        f"{_f(w['sd_delta_pkt'], 2)} pkt. **Licznik prób: 0.**",
        "",
        "## Przewidywania P1–P6 (progi z karty §9)",
        "",
        "| # | Wynik | Próg | |",
        "|---|---|---|---|",
        f"| P1 trwałość znaku | korelacja `I_t`–`I_t+1` **{_f(w['P1']['korelacja_pula'])}**, "
        f"dodatnia w **{w['P1']['sesji_dodatnich']}/{w['sesji']}** sesjach | > 0 i ≥ 18/22 | {ok[p['P1']]} |",
        f"| P2 przyrost ponad momentum | wsp. **{_f(w['P2']['wsp'])}** pkt, "
        f"t = **{_f(w['P2']['t'], 2)}** | > 0 i t ≥ 2,0 | {ok[p['P2']]} |",
        f"| P3 monotoniczność | rośnie w **{k['krokow_rosnacych']}/4** krokach | ≥ 3/4 i Q5 > Q1 | {ok[p['P3']]} |",
        f"| P4 symetria | Q5 **{_f(k['srednie_kwintyli_pkt'][4], 2)}**, "
        f"Q1 **{_f(k['srednie_kwintyli_pkt'][0], 2)}** pkt | Q5 > 0, Q1 < 0 | {ok[p['P4']]} |",
        f"| P5 koszty | (Q5 − Q1)/2 = **{_f(k['rozpietosc_pkt'], 2)}** pkt | ≥ 1,10 pkt | {ok[p['P5']]} |",
        f"| P6 stabilność | dodatni w **{w['P6']['sesji_dodatnich']}/{w['sesji']}** sesjach; "
        f"jackknife {_f(w['P6']['jackknife_min'])} … {_f(w['P6']['jackknife_max'])} "
        f"| ≥ 15/22 i jackknife > 0 | {ok[p['P6']]} |",
        "",
        "Średnie `Δ̃` (pkt) w kwintylach `I_t`, Q1 → Q5: "
        + " · ".join(_f(x, 2) for x in k["srednie_kwintyli_pkt"]),
        "",
        f"Stress-test ×2 (2,20 pkt, raportowany, nie rozstrzyga): "
        f"{'spełniony' if k['przechodzi_stress_x2'] else 'NIE spełniony'}.",
        "",
        "## Ablacje (karta §10 — raportowane, nie zmieniają werdyktu)",
        "",
        "| # | Ablacja | wsp. | t | (Q5 − Q1)/2 |",
        "|---|---|---|---|---|",
        f"| — | **`A` (karta)** | {_f(w['P2']['wsp'])} | {_f(w['P2']['t'], 2)} | {_f(k['rozpietosc_pkt'], 2)} |",
        f"| 1 | `A` → `C` (wolumen) | {_f(a['1_C_wolumen']['wsp'])} | {_f(a['1_C_wolumen']['t'], 2)} | {_f(a['1_C_wolumen']['rozpietosc'], 2)} |",
        f"| 2 | `A` → `B` (rekordy Trade) | {_f(a['2_B_trade']['wsp'])} | {_f(a['2_B_trade']['t'], 2)} | {_f(a['2_B_trade']['rozpietosc'], 2)} |",
        f"| 3 | bez kontroli `m_t` | {_f(a['3_bez_m']['wsp'])} | {_f(a['3_bez_m']['t'], 2)} | — |",
        f"| 4 | samo `m_t` (benchmark momentum) | {_f(a['4_samo_m']['wsp'])} | {_f(a['4_samo_m']['t'], 2)} | — |",
        "",
        "## Opisowe: normalizacja (nie wchodzi do werdyktu)",
        "",
        "| Grupa | par | wsp. przy `I_t` | t |",
        "|---|---|---|---|",
    ]
    for e, v in w["opis_normalizacji"].items():
        lin.append(f"| {e} | {v['par']} | {_f(v['wsp'])} | {_f(v['t'], 2)} |")
    lin += [
        "",
        "## Czego ten raport NIE mówi",
        "",
        "Lipiec jest zbiorem deweloperskim: 22 sesje to 5% podłogi N ≥ 400 "
        "(karta §5). Pre-flight może kartę **odrzucić**, nie może jej "
        "**potwierdzić**. Błędy grupowane przy 22 grupach są przybliżeniem.",
        "",
    ]
    return "\n".join(lin)


def main() -> int:
    sesje = wczytaj()
    if len(sesje) != 22:
        sys.exit(f"STOP: oczekiwano 22 sesji w {KATALOG}, jest {len(sesje)}")
    w = analizuj(sesje)
    RAPORT_JSON.write_text(json.dumps(w, indent=1, ensure_ascii=False),
                           encoding="utf-8", newline="\n")
    RAPORT_MD.write_text(raport_md(w), encoding="utf-8", newline="\n")
    print(raport_md(w))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
