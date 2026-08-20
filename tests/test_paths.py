"""Magazyn danych poza repozytorium — `PROJECT_G_DATA_ROOT`."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from engine.paths import REPO, ZMIENNA, clean_dir, data_root, raw_dir, wolne_gb


@pytest.fixture
def bez_zmiennej(monkeypatch):
    monkeypatch.delenv(ZMIENNA, raising=False)


@pytest.fixture
def z_katalogiem(monkeypatch, tmp_path):
    monkeypatch.setenv(ZMIENNA, str(tmp_path))
    return tmp_path


class TestDomyslnie:
    def test_bez_zmiennej_uzywa_repozytorium(self, bez_zmiennej):
        assert data_root() == REPO / "data"

    def test_raw_wzgledem_repozytorium(self, bez_zmiennej):
        assert raw_dir() == REPO / "data" / "raw"
        assert raw_dir("d5c_mbo") == REPO / "data" / "raw" / "d5c_mbo"

    def test_pusta_zmienna_traktowana_jak_brak(self, monkeypatch):
        """Pusty string w zmiennej srodowiskowej to czesty artefakt skryptow
        powloki — nie moze skierowac danych do katalogu glownego."""
        monkeypatch.setenv(ZMIENNA, "   ")
        assert data_root() == REPO / "data"


class TestPrzekierowanie:
    def test_zmienna_przekierowuje_raw(self, z_katalogiem):
        assert data_root() == z_katalogiem.resolve()
        assert raw_dir("mbo") == z_katalogiem.resolve() / "raw" / "mbo"

    def test_clean_zostaje_w_repozytorium(self, z_katalogiem):
        """KLUCZOWE: `data/clean/` jest artefaktem wersjonowanym i musi zostac
        w gicie, bo na nim stoi `hash_danych` golden baseline'u. Przekierowanie
        go zerwaloby punkt odniesienia."""
        assert clean_dir() == REPO / "data" / "clean"
        assert z_katalogiem not in clean_dir().parents

    def test_rozwija_tylde(self, monkeypatch):
        monkeypatch.setenv(ZMIENNA, "~/dane_g")
        assert "~" not in str(data_root())
        assert data_root().is_absolute()


class TestWolneMiejsce:
    def test_zwraca_dodatnia_liczbe(self, bez_zmiennej):
        assert wolne_gb() > 0

    def test_dziala_dla_nieistniejacej_sciezki(self, tmp_path):
        """Sprawdzamy miejsce PRZED utworzeniem katalogu docelowego, wiec
        funkcja musi wspinac sie do istniejacego przodka."""
        assert wolne_gb(tmp_path / "a" / "b" / "c") > 0


def test_zmienna_nie_wycieka_do_innych_testow():
    """Straznik higieny: gdyby ktorys test zostawil zmienna ustawiona,
    kolejne liczylyby sciezki wzgledem cudzego katalogu."""
    assert os.environ.get(ZMIENNA, "") in ("", str(Path(os.environ.get(ZMIENNA, "") or ".")))
