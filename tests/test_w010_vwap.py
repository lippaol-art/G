"""Testy sigmy VWAP liczonej narastajaco — W010, karta H002.

Pierwsza wersja W010 liczyla `suma v_i (p_i - VWAP_i)^2`, czyli odejmowala kazda
obserwacje od VWAP **z jej wlasnego momentu**, a nie od biezacego. To nie jest
wariancja wokol niczego i zawyzalo sigme, a od sigmy zalezy zarowno kwalifikacja
zdarzenia (|d| >= 1), jak i udzial odziedziczony.

Test wiaze implementacje narastajaca z **kanoniczna** `engine.features.vwap_sigma`:
sigma w chwili t musi rownac sie sigmie policzonej na prefiksie do t. To jest
mocniejsze niz porownanie z recznie policzonym przykladem, bo sprawdza zgodnosc
z definicja uzywana w calym projekcie, a nie z moim wlasnym rachunkiem.
"""

from __future__ import annotations

import numpy as np
import pytest

from engine.features import vwap, vwap_sigma
from research.W010_partia3_preflight import sigma_narastajaca


class TestSigmaNarastajaca:
    def test_zgodna_z_kanoniczna_na_kazdym_prefiksie(self):
        ceny = np.array([100.0, 101.0, 99.5, 102.0, 98.0, 103.5, 100.25])
        wol = np.array([10.0, 5.0, 20.0, 1.0, 8.0, 3.0, 12.0])
        got = sigma_narastajaca(ceny, wol)
        for t in range(1, ceny.size):
            oczekiwane = vwap_sigma(ceny[: t + 1], wol[: t + 1])
            assert got[t] == pytest.approx(oczekiwane, rel=1e-9, abs=1e-9), (
                f"prefiks do t={t}: {got[t]} != {oczekiwane}"
            )

    def test_pierwsza_obserwacja_ma_zerowa_sigme(self):
        """Jedna cena nie ma rozrzutu — kanoniczna zwraca 0.0 dla p.size < 2."""
        got = sigma_narastajaca(np.array([100.0]), np.array([7.0]))
        assert got[0] == pytest.approx(0.0, abs=1e-12)

    def test_stala_cena_daje_zero(self):
        ceny = np.full(6, 250.0)
        wol = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        assert np.allclose(sigma_narastajaca(ceny, wol), 0.0, atol=1e-9)

    def test_nie_zwraca_nan_przy_duzych_cenach(self):
        """Tozsamosc E[p^2] - VWAP^2 moze dac ujemne zero przy duzych poziomach.

        MNQ chodzi po ~20 000, wiec p^2 ~ 4e8 przy sigmie rzedu 20. Bez zabezpieczenia
        pierwiastek z ujemnej resztki zaokraglenia dalby NaN — i to w polowie serii,
        cicho.
        """
        rng = np.random.default_rng(7)
        ceny = 20000.0 + rng.normal(0, 0.25, 500)
        wol = rng.uniform(1, 100, 500)
        got = sigma_narastajaca(ceny, wol)
        assert np.isfinite(got).all()
        assert (got >= 0).all()

    def test_bledna_wersja_zawyza(self):
        """Regresja na konkretnej usterce: stara formula dawala inny wynik.

        Nie chodzi o to, ktora liczba jest wieksza, tylko o to, ze te dwie formuly
        **nie sa tym samym** — a poprzednia wersja W010 traktowala je zamiennie.
        """
        ceny = np.array([100.0, 110.0, 90.0, 105.0])
        wol = np.array([1.0, 1.0, 1.0, 1.0])
        vw = np.array([vwap(ceny[: t + 1], wol[: t + 1]) for t in range(ceny.size)])
        stara = np.sqrt(np.cumsum(wol * (ceny - vw) ** 2) / np.cumsum(wol))
        nowa = sigma_narastajaca(ceny, wol)
        assert not np.allclose(stara[-1], nowa[-1])
        assert nowa[-1] == pytest.approx(vwap_sigma(ceny, wol), rel=1e-9)
