"""Ponawianie zapytan metadanych — i granica, ktorej ponawiac NIE wolno."""

from __future__ import annotations

import pytest

from engine.databento_io import metadane_z_ponowieniem


class BladBramy(Exception):
    pass


class TestPonawianie:
    def test_sukces_za_pierwszym_razem_nie_ponawia(self):
        wolania = []

        def fn():
            wolania.append(1)
            return 42

        assert metadane_z_ponowieniem(fn, odstepy=()) == 42
        assert len(wolania) == 1

    def test_ponawia_po_504_i_zwraca_wynik(self):
        wolania = []

        def fn():
            wolania.append(1)
            if len(wolania) < 3:
                raise BladBramy("504 The remote gateway timed out.")
            return "ok"

        assert metadane_z_ponowieniem(fn, odstepy=(0, 0, 0)) == "ok"
        assert len(wolania) == 3

    def test_przekazuje_argumenty(self):
        def fn(a, *, b):
            return a + b

        assert metadane_z_ponowieniem(fn, 1, b=2, odstepy=()) == 3

    @pytest.mark.parametrize("komunikat", [
        "504 The remote gateway timed out.",
        "502 Bad Gateway",
        "503 Service Unavailable",
        "Connection timed out",
    ])
    def test_rozpoznaje_bledy_przejsciowe(self, komunikat):
        wolania = []

        def fn():
            wolania.append(1)
            if len(wolania) == 1:
                raise BladBramy(komunikat)
            return "ok"

        assert metadane_z_ponowieniem(fn, odstepy=(0,)) == "ok"

    def test_blad_trwaly_nie_jest_ponawiany(self):
        """4xx to blad zapytania, nie awaria dostawcy — ponawianie niczego nie
        naprawi, a opoznia zgloszenie problemu autorowi."""
        wolania = []

        def fn():
            wolania.append(1)
            raise BladBramy("422 Unprocessable Entity: zly zakres dat")

        with pytest.raises(BladBramy, match="422"):
            metadane_z_ponowieniem(fn, odstepy=(0, 0, 0))
        assert len(wolania) == 1, "blad trwaly ma polecec od razu"

    def test_wyczerpanie_prob_przekazuje_ostatni_blad(self):
        def fn():
            raise BladBramy("504 gateway")

        with pytest.raises(BladBramy, match="504"):
            metadane_z_ponowieniem(fn, odstepy=(0, 0))


def test_modul_nie_udostepnia_ponawiania_pobierania():
    """GRANICA ARCHITEKTONICZNA, nie przeoczenie.

    Pobieranie jest PLATNE i tworzy plik: slepe ponowienie grozi podwojnym
    naliczeniem i cichym pozostawieniem obcietej sesji, ktora parsuje sie bez
    bledu. Ten modul obsluguje wylacznie darmowe metadane. Gdyby ktos dopisal
    tu funkcje ponawiajaca `get_range`, ten test ma o tym przypomniec.
    """
    import engine.databento_io as m

    publiczne = [n for n in dir(m) if not n.startswith("_") and callable(getattr(m, n))]
    zakazane = [n for n in publiczne
                if any(s in n.lower() for s in ("range", "pobier", "download"))]
    assert not zakazane, f"modul nie moze ponawiac pobierania: {zakazane}"
