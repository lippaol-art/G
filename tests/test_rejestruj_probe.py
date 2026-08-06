"""Straznik licznika prob — testy o znanej odpowiedzi.

Licznik wchodzi wprost do mianownika DSR. Blad w te strone, ktora ZANIZA
licznik, certyfikuje strategie niezasluzenie i nie zostawia sladu w zadnym
wyniku — dlatego kazda odmowa ma tu wlasny test.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORZEN))

from scripts.rejestruj_probe import PROG_SR_DZIENNY, main  # noqa: E402


def _licznik(total=0, by=None, sharpes=None, history=None) -> dict:
    return {
        "_comment": "test",
        "_rules": {
            "max_variants_per_hypothesis": 10,
            "max_variants_per_batch": 40,
            "benchmarks_excluded": True,
            "benchmarks_reason": "test",
        },
        "total_trials": total,
        "by_hypothesis": by or {},
        "trial_sharpes_daily": sharpes or [],
        "history": history or [],
    }


@pytest.fixture
def licznik(tmp_path, monkeypatch):
    """Podstawia licznik na plik tymczasowy i udaje czyste drzewo."""
    import scripts.rejestruj_probe as rp

    plik = tmp_path / "trial_counter.json"
    plik.write_text(json.dumps(_licznik()), encoding="utf-8")
    monkeypatch.setattr(rp, "LICZNIK", plik)
    monkeypatch.setattr(rp, "stan_drzewa", lambda: "")
    monkeypatch.setattr(rp, "_git", lambda *a: "0" * 40)
    return plik


def _uruchom(argv, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["rejestruj_probe.py", *argv])
    return main()


ARGS = ["--karta", "H017", "--sr-dzienny", "0.031", "--opis", "wariant bazowy"]


class TestZapis:
    def test_proba_podnosi_licznik_i_dopisuje_sr(self, licznik, monkeypatch):
        _uruchom(ARGS, monkeypatch)
        d = json.loads(licznik.read_text(encoding="utf-8"))
        assert d["total_trials"] == 1
        assert d["by_hypothesis"] == {"H017": 1}
        assert d["trial_sharpes_daily"] == [0.031]
        assert len(d["history"]) == 1

    def test_wpis_wiaze_wynik_z_kodem(self, licznik, monkeypatch):
        """Bez SHA wpis mowi 'zmierzylismy 0.031' i nic wiecej — nie da sie
        wrocic do kodu, ktory te liczbe wyprodukowal."""
        _uruchom([*ARGS, "--raport", "reports/x.md"], monkeypatch)
        w = json.loads(licznik.read_text(encoding="utf-8"))["history"][0]
        assert w["commit"] == "0" * 40
        assert w["raport"] == "reports/x.md"
        assert w["opis"] == "wariant bazowy"

    def test_benchmark_nie_zuzywa_proby(self, licznik, monkeypatch):
        """Benchmark uruchamiany raz z parametrami z literatury nie jest proba
        selekcji — nie wchodzi ani do licznika, ani do rozrzutu SR-ow."""
        _uruchom(["--karta", "B06", "--sr-dzienny", "0.01",
                  "--opis", "z literatury", "--benchmark"], monkeypatch)
        d = json.loads(licznik.read_text(encoding="utf-8"))
        assert d["total_trials"] == 0
        assert d["trial_sharpes_daily"] == []
        assert d["by_hypothesis"] == {}
        assert len(d["history"]) == 1, "ale slad w historii ZOSTAJE"


class TestOdmowy:
    def test_brudne_drzewo_przerywa(self, licznik, monkeypatch):
        import scripts.rejestruj_probe as rp
        monkeypatch.setattr(rp, "stan_drzewa", lambda: " M engine/backtest.py")

        with pytest.raises(SystemExit) as e:
            _uruchom(ARGS, monkeypatch)
        assert "drzewo robocze" in str(e.value)
        assert json.loads(licznik.read_text())["total_trials"] == 0

    def test_sr_roczny_podany_jako_dzienny_przerywa(self, licznik, monkeypatch):
        """Najczestszy blad implementacji DSR (poprawka A2-4)."""
        with pytest.raises(SystemExit) as e:
            _uruchom(["--karta", "H017", "--sr-dzienny", "1.2",
                      "--opis", "x"], monkeypatch)
        assert "ROCZNY" in str(e.value)
        assert json.loads(licznik.read_text())["total_trials"] == 0

    def test_sr_tuz_pod_progiem_przechodzi(self, licznik, monkeypatch):
        """Straznik nie moze blokowac wartosci dopuszczalnej."""
        _uruchom(["--karta", "H017", "--sr-dzienny", str(PROG_SR_DZIENNY - 0.01),
                  "--opis", "x"], monkeypatch)
        assert json.loads(licznik.read_text())["total_trials"] == 1

    def test_ujemny_sr_jest_dozwolony(self, licznik, monkeypatch):
        """Proba nieudana to nadal zuzyta proba — inaczej licznik mierzylby
        sukcesy zamiast prob i DSR bylby zawyzony."""
        _uruchom(["--karta", "H017", "--sr-dzienny", "-0.08",
                  "--opis", "x"], monkeypatch)
        d = json.loads(licznik.read_text())
        assert d["total_trials"] == 1
        assert d["trial_sharpes_daily"] == [-0.08]

    def test_jedenasty_wariant_karty_przerywa(self, tmp_path, monkeypatch):
        import scripts.rejestruj_probe as rp

        plik = tmp_path / "c.json"
        plik.write_text(json.dumps(_licznik(total=10, by={"H017": 10})))
        monkeypatch.setattr(rp, "LICZNIK", plik)
        monkeypatch.setattr(rp, "stan_drzewa", lambda: "")
        monkeypatch.setattr(rp, "_git", lambda *a: "0" * 40)

        with pytest.raises(SystemExit) as e:
            _uruchom(ARGS, monkeypatch)
        assert "10" in str(e.value)
        assert json.loads(plik.read_text())["total_trials"] == 10

    def test_limit_partii_przerywa(self, tmp_path, monkeypatch):
        import scripts.rejestruj_probe as rp

        plik = tmp_path / "c.json"
        plik.write_text(json.dumps(_licznik(total=40, by={"H099": 9})))
        monkeypatch.setattr(rp, "LICZNIK", plik)
        monkeypatch.setattr(rp, "stan_drzewa", lambda: "")
        monkeypatch.setattr(rp, "_git", lambda *a: "0" * 40)

        with pytest.raises(SystemExit) as e:
            _uruchom(ARGS, monkeypatch)
        assert "partia" in str(e.value)

    def test_brak_opisu_przerywa(self, licznik, monkeypatch):
        with pytest.raises(SystemExit) as e:
            _uruchom(["--karta", "H017", "--sr-dzienny", "0.03"], monkeypatch)
        assert "--opis" in str(e.value)


class TestStanRzeczywisty:
    def test_licznik_w_repo_nadal_zeruje(self):
        """Zaden commit nie moze podniesc licznika po cichu — a dopoki wynosi
        zero, kazda liczba w projekcie pochodzi z pre-flightow, nie z prob."""
        d = json.loads((KORZEN / "validation" / "trial_counter.json")
                       .read_text(encoding="utf-8"))
        assert d["total_trials"] == 0
        assert d["trial_sharpes_daily"] == []

    def test_skrypt_czyta_ten_sam_plik_co_baseline(self):
        import scripts.rejestruj_probe as rp
        assert rp.LICZNIK == KORZEN / "validation" / "trial_counter.json"
