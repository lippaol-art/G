"""Glowna petla backtestu na barach spreparowanych — PLAN.pdf rozdz. 5.3-5.4.

Bramka z `test_engine_on_real_data.py` dowodzi, ze silnik mierzy rynek. Ten plik
dowodzi czegos komplementarnego: ze KAZDA POJEDYNCZA REGULA petli dziala tak,
jak opisuje tabela 5.4 — i to na barach, ktore skonstruowano wlasnie po to, by
dana regula miala szanse sie zlamac.

Jedno bez drugiego nie wystarcza. Na realnych danych regula "wyjscie dopiero od
bara nastepnego" jest spelniona w 99.9% przypadkow niezaleznie od tego, czy
silnik ja implementuje — bo rzadko ktory bar M1 obejmuje jednoczesnie wejscie
i stopa. Zeby ja sprawdzic, trzeba bara, ktory obejmuje.

Bary sa tu FIXTURE'AMI TESTOWYMI, nie danymi rynkowymi. Zasada projektu "zero
danych syntetycznych" dotyczy wnioskow o rynku; zaden wniosek o rynku z tego
pliku nie wynika i wynikac nie moze.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from engine.backtest import (
    AmbiguousBarPolicy,
    Bar,
    CostModel,
    Order,
    RiskLimits,
    default_slippage_points,
    run_backtest,
)

T0 = datetime(2026, 3, 10, 14, 30, tzinfo=UTC)
D0 = date(2026, 3, 10)
TICK = 0.25


def bar(i: int, o: float, h: float, low: float, c: float, *,
        vol: int = 100, seg: str = "midday", td: date = D0) -> Bar:
    return Bar(ts=T0 + timedelta(minutes=i), open=o, high=h, low=low, close=c,
               volume=vol, segment=seg, trade_date=td)


def plaskie(n: int, px: float = 100.0, **kw) -> list[Bar]:
    """n identycznych barow — tlo, na ktorym widac tylko badana regule."""
    return [bar(i, px, px, px, px, **kw) for i in range(n)]


class NaBarze:
    """Sklada dokladnie jedno zlecenie na barze o zadanym indeksie."""

    def __init__(self, idx: int, order: Order):
        self.idx, self.order, self.i = idx, order, -1

    def on_bar(self, b, history, state):
        self.i += 1
        return [self.order] if self.i == self.idx else []


class NigdyNiePlaska:
    """Sklada zlecenie na kazdym barze — do testow limitow i odrzucen."""

    def __init__(self, order: Order):
        self.order = order

    def on_bar(self, b, history, state):
        return [self.order]


BEZ_KOSZTOW = dict(cost_model=CostModel(commission_rt=0.0),
                   slippage_model=lambda b: 0.0)


# ==========================================================================
# WYKONANIE: sygnal -> otwarcie NASTEPNEGO bara
# ==========================================================================

class TestOpoznieniaWykonania:
    """Zasada konstrukcyjna nr 2: sygnal na close -> wykonanie na open nastepnego.

    Najczestszy cichy blad backtestu polega na wykonaniu po cenie z tego samego
    bara, na ktorym powstal sygnal. Efekt jest zawsze ten sam: krzywa kapitalu
    robi sie piekna, a strategia nie da sie handlowac.
    """

    def test_wypelnienie_po_open_bara_nastepnego(self):
        bars = [bar(0, 100, 100, 100, 100), bar(1, 105, 106, 104, 105), bar(2, 105, 105, 105, 105)]
        r = run_backtest(bars, NaBarze(0, Order(side="long", sl=None)),
                         risk=RiskLimits(require_stop=False), **BEZ_KOSZTOW)
        assert len(r.trades) == 0, "pozycja bez SL/TP nie ma prawa sie zamknac"
        # sprawdzamy cene wejscia przez equity: mark-to-market bara 1 = close-entry
        assert r.equity[1] == pytest.approx((105 - 105) * 2.0), \
            "wejscie musi byc po OPEN bara 1 (105), nie po close bara 0 (100)"

    def test_poslizg_dodawany_po_stronie_niekorzystnej(self):
        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 100, 100, 100)]
        for side, znak in (("long", +1), ("short", -1)):
            r = run_backtest(bars, NaBarze(0, Order(side=side, sl=None)),
                             risk=RiskLimits(require_stop=False),
                             cost_model=CostModel(commission_rt=0.0))
            slip = default_slippage_points(bars[1])
            oczek = -abs(slip) * 2.0          # kupujemy drozej / sprzedajemy taniej
            assert r.equity[1] == pytest.approx(oczek), \
                f"{side}: poslizg musi pogarszac wejscie o {slip} pkt (znak {znak})"

    def test_bar_bez_wolumenu_blokuje_wykonanie(self):
        """volume == 0 oznacza brak transakcji w tej minucie — nie bylo gdzie
        sie wykonac (rozdz. 4.2). Wykonanie tutaj to zysk, ktorego nie dalo sie
        zrealizowac."""
        bars = [bar(0, 100, 100, 100, 100), bar(1, 90, 90, 90, 90, vol=0),
                bar(2, 90, 90, 90, 90)]
        r = run_backtest(bars, NaBarze(0, Order(side="long", sl=None)),
                         risk=RiskLimits(require_stop=False), **BEZ_KOSZTOW)
        assert r.skipped_zero_volume == 1
        assert r.equity[2] == 0.0, "zlecenie przepadlo — nie moze sie wykonac bar pozniej"

    def test_zlecenie_przy_zajetej_pozycji_jest_odrzucane(self):
        bars = plaskie(6)
        r = run_backtest(bars, NigdyNiePlaska(Order(side="long", sl=None)),
                         risk=RiskLimits(require_stop=False), **BEZ_KOSZTOW)
        assert r.rejected_orders > 0, "usrednianie musi byc blokowane (rozdz. 10.4)"

    def test_zlecenie_bez_stopa_odrzucone_gdy_wymagany(self):
        bars = plaskie(4)
        r = run_backtest(bars, NigdyNiePlaska(Order(side="long", sl=None)),
                         risk=RiskLimits(require_stop=True), **BEZ_KOSZTOW)
        assert r.trades == []
        assert r.rejected_orders == len(bars)


# ==========================================================================
# WYJSCIE: nie w barze wejscia
# ==========================================================================

class TestBaraWejscia:
    """DWA NIEZALEZNE MECHANIZMY chronia te sama regule i to jest zamierzone.

    (a) kolejnosc krokow w petli — wyjscia rozstrzygane sa przed wypelnieniem
        zlecen, wiec swiezo otwarta pozycja fizycznie nie istnieje jeszcze
        w momencie sprawdzania SL/TP;
    (b) straznik `pos.entry_bar_index < i` w kroku wyjsc.

    Sprawdzone mutacja: usuniecie (a) ALBO (b) osobno nie lamie testu ponizej —
    drugi mechanizm ratuje wynik. Dopiero usuniecie obu naraz go wywraca.
    Straznik (b) wyglada wiec na martwy kod i NIE JEST NIM: to on sprawia, ze
    przestawienie krokow petli pozostaje bezpieczne. Nie usuwac.
    """

    def test_stop_w_barze_wejscia_nie_dziala(self):
        """Tabela 5.4: w barze wejscia znamy fakt wypelnienia, ale nie trajektorie
        ceny po nim. Bar 1 przebija stopa juz w dolku — mimo to wyjscie moze
        nastapic najwczesniej w barze 2."""
        bars = [bar(0, 100, 100, 100, 100),
                bar(1, 100, 100, 90, 100),      # dolek 90 przebija SL=95
                bar(2, 100, 100, 90, 95)]
        r = run_backtest(bars, NaBarze(0, Order(side="long", sl=95.0)), **BEZ_KOSZTOW)
        assert len(r.trades) == 1
        assert r.trades[0].exit_ts == bars[2].ts, \
            "wyjscie zaksiegowane w barze wejscia — silnik zgaduje kolejnosc w minucie"

    def test_wyjscie_dziala_od_bara_nastepnego(self):
        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 100, 100, 100),
                bar(2, 100, 100, 90, 95)]
        r = run_backtest(bars, NaBarze(0, Order(side="long", sl=95.0)), **BEZ_KOSZTOW)
        assert len(r.trades) == 1
        assert r.trades[0].exit_reason == "stop_loss"
        assert r.trades[0].exit_px == pytest.approx(95.0)


# ==========================================================================
# KSIEGOWANIE: R, koszty, equity
# ==========================================================================

class TestKsiegowania:
    def test_r_multiple_liczone_od_dystansu_do_stopa(self):
        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 100, 100, 100),
                bar(2, 100, 110, 100, 110), bar(3, 100, 100, 100, 100)]
        r = run_backtest(bars, NaBarze(0, Order(side="long", sl=95.0, tp=105.0)),
                         **BEZ_KOSZTOW)
        t = r.trades[0]
        assert t.exit_reason == "take_profit"
        assert t.pnl_points == pytest.approx(5.0)
        assert t.r_multiple == pytest.approx(1.0), \
            "5 pkt zysku przy stopie 5 pkt od wejscia to dokladnie 1R"

    def test_prowizja_skaluje_sie_liczba_kontraktow(self):
        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 100, 100, 100),
                bar(2, 100, 100, 90, 95)]
        r = run_backtest(bars, NaBarze(0, Order(side="long", qty=3, sl=95.0)),
                         slippage_model=lambda b: 0.0)
        assert r.commission_usd == pytest.approx(3 * 1.20)
        assert r.trades[0].pnl_usd == pytest.approx(-5.0 * 2.0 * 3 - 3.60)

    def test_equity_zawiera_wynik_niezrealizowany(self):
        """Bez mark-to-market obsuniecie otwartej pozycji bylo by niewidoczne,
        a to wlasnie ono wywraca rachunki — rozdz. 5.3 pkt 5."""
        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 100, 100, 100),
                bar(2, 100, 100, 96, 96), bar(3, 96, 96, 96, 96)]
        r = run_backtest(bars, NaBarze(0, Order(side="long", sl=90.0)), **BEZ_KOSZTOW)
        assert r.trades == [], "stop na 90 nie zostal dotkniety"
        assert r.equity[2] == pytest.approx(-4.0 * 2.0), \
            "equity musi pokazywac -4 pkt strat niezrealizowanych"

    def test_equity_ma_dlugosc_serii_barow(self):
        bars = plaskie(7)
        r = run_backtest(bars, NaBarze(0, Order(side="long", sl=None)),
                         risk=RiskLimits(require_stop=False), **BEZ_KOSZTOW)
        assert len(r.equity) == len(bars)


# ==========================================================================
# LIMITY RYZYKA — dzialaja PRZED strategia
# ==========================================================================

class TestLimitowRyzyka:
    @staticmethod
    def _seria_strat(n_barow: int, td: date) -> list[Bar]:
        """Bary, na ktorych kazda pozycja long z SL 1 pkt ponizej ginie."""
        out = []
        for i in range(n_barow):
            out.append(bar(i, 100, 100, 98 if i % 2 else 100, 100, td=td))
        return out

    def test_limit_dzienny_wylacza_strategie(self):
        """-2R w dniu sesyjnym konczy handel. Limit jest twardy: dziala PRZED
        strategia, wiec zadna regula nie moze go obejsc (rozdz. 10.3)."""
        bars = self._seria_strat(40, D0)
        r = run_backtest(bars, NigdyNiePlaska(Order(side="long", sl=99.0)),
                         risk=RiskLimits(daily_stop_r=2.0, weekly_stop_r=100.0),
                         **BEZ_KOSZTOW)
        assert r.blocked_bars > 0, "limit dzienny nigdy sie nie zalaczyl"
        suma_r = sum(t.r_multiple for t in r.trades)
        assert suma_r <= -2.0
        assert len(r.trades) <= 3, \
            f"po przekroczeniu -2R silnik dopuscil {len(r.trades)} transakcji"

    def test_nowy_dzien_sesyjny_zeruje_limit(self):
        """Limit dzienny zwiazany jest z `trade_date`, nie z data kalendarzowa —
        sesja zaczyna sie o 18:00 ET dnia poprzedniego (rozdz. 4.4)."""
        d1, d2 = date(2026, 3, 10), date(2026, 3, 11)
        bars = self._seria_strat(20, d1) + [
            Bar(ts=T0 + timedelta(minutes=100 + i), open=100, high=100,
                low=98 if i % 2 else 100, close=100, volume=100,
                segment="midday", trade_date=d2)
            for i in range(20)
        ]
        r = run_backtest(bars, NigdyNiePlaska(Order(side="long", sl=99.0)),
                         risk=RiskLimits(daily_stop_r=2.0, weekly_stop_r=100.0),
                         **BEZ_KOSZTOW)
        dni = {t.exit_ts for t in r.trades}
        assert len(r.trades) >= 4, "drugi dzien sesyjny musi znow dopuscic handel"
        assert len(dni) == len(r.trades)


# ==========================================================================
# PRZYMUSOWE SPLASZCZENIE I BARY SPORNE
# ==========================================================================

class TestSplaszczeniaISpornych:
    def test_force_flat_zamyka_po_close_z_poslizgiem(self):
        """Ostatni wiersz tabeli 5.4: przymusowe zamkniecie po close bara okna
        MINUS poslizg — nigdy po cenie korzystniejszej."""
        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 100, 100, 100),
                bar(2, 100, 104, 100, 104, seg="close")]
        r = run_backtest(bars, NaBarze(0, Order(side="long", sl=None)),
                         risk=RiskLimits(require_stop=False),
                         force_flat=lambda b, p: b.segment == "close",
                         cost_model=CostModel(commission_rt=0.0))
        assert len(r.trades) == 1
        t = r.trades[0]
        assert t.exit_reason == "flat_by"
        slip = default_slippage_points(bars[2])
        assert t.exit_px == pytest.approx(104.0 - slip), \
            "poslizg przy splaszczeniu musi dzialac na niekorzysc pozycji"

    def test_bar_sporny_jest_zliczany_i_rozstrzygany_konserwatywnie(self):
        """Bar 2 obejmuje i SL, i TP. Domyslnie wygrywa SL, a fakt spornosci
        musi trafic do licznika — bez niego nie da sie zaraportowac pasma
        wrazliwosci wymaganego przez rozdz. 5.4."""
        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 100, 100, 100),
                bar(2, 100, 110, 90, 100)]
        r = run_backtest(bars, NaBarze(0, Order(side="long", sl=95.0, tp=105.0)),
                         **BEZ_KOSZTOW)
        assert r.ambiguous_bars == 1
        assert r.trades[0].exit_reason == "stop_loss"

    def test_polityka_tp_wins_daje_gorna_granice_pasma(self):
        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 100, 100, 100),
                bar(2, 100, 110, 90, 100)]
        wspolne = dict(**BEZ_KOSZTOW)
        sl_wins = run_backtest(bars, NaBarze(0, Order(side="long", sl=95.0, tp=105.0)),
                               policy=AmbiguousBarPolicy.SL_WINS, **wspolne)
        tp_wins = run_backtest(bars, NaBarze(0, Order(side="long", sl=95.0, tp=105.0)),
                               policy=AmbiguousBarPolicy.TP_WINS, **wspolne)
        assert sl_wins.net_usd < tp_wins.net_usd, \
            "pasmo wrazliwosci musi miec niezerowa szerokosc, inaczej nic nie mierzy"
        assert sl_wins.ambiguous_bars == tp_wins.ambiguous_bars == 1

    def test_luka_przez_stopa_wykonuje_sie_po_open(self):
        """Open bara 2 (85) jest juz ponizej SL (95). Wyjscie po open, nie po
        cenie stopa — inaczej backtest obiecuje wypelnienie, ktorego nie bylo."""
        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 100, 100, 100),
                bar(2, 85, 86, 84, 85)]
        r = run_backtest(bars, NaBarze(0, Order(side="long", sl=95.0)), **BEZ_KOSZTOW)
        assert r.trades[0].exit_reason == "stop_gap"
        assert r.trades[0].exit_px == pytest.approx(85.0)


# ==========================================================================
# WIDOK HISTORII — strategia nie widzi przyszlosci
# ==========================================================================

class TestWidokuStrategii:
    def test_historia_konczy_sie_na_barze_biezacym(self):
        widziane: list[int] = []

        class Podglada:
            def on_bar(self, b, history, state):
                widziane.append(len(history))
                assert history[-1] is b, "ostatni widoczny bar musi byc biezacym"
                return []

        bars = plaskie(5)
        run_backtest(bars, Podglada(), **BEZ_KOSZTOW)
        assert widziane == [1, 2, 3, 4, 5]

    def test_stan_niesie_obraz_pozycji_od_silnika(self):
        """Strategia nie moze wywnioskowac z historii barow, czy jest w pozycji.
        Silnik podaje jej to jawnie — ten sam kontrakt obowiazuje w petli live."""
        strony: list[object] = []

        class Czyta:
            def __init__(self):
                self.i = -1

            def on_bar(self, b, history, state):
                self.i += 1
                strony.append(state.get("position_side"))
                return [Order(side="short", sl=None)] if self.i == 0 else []

        bars = plaskie(4)
        run_backtest(bars, Czyta(), risk=RiskLimits(require_stop=False), **BEZ_KOSZTOW)
        assert strony[0] is None
        assert strony[2] == "short", "silnik nie poinformowal strategii o otwartej pozycji"


# ==========================================================================
# ZLECENIA OCZEKUJACE — stop-entry, limit, OCO, wygasanie
# ==========================================================================

class TestZlecenOczekujacych:
    """Wybicie z konsolidacji to zlecenie LEZACE W KSIEDZE, nie rynkowe.

    Bez tego benchmark B02 (NR7 Crabela) i cala rodzina hipotez wybiciowych
    musialyby udawac wybicie zleceniem rynkowym po fakcie — a to inna cena
    i inny moment. Tabela 5.4 przewiduje stop-entry wprost.
    """

    def test_stop_entry_czeka_az_cena_dojdzie(self):
        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 101, 99, 100),
                bar(2, 100, 106, 100, 105), bar(3, 105, 105, 105, 105)]
        r = run_backtest(bars, NaBarze(0, Order(side="long", kind="stop", px=105.0, sl=95.0)),
                         **BEZ_KOSZTOW)
        assert len(r.trades) == 0, "pozycja bez SL/TP dotknietego nie zamyka sie"
        assert r.equity[1] == 0.0, "bar 1 nie siega 105 — zlecenie nie moze byc wypelnione"
        assert r.equity[2] == pytest.approx(0.0), "wejscie po 105, close 105 -> zero"
        assert r.equity[3] == pytest.approx(0.0)

    def test_stop_entry_wypelnia_sie_po_poziomie_nie_po_ekstremum(self):
        """Wypelnienie po cenie zlecenia, nie po maksimum bara — inaczej silnik
        obiecywalby najlepsza cene z minuty, ktorej nikt by nie dostal."""
        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 110, 100, 108)]
        r = run_backtest(bars, NaBarze(0, Order(side="long", kind="stop", px=105.0, sl=95.0)),
                         **BEZ_KOSZTOW)
        assert r.equity[1] == pytest.approx((108 - 105) * 2.0)

    def test_stop_entry_przeskoczony_luka_wypelnia_sie_po_open(self):
        """Open 107 przeskakuje poziom 105. Wejscie po 107 — cena, ktora byla
        na tablicy — a nie po 105, ktorej juz nie bylo (tabela 5.4)."""
        bars = [bar(0, 100, 100, 100, 100), bar(1, 107, 110, 107, 109)]
        r = run_backtest(bars, NaBarze(0, Order(side="long", kind="stop", px=105.0, sl=95.0)),
                         **BEZ_KOSZTOW)
        assert r.equity[1] == pytest.approx((109 - 107) * 2.0)

    def test_stop_entry_short_wyzwala_spadek(self):
        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 100, 94, 96)]
        r = run_backtest(bars, NaBarze(0, Order(side="short", kind="stop", px=95.0, sl=105.0)),
                         **BEZ_KOSZTOW)
        assert r.equity[1] == pytest.approx((95 - 96) * 2.0)

    def test_limit_wymaga_przebicia_o_tick(self):
        """Symetrycznie do take-profit: samo dotkniecie poziomu nie gwarantuje
        wypelnienia, bo kolejki zlecen nie odtworzymy z OHLCV M1."""
        dotkniecie = [bar(0, 100, 100, 100, 100), bar(1, 100, 100, 95.0, 97),
                      bar(2, 97, 97, 97, 97)]
        r = run_backtest(dotkniecie, NaBarze(0, Order(side="long", kind="limit", px=95.0, sl=90.0)),
                         **BEZ_KOSZTOW)
        assert r.equity[2] == 0.0, "dotkniecie 95.00 nie wystarcza do wypelnienia"

        przebicie = [bar(0, 100, 100, 100, 100), bar(1, 100, 100, 94.75, 97),
                     bar(2, 97, 97, 97, 97)]
        r2 = run_backtest(przebicie, NaBarze(0, Order(side="long", kind="limit", px=95.0, sl=90.0)),
                          **BEZ_KOSZTOW)
        assert r2.equity[2] == pytest.approx((97 - 95) * 2.0), "przebicie o tick musi wypelnic"

    def test_zlecenie_wygasa_z_koncem_dnia_sesyjnego(self):
        """Zlecenie dzienne — tak dziala domyslnie zlecenie na CME. Gdyby lezalo
        dalej, wykonaloby sie na luce otwarcia nastepnej sesji, ktorej nikt by
        nie przehandlowal."""
        d2 = date(2026, 3, 11)
        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 101, 99, 100),
                Bar(ts=T0 + timedelta(minutes=2), open=110, high=112, low=110, close=111,
                    volume=100, segment="midday", trade_date=d2)]
        r = run_backtest(bars, NaBarze(0, Order(side="long", kind="stop", px=105.0, sl=95.0)),
                         **BEZ_KOSZTOW)
        assert r.expired_orders == 1
        assert r.trades == [] and r.equity[2] == 0.0, \
            "wczorajsze zlecenie wykonalo sie na dzisiejszej luce"

    def test_oco_wypelnienie_kasuje_strone_przeciwna(self):
        """Wybicie dwustronne: jedna noga wypelniona, druga MUSI zniknac.
        Bez tego ten sam sygnal otwieralby dwie pozycje."""
        class Wybicie:
            def __init__(self):
                self.i = -1

            def on_bar(self, b, history, state):
                self.i += 1
                if self.i != 0:
                    return []
                return [
                    Order(side="long", kind="stop", px=105.0, sl=95.0, oco_group="orb"),
                    Order(side="short", kind="stop", px=95.0, sl=105.0, oco_group="orb"),
                ]

        # Bar 1 wybija w gore, bar 2 wraca ponizej dolnej nogi.
        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 106, 100, 106),
                bar(2, 106, 106, 90, 92), bar(3, 92, 92, 92, 92)]
        r = run_backtest(bars, Wybicie(), risk=RiskLimits(max_positions=1), **BEZ_KOSZTOW)
        assert len(r.trades) == 1, f"OCO nie zadzialalo — {len(r.trades)} transakcji"
        assert r.trades[0].side == "long"
        assert r.trades[0].exit_reason == "stop_loss"

    def test_bez_oco_druga_noga_probuje_wejsc(self):
        """Kontrola przeciwna: bez `oco_group` druga noga jest odrzucana dopiero
        przez warstwe ryzyka — czyli mechanizm OCO faktycznie cos wnosi."""
        class Wybicie:
            def __init__(self):
                self.i = -1

            def on_bar(self, b, history, state):
                self.i += 1
                if self.i != 0:
                    return []
                return [Order(side="long", kind="stop", px=105.0, sl=95.0),
                        Order(side="short", kind="stop", px=95.0, sl=105.0)]

        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 106, 100, 106),
                bar(2, 106, 106, 90, 92), bar(3, 92, 92, 92, 92)]
        r = run_backtest(bars, Wybicie(), risk=RiskLimits(max_positions=1), **BEZ_KOSZTOW)
        assert r.rejected_orders > 0, "bez OCO druga noga powinna dobijac sie do wejscia"

    def test_zlecenie_oczekujace_przezywa_bar_bez_wolumenu(self):
        """Rynkowe przepada (nie bylo gdzie sie wykonac), oczekujace lezy dalej —
        brak transakcji w minucie nie kasuje zlecenia z ksiegi."""
        bars = [bar(0, 100, 100, 100, 100), bar(1, 100, 100, 100, 100, vol=0),
                bar(2, 100, 106, 100, 106)]
        r = run_backtest(bars, NaBarze(0, Order(side="long", kind="stop", px=105.0, sl=95.0)),
                         **BEZ_KOSZTOW)
        assert r.skipped_zero_volume == 0, "to nie bylo zlecenie rynkowe"
        assert r.equity[2] == pytest.approx((106 - 105) * 2.0), "zlecenie musi przezyc pusta minute"

    def test_oco_kasuje_noge_ktora_juz_lezala_w_ksiedze(self):
        """Przypadek, ktory naprawde grozi w benchmarku B02.

        Noga PRZECIWNA jest rozpatrywana jako pierwsza, nie wyzwala sie i wraca
        do ksiegi. Dopiero potem wypelnia sie noga druga. Jesli kasowanie OCO
        dziala tylko wewnatrz petli, ta pierwsza LEZY DALEJ — i przy powrocie
        ceny w tej samej sesji otwiera druga pozycje na tym samym sygnale.

        Kolejnosc zlecen w liscie jest tu istotna i celowa: odwrotna kolejnosc
        (najpierw noga wypelniana) NIE wykrywa tego bledu. Sprawdzone mutacja.
        """
        class WybicieOdwrotnaKolejnosc:
            def __init__(self):
                self.i = -1

            def on_bar(self, b, history, state):
                self.i += 1
                if self.i != 0:
                    return []
                return [
                    Order(side="short", kind="stop", px=95.0, sl=105.0, oco_group="orb"),
                    Order(side="long", kind="stop", px=105.0, sl=95.0, oco_group="orb"),
                ]

        bars = [bar(0, 100, 100, 100, 100),
                bar(1, 100, 106, 100, 106),     # wybicie w gore: long wchodzi
                bar(2, 106, 106, 94, 94),       # zjazd: stop longa + poziom shorta
                bar(3, 94, 106, 94, 106),       # powrot w gore — domyka ewentualnego shorta
                bar(4, 106, 106, 106, 106)]
        r = run_backtest(bars, WybicieOdwrotnaKolejnosc(),
                         risk=RiskLimits(max_positions=1), **BEZ_KOSZTOW)
        assert len(r.trades) == 1, (
            f"OCO nie skasowalo nogi lezacej w ksiedze — {len(r.trades)} transakcje "
            f"z jednego sygnalu wybicia: {[(t.side, t.exit_reason) for t in r.trades]}"
        )
        assert r.trades[0].side == "long"
        assert r.final_position is None, "z jednego wybicia zostala otwarta druga pozycja"
        assert r.resting_orders == 0, "noga przeciwna nadal lezy w ksiedze"
