"""Testy aparatu walidacji silnika — PLAN.pdf rozdz. 5.6.

Uwaga na rekurencje pojeciowa: to sa testy TESTOW. Sprawdzaja nie to, czy
silnik jest poprawny, tylko czy narzedzie do wykrywania jego niepoprawnosci
w ogole cokolwiek wykrywa. Test, ktory zawsze przechodzi, jest gorszy niz brak
testu — daje spokoj sumienia bez pokrycia.

Dlatego kazdy check ma tu pare: przebieg na zdrowym silniku (ma przejsc)
i przebieg na wstrzyknietej usterce (ma zlapac).
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

import pytest

from engine.backtest import Bar, Order, run
from engine.costs import CostModel
from validation.engine_checks import (
    PROG_SIGMA,
    RandomStrategy,
    determinism_check,
    known_effect_check,
    mirror_bars,
    overnight_intraday_split,
    run_all,
    symmetry_check,
    zero_edge_check,
)

START = datetime(2024, 3, 15, 13, 30, tzinfo=UTC)   # 09:30 ET


def bladzenie(n: int = 4000, *, seed: int = 7, start: datetime = START,
              zmiennosc: float = 3.0) -> list[Bar]:
    """Bladzenie losowe jako FIXTURE — nie material badawczy.

    Zaden wniosek o rynku z tej serii nie wynika i zaden tu nie zapada. Sluzy
    wylacznie do sprawdzenia, czy narzedzie liczy to, co ma liczyc: prawdziwa
    seria rynkowa dalaby te same odpowiedzi, tylko wolniej i bez dostepu do
    danych, ktorych projekt jeszcze nie ma.

    Zmiennosc dobrana z grubsza pod MNQ (kilka punktow na minute). Przy serii
    spokojniejszej bariery +-10 pkt prawie nigdy nie zostaja trafione, wiec
    testy dostaja kilkanascie transakcji i traca moc — to nie jest wlasnosc
    silnika, tylko fixture'a.
    """
    rng = random.Random(seed)
    bars: list[Bar] = []
    px = 18000.0
    for i in range(n):
        o = px
        c = round(o + rng.gauss(0, zmiennosc), 2)
        bars.append(Bar(
            ts=start + timedelta(minutes=i),
            open=o, high=max(o, c) + abs(rng.gauss(0, 1)), low=min(o, c) - abs(rng.gauss(0, 1)),
            close=c, volume=rng.randint(5, 500), segment="midday",
        ))
        px = c
    return bars


# --------------------------------------------------------------------------
# Test 1 — zerowa przewaga
# --------------------------------------------------------------------------

def test_losowe_wejscia_nie_maja_przewagi():
    wynik = zero_edge_check(bladzenie(40000), seed=3)

    assert wynik.zdany, wynik.opis
    assert wynik.liczby["n_trades"] >= 30
    # Wynik netto musi byc gorszy od brutto dokladnie o prowizje.
    roznica = wynik.liczby["brutto_srednia"] - wynik.liczby["netto_srednia"]
    assert roznica == pytest.approx(wynik.liczby["koszt_na_transakcje"])
    # Rzut moneta traci: poslizg plus wymog przebicia limitu o tick.
    assert wynik.liczby["netto_srednia"] < 0


def test_kryterium_zerowej_przewagi_jest_jednostronne():
    """Zdrowy silnik traci na rzucie moneta tym pewniej, im wieksza proba —
    test dwustronny odrzucalby go tym czesciej, im wiecej mamy danych."""
    wynik = zero_edge_check(bladzenie(40000), seed=3)

    assert wynik.liczby["t_stat"] < 0, "konserwatyzm silnika ma byc widoczny"
    assert wynik.zdany, "strata nie moze byc powodem do odrzucenia silnika"


def test_przeciek_z_przyszlosci_jest_wykrywany():
    """Strategia z dostepem do przyszlosci musi wywalic test zerowej przewagi.

    Silnik nie da sie oszukac przez HistoryView, wiec przeciek symulujemy
    jawnie: strategia dostaje pelna serie osobnym kanalem. To jest dokladnie
    ten rodzaj bledu, ktory w prawdziwym silniku nie rzuca wyjatku, tylko
    rysuje piekna krzywa kapitalu.
    """
    bars = bladzenie()

    class Jasnowidz:
        def __init__(self, wszystkie):
            self.wszystkie = wszystkie
            self.i = 0

        def on_bar(self, bar, history, state):
            self.i = len(history)
            if self.i % 20 or self.i + 5 >= len(self.wszystkie):
                return []
            przyszly = self.wszystkie[self.i + 5].close
            side = "long" if przyszly > bar.close else "short"
            znak = 1.0 if side == "long" else -1.0
            return [Order(side=side, sl=bar.close - znak * 10.0, tp=bar.close + znak * 10.0)]

    wynik = run(bars, Jasnowidz(bars), cost=CostModel())
    brutto = [t.pnl_usd + 1.20 for t in wynik.trades]
    srednia = sum(brutto) / len(brutto)

    assert srednia > 0, "strategia widzaca przyszlosc musi zarabiac brutto"
    # A kryterium zerowej przewagi na TAKIM wyniku ma zapalic czerwone swiatlo.
    import math
    import statistics
    t = srednia / (statistics.stdev(brutto) / math.sqrt(len(brutto)))
    assert t > PROG_SIGMA, "przeciek tej wielkosci musi przekroczyc prog 3 sigma"


def test_za_malo_transakcji_to_test_bez_mocy_a_nie_sukces():
    wynik = zero_edge_check(bladzenie(50), seed=1)

    assert not wynik.zdany
    assert "bez mocy" in wynik.opis


# --------------------------------------------------------------------------
# Test 2 — znany efekt
# --------------------------------------------------------------------------

def test_rozklad_overnight_intraday_sumuje_sie_do_calosci():
    """Suma ruchu nocnego i sesyjnego to ruch calkowity miedzy pierwszym
    a ostatnim zamknieciem RTH — tozsamosc, ktora musi zachodzic co do grosza."""
    bars = bladzenie(6000)
    podzial = overnight_intraday_split(bars)

    assert podzial["sesji"] >= 3
    razem = podzial["overnight_pkt"] + podzial["intraday_pkt"]

    rth = [b for b in bars
           if 9 * 60 + 30 <= (b.ts.hour * 60 + b.ts.minute - 4 * 60) % (24 * 60) < 16 * 60]
    assert razem == pytest.approx(rth[-1].close - rth[0].open, abs=1e-6)


def test_znany_efekt_porownuje_silnik_z_rachunkiem_recznym():
    wynik = known_effect_check(bladzenie(6000))

    assert "rachunek reczny" in wynik.opis
    assert "silnik_pkt" in wynik.liczby


def test_znany_efekt_bez_sesji_nie_udaje_sukcesu():
    wynik = known_effect_check(bladzenie(30))

    assert not wynik.zdany
    assert "za malo sesji" in wynik.opis


# --------------------------------------------------------------------------
# Test 3 — symetria
# --------------------------------------------------------------------------

def test_symetria_long_short_na_dluzszej_serii():
    wynik = symmetry_check(bladzenie(), seed=11)

    assert wynik.zdany, wynik.opis
    assert wynik.liczby["n_roznic"] == 0


def test_odbicie_serii_zachowuje_zakresy():
    bars = bladzenie(100)
    odbite = mirror_bars(bars)

    for a, b in zip(bars, odbite, strict=True):
        assert (a.high - a.low) == pytest.approx(b.high - b.low)
        assert (a.close - a.open) == pytest.approx(-(b.close - b.open))


def test_asymetryczny_silnik_jest_wykrywany():
    """Gdyby short byl obslugiwany inaczej niz long, check ma to zlapac."""
    bars = bladzenie(2000)
    oryginal = run(bars, RandomStrategy(seed=11))

    # Symulacja usterki: seria odbita, ale strategia NIE odwrocona.
    krzywy = run(mirror_bars(bars), RandomStrategy(seed=11, odwroc=False))
    a = [round(t.pnl_points, 9) for t in oryginal.trades]
    b = [round(t.pnl_points, 9) for t in krzywy.trades]

    assert a != b, "gdyby to bylo rowne, test symetrii nie mialby mocy"


# --------------------------------------------------------------------------
# Test 4 — determinizm
# --------------------------------------------------------------------------

def test_determinizm_i_wrazliwosc_na_ziarno():
    wynik = determinism_check(bladzenie(), seed=5)

    assert wynik.zdany, wynik.opis
    assert wynik.liczby["n_trades"] > 0


def test_determinizm_wymaga_by_ziarno_cokolwiek_zmienialo():
    """Seria za krotka na jakiekolwiek wejscie: przebiegi sa identyczne, ale
    to nie jest dowod determinizmu, tylko brak mocy testu."""
    wynik = determinism_check(bladzenie(5), seed=5)

    assert not wynik.zdany
    assert "nie ma mocy" in wynik.opis


# --------------------------------------------------------------------------
# Komplet
# --------------------------------------------------------------------------

def test_run_all_bez_danych_pomija_testy_wymagajace_rynku():
    wyniki = run_all(bladzenie(), wymagaj_danych=False)

    assert [w.nazwa for w in wyniki] == ["symetria", "determinizm"]
    assert all(w.zdany for w in wyniki)


def test_run_all_na_fixturze_uruchamia_komplet():
    wyniki = run_all(bladzenie(40000), seed=13)

    assert [w.nazwa for w in wyniki] == [
        "zerowa przewaga", "znany efekt", "symetria", "determinizm",
    ]
    niezdane = [w for w in wyniki if not w.zdany]
    assert not niezdane, "; ".join(str(w) for w in niezdane)


@pytest.mark.needs_data
def test_bramka_silnika_na_prawdziwych_danych():
    """Bramka projektu: komplet musi byc zielony na danych z data/clean/,
    zanim ruszy jakakolwiek eksploracja (HANDOFF.md, zasada 4)."""
    from engine.loader import is_available, load_continuous

    if not is_available("mnq"):
        pytest.skip("brak danych — Etap 1 (patrz HANDOFF.md)")

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from engine_validation import bars_from_frame

    wyniki = run_all(bars_from_frame(load_continuous("mnq")))
    niezdane = [str(w) for w in wyniki if not w.zdany]
    assert not niezdane, "\n".join(niezdane)
