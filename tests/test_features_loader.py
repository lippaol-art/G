"""Testy cech pochodnych (rozdz. 5.2) i loadera (rozdz. 4.2).

Testy loadera wymagajace realnych danych sa oznaczone `needs_data` i pomijane
do czasu pobrania — to jawna GRANICA tego, co da sie zweryfikowac offline.
"""

from __future__ import annotations

import numpy as np
import pytest

from engine.features import (
    atr,
    atr_regime_ratio,
    initial_balance,
    overnight_range,
    prev_day_levels,
    rolling_percentile,
    true_range,
    vwap,
    vwap_sigma,
)
from engine.guards import AdjustedSeriesError
from engine.loader import (
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    DataNotAvailableError,
    SchemaError,
    clean_path,
    is_available,
    load_continuous,
    validate_schema,
)

# ==========================================================================
# CECHY
# ==========================================================================

class TestFeatures:
    def test_true_range_uwzglednia_luke(self):
        """TR musi widziec luke wzgledem poprzedniego zamkniecia."""
        assert true_range(105, 100, 102) == 5.0        # zakres wewnatrzbarowy
        assert true_range(105, 100, 90) == 15.0        # luka w gore od 90
        assert true_range(105, 100, 120) == 20.0       # luka w dol od 120

    def test_atr_usrednia_true_range(self):
        h = np.array([10.0, 11.0, 12.0, 13.0])
        low = np.array([9.0, 10.0, 11.0, 12.0])
        c = np.array([9.5, 10.5, 11.5, 12.5])
        assert atr(h, low, c, n=3) > 0

    def test_atr_krotkiej_serii_nie_wywala(self):
        assert atr(np.array([10.0]), np.array([9.0]), np.array([9.5])) == 0.0

    def test_vwap_wazy_wolumenem(self):
        """Cena z duzym wolumenem ma ciagnac VWAP ku sobie."""
        p = np.array([100.0, 200.0])
        assert vwap(p, np.array([1.0, 1.0])) == pytest.approx(150.0)
        assert vwap(p, np.array([9.0, 1.0])) == pytest.approx(110.0)

    def test_vwap_niewrazliwy_na_przesuniecie(self):
        """Back-adjust przesuwa ceny i VWAP o tyle samo — dlatego VWAP moze byc
        liczony na dowolnej serii (rozdz. 4.3)."""
        p = np.array([100.0, 110.0, 105.0])
        v = np.array([1.0, 2.0, 3.0])
        assert vwap(p + 500.0, v) == pytest.approx(vwap(p, v) + 500.0)

    def test_vwap_sigma_rosnie_z_rozrzutem(self):
        v = np.ones(4)
        waski = vwap_sigma(np.array([100.0, 101.0, 99.0, 100.0]), v)
        szeroki = vwap_sigma(np.array([90.0, 110.0, 85.0, 115.0]), v)
        assert szeroki > waski

    def test_percentyl_kroczacy(self):
        s = np.arange(100, dtype=float)
        assert rolling_percentile(s, 50.0, window=100) == pytest.approx(50.0)
        assert rolling_percentile(s, 5.0, window=100) < 10.0
        assert rolling_percentile(s, 95.0, window=100) > 90.0

    def test_percentyl_uzywa_tylko_okna(self):
        """Definicja rezimu ma byc lokalna, nie liczona od poczatku historii."""
        s = np.concatenate([np.zeros(500), np.arange(60, dtype=float)])
        assert rolling_percentile(s, 30.0, window=60) == pytest.approx(50.0, abs=5)

    def test_zakres_nocny(self):
        assert overnight_range(np.array([105.0, 103.0]), np.array([99.0, 101.0])) == 6.0

    def test_initial_balance(self):
        hi, lo = initial_balance(np.array([101.0, 103.0, 102.0]),
                                np.array([99.0, 100.0, 98.0]))
        assert (hi, lo) == (103.0, 98.0)

    def test_proxy_rezimu(self):
        assert atr_regime_ratio(2.0, 1.0) == 2.0      # cisza wzgledem oczekiwan
        assert atr_regime_ratio(1.0, 0.0) == 1.0      # zabezpieczenie przed dzieleniem


class TestPrevDayLevelsGuard:
    def test_poziomy_na_serii_surowej(self):
        lv = prev_day_levels(np.array([105.0]), np.array([99.0]), np.array([102.0]),
                             series_kind="raw")
        assert (lv.pdh, lv.pdl, lv.pdc) == (105.0, 99.0, 102.0)

    def test_poziomy_na_serii_skorygowanej_odrzucone(self):
        """Najwazniejszy strażnik tego modulu: PDH z serii skorygowanej to poziom,
        ktorego nikt nigdy nie widzial na tablicy (rozdz. 4.3)."""
        with pytest.raises(AdjustedSeriesError, match="4.3"):
            prev_day_levels(np.array([105.0]), np.array([99.0]), np.array([102.0]),
                            series_kind="adjusted")

    def test_brak_danych_odrzucony(self):
        with pytest.raises(ValueError):
            prev_day_levels(np.array([]), np.array([]), np.array([]))


# ==========================================================================
# LOADER — granica offline/online
# ==========================================================================

class TestLoaderSchema:
    def test_schemat_wymaga_rozdzielenia_serii(self):
        """Brak px_raw/px_adj to blad krytyczny — bez nich poziomy policzylyby
        sie na cenach skorygowanych."""
        assert "px_raw" in REQUIRED_COLUMNS
        assert "px_adj" in REQUIRED_COLUMNS

    def test_schemat_wymaga_klasyfikacji_luk(self):
        """gap_kind rozroznia expected od anomaly (rozdz. 4.2)."""
        assert "gap_kind" in REQUIRED_COLUMNS

    def test_walidacja_przepuszcza_komplet(self):
        assert validate_schema(list(REQUIRED_COLUMNS) + list(OPTIONAL_COLUMNS)) is None

    def test_walidacja_wskazuje_brakujace_kolumny(self):
        niepelne = [c for c in REQUIRED_COLUMNS if c != "px_raw"]
        with pytest.raises(SchemaError, match="px_raw"):
            validate_schema(niepelne)

    def test_sciezka_pliku(self):
        assert clean_path("MNQ").name == "mnq_1m_cont.parquet"

    def test_brak_danych_daje_instrukcje_a_nie_tylko_blad(self):
        """Komunikat ma prowadzic do rozwiazania — nastepna sesja moze nie miec
        kontekstu tej rozmowy."""
        if is_available("MNQ"):
            pytest.skip("dane juz dostepne")
        with pytest.raises(DataNotAvailableError, match="HANDOFF.md"):
            load_continuous("MNQ")


@pytest.mark.needs_data
class TestLoaderWithRealData:
    """GRANICA: te testy uruchomia sie dopiero po pobraniu danych (Etap 1).

    Do tego czasu sa jawnie pomijane — nie udajemy, ze cos zweryfikowalismy.
    """

    def setup_method(self):
        if not is_available("MNQ"):
            pytest.skip("brak data/clean/mnq_1m_cont.parquet — patrz HANDOFF.md")

    def test_wczytanie_i_schemat(self):
        df = load_continuous("MNQ")
        validate_schema(df.columns)
        assert df.height > 0

    def test_px_raw_i_px_adj_roznia_sie_przed_rolowaniem(self):
        df = load_continuous("MNQ")
        assert (df["px_raw"] != df["px_adj"]).any(), \
            "brak roznicy raw/adj — back-adjust nie zostal zastosowany"
