"""Testy rolowania (rozdz. 4.3) i metryk (rozdz. 6.1-6.3).

Fixture'y kontraktow konstruowane recznie — to dane testowe, nie rynkowe.
"""

from __future__ import annotations

import math
from datetime import date

import numpy as np
import pytest

from engine.metrics import (
    CONCENTRATION_GATE,
    PF_SUSPICIOUS,
    drawdown_stats,
    expectancy,
    profit_factor,
    sharpe_lo_correction,
    sharpe_ratio,
    sortino_ratio,
    sqn,
    summarize,
    top_n_concentration,
)
from engine.roll import (
    ContractDay,
    RollEvent,
    adjust_price,
    cumulative_offsets,
    days_to_roll,
    find_roll_dates,
    unadjust_price,
    verify_continuity,
)

# ==========================================================================
# ROLOWANIE
# ==========================================================================

class TestRoll:
    def _dwa_kontrakty(self):
        """MNQH5 traci plynnosc, MNQM5 przejmuje ja od 2025-03-13.

        MNQH5 wygasa w trzeci piatek marca 2025 (2025-03-21), wiec wszystkie
        te dni leza w oknie poszukiwania. Przewaga MNQM5 trwa TRZY kolejne dni
        (13, 14, 17 marca) — tyle wymaga `min_consecutive`.
        """
        h5 = [
            ContractDay(date(2025, 3, 11), "MNQH5", 20000.0, 900_000),
            ContractDay(date(2025, 3, 12), "MNQH5", 20010.0, 700_000),
            ContractDay(date(2025, 3, 13), "MNQH5", 20020.0, 300_000),
            ContractDay(date(2025, 3, 14), "MNQH5", 20030.0, 100_000),
            ContractDay(date(2025, 3, 17), "MNQH5", 20040.0, 50_000),
        ]
        m5 = [
            ContractDay(date(2025, 3, 11), "MNQM5", 20100.0, 100_000),
            ContractDay(date(2025, 3, 12), "MNQM5", 20110.0, 400_000),
            ContractDay(date(2025, 3, 13), "MNQM5", 20125.0, 800_000),
            ContractDay(date(2025, 3, 14), "MNQM5", 20135.0, 950_000),
            ContractDay(date(2025, 3, 17), "MNQM5", 20145.0, 990_000),
        ]
        return {"MNQH5": h5, "MNQM5": m5}

    def test_rolowanie_w_pierwszym_dniu_trwalej_przewagi(self):
        """Regula wolumenowa, nie kalendarzowa. Data = PIERWSZY dzien serii."""
        ev = find_roll_dates(self._dwa_kontrakty(), ["MNQH5", "MNQM5"])
        assert len(ev) == 1
        assert ev[0].roll_date == date(2025, 3, 13)
        assert ev[0].spread == pytest.approx(20125.0 - 20020.0)   # +105

    def test_jednodniowy_skok_wolumenu_nie_wyzwala_rolowania(self):
        """Zabezpieczenie z audytu: pojedyncza transakcja pakietowa nie moze
        przesadzac o dacie rolowania."""
        dane = self._dwa_kontrakty()
        m5 = list(dane["MNQM5"])
        # przewaga tylko w jednym dniu (13.03), potem znowu slabo
        m5[3] = ContractDay(date(2025, 3, 14), "MNQM5", 20135.0, 10_000)
        m5[4] = ContractDay(date(2025, 3, 17), "MNQM5", 20145.0, 10_000)
        dane["MNQM5"] = m5
        assert find_roll_dates(dane, ["MNQH5", "MNQM5"]) == []

    def test_przewaga_poza_oknem_wygasniecia_ignorowana(self):
        """Kontrakty listuja sie ponad rok wczesniej. Przewaga wolumenu
        dziesiec miesiecy przed wygasnieciem to artefakt rzadkiego handlu,
        nie rolowanie — na realnych danych dawala spready rzedu setek punktow.
        """
        dawno = [date(2024, 5, 6), date(2024, 5, 7), date(2024, 5, 8)]
        h5 = [ContractDay(d, "MNQH5", 18000.0, 5) for d in dawno]
        m5 = [ContractDay(d, "MNQM5", 18400.0, 50) for d in dawno]
        assert find_roll_dates({"MNQH5": h5, "MNQM5": m5}, ["MNQH5", "MNQM5"]) == []

    def test_brak_rolowania_gdy_wolumen_nie_przechodzi(self):
        dane = self._dwa_kontrakty()
        dane["MNQM5"] = [ContractDay(d.trade_date, d.contract, d.close, 1)
                         for d in dane["MNQM5"]]
        assert find_roll_dates(dane, ["MNQH5", "MNQM5"]) == []

    def test_offset_najnowszego_kontraktu_to_zero(self):
        """Ceny najnowszego kontraktu sa 'prawdziwe' — to punkt odniesienia."""
        ev = find_roll_dates(self._dwa_kontrakty(), ["MNQH5", "MNQM5"])
        off = cumulative_offsets(ev)
        assert off["MNQM5"] == 0.0
        assert off["MNQH5"] == pytest.approx(105.0)

    def test_offsety_kumuluja_sie_wstecz(self):
        ev = [
            RollEvent(date(2025, 3, 13), "A", "B", 100.0),
            RollEvent(date(2025, 6, 12), "B", "C", 50.0),
        ]
        off = cumulative_offsets(ev)
        assert off["C"] == 0.0
        assert off["B"] == pytest.approx(50.0)
        assert off["A"] == pytest.approx(150.0), "offset A = suma obu spreadow"

    def test_adjust_i_unadjust_sa_odwrotne(self):
        """Rozdzielenie serii wymaga konwersji w obie strony (rozdz. 4.3)."""
        off = {"MNQH5": 105.0, "MNQM5": 0.0}
        raw = 20020.0
        adj = adjust_price(raw, "MNQH5", off)
        assert adj == pytest.approx(20125.0)
        assert unadjust_price(adj, "MNQH5", off) == pytest.approx(raw)

    def test_back_adjust_zachowuje_roznice_cen(self):
        """Klucz metody roznicowej: P&L w punktach i ATR sa nietkniete."""
        off = {"MNQH5": 105.0}
        a_raw, b_raw = 20000.0, 20010.0
        a_adj = adjust_price(a_raw, "MNQH5", off)
        b_adj = adjust_price(b_raw, "MNQH5", off)
        assert (b_adj - a_adj) == pytest.approx(b_raw - a_raw)

    def test_nieznany_kontrakt_traktowany_jak_najnowszy(self):
        assert adjust_price(100.0, "NIEZNANY", {"A": 5.0}) == 100.0

    def test_dni_do_rolowania(self):
        ev = [RollEvent(date(2025, 3, 13), "A", "B", 100.0)]
        assert days_to_roll(date(2025, 3, 10), ev) == 3
        assert days_to_roll(date(2025, 3, 13), ev) == 0
        assert days_to_roll(date(2025, 3, 20), ev) is None


# ==========================================================================
# METRYKI
# ==========================================================================

class TestMetrics:
    def test_expectancy_to_srednia_w_r(self):
        assert expectancy(np.array([1.0, -1.0, 2.0, -1.0])) == pytest.approx(0.25)

    def test_profit_factor(self):
        assert profit_factor(np.array([2.0, -1.0, 1.0, -1.0])) == pytest.approx(1.5)

    def test_profit_factor_bez_strat_to_nieskonczonosc(self):
        assert profit_factor(np.array([1.0, 2.0])) == float("inf")

    def test_prog_podejrzliwosci(self):
        """PF > 2 w intraday: protokol nakazuje najpierw szukac bledu."""
        m = summarize(np.array([3.0, -1.0, 3.0, -1.0]), np.array([1.0, -0.3, 1.0, -0.3]))
        assert m.profit_factor > PF_SUSPICIOUS
        assert m.suspicious

    def test_sharpe_annualizowany(self):
        rng = np.random.default_rng(1)
        d = rng.normal(0.001, 0.01, 500)
        sr_d = sharpe_ratio(d, annualize=False)
        assert sharpe_ratio(d) == pytest.approx(sr_d * np.sqrt(252))

    def test_poprawka_lo_zmniejsza_modul_sharpe_przy_autokorelacji(self):
        """Autokorelacja ZAWYZA MODUL annualizowanego Sharpe'a.

        Uwaga na kierunek: poprawka dzieli przez sqrt(czynnik) > 1, wiec przy
        DODATNIM Sharpie obniza wartosc, a przy UJEMNYM podnosi ja (ku zeru).
        Wlasnoscia niezmiennicza jest zmniejszenie modulu — i to testujemy.
        (Pierwsza wersja tego testu asertowala na wartosci ze znakiem i poleglа
        na serii, ktorej zrealizowany dryf wyszedl ujemny.)
        """
        rng = np.random.default_rng(2)
        n = 600
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = 0.6 * x[i - 1] + rng.normal(0.004, 0.01)   # wyrazny dodatni dryf

        surowy = sharpe_ratio(x)
        poprawiony = sharpe_lo_correction(x)
        assert surowy > 0, "test wymaga dodatniego Sharpe'a, zeby kierunek byl jednoznaczny"
        assert abs(poprawiony) < abs(surowy)
        assert poprawiony < surowy

    def test_poprawka_lo_zmniejsza_modul_takze_dla_ujemnego_sharpe(self):
        """Kontrola symetrii: przy ujemnym Sharpie poprawka przesuwa go ku zeru."""
        rng = np.random.default_rng(21)
        n = 600
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = 0.6 * x[i - 1] + rng.normal(-0.004, 0.01)

        surowy = sharpe_ratio(x)
        poprawiony = sharpe_lo_correction(x)
        assert surowy < 0
        assert abs(poprawiony) < abs(surowy)
        assert poprawiony > surowy, "ujemny Sharpe po poprawce zbliza sie do zera"

    def test_poprawka_lo_neutralna_bez_autokorelacji(self):
        rng = np.random.default_rng(3)
        d = rng.normal(0.001, 0.01, 800)
        assert sharpe_lo_correction(d) == pytest.approx(sharpe_ratio(d), rel=0.25)

    def test_sortino_wyzszy_gdy_ogon_jest_po_stronie_zyskow(self):
        symetryczny = np.array([0.01, -0.01] * 50)
        asymetryczny = np.array([0.03, -0.005] * 50)
        assert sortino_ratio(asymetryczny) > sortino_ratio(symetryczny)

    def test_drawdown_i_czas_pod_woda(self):
        equity = np.array([0.0, 5.0, 3.0, 2.0, 6.0, 4.0])
        mdd, czas = drawdown_stats(equity)
        assert mdd == pytest.approx(3.0)     # szczyt 5 -> dolek 2
        assert czas == 2                      # dwa kroki ponizej szczytu

    def test_rosnaca_krzywa_bez_obsuniecia(self):
        mdd, czas = drawdown_stats(np.array([0.0, 1.0, 2.0, 3.0]))
        assert mdd == 0.0 and czas == 0

    def test_koncentracja_lapie_strategie_z_kilku_dni(self):
        """Chroni przed strategia 'z trzech szczesliwych dni' (rozdz. 1.3)."""
        skoncentrowana = np.array([10.0, 10.0, 10.0, 10.0, 10.0] + [0.01] * 200)
        rozlozona = np.array([0.5] * 205)
        assert top_n_concentration(skoncentrowana, 5) > CONCENTRATION_GATE
        assert top_n_concentration(rozlozona, 5) < CONCENTRATION_GATE

    def test_sqn_rosnie_z_liczba_transakcji(self):
        maly = np.array([1.0, -0.5] * 10)
        duzy = np.array([1.0, -0.5] * 100)
        assert sqn(duzy) > sqn(maly)

    def test_summarize_zwraca_komplet(self):
        rng = np.random.default_rng(4)
        r = rng.normal(0.1, 1.0, 300)
        d = rng.normal(0.002, 0.01, 300)
        m = summarize(r, d)
        assert m.n_trades == 300
        assert 0.0 <= m.win_rate <= 1.0
        assert isinstance(m.gate_report(), dict)
        assert set(m.gate_report()) == {"profit_factor", "sharpe", "koncentracja"}

    def test_puste_dane_nie_wywalaja(self):
        assert expectancy(np.array([])) == 0.0
        assert sharpe_ratio(np.array([1.0])) == 0.0
        assert drawdown_stats(np.array([])) == (0.0, 0)


class TestMetrykRBezStopa:
    """Strategia bez stopa ma R niezdefiniowane — i musi to POWIEDZIEC.

    Wykryte na benchmarkach B03/B04, ktorych regula literaturowa nie przewiduje
    stopa. Przed poprawka raport pokazywal `PF = 0.00` obok realnego wyniku
    w dolarach: liczba wygladajaca na pomiar, a bedaca cicha awaria pomiaru.
    """

    def test_wszystkie_r_zerowe_uniewazniaja_metryki_r(self):
        import numpy as np

        from engine.metrics import summarize
        m = summarize(np.zeros(40), np.array([10.0, -5.0, 3.0] * 30))
        assert m.r_metrics_valid is False
        assert math.isnan(m.profit_factor), "PF bez stopa musi byc NaN, nie zero"
        assert math.isnan(m.expectancy_r)
        assert math.isnan(m.sqn)
        assert math.isnan(m.win_rate)

    def test_metryki_dolarowe_pozostaja_poprawne(self):
        """Sharpe, MDD i koncentracja licza sie z dziennego P&L, nie z R —
        brak stopa ich nie uniewaznia."""
        import numpy as np

        from engine.metrics import summarize
        d = np.array([10.0, -5.0, 3.0] * 30)
        m = summarize(np.zeros(40), d)
        assert not math.isnan(m.sharpe) and m.sharpe != 0.0
        assert m.max_drawdown > 0
        assert 0.0 <= m.top5_concentration <= 1.0

    def test_choc_jedno_niezerowe_r_przywraca_metryki(self):
        import numpy as np

        from engine.metrics import summarize
        r = np.zeros(40)
        r[7] = 1.5
        m = summarize(r, np.array([10.0, -5.0, 3.0] * 30))
        assert m.r_metrics_valid is True
        assert not math.isnan(m.profit_factor)

    def test_pusty_zbior_transakcji_nie_wybucha(self):
        import numpy as np

        from engine.metrics import summarize
        m = summarize(np.array([]), np.array([1.0, -1.0]))
        assert m.n_trades == 0
        assert m.r_metrics_valid is False

    def test_koncentracja_niezdefiniowana_dla_strategii_stratnej(self):
        """Poprzednia wersja zwracala 0.0, co w raporcie czytalo sie jako
        'koncentracja wzorowa' — przy strategii, ktora po prostu traci."""
        import numpy as np

        from engine.metrics import top_n_concentration
        assert math.isnan(top_n_concentration(np.array([-10.0, -5.0, -1.0, 2.0])))
        assert math.isnan(top_n_concentration(np.array([])))

    def test_koncentracja_liczona_dla_strategii_zyskownej(self):
        import numpy as np

        from engine.metrics import top_n_concentration
        # 100 dni: piec po +10, reszta zerowa -> caly zysk z piatki
        d = np.zeros(100)
        d[:5] = 10.0
        assert top_n_concentration(d, 5) == pytest.approx(1.0)

    def test_koncentracja_rozproszona_jest_niska(self):
        import numpy as np

        from engine.metrics import top_n_concentration
        d = np.full(100, 1.0)
        assert top_n_concentration(d, 5) == pytest.approx(0.05)


# ==========================================================================
# CIAGLOSC PO ROLOWANIU — PLAN rozdz. 4.6 / 5.6
#
# Funkcja `verify_continuity` istniala od poczatku projektu i NIGDY nie byla
# wywolana ani przetestowana (audyt kodu, poz. R2). Ponizsze testy zamykaja
# ta luke ORAZ dokumentuja rzeczywiste ograniczenie tej funkcji, zamiast
# udawac, ze go nie ma.
# ==========================================================================

class TestCiaglosc:
    ROLL = date(2025, 3, 13)

    def _zdarzenie(self, spread: float = 100.0) -> list[RollEvent]:
        return [RollEvent(self.ROLL, "MNQH5", "MNQM5", spread)]

    def test_poprawnie_zrolowany_szereg_nie_zglasza_naruszen(self):
        """Seria po back-adjuscie rozni sie z dnia na dzien o ruch rynku,
        nie o spread rolowania."""
        seria = [
            (date(2025, 3, 11), 20000.0),
            (date(2025, 3, 12), 20010.0),
            (self.ROLL, 20005.0),        # ruch 5 pkt, spread 100 pkt
            (date(2025, 3, 14), 20020.0),
        ]
        assert verify_continuity(seria, self._zdarzenie()) == []

    def test_prawdziwa_nieciaglosc_jest_wykrywana(self):
        """Seria NIESKORYGOWANA: w dniu rolowania cena skacze o spread.
        To jest dokladnie ten skok, na ktorym amatorskie backtesty futures
        'zarabiaja' bez pokrycia."""
        seria = [
            (date(2025, 3, 12), 20010.0),
            (self.ROLL, 20110.0),        # skok = 100 = spread
            (date(2025, 3, 14), 20115.0),
        ]
        zgloszenia = verify_continuity(seria, self._zdarzenie())
        assert len(zgloszenia) == 1
        assert str(self.ROLL) in zgloszenia[0]
        # ETYKIETA: heurystyka NIE MOZE twierdzic, ze back-adjust zawiodl —
        # nie umie odroznic ruchu rynku od bledu korekty (patrz test ponizej).
        assert "back-adjust nie zadzialal" not in zgloszenia[0]
        assert "Heurystyka nie rozroznia" in zgloszenia[0]

    def test_granica_rollu_poza_seria_jest_pomijana(self):
        """Rolowanie, dla ktorego nie mamy danych, nie moze ani zglaszac
        naruszenia, ani wywracac funkcji."""
        seria = [(date(2025, 6, 1), 21000.0), (date(2025, 6, 2), 21010.0)]
        assert verify_continuity(seria, self._zdarzenie()) == []

    def test_rolowanie_w_pierwszym_dniu_serii_pomijane(self):
        """Nie ma dnia poprzedniego, wiec nie ma czego porownac."""
        seria = [(self.ROLL, 20110.0), (date(2025, 3, 14), 20115.0)]
        assert verify_continuity(seria, self._zdarzenie()) == []

    def test_pusta_seria_i_brak_zdarzen(self):
        assert verify_continuity([], self._zdarzenie()) == []
        assert verify_continuity([(self.ROLL, 20000.0)], []) == []

    def test_zerowy_spread_nie_generuje_naruszenia(self):
        """Rolowanie bez spreadu nie moze wygenerowac skoku, wiec kazdy ruch
        ceny tego dnia jest ruchem rynku."""
        seria = [(date(2025, 3, 12), 20010.0), (self.ROLL, 20300.0)]
        assert verify_continuity(seria, self._zdarzenie(spread=0.0)) == []

    def test_ujemny_spread_traktowany_symetrycznie(self):
        seria = [(date(2025, 3, 12), 20010.0), (self.ROLL, 19910.0)]
        assert len(verify_continuity(seria, self._zdarzenie(spread=-100.0))) == 1

    def test_ZNANE_OGRANICZENIE_duzy_ruch_rynku_daje_falszywy_alarm(self):
        """UDOKUMENTOWANA WADA, nie zyczenie.

        Warunek funkcji brzmi "skok >= |spread|", wiec KAZDY dzien rolowania
        z ruchem rynku wiekszym od spreadu zostanie zgloszony — nawet gdy
        back-adjust zadzialal bez zarzutu. Przy MNQ spread rolowania to
        zwykle kilkadziesiat punktow, a dzienny ruch 100+ punktow nie jest
        niczym nadzwyczajnym.

        Test jest tu po to, zeby ta wlasciwosc byla JAWNA. Wniosek praktyczny:
        `verify_continuity` nadaje sie na alarm wstepny, a nie na rozstrzygajacy
        pomiar ciaglosci — do tego sluzy niezmiennik arytmetyczny sprawdzany
        w scripts/data_quality.py (rownosc cen skorygowanych obu kontraktow
        w dniu rolowania), ktory ma odpowiedz DOKLADNIE zerowa.
        """
        seria = [
            (date(2025, 3, 12), 20000.0),
            (self.ROLL, 20150.0),        # ruch rynku 150 pkt, spread 100 pkt
        ]
        zgloszenia = verify_continuity(seria, self._zdarzenie(spread=100.0))
        assert len(zgloszenia) == 1, (
            "jesli ten test zaczal przechodzic inaczej, ktos zmienil semantyke "
            "verify_continuity — zaktualizuj raport jakosci i golden baseline"
        )

    def test_wartosci_diagnostyczne_nie_zmienily_sie_po_przeetykietowaniu(self):
        """BLOKADA NA ZMIANE KRYTERIUM PRZY OKAZJI ZMIANY ETYKIETY.

        Etap 2.5 zmienil ROLE tej funkcji z bramki PASS/FAIL na diagnostyke
        i przepisal tresc komunikatu. Ten test pilnuje, ze przy okazji NIE
        zmienil sie sam warunek: dokladnie te same granice maja byc zgloszone,
        co przed przeetykietowaniem.

        Cztery rolowania o znanym z gory werdykcie, wszystkie ze spreadem 50:
          A: ruch  10 < 50  -> cisza
          B: ruch  50 = 50  -> zgloszenie (prawdziwa nieciaglosc)
          C: ruch 150 > 50  -> zgloszenie (FALSZYWY ALARM, ruch rynku)
          D: ruch   0       -> cisza
        """
        daty = [date(2025, 3, 13), date(2025, 6, 12),
                date(2025, 9, 11), date(2025, 12, 11)]
        ruchy = [10.0, 50.0, 150.0, 0.0]
        seria: list[tuple[date, float]] = []
        zdarzenia: list[RollEvent] = []
        for i, (d, ruch) in enumerate(zip(daty, ruchy, strict=True)):
            seria.append((d.replace(day=d.day - 1), 20000.0))
            seria.append((d, 20000.0 + ruch))
            zdarzenia.append(RollEvent(d, f"K{i}", f"K{i + 1}", 50.0))

        zgloszone = {
            str(d) for d in daty
            if any(str(d) in z for z in verify_continuity(seria, zdarzenia))
        }
        assert zgloszone == {str(daty[1]), str(daty[2])}, (
            f"zgloszono {sorted(zgloszone)}, oczekiwano granic B i C — "
            "kryterium sie zmienilo, a mialo zmienic sie tylko nazewnictwo"
        )
