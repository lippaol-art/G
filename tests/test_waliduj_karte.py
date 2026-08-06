"""Straznik procesu — linter kart hipotez.

Kazde sprawdzane pole odpowiada bledowi, ktory projekt juz popelnil. Testy sa
wiec pisane parami: brak pola musi byc WYKRYTY, a karta kompletna musi PRZEJSC.
Linter, ktory odrzuca wszystko, jest tak samo bezuzyteczny jak taki, ktory
przepuszcza wszystko.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORZEN))

from scripts.waliduj_karte import MAX_WARIANTOW, liczba_wariantow, waliduj  # noqa: E402

KOMPLETNA = """# H017 — karta testowa

## 2. Uzasadnienie strukturalne
Przymuszony uczestnik: animator kwotujacy w oknie rozliczeniowym, ktory ma
obowiazek utrzymania kwotowan wynikajacy z umowy z gielda i nie moze przestac
handlowac, gdy cena idzie przeciw niemu.

## 3. Najblizszy publiczny benchmark
B04 — momentum wewnatrzdzienne, Gao i in. JFE 2018, parametry z literatury.

## 4. Roznica mechanizmu
Benchmark mierzy zwrot w oknie kalendarzowym. Ta karta warunkuje sygnal
kierunkiem przeplywu agresywnego, czyli innym zjawiskiem, nie innym progiem.

## 5. Plan N i mocy
N >= 400 przy mocy 80%, sigma estymowana empirycznie z rozkladu zwrotow.
Czestotliwosc okazji: okolo 190 zdarzen rocznie, wiec zebranie N zajmie ~2 lata.

## 8. Warianty — wszystkie 6 zadeklarowane z gory
Szesc wariantow progu, kazdy uzasadniony mechanizmem, zadnych siatek.

## 9. Co by te karte sfalsyfikowalo
Brak zaleznosci od wielkosci rezyduum albo asymetria bez wyjasnienia
mechanizmem obala karte niezaleznie od P&L.

## 13. Recenzje
Zarzut 1 (recenzent slepy): probka moze byc zdominowana przez jeden rok.
Odpowiedz: dodany rozklad roczny jako warunek wstepny.

SHA zamrozenia: PENDING
"""


def _karta(tmp_path: Path, tresc: str) -> Path:
    p = tmp_path / "H017.md"
    p.write_text(tresc, encoding="utf-8")
    return p


class TestKartaKompletna:
    def test_przechodzi_przed_zamrozeniem(self, tmp_path):
        assert waliduj(_karta(tmp_path, KOMPLETNA), przed_zamrozeniem=True) == []

    def test_pending_blokuje_zamrozenie(self, tmp_path):
        braki = waliduj(_karta(tmp_path, KOMPLETNA), przed_zamrozeniem=False)
        assert len(braki) == 1
        assert "PENDING" in braki[0]

    def test_wpisany_sha_odblokowuje(self, tmp_path):
        tresc = KOMPLETNA.replace("SHA zamrozenia: PENDING",
                                  "SHA zamrozenia: 1d87614abc0123")
        assert waliduj(_karta(tmp_path, tresc)) == []


class TestWykrywanieBrakow:
    @pytest.mark.parametrize("naglowek,fragment", [
        ("przymuszony uczestnik", "Przymuszony uczestnik: animator"),
        ("benchmark", "## 3. Najblizszy publiczny benchmark"),
        ("roznica mechanizmu", "## 4. Roznica mechanizmu"),
        ("warunek negatywny", "## 9. Co by te karte sfalsyfikowalo"),
        ("recenzje", "## 13. Recenzje"),
    ])
    def test_usuniecie_sekcji_jest_wykryte(self, tmp_path, naglowek, fragment):
        okrojona = KOMPLETNA.replace(fragment, "## Sekcja bez znaczenia")
        braki = waliduj(_karta(tmp_path, okrojona), przed_zamrozeniem=True)
        assert braki, f"brak sekcji `{naglowek}` przeszedl niezauwazony"

    def test_sam_naglowek_bez_tresci_nie_wystarcza(self, tmp_path):
        """Pusta sekcja spelnialaby kontrole obecnosci, nie wnoszac nic."""
        pusta = KOMPLETNA.replace(
            "Brak zaleznosci od wielkosci rezyduum albo asymetria bez wyjasnienia\n"
            "mechanizmem obala karte niezaleznie od P&L.", "")
        braki = waliduj(_karta(tmp_path, pusta), przed_zamrozeniem=True)
        assert any("WARUNEK NEGATYWNY" in b for b in braki)

    def test_brak_pola_sha_jest_wykryty(self, tmp_path):
        bez = KOMPLETNA.replace("SHA zamrozenia: PENDING", "")
        braki = waliduj(_karta(tmp_path, bez), przed_zamrozeniem=True)
        assert any("SHA zamrozenia" in b for b in braki)

    def test_brak_pliku(self, tmp_path):
        assert waliduj(tmp_path / "nie_ma.md") != []


class TestLimitWariantow:
    def test_przekroczony_limit_jest_wykryty(self, tmp_path):
        tresc = KOMPLETNA.replace("wszystkie 6 zadeklarowane",
                                  "wszystkie 30 zadeklarowane")
        braki = waliduj(_karta(tmp_path, tresc), przed_zamrozeniem=True)
        assert any("30" in b and str(MAX_WARIANTOW) in b for b in braki)

    def test_limit_dokladnie_na_progu_przechodzi(self, tmp_path):
        tresc = KOMPLETNA.replace("wszystkie 6 zadeklarowane",
                                  f"wszystkie {MAX_WARIANTOW} zadeklarowane")
        assert waliduj(_karta(tmp_path, tresc), przed_zamrozeniem=True) == []

    def test_odczyt_liczby_wariantow(self):
        assert liczba_wariantow("## 8. Warianty — wszystkie 8 zadeklarowane") == 8
        assert liczba_wariantow("karta bez deklaracji") is None


class TestZakresObowiazywania:
    def test_karty_gen1_nie_sa_objete_wstecznie(self):
        """Karty Gen1 powstaly przed linterem. Ich wyniki maja pozostac
        ODTWARZALNE, a nie zgodne z pozniejszym formularzem — przerabianie ich
        pod nowy szablon byloby zmienianiem historii, nie poprawa procesu.

        Test celowo NIE wymaga, zeby przechodzily; pilnuje jedynie, zeby
        ktos nie zaczal ich po cichu przerabiac pod linter.
        """
        stare = sorted((KORZEN / "hypotheses").glob("H0*.md"))
        assert stare, "brak kart Gen1 — czy nie zostaly usuniete?"
        objete = [p.name for p in stare if p.name >= "H017.md"]
        assert not objete, (
            f"karty {objete} sa >= H017 i podlegaja linterowi — uruchom "
            "scripts/waliduj_karte.py przed ich zamrozeniem")


class TestSpojnoscZRejestratorem:
    def test_ten_sam_wzorzec_sha_w_obu_narzedziach(self):
        """Linter i rejestrator musza rozumiec `SHA zamrozenia` tak samo —
        inaczej karta przeszlaby linter i zostala odrzucona przy rejestracji
        proby (albo, gorzej, odwrotnie)."""
        from scripts.rejestruj_probe import WZORZEC_SHA as A
        from scripts.waliduj_karte import WZORZEC_SHA as B
        assert A.pattern == B.pattern

    def test_lockbox_log_ma_wymagany_schemat(self):
        d = json.loads((KORZEN / "validation" / "lockbox_log.json")
                       .read_text(encoding="utf-8"))
        assert d["wpisy"] == [], "sejf nie byl jeszcze otwierany"
        assert set(d["_pola_wymagane"]) == {"utc", "hipoteza", "powod", "sha"}
