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
    # `.venv`/`venv`: gitignorowane, ale ten skan chodzi po dysku, nie po
    # `git ls-files`. Zlapane na maszynie lokalnej, gdzie instalacja tworzy
    # wirtualne srodowisko WEWNATRZ drzewa repo (`py -3.12 -m venv .venv`) —
    # pakiety (ruff, numpy, pyarrow) maja we wlasnych testach/metadanych ciagi
    # wygladajace jak sekrety, np. "password=\"hunter2\"" w binarce testowej
    # ruff.exe. To falszywe alarmy o zrodle poza kontrola tego repozytorium.
    skip = {".git", "__pycache__", ".pytest_cache", "data", ".ruff_cache",
            ".mypy_cache", ".venv", "venv"}
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
    def test_wbudowany_hash_nie_sluzy_za_ziarno(self):
        """`hash()` na stringu jest RANDOMIZOWANY przy kazdym starcie procesu.

        TRYB AWARII, KTORY SIE WYDARZYL. Raport W001 wyznaczal ziarno bootstrapu
        jako `abs(hash(symbol + okres)) % 2**31`. Kazde uruchomienie dawalo inne
        granice przedzialow ufnosci — raport badawczy nie byl odtwarzalny, mimo
        ze nie zawieral ani jednego jawnego wywolania losowosci bez seeda.
        Wykryte dopiero przez porownanie dwoch kolejnych regeneracji.

        `hashlib` i pola nazwane `*_hash` sa w porzadku — chodzi wylacznie
        o wbudowana funkcje `hash()` uzyta jako zrodlo determinizmu.
        """
        naruszenia = []
        for d in ("engine", "validation", "research", "scripts"):
            kat = ROOT / d
            if not kat.is_dir():
                continue
            for path in kat.rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                            and node.func.id == "hash"):
                        naruszenia.append(f"{d}/{path.name}:{node.lineno}")
        assert not naruszenia, (
            "Wbudowany `hash()` w kodzie liczacym:\n" + "\n".join(naruszenia)
            + "\nUzyj `zlib.crc32` albo jawnej stalej — `hash()` na stringu zmienia "
              "sie miedzy procesami i cicho psuje odtwarzalnosc."
        )

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
    def test_bloki_powershell_nie_uzywaja_operatora_and(self):
        """Windows PowerShell 5.1 NIE zna `&&`.

        Wlasciciel projektu pracuje na Windows i wykonuje instrukcje z tych
        plikow doslownie. Wklejenie `git add X && git commit -m Y` wywala sie
        na `The token '&&' is not a valid statement separator in this version`
        — czyli instrukcja jest po prostu niewykonalna. Zdarzylo sie raz,
        w HANDOFF §4.

        Sprawdzamy WYLACZNIE bloki oznaczone jako ```powershell. Bloki ```bash
        maja pelne prawo do `&&` i nie sa tu ruszane.
        """
        import re

        korzen = Path(__file__).resolve().parent.parent
        winne: list[str] = []
        for plik in [*korzen.glob("*.md"), *korzen.glob("docs/*.md")]:
            tekst = plik.read_text(encoding="utf-8")
            for blok in re.findall(r"```powershell\n(.*?)```", tekst, re.S):
                for linia in blok.splitlines():
                    if "&&" in linia:
                        winne.append(f"{plik.name}: {linia.strip()}")
        assert not winne, (
            "blok ```powershell uzywa `&&`, ktorego Windows PowerShell 5.1 nie "
            "obsluguje — rozbij na osobne linie:\n  " + "\n  ".join(winne))

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

    def test_handoff_podaje_aktualna_liczbe_testow(self):
        """HANDOFF musi sie zgadzac z repo — inaczej lamie wlasna regule P1.

        Liczba testow w HANDOFF zdezaktualizowala sie DWA RAZY w ciagu doby
        (531 -> 562 -> 578 -> ...), za kazdym razem cicho. Reczna dyscyplina
        tego nie utrzyma, bo liczba zmienia sie przy kazdym dodanym tescie.

        Ten straznik zamienia regule "HANDOFF aktualizuje sie w tym samym
        commicie" z deklaracji w mechanizm: dodanie testu bez poprawienia
        HANDOFF jest czerwone.

        Liczymy FUNKCJE testowe statycznie (AST), nie przypadki zebrane przez
        pytest — liczba przypadkow zalezy od parametryzacji i liczenie jej
        z wnetrza przebiegu byloby rekurencyjne.
        """
        n = 0
        for path in sorted((ROOT / "tests").rglob("test_*.py")):
            drzewo = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(drzewo):
                if (isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
                        and node.name.startswith("test_")):
                    n += 1

        handoff = (ROOT / "HANDOFF.md").read_text(encoding="utf-8")
        m = re.search(r"\*\*(\d+) funkcji testowych", handoff)
        assert m, "HANDOFF nie podaje liczby funkcji testowych"
        assert int(m.group(1)) == n, (
            f"HANDOFF mowi o {m.group(1)} funkcjach testowych, a jest ich {n}. "
            "Popraw HANDOFF W TYM SAMYM COMMICIE (regula P1 z naglowka pliku).")

    def test_ci_instaluje_extras_potrzebne_testom(self):
        """CI musi instalowac kazdy extras, bez ktorego test sie nie zaimportuje.

        POWSTALO PO REALNEJ AWARII (06.08.2026). Test downloadera importuje
        `scripts/fetch_d5b2_month.py`, ten importuje `databento` — a CI
        instalowalo tylko `[dev,validation]`. Lokalna bramka byla ZIELONA, bo
        lokalnie `databento` jest zainstalowane.

        `scripts/check_all.sh` tego nie wykryje z zalozenia: porownuje KOMENDY
        z CI, a rozjazd byl w ZALEZNOSCIACH. Ten straznik zamyka te luke od
        drugiej strony — pilnuje, ze nikt nie usunie extras z workflow.

        `live` celowo POZA lista: ib_async jest potrzebny dopiero na Etapie 5
        i zaden test go dzis nie importuje.
        """
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        m = re.search(r"pip install -e '\.\[([^\]]+)\]'", ci)
        assert m, "nie znaleziono linii instalacji extras w ci.yml"
        zainstalowane = {s.strip() for s in m.group(1).split(",")}

        wymagane = {
            "dev": "pytest, ruff, mypy — bez nich nie ma czego uruchomic",
            "validation": "arch i scikit-learn; bez nich spa.py i dsr.py cicho "
                          "schodza na sciezke zapasowa i sciezka glowna nie "
                          "jest wykonana ani razu",
            "data": "databento; bez niego skryptow zakupowych nie da sie nawet "
                    "zaimportowac, wiec ich testy nie moglyby biec w CI — a to "
                    "jedyne skrypty, ktorych blad kosztuje pieniadze",
        }
        braki = {k: v for k, v in wymagane.items() if k not in zainstalowane}
        assert not braki, (
            "ci.yml nie instaluje extras: "
            + "; ".join(f"`{k}` ({v})" for k, v in braki.items()))

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


# ==========================================================================
# 10. PAKOWALNOSC — zielony pytest lokalnie nie dowodzi, ze CI wstanie
# ==========================================================================

class TestPakowalnosc:
    """CI instaluje projekt przez `pip install -e .`; lokalne testy tego nie robia.

    TRYB AWARII, KTORY SIE WYDARZYL. Dodanie katalogu `reports/` sprawilo, ze
    setuptools w trybie flat-layout zobaczyl szesc kandydatow na pakiet
    top-level (`data`, `engine`, `reports`, `research`, `hypotheses`,
    `validation`) i odmowil budowy. CI bylo czerwone przez trzy commity, a kazdy
    z nich raportowal komplet zielonych testow — bo lokalnie nikt nie instalowal
    paczki. Bledu nie widac w pytest, ruff ani mypy.

    Straznik zamyka te luke: kazdy katalog z kodem w korzeniu repo musi byc albo
    zadeklarowany jako pakiet, albo jawnie wymieniony jako niepakiet.
    """

    #: Katalogi z kodem, ktore CELOWO nie sa pakietami instalowanymi.
    #: `scripts` i `tests` uruchamiane sa z korzenia repo przez PYTHONPATH,
    #: nie importowane z zainstalowanej dystrybucji.
    NIE_PAKIETY = {"scripts", "tests"}

    @staticmethod
    def _zadeklarowane() -> list[str]:
        import tomllib
        cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        return cfg.get("tool", {}).get("setuptools", {}).get("packages", [])

    def test_lista_pakietow_jest_jawna(self):
        """Automatyczne wykrywanie pakietow jest tu bledem, nie wygoda —
        repo ma katalogi danych i raportow obok katalogow kodu."""
        assert self._zadeklarowane(), (
            "pyproject.toml nie deklaruje [tool.setuptools] packages. Bez jawnej "
            "listy setuptools probuje zgadnac i wywraca instalacje, gdy w korzeniu "
            "pojawi sie katalog niebedacy pakietem (data/, reports/, hypotheses/)."
        )

    def test_kazdy_katalog_z_kodem_jest_rozstrzygniety(self):
        zadeklarowane = set(self._zadeklarowane())
        pominiete = {".git", "__pycache__", ".pytest_cache", ".ruff_cache",
                     ".mypy_cache", ".github", ".claude", "docs", "data",
                     "reports", "hypotheses", ".venv"}
        nierozstrzygniete = []
        for p in ROOT.iterdir():
            if not p.is_dir() or p.name in pominiete or p.name.startswith("."):
                continue
            if not any(p.rglob("*.py")):
                continue
            if p.name not in zadeklarowane and p.name not in self.NIE_PAKIETY:
                nierozstrzygniete.append(p.name)
        assert not nierozstrzygniete, (
            f"Katalogi z kodem nierozstrzygniete w pyproject.toml: {nierozstrzygniete}.\n"
            "Dopisz je do [tool.setuptools] packages albo do NIE_PAKIETY w tym tescie. "
            "Inaczej `pip install -e .` w CI moze zaczac zgadywac."
        )

    def test_zadeklarowane_pakiety_istnieja_i_maja_init(self):
        """Pakiet zadeklarowany, ale bez `__init__.py`, instaluje sie niekompletnie."""
        braki = []
        for nazwa in self._zadeklarowane():
            kat = ROOT / nazwa
            if not kat.is_dir():
                braki.append(f"{nazwa}: katalog nie istnieje")
            elif not (kat / "__init__.py").exists():
                braki.append(f"{nazwa}: brak __init__.py")
        assert not braki, "Niespojna deklaracja pakietow:\n" + "\n".join(braki)


class TestKopiaZapasowa:
    """Lista plikow do kopii zapasowej musi byc KOMPLETNA.

    Databento potwierdzilo 11.08: *"The old data is not available anymore in
    our API."* Piec sesji pobranych przed przelomem normalizacji to jedyny
    istniejacy egzemplarz tamtej wersji danych — nie da sie ich odtworzyc
    za zadna cene.

    Sesja 2026-07-06 wypadla z tej listy DWA RAZY: raz w mailu do dostawcy
    ("We hold four"), raz w ramce kopii zapasowej w HANDOFF. Pierwsza pomylka
    byla zawstydzajaca, druga bylaby fizyczna — kopia zrobiona wedlug tej
    ramki zostawilaby 07-06 na jednym dysku.
    """

    def test_handoff_wymienia_wszystkie_stare_sesje(self):
        import sys
        korzen = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(korzen))
        from scripts.fetch_d5b2_month import SESJE_STARA_NORMALIZACJA

        tekst = (korzen / "HANDOFF.md").read_text(encoding="utf-8")
        blok = tekst.split("KOPIA ZAPASOWA", 1)
        assert len(blok) == 2, "HANDOFF nie ma juz ramki o kopii zapasowej"
        # Do konca sekcji cytatu — dalej zaczyna sie zwykly tekst.
        ramka = blok[1].split("\n\n", 1)[0] + blok[1].split("\n\n", 1)[1][:1200]

        brakuje = [s for s in SESJE_STARA_NORMALIZACJA
                   if s not in ramka and s[5:] not in ramka]
        assert not brakuje, (
            "ramka kopii zapasowej w HANDOFF nie wymienia sesji: "
            f"{brakuje}. Tych plikow NIE DA SIE odtworzyc z API — "
            "pominiete w liscie zostana na jednym dysku.")

    def test_stala_zgadza_sie_z_liczba_oplaconych_sesji(self):
        import sys
        korzen = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(korzen))
        from scripts.fetch_d5b2_month import (
            SESJA_D5C,
            SESJE,
            SESJE_STARA_NORMALIZACJA,
        )
        assert len(SESJE_STARA_NORMALIZACJA) == 5
        assert SESJA_D5C in SESJE_STARA_NORMALIZACJA
        assert set(SESJE_STARA_NORMALIZACJA) <= set(SESJE)


def _raporty_mikro() -> list[Path]:
    """Wszystkie zacommitowane raporty mikro-diffu.

    Discovery zamiast listy: kazdy kolejny pomiar ma byc objety straznikiem
    AUTOMATYCZNIE. Pierwsza wersja tej klasy pilnowala jednego pliku po nazwie
    i drugi raport (07-06) wszedl do repo niechroniony — dokladnie ta klasa
    przeoczenia, ktora wytknela korekta A przy sciezce raportu.
    """
    return sorted((ROOT / "reports").glob("D5_mikro_diff*.json"))


#: Puste tylko na maszynie bez artefaktow (np. swiezy klon bez pomiarow).
RAPORTY = _raporty_mikro()
IDS = [p.stem for p in RAPORTY]


@pytest.mark.skipif(not RAPORTY, reason="brak raportow mikro-diffu w repo")
class TestRaportMikroDiffu:
    """Liczby w dokumentach musza zgadzac sie z MASZYNOWYMI artefaktami pomiarow.

    `reports/D5_mikro_diff*.json` to jedyne automatyczne zapisy mikro-diffow —
    pomiarow, ktorych NIE DA SIE POWTORZYC, bo stara normalizacja GLBX.MDP3
    przestala byc dostepna w API (Databento, 11.08). Na ich wyniku stoi decyzja
    o skladzie miesiecznej probki i o kilkudziesieciu dolarach.

    Testy chodza po WSZYSTKICH raportach, nie po nazwanym jednym.
    """

    @staticmethod
    def _wczytaj(p: Path) -> dict:
        return json.loads(p.read_text(encoding="utf-8"))

    @pytest.mark.parametrize("plik", RAPORTY, ids=IDS)
    def test_arytmetyka_raportu_sie_domyka(self, plik):
        """Wewnetrzna spojnosc pomiaru — niezalezna od jakiegokolwiek tekstu."""
        j = self._wczytaj(plik)
        assert j["wspolnych"] + j["tylko_dostawca"] == j["rekordow_dostawca"]
        assert sum(j["typy_dostawca"].values()) == j["rekordow_dostawca"]
        assert sum(j["typy_nasze"].values()) == j["rekordow_nasze"]
        assert j["rekordow_wg_api"] == j["rekordow_dostawca"], \
            "metadane i pobrany plik musza sie zgadzac co do rekordu"

    @pytest.mark.parametrize("plik", RAPORTY, ids=IDS)
    def test_werdykt_B_prim_wynika_z_liczb_a_nie_z_narracji(self, plik):
        """Wariant B' stoi na DWOCH faktach: zero brakow u nas i zgodnosc
        wszystkich realnych typow akcji. Gdyby ktorykolwiek upadl, decyzja
        o nieodkupywaniu piecu sesji traci podstawe."""
        j = self._wczytaj(plik)
        assert j["tylko_nasze"] == 0
        realne = {k: v for k, v in j["typy_dostawca"].items() if k != "N"}
        assert realne == j["typy_nasze"]
        assert "N" not in j["typy_nasze"]

    @pytest.mark.parametrize("plik", RAPORTY, ids=IDS)
    def test_dokumenty_cytuja_liczby_z_artefaktu(self, plik):
        """Kazda kluczowa liczba pomiaru musi wystapic w D5_DRYF.

        Format dokumentu uzywa spacji jako separatora tysiecy — porownujemy
        wiec po znormalizowanym zapisie, a nie po surowym `int`.
        """
        j = self._wczytaj(plik)
        tekst = (ROOT / "docs" / "D5_DRYF_METADANYCH.md").read_text(
            encoding="utf-8")
        # Spacja zwykla i nierozdzielajaca — dokument uzywa obu.
        plaski = tekst.replace("\u00a0", " ")

        wymagane = [j["wspolnych"], j["tylko_dostawca"], j["rekordow_dostawca"],
                    *j["typy_dostawca"].values()]
        brakuje = [n for n in sorted(set(wymagane))
                   if f"{n:,}".replace(",", " ") not in plaski]
        assert not brakuje, (
            f"D5_DRYF nie cytuje liczb z {plik.name}: {brakuje}. "
            "Albo dokument sie rozjechal, albo pomiar zostal nadpisany.")

    @pytest.mark.parametrize("plik", RAPORTY, ids=IDS)
    def test_koszt_zgadza_sie_z_ksiega(self, plik):
        """Warunek 4 zgody R1: wpis do KOSZTY niezaleznie od wyniku."""
        j = self._wczytaj(plik)
        koszty = (ROOT / "data" / "KOSZTY.md").read_text(encoding="utf-8")
        zapis = f"{j['koszt_usd']:.4f}".replace(".", ",")
        assert zapis in koszty, (
            f"KOSZTY.md nie podaje kosztu {zapis} USD z {plik.name} — "
            "warunek 4 zgody R1 wymaga wpisu niezaleznie od wyniku")

    @pytest.mark.parametrize("plik", RAPORTY, ids=IDS)
    def test_koszt_miesci_sie_w_limicie_swojego_okna(self, plik):
        """Limit z rejestru okien mial byc egzekwowany PRZED pobraniem.

        Raport jest dowodem po fakcie: gdyby ktorys pomiar przekroczyl swoj
        limit, znaczyloby to, ze bramka kosztowa nie zadzialala.
        """
        import sys
        sys.path.insert(0, str(ROOT))
        from scripts.diff_mikro import wybierz_okno

        j = self._wczytaj(plik)
        limit = wybierz_okno(j["sesja"]).limit_usd
        assert j["koszt_usd"] <= limit, (
            f"{plik.name}: zaplacono {j['koszt_usd']} przy limicie {limit}")





class TestStanProjektu:
    """`docs/STAN_PROJEKTU.md` jest skorowidzem — wiec jego odsylacze musza dzialac.

    Dokument ma jedno zadanie: pokazac calosc i odeslac do zrodel prawdy.
    Odsylacz do pliku, ktorego nie ma, jest gorszy niz brak odsylacza — czytelnik
    traci zaufanie do calej mapy i wraca do zgadywania, gdzie co lezy.

    Ten straznik NIE sprawdza tresci. Sprawdza dwie rzeczy, ktore rotuja same
    z siebie: czy wskazywane pliki istnieja i czy dokument nie zaczal duplikowac
    kwot, ktorych zrodlem jest `data/KOSZTY.md`.
    """

    PLIK = ROOT / "docs" / "STAN_PROJEKTU.md"

    def _tekst(self) -> str:
        return self.PLIK.read_text(encoding="utf-8")

    def test_wszystkie_wskazywane_pliki_istnieja(self):
        """Sciezki w backtickach, wygladajace na pliki repo, musza istniec."""
        wzorzec = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|pdf|json|py|sh|html))`")
        brakuje = sorted({
            s for s in wzorzec.findall(self._tekst())
            # Wzorce globalne (np. reports/D5_mikro_diff*.json) i sciezki
            # spoza repo nie sa tu sprawdzane — te pierwsze nie sa pojedynczym
            # plikiem, drugich repo nie kontroluje.
            if "*" not in s and not (ROOT / s).exists()
        })
        assert not brakuje, (
            f"STAN_PROJEKTU.md odsyla do nieistniejacych plikow: {brakuje}")

    def test_nie_duplikuje_kwot_z_ksiegi(self):
        """Zrodlem prawdy o pieniadzach jest data/KOSZTY.md — i tylko on.

        Dokument sam deklaruje w naglowku, ze nie zawiera kwot. Ten test pilnuje,
        zeby deklaracja nie rozjechala sie z trescia przy pierwszej edycji
        „dla wygody czytelnika". Wyjatkiem sa LIMITY (82,00 / 1,00), bo to nie
        wydatki, tylko bramki — i o nich dokument mowi wprost.
        """
        limity = {"82,00", "1,00"}
        kwoty = set(re.findall(r"\b\d+,\d{2,4}\b", self._tekst())) - limity
        assert not kwoty, (
            f"STAN_PROJEKTU.md zaczal duplikowac kwoty: {sorted(kwoty)}. "
            "Zrodlem prawdy jest data/KOSZTY.md — tu ma byc odsylacz, nie liczba.")

    def test_wymienia_komplet_regul_trwalych(self):
        """Reguly R sa rdzeniem governance — mapa nie moze zgubic zadnej."""
        tekst = self._tekst()
        brak = [r for r in ("R1", "R2", "R3", "R4", "R9") if f"**{r}**" not in tekst]
        assert not brak, f"STAN_PROJEKTU.md nie wymienia regul: {brak}"

    def test_regula_R4_jest_w_rejestrze_regul(self):
        """R4 byla cytowana w KOSZTY §4, ale nie miala wpisu w REGISTRY.

        Znalezione przy pisaniu mapy 13.08. Regula egzekwowana przez kod
        (LIMIT_USD) musi byc w rejestrze regul, inaczej nowa osoba widzi
        w tabeli luke i nie wie, czy to pomylka w numeracji, czy brakujaca zasada.
        """
        rejestr = (ROOT / "hypotheses" / "REGISTRY.md").read_text(encoding="utf-8")
        assert "| **R4** |" in rejestr, "R4 zniknela z tabeli regul w REGISTRY"


REKONSTRUKCJE = sorted((ROOT / "reports").glob("D5_rekonstrukcja_*.json"))
IDS_REK = [p.stem for p in REKONSTRUKCJE]


@pytest.mark.skipif(not REKONSTRUKCJE, reason="brak artefaktow rekonstrukcji")
class TestArtefaktRekonstrukcji:
    """Cztery liczby kryterium §5e nie moga zyc wylacznie w prozie.

    Zarzut recenzji z 13.08, trafny: `--rekonstrukcja` drukowal akcje, sumy
    n_trade i rozmiaru na konsole, a raport JSON zapisywal CO INNEGO (diff
    rekordow). Straznik dokument<->artefakt nie mial wiec z czym porownac
    tych czterech liczb — a to na nich stoi werdykt.

    Przy pomiarze, ktorego nie da sie powtorzyc, rozjazd miedzy dokumentem
    a konsola bylby niewykrywalny.
    """

    @staticmethod
    def _wczytaj(p: Path) -> dict:
        return json.loads(p.read_text(encoding="utf-8"))

    @pytest.mark.parametrize("plik", REKONSTRUKCJE, ids=IDS_REK)
    def test_cztery_punkty_kryterium_sa_spojne(self, plik):
        """`identyczne` musi wynikac z liczb, a nie byc osobna deklaracja."""
        j = self._wczytaj(plik)
        rowne = (j["akcji_swiezy"] == j["akcji_nasz"]
                 and j["n_trade_swiezy"] == j["n_trade_nasz"]
                 and j["rozmiar_swiezy"] == j["rozmiar_nasz"]
                 and j["pozycja_pierwszej_roznicy"] is None
                 and j["roznych_pozycji"] == 0)
        assert j["identyczne"] == rowne, (
            f"{plik.name}: flaga `identyczne` nie zgadza sie z liczbami")

    @pytest.mark.parametrize("plik", REKONSTRUKCJE, ids=IDS_REK)
    def test_dokument_cytuje_liczby_rekonstrukcji(self, plik):
        j = self._wczytaj(plik)
        tekst = (ROOT / "docs" / "D5_DRYF_METADANYCH.md").read_text(
            encoding="utf-8").replace("\u00a0", " ")
        wymagane = [j["akcji_swiezy"], j["n_trade_swiezy"], j["rozmiar_swiezy"]]
        brakuje = [n for n in sorted(set(wymagane))
                   if f"{n:,}".replace(",", " ") not in tekst]
        assert not brakuje, (
            f"D5_DRYF nie cytuje liczb z {plik.name}: {brakuje}")

    @pytest.mark.parametrize("plik", REKONSTRUKCJE, ids=IDS_REK)
    def test_okno_pochodzi_z_zamrozonego_rejestru(self, plik):
        """Artefakt nie moze opisywac okna, ktorego rejestr nie zna."""
        import sys
        sys.path.insert(0, str(ROOT))
        from scripts.diff_mikro import wybierz_okno

        j = self._wczytaj(plik)
        o = wybierz_okno(j["sesja"])
        assert j["zakres_utc"] == [o.start_utc, o.end_utc]


def test_rekonstrukcja_zapisuje_artefakt_i_nadal_jest_darmowa():
    """Dopisanie zapisu NIE moze przemycic wywolania sieciowego.

    Tryb `--rekonstrukcja` jest uruchamiany bez zgody R1, bo nic nie kosztuje.
    Ta wlasnosc musi przezyc kazda przyszla zmiane funkcji.
    """
    import inspect
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts import diff_mikro

    zrodlo = inspect.getsource(diff_mikro.raport_rekonstrukcji)
    assert "sciezka_rekonstrukcji(" in zrodlo, "tryb przestal zapisywac artefakt"
    bez_docstringa = zrodlo.replace(diff_mikro.raport_rekonstrukcji.__doc__, "")
    for zakazane in ("Historical", "get_cost", "get_range", "DATABENTO_API_KEY"):
        assert zakazane not in bez_docstringa, (
            f"tryb --rekonstrukcja siega po {zakazane} — przestal byc darmowy")


class TestDatyPrzySHA:
    """Data podana obok skrotu commita musi zgadzac sie z gitem.

    TRZY NAWROTY TEJ SAMEJ KLASY BLEDU. Za kazdym razem pisalem date z pamieci
    zamiast z `git show`: najpierw "wykonany 11.08" dla biegu z 13.08, potem
    "znaleziona 13.08" dla commita z 18.08, potem "PASS (13.08)" dla commita
    z 18.08. Recenzent ujal to precyzyjnie: w incydencie, w ktorym os czasu
    obalila juz dwie diagnozy, DATY SA DANYMI.

    Zamiast czwartego postanowienia poprawy — mechanizm. Szukamy wzorca
    `<skrot>` w poblizu daty `DD.MM` i porownujemy z data commita.

    Straznik pomija sie czysto, gdy repo nie ma historii (plytki klon w CI) —
    lepiej stracic pokrycie w CI niz miec test, ktory klamie o powodzie.
    """

    #: Dokumenty, w ktorych daty przy SHA maja znaczenie dowodowe.
    PLIKI = ("docs/D5_DRYF_METADANYCH.md", "data/KOSZTY.md", "HANDOFF.md")

    @staticmethod
    def _data_commita(sha: str) -> str | None:
        import subprocess
        try:
            r = subprocess.run(
                ["git", "show", "-s", "--format=%cd", "--date=format:%d.%m", sha],
                cwd=ROOT, capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            return None
        return r.stdout.strip() if r.returncode == 0 else None

    def test_daty_obok_skrotow_zgadzaja_sie_z_gitem(self):
        # `SHA` w backtickach, a w tej samej linii gdzies data DD.MM.
        wzorzec = re.compile(r"`([0-9a-f]{7,40})`")
        data_re = re.compile(r"\b(\d{2}\.\d{2})\b")

        sprawdzone, rozjazdy = 0, []
        for wzgledna in self.PLIKI:
            plik = ROOT / wzgledna
            if not plik.exists():
                continue
            for linia in plik.read_text(encoding="utf-8").splitlines():
                daty = data_re.findall(linia)
                if not daty:
                    continue
                for sha in wzorzec.findall(linia):
                    prawdziwa = self._data_commita(sha)
                    if prawdziwa is None:
                        continue          # nie commit albo brak historii
                    sprawdzone += 1
                    if prawdziwa not in daty:
                        rozjazdy.append(
                            f"{wzgledna}: `{sha}` ma w gicie {prawdziwa}, "
                            f"a w tekscie {daty}")
        if sprawdzone == 0:
            pytest.skip("brak historii gita albo zadnej pary SHA+data")
        assert not rozjazdy, "daty rozjechane z gitem:\n  " + "\n  ".join(rozjazdy)
