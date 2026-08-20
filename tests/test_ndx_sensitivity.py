"""Wrazliwosc indeksu na skladniki — PLAN.pdf rozdz. 4.7, karta H013.

Modul liczy lewa strone rownania H013: ile indeks POWINIEN sie poruszyc przy
zadanych zwrotach skladnikow. Rezyduum karty to roznica wobec ruchu faktycznego,
wiec systematyczny blad w tych wspolczynnikach jest NIEODROZNIALNY OD SYGNALU.

Stad dwa priorytety tych testow: brak lookaheadu i stabilnosc estymacji.
"""

from __future__ import annotations

import numpy as np
import pytest

from engine.ndx_sensitivity import (
    MEGACAPY,
    MIN_OKNO,
    dopasuj,
    kroczaca,
)


def dane(n: int = 600, seed: int = 0, wagi=None):
    """Indeks zbudowany JAWNIE jako kombinacja skladnikow o znanych wagach."""
    rng = np.random.default_rng(seed)
    w = np.array(wagi if wagi is not None else [0.15, 0.14, 0.10, 0.10, 0.09, 0.07, 0.08, 0.06])
    X = rng.normal(0, 0.02, (n, 8))
    y = X @ w + rng.normal(0, 0.001, n)     # maly szum idiosynkratyczny indeksu
    return y, X, w


class TestOdtwarzaniaWspolczynnikow:
    def test_znane_wagi_sa_odtwarzane(self):
        """Warunek konieczny: jesli indeks JEST kombinacja liniowa, musimy
        odzyskac jej wspolczynniki."""
        y, X, w = dane()
        wyn = dopasuj(y, X)
        assert np.abs(wyn.beta - w).max() < 0.01, f"odzyskano {wyn.beta.round(3)}, oczekiwano {w}"
        # R^2 < 1 Z KONSTRUKCJI: fixture zawiera szum idiosynkratyczny indeksu,
        # ktory odwzorowuje pozostale ~92 skladniki NDX. Przy sile szumu 0.001
        # wobec sygnalu 0.006 teoretyczne R^2 wynosi ~0.97 — i tyle wychodzi.
        # Na realnych danych QQQ vs osemka megacapow daje 0.88-0.98, wiec
        # fixture jest tu wiernym, a nie wyidealizowanym modelem.
        assert wyn.r2 > 0.95

    def test_ridge_nie_przesuwa_sumy(self):
        """Regularyzacja ma stabilizowac, nie zanizac. Suma wspolczynnikow
        wchodzi wprost w implikowany impuls, wiec jej przesuniecie przesuwa
        kazde rezyduum."""
        y, X, w = dane()
        wyn = dopasuj(y, X)
        assert abs(wyn.suma - w.sum()) / w.sum() < 0.01

    def test_skorelowane_skladniki_nie_wywracaja_estymacji(self):
        """Megacapy sa skorelowane 0.4-0.7. OLS daje wtedy wspolczynniki
        niestabilne i czesciowo ujemne — ridge ma temu zapobiec."""
        rng = np.random.default_rng(3)
        wspolny = rng.normal(0, 0.015, 600)
        X = np.column_stack([wspolny + rng.normal(0, 0.01, 600) for _ in range(8)])
        w = np.full(8, 0.1)
        y = X @ w + rng.normal(0, 0.001, 600)
        wyn = dopasuj(y, X)
        assert abs(wyn.suma - 0.8) < 0.05, f"suma {wyn.suma:.3f} zamiast ~0.8"
        assert (wyn.beta > -0.05).all(), f"ujemne wspolczynniki: {wyn.beta.round(3)}"

    def test_implikowany_impuls_to_iloczyn_skalarny(self):
        y, X, w = dane()
        wyn = dopasuj(y, X)
        zwroty = np.array([0.05, 0, 0, 0, 0, 0, 0, 0])
        assert wyn.implikowany_impuls(zwroty) == pytest.approx(wyn.beta[0] * 0.05)

    def test_zla_liczba_zwrotow_jest_bledem(self):
        y, X, _ = dane()
        wyn = dopasuj(y, X)
        with pytest.raises(ValueError, match="oczekiwano 8"):
            wyn.implikowany_impuls(np.array([0.01, 0.02]))


class TestBrakuLookaheadu:
    """Najwazniejsza klasa w tym pliku.

    Wspolczynnik na dzien D policzony z okna OBEJMUJACEGO dzien D czynilby
    implikowany impuls czesciowo znanym z przyszlosci — a rezyduum, ktore z niego
    wychodzi, wygladaloby na przewage. Byloby to dokladnie to skrzywienie, przed
    ktorym broni cala reszta silnika.
    """

    def test_okno_konczy_sie_przed_dniem_docelowym(self):
        """Test konstrukcyjny: dzien docelowy zmieniamy DRASTYCZNIE i sprawdzamy,
        ze wspolczynniki sie nie ruszaja."""
        y, X, _ = dane(600, seed=1)
        wyn_a = kroczaca(y, X, 400)
        y2, X2 = y.copy(), X.copy()
        y2[400] = 999.0                       # absurdalna wartosc w dniu docelowym
        X2[400] = 999.0
        wyn_b = kroczaca(y2, X2, 400)
        assert wyn_a is not None and wyn_b is not None
        assert np.array_equal(wyn_a.beta, wyn_b.beta), \
            "dzien docelowy wplynal na wspolczynniki — okno siega za daleko"

    def test_przyszlosc_nie_wplywa_na_biezacy_dzien(self):
        y, X, _ = dane(600, seed=1)
        wyn_a = kroczaca(y, X, 400)
        y2, X2 = y.copy(), X.copy()
        y2[401:] = 999.0                      # cala przyszlosc zepsuta
        X2[401:] = 999.0
        wyn_b = kroczaca(y2, X2, 400)
        assert np.array_equal(wyn_a.beta, wyn_b.beta)

    def test_zmiana_przeszlosci_WPLYWA(self):
        """Kontrola przeciwna. Bez niej poprzednie testy przechodzilyby takze
        wtedy, gdyby funkcja zwracala stala."""
        y, X, _ = dane(600, seed=1)
        wyn_a = kroczaca(y, X, 400)
        y2 = y.copy()
        y2[300] = 0.5
        wyn_b = kroczaca(y2, X, 400)
        assert not np.array_equal(wyn_a.beta, wyn_b.beta), \
            "zmiana danych W OKNIE nie zmienila wspolczynnikow — estymacja jest martwa"

    def test_za_krotka_historia_zwraca_None_a_nie_zero(self):
        """Ciche zero bylo by gorsze niz brak wyniku: implikowany impuls wyszedlby
        zerowy, a rezyduum rowne calemu ruchowi indeksu."""
        y, X, _ = dane(600)
        assert kroczaca(y, X, MIN_OKNO - 1) is None
        assert kroczaca(y, X, 0) is None

    def test_okno_ma_zadana_dlugosc(self):
        y, X, _ = dane(600)
        wyn = kroczaca(y, X, 400, okno=250)
        assert wyn is not None and wyn.n_obs == 250

    def test_na_poczatku_okno_jest_krotsze_ale_wystarczajace(self):
        y, X, _ = dane(600)
        wyn = kroczaca(y, X, MIN_OKNO, okno=250)
        assert wyn is not None and wyn.n_obs == MIN_OKNO


class TestWalidacjiWejscia:
    def test_niezgodne_ksztalty_sa_bledem(self):
        y, X, _ = dane(600)
        with pytest.raises(ValueError, match="niezgodne ksztalty"):
            dopasuj(y[:100], X)

    def test_zla_liczba_kolumn_jest_bledem(self):
        y, X, _ = dane(600)
        with pytest.raises(ValueError, match="kolumn wobec"):
            dopasuj(y, X[:, :5])

    def test_za_male_okno_jest_bledem(self):
        y, X, _ = dane(600)
        with pytest.raises(ValueError, match="ponizej minimum"):
            dopasuj(y[:50], X[:50])

    def test_lista_megacapow_ma_osiem_pozycji(self):
        assert len(MEGACAPY) == 8
        assert len(set(MEGACAPY)) == 8
