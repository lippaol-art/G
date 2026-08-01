"""Straznicy niezmiennikow calego projektu.

Zwykle testy sprawdzaja pojedyncze funkcje. Te sprawdzaja WLASNOSCI CALEGO REPO —
rzeczy, ktore latwo zepsuc przez nieuwage w dowolnym pliku, a ktorych zaden
linter nie wychwyci, bo nie sa bledami jezyka, tylko naruszeniem zasad projektu.

Kazdy test odpowiada konkretnemu trybowi awarii zidentyfikowanemu w audytach.
"""

from __future__ import annotations

import ast
import json
import re
from datetime import UTC
from pathlib import Path

import pytest

from engine.guards import (
    AdjustedSeriesError,
    HistoryView,
    LookaheadError,
    ZeroVolumeExecutionError,
    assert_raw_series,
    assert_tradeable,
)

ROOT = Path(__file__).resolve().parent.parent
CODE_DIRS = ["engine", "validation", "scripts", "tests", "research"]


def _py_files() -> list[Path]:
    out: list[Path] = []
    for d in CODE_DIRS:
        out.extend((ROOT / d).rglob("*.py"))
    return sorted(out)


def _all_repo_files() -> list[Path]:
    skip = {".git", "__pycache__", ".pytest_cache", "data", ".ruff_cache", ".mypy_cache"}
    return [
        p for p in ROOT.rglob("*")
        if p.is_file() and not any(part in skip for part in p.parts)
    ]


# ==========================================================================
# 1. LOOKAHEAD — najgrozniejszy blad backtestingu
# ==========================================================================

class TestLookahead:
    """Strategia, ktora podejrzala przyszlosc, nie rzuca wyjatkiem —
    rysuje piekna krzywa kapitalu. Stad zabezpieczenie architektoniczne."""

    def test_widok_nie_udostepnia_przyszlosci(self):
        view = HistoryView([10, 20, 30, 40, 50], cutoff=2)
        assert len(view) == 3
        assert list(view) == [10, 20, 30]
        with pytest.raises(LookaheadError):
            _ = view[3]

    def test_indeks_ujemny_liczy_od_biezacego_bara(self):
        view = HistoryView([10, 20, 30, 40, 50], cutoff=2)
        assert view[-1] == 30, "ostatni widoczny bar to biezacy, nie ostatni w danych"
        assert view[-3] == 10

    def test_slice_nie_wycieka_poza_cutoff(self):
        view = HistoryView([10, 20, 30, 40, 50], cutoff=2)
        assert view[:] == [10, 20, 30]
        assert view[0:99] == [10, 20, 30], "slice poza zakres nie moze odslonic przyszlosci"

    def test_last_ogranicza_sie_do_widocznych(self):
        view = HistoryView([10, 20, 30, 40, 50], cutoff=2)
        assert view.last(2) == [20, 30]
        assert view.last(10) == [10, 20, 30]

    def test_pusty_widok_na_starcie(self):
        view = HistoryView([10, 20], cutoff=-1)
        assert len(view) == 0
        with pytest.raises(LookaheadError):
            _ = view[0]

    def test_komunikat_wskazuje_specyfikacje(self):
        """Blad ma uczyc, nie tylko przerywac."""
        view = HistoryView([1, 2, 3], cutoff=0)
        with pytest.raises(LookaheadError, match="5.1"):
            _ = view[2]


# ==========================================================================
# 2. WOLUMEN ZERO — zysk, ktorego nie dalo sie zrealizowac
# ==========================================================================

class TestZeroVolume:
    def test_bar_bez_transakcji_blokuje_wykonanie(self):
        from datetime import datetime

        from engine.backtest import Bar
        b = Bar(ts=datetime(2024, 1, 1, tzinfo=UTC),
                open=100, high=101, low=99, close=100, volume=0)
        with pytest.raises(ZeroVolumeExecutionError, match="4.2"):
            assert_tradeable(b, context="wejscie")

    def test_bar_z_wolumenem_przechodzi(self):
        from datetime import datetime

        from engine.backtest import Bar
        b = Bar(ts=datetime(2024, 1, 1, tzinfo=UTC),
                open=100, high=101, low=99, close=100, volume=5)
        assert b.tradeable
        assert assert_tradeable(b) is None, "bar z wolumenem nie moze byc blokowany"

    def test_brak_pola_wolumen_tez_jest_bledem(self):
        class Fake:
            pass
        with pytest.raises(ZeroVolumeExecutionError):
            assert_tradeable(Fake())


# ==========================================================================
# 3. ROZDZIELENIE SERII — poziom, ktorego nikt nie widzial
# ==========================================================================

class TestSeriesSeparation:
    def test_poziom_na_serii_skorygowanej_odrzucony(self):
        with pytest.raises(AdjustedSeriesError, match="4.3"):
            assert_raw_series("adjusted", what="PDH")

    def test_poziom_na_serii_surowej_przechodzi(self):
        assert assert_raw_series("raw", what="PDH") is None, \
            "seria surowa jest jedyna dozwolona dla poziomow — nie moze byc blokowana"


# ==========================================================================
# 4. SEKRETY — klucz w repo to incydent, nie usterka
# ==========================================================================

class TestSecrets:
    SECRET_PATTERNS = [
        (r"db-[A-Za-z0-9]{20,}", "klucz API Databento"),
        (r"(?i)api[_-]?key\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "zahardkodowany klucz API"),
        (r"(?i)password\s*=\s*['\"][^'\"]{6,}['\"]", "zahardkodowane haslo"),
        (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "klucz prywatny"),
    ]

    def test_brak_sekretow_w_repo(self):
        naruszenia = []
        for path in _all_repo_files():
            if path.suffix in {".pdf", ".png", ".parquet", ".zst"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for pattern, opis in self.SECRET_PATTERNS:
                for m in re.finditer(pattern, text):
                    # Dokument i testy moga OPISYWAC wzorce, nie zawierac sekretow
                    if path.name == "test_guards.py":
                        continue
                    naruszenia.append(f"{path.relative_to(ROOT)}: {opis} -> {m.group()[:24]}...")
        assert not naruszenia, "SEKRETY W REPO:\n" + "\n".join(naruszenia)

    def test_gitignore_chroni_wrazliwe_sciezki(self):
        gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for wzorzec in [".env", "data/raw/", "*.dbn"]:
            assert wzorzec in gi, f".gitignore nie chroni {wzorzec}"

    def test_skrypt_danych_nie_ma_domyslnego_klucza(self):
        """Wartosc domyslna klucza to zaproszenie do wyciekniecia."""
        src = (ROOT / "scripts" / "build_dataset.py").read_text(encoding="utf-8")
        assert 'os.environ.get("DATABENTO_API_KEY", "")' in src
        assert "db-DJ" not in src


# ==========================================================================
# 5. DETERMINIZM — dwa uruchomienia musza dac ten sam wynik
# ==========================================================================

class TestDeterminism:
    def test_brak_nieziarnowanej_losowosci_w_silniku(self):
        """`random` bez seeda w engine/ lamie odtwarzalnosc wynikow.

        Wymog z rozdz. 5.6: dwa uruchomienia z tym samym seedem musza dac
        bitowo identyczne wyniki.
        """
        naruszenia = []
        for path in (ROOT / "engine").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        if a.name == "random":
                            naruszenia.append(f"{path.name}: import random")
                if isinstance(node, ast.Call):
                    f = node.func
                    if (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                            and f.value.id == "np" and f.attr == "seed"):
                        naruszenia.append(f"{path.name}: np.seed (uzyj default_rng)")
        assert not naruszenia, "Losowosc bez kontroli:\n" + "\n".join(naruszenia)


# ==========================================================================
# 6. IZOLACJA WARSTW — silnik nie moze zalezec od sieci ani skryptow
# ==========================================================================

class TestLayering:
    ZAKAZANE_W_ENGINE = {"requests", "urllib", "httpx", "databento", "ib_async", "socket"}

    def test_silnik_nie_siega_do_sieci(self):
        """Modul liczacy musi byc czysty — inaczej backtest zalezy od dostepnosci API."""
        naruszenia = []
        for path in (ROOT / "engine").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods = [node.module.split(".")[0]]
                for m in mods:
                    if m in self.ZAKAZANE_W_ENGINE:
                        naruszenia.append(f"{path.name}: import {m}")
        assert not naruszenia, "Silnik zalezy od IO:\n" + "\n".join(naruszenia)

    def test_silnik_nie_importuje_skryptow(self):
        naruszenia = []
        for path in (ROOT / "engine").rglob("*.py"):
            src = path.read_text(encoding="utf-8")
            if re.search(r"^\s*(from|import)\s+scripts", src, re.MULTILINE):
                naruszenia.append(path.name)
        assert not naruszenia, f"engine/ importuje scripts/: {naruszenia}"


# ==========================================================================
# 7. LICZNIK PROB — fundament DSR
# ==========================================================================

class TestTrialCounter:
    def test_schemat_licznika_jest_poprawny(self):
        data = json.loads((ROOT / "validation" / "trial_counter.json").read_text())
        for key in ("total_trials", "by_hypothesis", "trial_sharpes_daily", "_rules"):
            assert key in data, f"brak pola {key} w trial_counter.json"
        assert isinstance(data["total_trials"], int)
        assert data["total_trials"] >= 0

    def test_limity_zgodne_z_dokumentem(self):
        """Limit 10 wariantow to nie preferencja, tylko wynik tabeli wykonalnosci
        DSR (rozdz. 6.5): przy N_eff=30 nie przechodzi nawet Sharpe 1.5."""
        rules = json.loads((ROOT / "validation" / "trial_counter.json").read_text())["_rules"]
        assert rules["max_variants_per_hypothesis"] == 10
        assert rules["max_variants_per_batch"] == 40
        assert rules["benchmarks_excluded"] is True


# ==========================================================================
# 8. SPOJNOSC KODU Z DOKUMENTEM
# ==========================================================================

class TestDocConsistency:
    def test_stale_kosztowe_zgodne_ze_specyfikacja(self):
        from engine.costs import POINT_VALUE, TICK_SIZE, TICK_VALUE, CostModel
        assert POINT_VALUE == 2.0
        assert TICK_SIZE == 0.25
        assert TICK_VALUE == 0.50
        assert CostModel().commission_rt == 1.20
        assert CostModel().round_turn_cost(2) == pytest.approx(2.20)

    def test_progi_licznosci_proby(self):
        from validation.power import FLOOR_TRADES, TARGET_TRADES
        assert FLOOR_TRADES == 400, "podloga podniesiona z 300 po audycie statystycznym"
        assert TARGET_TRADES == 800

    def test_bramka_dsr(self):
        from validation.dsr import deflated_sharpe_annualized
        assert deflated_sharpe_annualized(1.5, 1500, 5).passes
        assert not deflated_sharpe_annualized(0.8, 1500, 10).passes

    def test_wszystkie_moduly_maja_odwolanie_do_specyfikacji(self):
        """Kazdy modul musi wskazywac, ktora czesc PLAN.pdf realizuje —
        inaczej po miesiacach nikt nie odtworzy, skad wziely sie decyzje."""
        braki = []
        for d in ("engine", "validation"):
            for path in (ROOT / d).rglob("*.py"):
                if path.name == "__init__.py":
                    continue
                head = path.read_text(encoding="utf-8")[:1200]
                if "PLAN.pdf" not in head and "rozdz." not in head:
                    braki.append(str(path.relative_to(ROOT)))
        assert not braki, "Moduly bez odwolania do specyfikacji:\n" + "\n".join(braki)


# ==========================================================================
# 9. HIGIENA TESTOW — test, ktory nic nie sprawdza, jest gorszy niz jego brak
# ==========================================================================

class TestTestHygiene:
    def test_kazdy_test_ma_asercje(self):
        """Test bez asercji zawsze przechodzi i daje falszywe poczucie pokrycia."""
        bez_asercji = []
        for path in (ROOT / "tests").rglob("test_*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    ma = any(
                        isinstance(n, (ast.Assert, ast.Raise))
                        or (isinstance(n, ast.With)
                            and any("raises" in ast.dump(i) for i in n.items))
                        for n in ast.walk(node)
                    )
                    if not ma:
                        bez_asercji.append(f"{path.name}::{node.name}")
        assert not bez_asercji, "Testy bez asercji:\n" + "\n".join(bez_asercji)

    def test_brak_pominietych_testow_bez_powodu(self):
        """`skip` bez uzasadnienia to ukryty dlug — musi miec `reason`."""
        naruszenia = []
        for path in (ROOT / "tests").rglob("test_*.py"):
            src = path.read_text(encoding="utf-8")
            for m in re.finditer(r"@pytest\.mark\.skip(?!if)\s*(\([^)]*\))?", src):
                if not m.group(1) or "reason" not in m.group(1):
                    naruszenia.append(f"{path.name}: skip bez reason")
        assert not naruszenia, "\n".join(naruszenia)
