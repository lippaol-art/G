"""Testy glownej petli backtestu — PLAN.pdf rozdz. 5.1-5.4.

Bary sa budowane recznie: to FIXTURE'Y, nie dane rynkowe. Zasada "zero danych
syntetycznych" dotyczy wnioskow o rynku, nie dowodow poprawnosci silnika —
a niesprawdzona petla produkuje smieci z dokladnoscia do szesciu miejsc
po przecinku (rozdz. 5.6).
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

import pytest

from engine.backtest import (
    Bar,
    Order,
    RiskLimits,
    entry_fill,
    run,
)
from engine.costs import POINT_VALUE
from engine.guards import LookaheadError

START = datetime(2024, 3, 15, 14, 30, tzinfo=UTC)   # 10:30 ET, segment midday


def seria(closes: list[float], *, volume: int = 100, segment: str = "midday",
          rozpietosc: float = 1.0, start: datetime = START) -> list[Bar]:
    """Bary M1 o zadanych zamknieciach; open = poprzedni close."""
    bars: list[Bar] = []
    prev = closes[0]
    for i, c in enumerate(closes):
        o = prev
        bars.append(Bar(
            ts=start + timedelta(minutes=i),
            open=o, high=max(o, c) + rozpietosc, low=min(o, c) - rozpietosc,
            close=c, volume=volume, segment=segment,
        ))
        prev = c
    return bars


class KupNaBarze:
    """Sklada zlecenie kupna po zamknieciu bara o zadanym indeksie."""

    def __init__(self, idx: int = 0, sl_odleglosc: float = 4.0, tp_odleglosc: float | None = 8.0,
                 side: str = "long", **kwargs):
        self.idx, self.sl_o, self.tp_o, self.side, self.kwargs = idx, sl_odleglosc, tp_odleglosc, side, kwargs

    def on_bar(self, bar, history, state):
        if len(history) != self.idx + 1:
            return []
        znak = 1.0 if self.side == "long" else -1.0
        tp = bar.close + znak * self.tp_o if self.tp_o is not None else None
        return [Order(side=self.side, sl=bar.close - znak * self.sl_o, tp=tp, **self.kwargs)]


class Nic:
    def on_bar(self, bar, history, state):
        return []


# --------------------------------------------------------------------------
# Sygnal na close -> wykonanie na open NASTEPNEGO bara (rozdz. 5.1)
# --------------------------------------------------------------------------

def test_wykonanie_dopiero_na_nastepnym_barze():
    bars = seria([100.0, 101.0, 102.0, 103.0])
    res = run(bars, KupNaBarze(idx=0))

    assert len(res.trades) == 1
    trade = res.trades[0]
    assert trade.entry_ts == bars[1].ts, "sygnal z bara 0 nie moze wykonac sie na barze 0"
    assert trade.entry_px >= bars[1].open, "kupujemy po open nastepnego bara plus poslizg"


def test_poslizg_zawsze_przeciwko_strategii():
    bars = seria([100.0, 101.0, 102.0])
    dlugi = run(bars, KupNaBarze(idx=0, side="long")).trades[0]
    krotki = run(bars, KupNaBarze(idx=0, side="short")).trades[0]

    assert dlugi.entry_px > bars[1].open, "long kupuje DROZEJ niz open"
    assert krotki.entry_px < bars[1].open, "short sprzedaje TANIEJ niz open"


# --------------------------------------------------------------------------
# Zakaz wykonania przy zerowym wolumenie (rozdz. 4.2)
# --------------------------------------------------------------------------

def test_zerowy_wolumen_blokuje_wejscie():
    bars = seria([100.0, 101.0, 102.0])
    bars[1] = Bar(ts=bars[1].ts, open=bars[1].open, high=bars[1].high, low=bars[1].low,
                  close=bars[1].close, volume=0, segment="midday")

    res = run(bars, KupNaBarze(idx=0))

    assert res.trades == [], "wolumen zero znaczy, ze nie bylo gdzie sie wykonac"
    assert res.skipped_zero_volume >= 1


# --------------------------------------------------------------------------
# Wejscie i wyjscie w tym samym barze (tabela 5.4)
# --------------------------------------------------------------------------

def test_pozycja_nie_wychodzi_na_barze_wejscia():
    """Bar wejscia obejmuje SL i TP, ale trajektorii po wypelnieniu nie znamy."""
    bars = seria([100.0, 100.0, 100.0], rozpietosc=50.0)
    res = run(bars, KupNaBarze(idx=0, sl_odleglosc=2.0, tp_odleglosc=2.0))

    assert len(res.trades) == 1
    assert res.trades[0].exit_ts > res.trades[0].entry_ts, (
        "wyjscie moze nastapic najwczesniej na barze NASTEPNYM po wejsciu"
    )


# --------------------------------------------------------------------------
# Warstwa ryzyka dziala PRZED strategia (rozdz. 5.3 krok 2, 10.3)
# --------------------------------------------------------------------------

class ZawszeKupuj:
    """Sklada zlecenie na kazdym barze — sprawdza, czy limit ryzyka je zatrzyma."""

    def __init__(self):
        self.wywolania = 0

    def on_bar(self, bar, history, state):
        self.wywolania += 1
        if len(history) % 3 != 1:
            return []
        return [Order(side="long", sl=bar.close - 2.0, tp=bar.close + 2.0)]


def test_limit_dzienny_wylacza_strategie():
    # Seria spadkowa: kazde wejscie long konczy sie stopem.
    bars = seria([100.0 - i for i in range(60)])
    strat = ZawszeKupuj()
    res = run(bars, strat, risk=RiskLimits(daily_stop_r=2.0))

    assert res.risk_blocked_bars > 0, "po -2R w dniu strategia nie moze byc dalej pytana"
    suma_r = sum(t.r_multiple for t in res.trades)
    assert suma_r <= 0
    # Po przekroczeniu limitu zadna nowa transakcja nie moze sie pojawic.
    r_narastajaco = 0.0
    for t in res.trades[:-1]:
        r_narastajaco += t.r_multiple
    assert r_narastajaco > -2.0, "transakcja otwarta juz po przekroczeniu limitu dziennego"


def test_zlecenie_bez_stopa_jest_odrzucane_a_nie_wywraca_badania():
    class BezStopa:
        def on_bar(self, bar, history, state):
            return [Order(side="long")] if len(history) == 1 else []

    res = run(seria([100.0, 101.0, 102.0]), BezStopa())

    assert res.trades == []
    assert len(res.rejected_orders) == 1
    assert "stop" in res.rejected_orders[0][1].lower()


def test_limit_otwartych_pozycji():
    class Ciagle:
        def on_bar(self, bar, history, state):
            return [Order(side="long", sl=bar.close - 5.0)]

    res = run(seria([100.0 + i * 0.1 for i in range(10)]), Ciagle())
    assert res.rejected_orders, "drugie zlecenie przy otwartej pozycji musi zostac odrzucone"


# --------------------------------------------------------------------------
# Determinizm i symetria (rozdz. 5.6)
# --------------------------------------------------------------------------

def test_determinizm_dwa_przebiegi_identyczne():
    bars = seria([100.0 + (i % 7) - 3 for i in range(120)])
    a = run(bars, ZawszeKupuj())
    b = run(bars, ZawszeKupuj())

    assert [(t.entry_px, t.exit_px, t.pnl_usd) for t in a.trades] == \
           [(t.entry_px, t.exit_px, t.pnl_usd) for t in b.trades]
    assert a.equity == b.equity
    assert a.config["config_hash"] == b.config["config_hash"]


def test_symetria_long_short():
    """Odbicie serii wzgledem poziomu + odwrocenie strony = wynik lustrzany."""
    closes = [100.0, 101.5, 103.0, 101.0, 99.0, 100.5]
    bars = seria(closes)
    lustro = [Bar(ts=b.ts, open=200.0 - b.open, high=200.0 - b.low, low=200.0 - b.high,
                  close=200.0 - b.close, volume=b.volume, segment=b.segment) for b in bars]

    dlugi = run(bars, KupNaBarze(idx=0, side="long", sl_odleglosc=3.0, tp_odleglosc=3.0))
    krotki = run(lustro, KupNaBarze(idx=0, side="short", sl_odleglosc=3.0, tp_odleglosc=3.0))

    assert len(dlugi.trades) == len(krotki.trades) == 1
    assert dlugi.trades[0].pnl_points == pytest.approx(krotki.trades[0].pnl_points)
    assert dlugi.trades[0].exit_reason == krotki.trades[0].exit_reason


# --------------------------------------------------------------------------
# Lookahead jest bledem, nie zawyzeniem wyniku (rozdz. 5.1)
# --------------------------------------------------------------------------

def test_strategia_nie_moze_zobaczyc_przyszlosci():
    class Oszust:
        def on_bar(self, bar, history, state):
            history[len(history)]      # bar z przyszlosci
            return []

    with pytest.raises(LookaheadError):
        run(seria([100.0, 101.0, 102.0]), Oszust())


# --------------------------------------------------------------------------
# Ksiegowanie
# --------------------------------------------------------------------------

def test_dni_bez_transakcji_sa_w_dziennym_pnl():
    """Pominiecie dni zerowych zawyzyloby Sharpe strategii rzadko handlujacych."""
    dzien1 = seria([100.0, 100.5], start=START)
    dzien2 = seria([100.0, 100.5], start=START + timedelta(days=1))
    res = run(dzien1 + dzien2, Nic())

    assert len(res.daily_pnl) == 2
    assert res.daily_pnl_series() == [0.0, 0.0]


def test_equity_jest_mark_to_market_a_pozycja_koncowa_domknieta():
    bars = seria([100.0, 101.0, 102.0, 103.0])
    res = run(bars, KupNaBarze(idx=0, sl_odleglosc=10.0, tp_odleglosc=None))

    assert len(res.equity) == len(bars), "equity zapisujemy na close KAZDEGO bara"
    assert len(res.trades) == 1
    assert res.trades[0].exit_reason == "end_of_data"


def test_prowizja_obciaza_wynik():
    bars = seria([100.0, 101.0, 102.0])
    res = run(bars, KupNaBarze(idx=0, sl_odleglosc=10.0, tp_odleglosc=None))
    t = res.trades[0]

    assert t.pnl_usd == pytest.approx(t.pnl_points * POINT_VALUE - 1.20), (
        "R i P&L licza sie PO kosztach — wyjscie na zero po prowizji nie jest zyskiem"
    )


# --------------------------------------------------------------------------
# Przymusowe zamkniecie (flat-by) i blackout
# --------------------------------------------------------------------------

def test_flat_by_zamyka_pozycje_o_zadanej_godzinie():
    # 14:30 UTC = 10:30 ET; flat_by 10:33 ET wypada na barze o indeksie 3.
    bars = seria([100.0 + i * 0.1 for i in range(8)])
    res = run(bars, KupNaBarze(idx=0, sl_odleglosc=50.0, tp_odleglosc=50.0),
              flat_by=time(10, 33))

    assert res.forced_exits >= 1
    assert res.trades[0].exit_reason == "flat_by"


def test_blackout_wokol_zdarzenia_rangi_1():
    bars = seria([100.0 + i * 0.1 for i in range(10)])
    res = run(bars, KupNaBarze(idx=0), events=[START], blackout_minutes=10)

    assert res.blackout_bars > 0
    assert res.trades == [], "w oknie blackoutu strategia nie jest nawet pytana"


def test_blackout_mozna_wylaczyc_dla_strategii_zdarzeniowych():
    bars = seria([100.0 + i * 0.1 for i in range(10)])
    res = run(bars, KupNaBarze(idx=0), events=[START], blackout=False)

    assert res.blackout_bars == 0
    assert len(res.trades) == 1


def test_poslizg_rosnie_w_oknie_zdarzenia():
    """Zdarzenie rangi 1 podnosi baze poslizgu do 4 tickow (tabela 5.5)."""
    bars = seria([100.0, 101.0, 102.0])
    spokojnie = run(bars, KupNaBarze(idx=0), blackout=False).trades[0]
    przy_zdarzeniu = run(bars, KupNaBarze(idx=0), events=[START], blackout=False).trades[0]

    assert przy_zdarzeniu.entry_px > spokojnie.entry_px


# --------------------------------------------------------------------------
# Wejscia stop i limit (tabela 5.4)
# --------------------------------------------------------------------------

def test_stop_entry_przeskoczony_luka_wchodzi_po_open():
    bar = Bar(ts=START, open=105.0, high=106.0, low=104.0, close=105.5, volume=10)
    px = entry_fill(Order(side="long", kind="stop", px=102.0, sl=100.0), bar, 0.25)

    assert px == pytest.approx(105.25), "przy luce wchodzimy po OPEN, nie po cenie zlecenia"


def test_stop_entry_dotkniety_wewnatrz_bara():
    bar = Bar(ts=START, open=100.0, high=103.0, low=99.0, close=102.0, volume=10)
    px = entry_fill(Order(side="long", kind="stop", px=102.0, sl=100.0), bar, 0.25)

    assert px == pytest.approx(102.25)


def test_limit_entry_wymaga_przebicia():
    dotkniecie = Bar(ts=START, open=100.0, high=100.5, low=99.0, close=99.5, volume=10)
    przebicie = Bar(ts=START, open=100.0, high=100.5, low=98.75, close=99.0, volume=10)
    order = Order(side="long", kind="limit", px=99.0, sl=95.0)

    assert entry_fill(order, dotkniecie, 0.25) is None
    assert entry_fill(order, przebicie, 0.25) == pytest.approx(99.0), (
        "limit wypelnia sie po swojej cenie — nigdy lepiej"
    )


def test_zlecenie_next_bar_wygasa_po_jednym_barze():
    class StopDaleko:
        def on_bar(self, bar, history, state):
            if len(history) != 1:
                return []
            return [Order(side="long", kind="stop", px=bar.close + 50.0, sl=bar.close)]

    res = run(seria([100.0 + i for i in range(6)]), StopDaleko())
    assert res.trades == []


def test_zlecenie_day_pracuje_do_konca_dnia():
    class StopBlisko:
        def on_bar(self, bar, history, state):
            if len(history) != 1:
                return []
            return [Order(side="long", kind="stop", px=bar.close + 3.0,
                          sl=bar.close - 5.0, tif="day")]

    res = run(seria([100.0 + i for i in range(8)]), StopBlisko())
    assert len(res.trades) == 1, "zlecenie z tif=day musi doczekac dotkniecia poziomu"
