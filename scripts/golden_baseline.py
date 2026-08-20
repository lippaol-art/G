#!/usr/bin/env python3
"""Golden baseline Gen1 — zamrożenie zachowania systemu PRZED refaktorem.

PO CO TO ISTNIEJE. Refaktor przy 11 tysiącach linii potrafi stworzyć błąd
trudniejszy do zauważenia niż duplikacja, którą usuwa. Baseline jest jedyną
rzeczą, która pozwoli stwierdzić, że po porządkach system liczy TO SAMO.

TRZY WARSTWY, ROZDZIELONE CELOWO:

  dane      — odcisk zbiorów wejściowych (schemat, zakres, liczby, SHA-256)
  silnik    — zachowanie na ręcznych fixture'ach, z pełnym detalem transakcji
  walidacja — DSR/PBO/CPCV/SPA na deterministycznych wejściach
  raporty   — znormalizowany hash każdego raportu + wyciągnięte metryki

Rozdzielenie hasha DANYCH od hasha WYNIKÓW jest wymogiem, nie ozdobą: zmiana
danych i zmiana zachowania kodu muszą dać się odróżnić. Gdyby był jeden hash,
każde odświeżenie kalendarza wyglądałoby jak regresja silnika.

FORMAT KANONICZNY. Bez daty wykonania, bez ścieżek środowiskowych, bez
identyfikatorów losowych, stała kolejność kluczy, jawna precyzja. Hash całego
Markdown byłby bezużyteczny — raporty zawierają datę generacji, więc zmieniałyby
hash mimo identycznych obliczeń. Stąd normalizacja przed hashowaniem.

Wyjście: golden/baseline.json + golden/README.md
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.backtest import (  # noqa: E402
    AmbiguousBarPolicy,
    Bar,
    Order,
    run_backtest,
)
from engine.costs import CostModel  # noqa: E402
from engine.sessions import segment_of, trade_date  # noqa: E402

WYJSCIE = Path("golden/baseline.json")
WERSJA_SCHEMATU = 1
PREC = 10          # miejsc po przecinku dla liczb w baseline


def r(x: float) -> float:
    """Zaokrąglenie do zadeklarowanej precyzji — inaczej ostatni bit float
    potrafiłby zmienić hash mimo identycznych obliczeń."""
    return round(float(x), PREC)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------- dane -----
def odcisk_parquet(p: Path) -> dict:
    d = pl.read_parquet(p)
    schemat = {k: str(v) for k, v in sorted(d.schema.items())}
    out: dict = {
        "wierszy": int(d.height),
        "kolumn": int(d.width),
        "schemat": schemat,
        "sha256": sha(p.read_bytes()),
        "bajtow": p.stat().st_size,
    }
    if "trade_date" in d.columns:
        out["sesji"] = int(d["trade_date"].n_unique())
        out["od"] = str(d["trade_date"].min())
        out["do"] = str(d["trade_date"].max())
    if "symbol" in d.columns:
        out["symboli"] = int(d["symbol"].n_unique())
    if "contract" in d.columns:
        out["kontraktow"] = int(d["contract"].n_unique())
    if "split_factor" in d.columns:
        out["wspolczynnikow_splitu"] = int(d["split_factor"].n_unique())
    return out


def odcisk_csv(p: Path) -> dict:
    tekst = p.read_text(encoding="utf-8")
    wiersze = tekst.splitlines()
    return {
        "wierszy": len(wiersze) - 1,
        "naglowek": wiersze[0] if wiersze else "",
        "sha256": sha(p.read_bytes()),
        "bajtow": p.stat().st_size,
    }


def warstwa_dane() -> dict:
    out: dict = {"parquet": {}, "csv": {}, "manifesty": {}}
    for p in sorted(Path("data/clean").glob("*.parquet")):
        out["parquet"][p.name] = odcisk_parquet(p)
    for p in sorted(Path("data/clean/k6").glob("*.parquet")):
        out["parquet"]["k6/" + p.name] = odcisk_parquet(p)
    for p in sorted(Path("data/clean").glob("*.csv")):
        out["csv"][p.name] = odcisk_csv(p)
    for p in sorted(Path("data").glob("manifest*.md")):
        out["manifesty"][p.name] = sha(p.read_bytes())
    return out


# -------------------------------------------------------------- silnik -----
def _bar(i: int, o: float, h: float, low: float, c: float, v: int = 100,
         seg: str = "midday") -> Bar:
    """Bar o deterministycznym znaczniku — bez zależności od zegara."""
    return Bar(ts=datetime(2024, 3, 5, 15, i, tzinfo=UTC), open=o, high=h, low=low,
               close=c, volume=v, segment=seg,
               trade_date=datetime(2024, 3, 5).date())


class _Raz:
    """Strategia składająca jedno zlecenie na barze 0 i nic więcej."""

    def __init__(self, order: Order):
        self.order, self.i = order, -1

    def on_bar(self, bar, history, state):
        self.i += 1
        return [self.order] if self.i == 0 else []


def _przebieg(nazwa: str, bary: list[Bar], order: Order, **kw) -> dict:
    wynik = run_backtest(bary, _Raz(order), **kw)
    t = wynik.trades[0] if wynik.trades else None
    return {
        "nazwa": nazwa,
        "transakcji": len(wynik.trades),
        "barow_spornych": wynik.ambiguous_bars,
        "zablokowanych_zerowym_wolumenem": wynik.skipped_zero_volume,
        "odrzuconych_zlecen": wynik.rejected_orders,
        "wygaslych_zlecen": wynik.expired_orders,
        "transakcja": None if t is None else {
            "strona": str(t.side),
            "ts_wejscia": t.entry_ts.isoformat(),
            "cena_wejscia": r(t.entry_px),
            "ts_wyjscia": t.exit_ts.isoformat(),
            "cena_wyjscia": r(t.exit_px),
            "powod_wyjscia": t.exit_reason,
            "pnl_punkty": r(t.pnl_points),
            "prowizja_usd": r(t.commission_usd),
            "pnl_usd_brutto": r(t.pnl_usd_gross),
            "pnl_usd_netto": r(t.pnl_usd),
            "r_multiple": r(t.r_multiple),
        },
        "equity_koncowe": r(wynik.equity[-1]) if wynik.equity else None,
    }


def warstwa_silnik() -> dict:
    """Zachowanie na ręcznych fixture'ach. Każdy przypadek to osobne założenie."""
    zero = CostModel(commission_rt=0.0)
    przypadki = []

    # 1-2. long i short o znanym wyniku, bez kosztów — symetria musi być dokładna
    rosnace = [_bar(0, 100, 101, 99, 100), _bar(1, 100, 106, 100, 105),
               _bar(2, 105, 106, 104, 105)]
    przypadki.append(_przebieg("long_market_bez_kosztow", rosnace,
                               Order(side="long", kind="mkt", sl=90.0, tp=105.0),
                               cost_model=zero, slippage_model=lambda b: 0.0))
    malejace = [_bar(0, 100, 101, 99, 100), _bar(1, 100, 100, 94, 95),
                _bar(2, 95, 96, 94, 95)]
    przypadki.append(_przebieg("short_market_bez_kosztow", malejace,
                               Order(side="short", kind="mkt", sl=110.0, tp=95.0),
                               cost_model=zero, slippage_model=lambda b: 0.0))

    # 3-4. SL i TP dotknięte w jednym barze — obie polityki
    sporny = [_bar(0, 100, 101, 99, 100), _bar(1, 100, 101, 99, 100),
              _bar(2, 100, 110, 90, 100)]
    for polityka in (AmbiguousBarPolicy.SL_WINS, AmbiguousBarPolicy.TP_WINS):
        przypadki.append(_przebieg(f"sporny_bar_{polityka}", sporny,
                                   Order(side="long", kind="mkt", sl=95.0, tp=105.0),
                                   cost_model=zero, slippage_model=lambda b: 0.0,
                                   policy=polityka))

    # 5. stop przeskoczony luką — wypełnienie na OTWARCIU, nie na poziomie stopa
    luka = [_bar(0, 100, 101, 99, 100), _bar(1, 100, 101, 99, 100),
            _bar(2, 80, 82, 78, 80)]
    przypadki.append(_przebieg("stop_przeskoczony_luka", luka,
                               Order(side="long", kind="mkt", sl=95.0),
                               cost_model=zero, slippage_model=lambda b: 0.0))

    # 6. bar o zerowym wolumenie nie może wykonać zlecenia
    bez_obrotu = [_bar(0, 100, 101, 99, 100), _bar(1, 100, 101, 99, 100, v=0),
                  _bar(2, 100, 101, 99, 100)]
    przypadki.append(_przebieg("zerowy_wolumen_blokuje_wejscie", bez_obrotu,
                               Order(side="long", kind="mkt", sl=95.0),
                               cost_model=zero, slippage_model=lambda b: 0.0))

    # 7. koszty domyślne — prowizja musi się pojawić bez proszenia
    przypadki.append(_przebieg("koszty_domyslne", rosnace,
                               Order(side="long", kind="mkt", sl=90.0, tp=105.0)))

    # 8. zlecenie limitowe wymaga penetracji o tick
    limit_bary = [_bar(0, 100, 101, 99, 100), _bar(1, 100, 101, 98.0, 99),
                  _bar(2, 99, 100, 98, 99)]
    przypadki.append(_przebieg("limit_wymaga_penetracji", limit_bary,
                               Order(side="long", kind="limit", px=98.0, sl=95.0),
                               cost_model=zero, slippage_model=lambda b: 0.0))

    # 9. determinizm — dwa identyczne przebiegi muszą dać identyczny wynik
    a = _przebieg("determinizm_a", rosnace,
                  Order(side="long", kind="mkt", sl=90.0, tp=105.0))
    b = _przebieg("determinizm_b", rosnace,
                  Order(side="long", kind="mkt", sl=90.0, tp=105.0))
    deterministyczny = {k: v for k, v in a.items() if k != "nazwa"} == \
                       {k: v for k, v in b.items() if k != "nazwa"}

    # sesje: segmenty i trade_date w punktach granicznych, w tym DST
    punkty = [
        ("2024-03-05T23:30:00+00:00", "zwykly_wieczor"),
        ("2024-03-05T14:35:00+00:00", "rth_open_zima"),
        ("2024-07-05T13:35:00+00:00", "rth_open_lato"),
        ("2024-03-10T07:30:00+00:00", "przejscie_na_letni"),
        ("2024-11-03T06:30:00+00:00", "przejscie_na_zimowy"),
        ("2024-12-24T18:30:00+00:00", "wigilia"),
    ]
    sesje = {
        nazwa: {
            "segment": segment_of(datetime.fromisoformat(ts)),
            "trade_date": str(trade_date(datetime.fromisoformat(ts))),
        }
        for ts, nazwa in punkty
    }

    return {"przypadki": przypadki, "deterministyczny": deterministyczny,
            "sesje": sesje}


# ----------------------------------------------------------- walidacja -----
def _macierz(n_obs: int, n_war: int, przewaga: float, seed: int) -> np.ndarray:
    """Deterministyczna macierz wariantów do PBO/SPA.

    UWAGA O REGULE "ZERO DANYCH SYNTETYCZNYCH". Ta macierz nie jest danymi
    badawczymi i nie wynika z niej żaden wniosek o rynku — to fixture aparatu
    statystycznego, dokładnie jak ręczne bary w testach silnika. Ziarno jest
    stałe, więc wejście jest tą samą liczbą przy każdym przebiegu; gdyby było
    losowe, baseline nie mógłby się odtworzyć.
    """
    rng = np.random.default_rng(seed)
    M = rng.normal(0.0, 1.0, size=(n_obs, n_war))
    if przewaga:
        M[:, 0] += przewaga
    return M


def warstwa_walidacja() -> dict:
    """Aparat statystyczny na deterministycznych wejściach — stałe ziarna."""
    from validation.cpcv import expected_n_paths, make_cpcv
    from validation.dsr import days_to_certify, deflated_sharpe_annualized
    from validation.montecarlo import (
        bootstrap_expectancy,
        permutation_test,
        synthetic_pvalue,
    )
    from validation.pbo import probability_of_backtest_overfitting
    from validation.power import (
        conditional_edge_multiplier,
        minimum_detectable_effect,
        required_sample_size,
    )
    from validation.spa import superior_predictive_ability
    from validation.walkforward import embargo_for, make_split

    out: dict = {}

    # DSR — tablica z PLAN rozdz. 6.5. To jest test regresyjny na liczbach,
    # które są już opublikowane w dokumencie założycielskim.
    out["dsr"] = {
        f"sr{sr}_T{T}_neff{n}": r(deflated_sharpe_annualized(sr, T, n).dsr)
        for sr in (0.8, 1.0, 1.2, 1.5) for T in (1500,) for n in (1, 5, 10, 30)
    }
    out["dsr_dni_do_certyfikacji"] = {
        f"sr{sr}_neff1": days_to_certify(sr_annual=sr, n_eff=1)
        for sr in (0.8, 1.0, 1.2, 1.5)
    }

    # Moc testu — N ≈ 384 / 785 / 1051 przy E=0.12R, sigma=1.2R
    out["moc_testu"] = {
        f"moc{int(m * 100)}": required_sample_size(power=m).n_required
        for m in (0.5, 0.8, 0.9)
    }
    out["mde_n400"] = r(minimum_detectable_effect(400))
    out["mnoznik_warunkowy"] = {
        f"f{f}": r(conditional_edge_multiplier(f)) for f in (1.0, 0.5, 0.25, 0.1)
    }

    # CPCV — liczba ścieżek jest własnością kombinatoryczną, nie parametrem
    split = make_cpcv(600, n_blocks=6, k_test=2)
    out["cpcv"] = {
        "sciezek": split.n_paths,
        "oczekiwanych": expected_n_paths(6, 2),
        "granice_blokow": [list(b) for b in split.block_bounds],
        "test_i_trening_rozlaczne": all(
            not (set(p.test_blocks) & set(p.train_blocks)) for p in split.paths
        ),
        "purge_zawsze_niepusty": all(bool(p.purged_blocks) for p in split.paths),
    }

    # Walk-forward — okna i embargo na kalendarzu, bez danych
    from datetime import date
    s = make_split(date(2019, 4, 14), date(2026, 7, 31))
    out["walkforward"] = {
        "okien": len(s),
        "oos_dni_lacznie": s.oos_days_total,
        "lockbox_od": str(s.lockbox_start),
        "purge_pierwszego_okna_dni": s.windows[0].purge_days,
        "embargo_intraday_s": int(embargo_for("intraday").total_seconds()),
        "embargo_swing_s": int(embargo_for("swing", max_position_days=5).total_seconds()),
    }

    # PBO — dwa przypadki o znanej odpowiedzi: czysty szum (~0.5) i realna przewaga (~0)
    out["pbo"] = {
        "szum": r(probability_of_backtest_overfitting(_macierz(500, 8, 0.0, 11)).pbo),
        "z_przewaga": r(
            probability_of_backtest_overfitting(_macierz(500, 8, 0.25, 11)).pbo
        ),
    }

    # SPA — obie ścieżki implementacji, przy braku przewagi i przy przewadze.
    #
    # ŚCIEŻKA `arch` JEST W TYM MOMENCIE WADLIWA i baseline to utrwala celowo.
    # `arch.bootstrap.SPA` przyjmuje STRATY (mniej = lepiej), a moduł podaje mu
    # ZWROTY — znak jest odwrócony, więc testowana jest hipoteza przeciwna.
    # Widać to wprost: przy przewadze 1.0σ na 400 obserwacjach (t≈20) ścieżka
    # arch zwraca p=0.12, a własny fallback p=0.002. Żaden wynik badawczy tym
    # nie stoi — SPA nie było użyte w W001-W013, licznik prób wynosi 0.
    # Naprawa jest pozycją nr 1 planu refaktoru i ŚWIADOMIE zmieni hash wyników;
    # dlatego rejestrujemy też fallback, który po naprawie ma zostać bez zmian.
    out["spa"] = {}
    for nazwa, przewaga in (("szum", 0.0), ("z_przewaga", 0.30)):
        for sciezka, wymus in (("arch", False), ("fallback", True)):
            w = superior_predictive_ability(
                _macierz(400, 6, przewaga, 22), n_bootstrap=500, seed=7,
                force_fallback=wymus,
            )
            out["spa"][f"{nazwa}_{sciezka}"] = {
                "p": r(w.pvalue),
                "najlepszy_wariant": w.best_variant,
                "sredni_wynik": r(w.best_mean),
                "implementacja": w.implementation,
            }

    # Monte Carlo — permutacja, bootstrap blokowy vs iid, p-wartość syntetyków.
    # Szereg AR(1) o phi=0.85, bo cały sens bootstrapu blokowego ujawnia się
    # DOPIERO przy zależności; na szeregu iid oba warianty są równoważne
    # i niezmiennik "blokowy szerszy" nie miałby treści.
    rng = np.random.default_rng(33)
    seria = np.zeros(600)
    for i in range(1, 600):
        seria[i] = 0.85 * seria[i - 1] + rng.normal(0.01, 0.05)
    perm = permutation_test(seria, n_permutations=1000, seed=5)
    blok = bootstrap_expectancy(seria, block=True, mean_block_len=20.0,
                                n_resamples=1000, seed=5)
    iid = bootstrap_expectancy(seria, block=False, n_resamples=1000, seed=5)
    out["montecarlo"] = {
        "mdd_obserwowany": r(perm.mdd_observed),
        "mdd_p95": r(perm.mdd_p95),
        "bootstrap_blokowy": {"punkt": r(blok.point_estimate), "dol": r(blok.ci_low),
                              "gora": r(blok.ci_high), "szerokosc": r(blok.width)},
        "bootstrap_iid": {"dol": r(iid.ci_low), "gora": r(iid.ci_high),
                          "szerokosc": r(iid.width)},
        # niezmiennik, nie liczba: blokowy MUSI być szerszy od iid
        "blokowy_szerszy_niz_iid": bool(blok.width > iid.width),
        "p_syntetykow": r(synthetic_pvalue(1.5, _macierz(1000, 1, 0.0, 44)[:, 0])),
    }
    return out


# -------------------------------------------------------------- metryki -----
def warstwa_metryki() -> dict:
    """Metryki wyniku na stałym wektorze R — najbardziej krytyczna warstwa
    raportowania, bo z niej biorą się progi bramki z rozdz. 1.3."""
    from engine.metrics import drawdown_stats, summarize

    r_mult = np.array([1.5, -1.0, 2.0, -1.0, 0.5, -1.0, 3.0, -1.0, 1.0, -0.5,
                       0.8, -1.0, 1.2, -1.0, 2.5])
    dzienne = r_mult * 100.0
    m = summarize(r_mult, dzienne)
    mdd, dni = drawdown_stats(np.cumsum(dzienne))
    return {
        "n": m.n_trades,
        "expectancy_r": r(m.expectancy_r),
        "profit_factor": r(m.profit_factor),
        "win_rate": r(m.win_rate),
        "payoff": r(m.payoff_ratio),
        "sharpe": r(m.sharpe),
        "sharpe_lo": r(m.sharpe_lo_adjusted),
        "sortino": r(m.sortino),
        "mdd": r(m.max_drawdown),
        "mar": r(m.mar),
        "sqn": r(m.sqn),
        "koncentracja_top5": r(m.top5_concentration),
        "bramki": m.gate_report(),
        "dd_z_equity": [r(mdd), int(dni)],
    }


# ------------------------------------------------------------- raporty -----
_ZMIENNE = [
    re.compile(r"^\*Wygenerowane.*$", re.M),          # data generacji
    re.compile(r"^\*Pobrane.*$", re.M),
    re.compile(r"/home/[^\s`]*"),                     # ścieżki środowiskowe
]


def znormalizuj(tekst: str) -> str:
    """Usuwa z raportu wszystko, co zmienia się bez zmiany obliczeń."""
    for wz in _ZMIENNE:
        tekst = wz.sub("", tekst)
    return "\n".join(w.rstrip() for w in tekst.splitlines() if w.strip())


#: Metryki wyciągane jawnie z raportów. Klucz -> (plik, wzorzec).
#: Regex, który przestanie pasować, jest sam w sobie sygnałem — dlatego
#: brakująca metryka trafia do baseline jako null, a nie jest pomijana.
METRYKI = {
    "W009_korelacja_10_30": ("W009_H013_preflight.md",
                             r"korelacja\(rezyduum, zwrot 09:31→10:30\) \| \*\*([+-][\d.]+)"),
    "W010_h001_beta_wolumen_t": ("W010_partia3_preflight.md",
                                 r"β₂ percentyl wolumenu\*\* \| [+-][\d.]+ \| \*\*([+-][\d.]+)"),
    "W010_h002_pochodzenie_t": ("W010_partia3_preflight.md",
                                r"Roznica odsetka powrotow \(swieze vs odziedziczone\) \| "
                                r"t = \*\*([+-][\d.]+)"),
    "W011_oos_r2_pelny": ("W011_model_nocny_oos.md",
                          r"pelny \(skladniki \+ ES \+ SOXX\) \| ([\d.]+)"),
    "W011_obciazenie_zdarzenia": ("W011_model_nocny_oos.md",
                                  r"sesje zdarzen \| \d+ \| [\d.]+ \| ([+-][\d.]+)‱"),
    "W013_beta_ranga_t": ("W013_H003_preflight.md",
                          r"\*\*β ranga ilorazu\*\* \| \*\*[+-][\d.]+\*\* \| \*\*([+-][\d.]+)"),
    "W013_ablacja_iloraz": ("W013_H003_preflight.md",
                            r"\*\*iloraz \\\|I\\\|/R\*\* \(karta\) \| \d+ \| ([+-][\d.]+)"),
    "W013_ablacja_wielkosc": ("W013_H003_preflight.md",
                              r"sama wielkosc \\\|I\\\| \(odpowiednik H014\) \| \d+ \| ([+-][\d.]+)"),
}


def warstwa_raporty() -> dict:
    out: dict = {"hashe": {}, "metryki": {}}
    for p in sorted(Path("reports").glob("*.md")):
        out["hashe"][p.name] = sha(znormalizuj(p.read_text(encoding="utf-8")).encode())
    for klucz, (plik, wz) in sorted(METRYKI.items()):
        sciezka = Path("reports") / plik
        if not sciezka.exists():
            out["metryki"][klucz] = None
            continue
        m = re.search(wz, sciezka.read_text(encoding="utf-8"), re.S)
        out["metryki"][klucz] = float(m.group(1)) if m else None
    return out


# ------------------------------------------------------------- rejestr -----
def warstwa_rejestr() -> dict:
    licznik = json.loads(Path("validation/trial_counter.json").read_text(encoding="utf-8"))
    rej = Path("hypotheses/REGISTRY.md").read_text(encoding="utf-8")
    statusy = {}
    for m in re.finditer(r"\| (H\d{3}) \|.*?\| ([^|]*?(?:REJECTED|IDEA|CANDIDATE)[^|]*?) \|",
                         rej):
        statusy.setdefault(m.group(1), re.sub(r"[*\[\]()]|\.md", "", m.group(2)).strip())
    return {
        "licznik_prob": licznik["total_trials"],
        "statusy_kart": dict(sorted(statusy.items())),
        "kart_odrzuconych": sum(1 for v in statusy.values() if "REJECTED" in v),
    }


WARSTWY_WYNIKOW = ("silnik", "metryki", "walidacja", "raporty", "rejestr")


def zbuduj() -> dict:
    baseline = {
        "schema_version": WERSJA_SCHEMATU,
        "precyzja": PREC,
        "dane": warstwa_dane(),
        "silnik": warstwa_silnik(),
        "metryki": warstwa_metryki(),
        "walidacja": warstwa_walidacja(),
        "raporty": warstwa_raporty(),
        "rejestr": warstwa_rejestr(),
    }
    # Rozdzielone hashe: danych i wyników. Zmiana danych i zmiana zachowania
    # kodu muszą dać się odróżnić — przy jednym hashu każde odświeżenie
    # kalendarza wyglądałoby jak regresja silnika.
    baseline["hash_danych"] = sha(json.dumps(
        baseline["dane"], ensure_ascii=False, sort_keys=True).encode())
    baseline["hash_wynikow"] = sha(json.dumps(
        {k: baseline[k] for k in WARSTWY_WYNIKOW},
        ensure_ascii=False, sort_keys=True).encode())
    return baseline


def _splaszcz(obj: object, prefiks: str = "") -> dict[str, object]:
    """Spłaszcza zagnieżdżony słownik do ścieżek — żeby raport rozbieżności
    wskazywał KONKRETNĄ wartość, a nie 'gałąź walidacja się zmieniła'."""
    if isinstance(obj, dict):
        out: dict[str, object] = {}
        for k, v in obj.items():
            out.update(_splaszcz(v, f"{prefiks}.{k}" if prefiks else str(k)))
        return out
    if isinstance(obj, list):
        out = {}
        for i, v in enumerate(obj):
            out.update(_splaszcz(v, f"{prefiks}[{i}]"))
        return out
    return {prefiks: obj}


def sprawdz() -> int:
    """Porównuje bieżące zachowanie z zapisanym baseline'em. To jest bramka
    refaktoru: każda rozbieżność musi być ZAMIERZONA i opisana, inaczej
    refaktor zmienił wynik."""
    if not WYJSCIE.exists():
        print(f"BRAK {WYJSCIE} — najpierw uruchom bez --sprawdz")
        return 2
    stary = json.loads(WYJSCIE.read_text(encoding="utf-8"))
    nowy = zbuduj()

    if stary.get("schema_version") != nowy["schema_version"]:
        print(f"SCHEMAT: {stary.get('schema_version')} -> {nowy['schema_version']} "
              "— porównanie wartość po wartości nie jest miarodajne")

    a, b = _splaszcz(stary), _splaszcz(nowy)
    tylko_stare = sorted(set(a) - set(b))
    tylko_nowe = sorted(set(b) - set(a))
    rozne = sorted(k for k in set(a) & set(b) if a[k] != b[k])

    for etykieta, klucze in (("USUNIETE", tylko_stare), ("NOWE", tylko_nowe)):
        for k in klucze:
            print(f"{etykieta:9s} {k}")
    for k in rozne:
        print(f"ROZNICA   {k}: {a[k]!r} -> {b[k]!r}")

    zgodne = not (tylko_stare or tylko_nowe or rozne)
    print(f"\ndane   : {'OK' if stary.get('hash_danych') == nowy['hash_danych'] else 'ZMIANA'}")
    print(f"wyniki : {'OK' if stary.get('hash_wynikow') == nowy['hash_wynikow'] else 'ZMIANA'}")
    print("BASELINE ZGODNY" if zgodne else f"ROZBIEZNOSCI: {len(rozne)} zmian, "
          f"{len(tylko_stare)} usunietych, {len(tylko_nowe)} nowych")
    return 0 if zgodne else 1


def main(argv: list[str]) -> int:
    if "--sprawdz" in argv:
        return sprawdz()

    baseline = zbuduj()
    WYJSCIE.parent.mkdir(parents=True, exist_ok=True)
    WYJSCIE.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"-> {WYJSCIE}")
    print(f"   hash danych : {baseline['hash_danych']}")
    print(f"   hash wynikow: {baseline['hash_wynikow']}")
    print(f"   przypadkow silnika: {len(baseline['silnik']['przypadki'])}, "
          f"deterministyczny: {baseline['silnik']['deterministyczny']}")
    print(f"   raportow: {len(baseline['raporty']['hashe'])}, "
          f"metryk: {sum(1 for v in baseline['raporty']['metryki'].values() if v is not None)}"
          f"/{len(baseline['raporty']['metryki'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
