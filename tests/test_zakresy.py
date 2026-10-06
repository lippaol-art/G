"""Asercje zakresu — druga warstwa obrony po rzutowaniu typow.

Testy odtwarzaja RZECZYWISTE przepelnienie, ktore dwa razy przeszlo przez ten
projekt: odejmowanie kolumn bez znaku daje ~1,8e19 zamiast liczby ujemnej.
Nie symuluja go stala — wykonuja prawdziwe odejmowanie na typach UInt64,
zeby test przestal chronic, gdyby polars zmienil zachowanie.
"""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from engine.guards import (
    RangeError,
    assert_imbalance,
    assert_liczebnosc,
    assert_prawdopodobienstwo,
    assert_udzial,
    assert_vif,
    assert_w_zakresie,
)


class TestPrzepelnienieJestRealne:
    """Fundament: bez tego reszta testow bylaby teatrem."""

    def test_odejmowanie_uint_naprawde_sie_przepelnia(self):
        d = pl.DataFrame({"a": [1], "b": [5]},
                         schema={"a": pl.UInt64, "b": pl.UInt64})
        wynik = d.select((pl.col("a") - pl.col("b")).alias("r"))["r"][0]
        assert wynik > 1e19, "polars zmienil zachowanie — przejrzyj asercje"

    def test_rzutowanie_na_int64_naprawia(self):
        d = pl.DataFrame({"a": [1], "b": [5]},
                         schema={"a": pl.UInt64, "b": pl.UInt64})
        wynik = d.select(
            (pl.col("a").cast(pl.Int64) - pl.col("b").cast(pl.Int64)).alias("r")
        )["r"][0]
        assert wynik == -4

    def test_asercja_lapie_przepelniona_nierownowage(self):
        """Dokladny ksztalt bledu z Etapu 2 D5."""
        d = pl.DataFrame({"n_buy": [1, 8], "n_sell": [5, 2]},
                         schema={"n_buy": pl.UInt32, "n_sell": pl.UInt32})
        zle = d.select(
            ((pl.col("n_buy") - pl.col("n_sell"))
             / (pl.col("n_buy") + pl.col("n_sell"))).alias("I")
        )["I"]
        with pytest.raises(RangeError, match="BLAD OBLICZENIA"):
            assert_imbalance(zle, nazwa="I_count")

    def test_asercja_przepuszcza_poprawna_nierownowage(self):
        d = pl.DataFrame({"n_buy": [1, 8], "n_sell": [5, 2]},
                         schema={"n_buy": pl.UInt32, "n_sell": pl.UInt32})
        dobre = d.select(
            ((pl.col("n_buy").cast(pl.Int64) - pl.col("n_sell").cast(pl.Int64))
             / (pl.col("n_buy") + pl.col("n_sell"))).alias("I")
        )["I"]
        assert_imbalance(dobre, nazwa="I_count")
        assert abs(dobre[0] + 4 / 6) < 1e-12


class TestZakresy:
    def test_imbalance_granice_wlaczne(self):
        # Granice sa WLACZNE: nierownowaga +-1 to okno jednostronne,
        # zjawisko normalne, a nie blad. Asercja zwraca None, gdy przechodzi.
        assert assert_imbalance([-1.0, 0.0, 1.0]) is None

    def test_imbalance_odrzuca_poza(self):
        with pytest.raises(RangeError):
            assert_imbalance([0.0, 1.5])
        with pytest.raises(RangeError):
            assert_imbalance([-1.000001, 0.0])

    def test_udzial_i_prawdopodobienstwo(self):
        assert_udzial([0.0, 0.5, 1.0])
        assert_prawdopodobienstwo(np.array([0.0, 1.0]))
        with pytest.raises(RangeError):
            assert_udzial([-0.01])
        with pytest.raises(RangeError):
            assert_prawdopodobienstwo([1.01])

    def test_liczebnosc(self):
        assert_liczebnosc([0, 1, 10_000])
        with pytest.raises(RangeError, match="liczebnosc musi byc >= 0"):
            assert_liczebnosc([3, -1])

    def test_vif(self):
        assert_vif([1.0, 1.548, 12.0])
        with pytest.raises(RangeError, match="VIF < 1"):
            assert_vif([0.9])

    def test_nan_jest_bledem_nie_cisza(self):
        """Metryka zwracajaca NaN nie moze po cichu przejsc asercji (W003)."""
        with pytest.raises(RangeError, match="NaN"):
            assert_w_zakresie(np.array([0.5, np.nan]), 0.0, 1.0, nazwa="x")

    def test_pusta_seria_nie_wybucha(self):
        assert assert_imbalance(pl.Series("x", [], dtype=pl.Float64)) is None

    def test_dziala_na_numpy_polars_i_liscie(self):
        for w in ([0.5], np.array([0.5]), pl.Series("x", [0.5])):
            assert assert_udzial(w) is None

    def test_komunikat_nazywa_zmienna(self):
        with pytest.raises(RangeError, match="A_count"):
            assert_imbalance([2.0], nazwa="A_count")


class TestSkalary:
    """Asercja musi dzialac na pojedynczej liczbie — inaczej wywraca sie
    dokladnie tam, gdzie miala chronic (zlapane przy podlaczaniu do D5-B)."""

    def test_skalar_w_zakresie(self):
        assert assert_udzial(0.1021, nazwa="koncentracja") is None
        assert assert_vif(1.548, nazwa="pooled VIF") is None
        assert assert_imbalance(-0.5) is None

    def test_skalar_poza_zakresem(self):
        with pytest.raises(RangeError):
            assert_udzial(1.5, nazwa="koncentracja")
        with pytest.raises(RangeError):
            assert_vif(0.5)

    def test_skalar_int(self):
        assert_liczebnosc(0)
        with pytest.raises(RangeError):
            assert_liczebnosc(-1)

    def test_pusta_lista(self):
        assert assert_udzial([]) is None
