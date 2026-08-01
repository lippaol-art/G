#!/usr/bin/env python3
"""Partia 0 — benchmarki B01-B05.  PLAN.pdf rozdz. 8.4 (krok 1 i 3).

Uruchamia cztery publiczne setupy z parametrami wprost z literatury i zapisuje
wyniki jako TRWALA LINIE ODNIESIENIA dla wszystkich przyszlych kart.

**Zero zuzycia licznika prob.** Nie szukamy tu przewagi — mierzymy, ile daje
rzecz powszechnie znana. Karta wlasna, ktora nie pobije swojego benchmarku po
kosztach, nie jest oryginalna niezaleznie od tego, jak wyglada jej krzywa.

Wyjscie:
  reports/B00_benchmarks.md    — raport do czytania
  reports/benchmarks.json      — liczby do porownan maszynowych w krokach 3 i 4
                                 testu oryginalnosci
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.backtest import (  # noqa: E402
    CostModel,
    RiskLimits,
    default_slippage_points,
    run_backtest,
)
from engine.loader import is_available, load_continuous, to_bars  # noqa: E402
from engine.metrics import summarize  # noqa: E402
from engine.sessions import trade_date  # noqa: E402
from research.benchmarks import BENCHMARKI  # noqa: E402

RAPORT = Path("reports/B00_benchmarks.md")
JSON_OUT = Path("reports/benchmarks.json")
SYMBOL = "MNQ"

# Benchmark nie jest strategia — nie nakladamy na niego limitow ryzyka, bo
# mierzylibysmy limit, a nie setup. Karta wlasna bedzie miala limity wlaczone
# i to DZIALA NA JEJ NIEKORZYSC — czyli poprzeczka jest ustawiona uczciwie.
BEZ_LIMITOW = RiskLimits(daily_stop_r=1e9, weekly_stop_r=1e9, require_stop=False)


def dzienny_pnl(trades, wszystkie_dni: list) -> np.ndarray:
    """P&L per dzien sesyjny, po WSZYSTKICH dniach historii.

    Rozdz. 6.3 pulapka 2: liczenie odchylenia tylko po dniach czynnych zawyza
    Sharpe'a strategii rzadkiej. B02 handluje ~15% dni, B03 ~19% — bez tego
    ich Sharpe bylby nieporownywalny z B01 i B04.
    """
    per_day: dict = defaultdict(float)
    for t in trades:
        per_day[trade_date(t.exit_ts)] += t.pnl_usd
    return np.array([per_day.get(d, 0.0) for d in wszystkie_dni])


def main() -> int:
    if not is_available(SYMBOL):
        sys.exit(f"Brak danych {SYMBOL} — patrz HANDOFF.md")

    df = load_continuous(SYMBOL)
    bars = to_bars(df, price="adj")
    dni = sorted({b.trade_date for b in bars})
    print(f"Barow: {len(bars):,}, dni sesyjnych: {len(dni)}")

    wyniki: dict[str, dict] = {}
    for bid, (nazwa, Klasa, flat) in BENCHMARKI.items():
        print(f"\n[{bid}] {nazwa}...")
        r = run_backtest(bars, Klasa(), risk=BEZ_LIMITOW, force_flat=flat())
        # Stress-test x2 (bramka 7.6): podwojona prowizja I podwojony poslizg.
        # `stress_multiplier` w CostModel dotyczy tylko czlonu poslizgowego
        # w `round_turn_cost`, a silnik bierze poslizg z `slippage_model` —
        # wiec obie warstwy trzeba podwoic jawnie, inaczej stress bylby polowiczny.
        stress = run_backtest(
            bars, Klasa(), risk=BEZ_LIMITOW, force_flat=flat(),
            cost_model=CostModel(commission_rt=2.40),
            slippage_model=lambda b: 2.0 * default_slippage_points(b),
        )
        if not r.trades:
            print("   brak transakcji — pomijam")
            continue
        d = dzienny_pnl(r.trades, dni)
        m = summarize(np.array([t.r_multiple for t in r.trades]), d)

        # PF i win rate liczymy z P&L W DOLARACH, nie z R. Powod: B03 i B04 nie
        # maja stopa (tak brzmi ich regula literaturowa), wiec ich R jest
        # niezdefiniowane — `summarize` sygnalizuje to przez NaN. Wersja dolarowa
        # jest zdefiniowana zawsze i porownywalna miedzy benchmarkami.
        pnl = np.array([t.pnl_usd for t in r.trades])
        zyski, straty = pnl[pnl > 0].sum(), abs(pnl[pnl < 0].sum())
        pf_usd = float(zyski / straty) if straty > 0 else float("inf")
        win_usd = float(np.count_nonzero(pnl > 0) / pnl.size)
        lata: dict = defaultdict(float)
        for t in r.trades:
            lata[trade_date(t.exit_ts).year] += t.pnl_usd
        wyniki[bid] = dict(
            nazwa=nazwa, n_trades=m.n_trades, net_usd=r.net_usd, gross_usd=r.gross_usd,
            commission_usd=r.commission_usd, sharpe=m.sharpe, sharpe_lo=m.sharpe_lo_adjusted,
            profit_factor=pf_usd, win_rate=win_usd,
            expectancy_r=m.expectancy_r, r_metrics_valid=m.r_metrics_valid,
            expectancy_usd=float(pnl.mean()),
            max_drawdown=m.max_drawdown, max_dd_days=m.max_dd_duration_days,
            top5=m.top5_concentration, sqn=m.sqn,
            per_year={str(k): v for k, v in sorted(lata.items())},
            ambiguous_bars=r.ambiguous_bars, expired_orders=r.expired_orders,
            udzial_dni_czynnych=float(np.count_nonzero(d) / len(d)),
            net_usd_stress=stress.net_usd,
        )
        print(f"   N={m.n_trades} net=${r.net_usd:,.0f} SR={m.sharpe:.2f} PF={m.profit_factor:.2f}")

    # Teza o bramce ma byc POLICZONA, nie wpisana: gdyby ktorys benchmark ja
    # przeszedl, raport musi to powiedziec glosno, a nie powtorzyc wygodne zdanie.
    przechodzace = [b for b, w in wyniki.items()
                    if w["sharpe"] >= 0.8 and w["profit_factor"] >= 1.15]

    # ------------------------------------------------------------------
    L: list[str] = [
        "# Partia 0 — benchmarki B01-B05",
        "",
        f"*Wygenerowane przez `research/B00_benchmarks.py`, "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}. Instrument: {SYMBOL}, "
        f"{len(bars):,} barow M1, {len(dni)} dni sesyjnych.*",
        "",
        "**Status licznika prob: 0 zuzytych.** Benchmarki nie sa proba znalezienia",
        "przewagi — sa linia odniesienia, wzgledem ktorej mierzy sie przyrost kart",
        "wlasnych (rozdz. 8.4 krok 3). Parametry pochodza wprost z literatury i **nie",
        "byly dobierane**; kazde podkrecenie zanizaloby poprzeczke dla naszych hipotez.",
        "",
        "Koszty pelne (2.20 USD RT z poslizgiem segmentowym), limity ryzyka wylaczone.",
        "Karty wlasne beda testowane z limitami wlaczonymi — poprzeczka jest wiec",
        "ustawiona na ich niekorzysc, i tak ma byc.",
        "",
        "---",
        "",
        "## Wyniki zbiorcze",
        "",
        "| ID | Setup | Transakcji | Dni czynnych | Netto [USD] | Netto przy x2 kosztach | Sharpe | PF | Win% | MaxDD [USD] |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for bid, w in wyniki.items():
        L.append(f"| {bid} | {w['nazwa']} | {w['n_trades']:,} | {w['udzial_dni_czynnych']:.0%} | "
                 f"{w['net_usd']:+,.0f} | {w['net_usd_stress']:+,.0f} | "
                 f"{w['sharpe']:+.2f} | {w['profit_factor']:.2f} | "
                 f"{w['win_rate']:.0%} | {w['max_drawdown']:,.0f} |")
    L += [
        "| B05 | Dryf nocny, bezwarunkowo | 1 438 | 100% | — | — | **+0.47** | — | — | — |",
        "",
        "*(B05 zmierzony osobno w badaniu W001 — patrz `reports/W001_overnight_drift.md`.)*",
        "",
        "Prog projektu: Sharpe >= 0.8 i PF >= 1.15 (rozdz. 1.3). " + (
            "**Zaden z benchmarkow go nie osiaga** — i tak byc powinno: to setupy "
            "opisane publicznie kilkadziesiat lat temu, na instrumencie, ktorego "
            "wtedy nie bylo."
            if not przechodzace else
            "**UWAGA — prog osiagaja: " + ", ".join(przechodzace) + ".** Publiczny "
            "setup przechodzacy bramke projektu to sygnal do sprawdzenia silnika, "
            "nie do swietowania: albo mamy blad, albo trafilismy na okres, w ktorym "
            "efekt zyl. Przed jakimkolwiek wnioskiem — przeglad kodu tego benchmarku."
        ),
        "",
        "## Wynik per rok [USD netto]",
        "",
        "| ID | " + " | ".join(str(y) for y in range(2019, 2027)) + " |",
        "|---" * 9 + "|",
    ]
    for bid, w in wyniki.items():
        kom = " | ".join(f"{w['per_year'].get(str(y), 0.0):+,.0f}" for y in range(2019, 2027))
        L.append(f"| {bid} | {kom} |")

    L += [
        "",
        "> **PF i win rate liczone z P&L w dolarach, nie w R.** Reguly B03 i B04 nie",
        "> przewiduja stopa, wiec ich `r_multiple` jest niezdefiniowane. Wersja R-owa",
        "> zwrocilaby dla nich zera wygladajace jak pomiar — silnik sygnalizuje to",
        "> teraz jawnie jako NaN (`r_metrics_valid=false` w JSON-ie).",
        "",
        "---", "", "## Komentarz do poszczegolnych benchmarkow", ""]
    for bid, w in wyniki.items():
        L += [
            f"### {bid} — {w['nazwa']}",
            "",
            f"- transakcji: **{w['n_trades']:,}**, czynny w {w['udzial_dni_czynnych']:.0%} dni sesyjnych",
            f"- brutto {w['gross_usd']:+,.0f} USD, prowizje {w['commission_usd']:,.0f} USD, "
            f"**netto {w['net_usd']:+,.0f} USD**",
            f"- Sharpe {w['sharpe']:+.2f} (z poprawka Lo {w['sharpe_lo']:+.2f}), "
            f"PF {w['profit_factor']:.2f}, expectancy {w['expectancy_usd']:+.2f} USD/transakcje"
            + (f", {w['expectancy_r']:+.3f} R" if w["r_metrics_valid"]
               else " *(R niezdefiniowane — regula bez stopa)*"),
            f"- max DD {w['max_drawdown']:,.0f} USD przez {w['max_dd_days']} dni"
            + (f", koncentracja top-5 {w['top5']:.0%}" if not np.isnan(w["top5"])
               else ", koncentracja top-5 *(niezdefiniowana — setup stratny)*"),
            "",
        ]
        if not np.isnan(w["top5"]) and w["top5"] >= 0.40:
            L += [f"> **Koncentracja {w['top5']:.0%} przy progu 40% (rozdz. 1.3).** "
                  f"Piec najlepszych dni daje {w['top5']:.1f}x calego wyniku — reszta "
                  "historii jest netto ujemna. Setup dodatni w sumie, ale nie majacy "
                  "przewagi: to loteria z dodatnim losem, nie edge. Karta wlasna z takim "
                  "profilem zostalaby odrzucona przez bramke, i ten benchmark tez nie "
                  "jest poprzeczka do przeskoczenia — jest ostrzezeniem, jak wyglada "
                  "szum udajacy wynik.", ""]

        koszt = w["commission_usd"]
        if w["gross_usd"] > 0 > w["net_usd"]:
            L += [f"> **Setup zarabia brutto ({w['gross_usd']:+,.0f} USD), a traci netto.** "
                  f"Roznice zjadaja prowizje ({koszt:,.0f} USD). To najczestszy powod, dla "
                  "ktorego publiczne setupy 'dzialaja na wykresie' — rachunek robi sie bez kosztow.",
                  ""]

    L += [
        "---",
        "",
        "## Jak uzywac tych liczb",
        "",
        "Krok 3 testu oryginalnosci (rozdz. 8.4) wymaga, by karta wlasna wykazala",
        "**przyrost ponad najblizszy benchmark po kosztach**. Liczby maszynowe leza",
        "w `reports/benchmarks.json` — porownanie ma byc automatyczne, nie z pamieci.",
        "",
        "| Karta warunkujaca na... | Musi pobic |",
        "|---|---|",
        "| luce otwarcia | B01 |",
        "| kontrakcji zakresu / wybiciu | B02 |",
        "| dniu tygodnia | B03 |",
        "| porze dnia, momentum sesyjnym | B04 |",
        "| trzymaniu przez noc | B05 |",
        "",
        "**Pobicie benchmarku jest warunkiem koniecznym, nie wystarczajacym.** Karta",
        "musi dodatkowo przejsc krok 4 — ablacje pokazujace, ze jej wlasne warunki",
        "cokolwiek wnosza, a nie sa dekoracja wokol setupu publicznego.",
        "",
        "Odtworzenie: `python3 research/B00_benchmarks.py`",
    ]

    RAPORT.parent.mkdir(parents=True, exist_ok=True)
    RAPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    # NaN -> null. `json.dumps` domyslnie pisze goly `NaN`, ktorego scisle
    # parsery odrzucaja — a ten plik ma sluzyc porownaniom maszynowym w kroku 3
    # testu oryginalnosci, wiec musi byc czytelny takze poza Pythonem.
    def _bez_nan(x):
        if isinstance(x, dict):
            return {k: _bez_nan(v) for k, v in x.items()}
        if isinstance(x, float) and (np.isnan(x) or np.isinf(x)):
            return None
        return x

    JSON_OUT.write_text(json.dumps(
        _bez_nan({"symbol": SYMBOL, "n_bars": len(bars), "n_days": len(dni),
                  "generated": datetime.now(UTC).isoformat(timespec="seconds"),
                  "benchmarks": wyniki}),
        indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(f"\n-> {RAPORT}\n-> {JSON_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
