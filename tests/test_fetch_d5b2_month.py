"""Straznik downloadera miesiaca — testy o cenie w USD.

Kazdy blad w tym pliku kosztuje realne pieniadze i jest NIEODWRACALNY: raz
naliczonego pobrania nie da sie cofnac. Dlatego testy sa tu pisane wokol dwoch
pytan — czy skrypt WIDZI to, co juz mamy, i czy na pewno nie NADPISZE tego,
za co juz zaplacilismy.

Powod powstania: przy wycenie miesiaca skrypt zglosil "kompletnych juz na
dysku: 0" i zaproponowal zakup 22 sesji zamiast 21, bo sesji 2026-07-30
szukal w `d5b2_mbo/`, a ta lezy w `d5c_mbo/` pod ta sama nazwa. Wykryte przed
zakupem; kosztowaloby 3,5961 USD trzeciego naliczenia tej samej doby.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORZEN))

from scripts import fetch_d5b2_month as f  # noqa: E402

SESJA_D5C = "2026-07-30"


@pytest.fixture
def dane(tmp_path, monkeypatch):
    """Podstawia korzen danych na katalog tymczasowy."""
    def raw_dir(*czesci):
        p = tmp_path.joinpath(*czesci)
        (p.parent if p.suffix else p).mkdir(parents=True, exist_ok=True)
        return p
    monkeypatch.setattr(f, "raw_dir", raw_dir)
    return tmp_path


class TestSesjaZD5C:
    def test_plik_z_katalogu_d5c_jest_znaleziony(self, dane):
        """Sedno naprawy: ta sama nazwa, inny katalog."""
        plik = dane / f.KATALOG_D5C / f.nazwa_pliku(SESJA_D5C)
        plik.parent.mkdir(parents=True, exist_ok=True)
        plik.write_bytes(b"x")
        assert f.sciezka_istniejaca(SESJA_D5C) == plik

    def test_wlasny_katalog_ma_pierwszenstwo(self, dane):
        """Gdy sesja jest w obu miejscach, uzywamy swojej kopii."""
        for kat in (f.KATALOG, f.KATALOG_D5C):
            p = dane / kat / f.nazwa_pliku(SESJA_D5C)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"x")
        assert f.sciezka_istniejaca(SESJA_D5C).parent.name == f.KATALOG

    def test_bez_pliku_wskazuje_cel_pobrania(self, dane):
        assert f.sciezka_istniejaca(SESJA_D5C) == f.sciezka_docelowa(SESJA_D5C)


class TestOchronaKanonicznegoPliku:
    def test_pobieranie_nigdy_nie_celuje_w_katalog_d5c(self, dane):
        """NAJWAZNIEJSZY TEST W TYM PLIKU.

        Skrypt kasuje niekompletny plik przed ponownym pobraniem. Gdyby celem
        pobrania mogl byc `d5c_mbo/`, przerwany transfer skasowalby kanoniczny
        plik D5-C — ten, na ktorym stoi caly audyt Etapu 3 (842 757 zdarzen,
        0 niewyjasnionych) i ktorego SHA jest zamrozony w golden baseline.
        """
        for sesja in f.SESJE:
            assert f.sciezka_docelowa(sesja).parent.name == f.KATALOG

    def test_cel_pobrania_nie_zalezy_od_tego_co_lezy_na_dysku(self, dane):
        plik = dane / f.KATALOG_D5C / f.nazwa_pliku(SESJA_D5C)
        plik.parent.mkdir(parents=True, exist_ok=True)
        plik.write_bytes(b"x")
        assert f.sciezka_docelowa(SESJA_D5C).parent.name == f.KATALOG
        assert f.sciezka_istniejaca(SESJA_D5C).parent.name == f.KATALOG_D5C


class TestKompletnosc:
    def test_pusty_plik_nie_jest_kompletny(self, dane):
        p = dane / "pusty.dbn.zst"
        p.write_bytes(b"")
        ok, powod = f.kompletny(p, 100)
        assert not ok and "pusty" in powod

    def test_brak_pliku_nie_jest_kompletny(self, dane):
        ok, powod = f.kompletny(dane / "nie_ma.dbn.zst", 100)
        assert not ok and "brak" in powod

    def test_smiec_nie_udaje_kompletnego(self, dane):
        """Istnienie nie wystarcza — plik musi sie SPARSOWAC."""
        p = dane / "smiec.dbn.zst"
        p.write_bytes(b"to nie jest DBN")
        ok, powod = f.kompletny(p, 100)
        assert not ok and "parsuje" in powod


class TestZamrozoneStale:
    def test_lista_sesji_ma_22_pozycje_lipca_2026(self):
        assert len(f.SESJE) == 22
        assert all(s.startswith("2026-07-") for s in f.SESJE)
        assert SESJA_D5C in f.SESJE, "sesja z D5-C nalezy do miesiaca"

    def test_limit_kosztu_zgodny_ze_specyfikacja(self):
        """Zamrozony w docs/D5_ETAP4_SPEC.md §7 PRZED zakupem."""
        assert f.LIMIT_USD == 82.00

    def test_okno_rth_wyprowadzone_ze_strefy_et(self):
        """Lipiec to czas letni: 09:30 ET = 13:30 UTC."""
        a, b = f.okno("2026-07-15")
        assert a == "2026-07-15T13:30"
        assert b == "2026-07-15T20:00"
