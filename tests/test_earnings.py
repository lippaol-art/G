"""Testy kalendarza wynikow — engine/earnings.py.

Fixture'y sa recznie zbudowane i jest to swiadome: to nie sa dane rynkowe, tylko
przypadki brzegowe parsera i klasyfikatora. Zasada "zero danych syntetycznych"
dotyczy wnioskow o rynku, nie dowodow poprawnosci kodu.

Kazdy przypadek strefy czasowej pochodzi z REALNEGO zlozenia (accession w tescie),
bo to na realnych danych wyszla niespojnosc, ktorej fixture by nie wymyslil.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from engine.earnings import (
    AMC,
    BMO,
    CIK,
    ET,
    POZA_SESJA,
    SRODSESYJNE,
    Publikacja,
    klasyfikuj,
    parsuj_akceptacje,
    parsuj_submissions,
    sesja_reakcji,
)


def _sesja(dzien: date, otwarcie=(9, 30), zamkniecie=(15, 59)):
    return (
        datetime(dzien.year, dzien.month, dzien.day, *otwarcie, tzinfo=ET),
        datetime(dzien.year, dzien.month, dzien.day, *zamkniecie, tzinfo=ET),
    )


class TestKlasyfikacja:
    def test_po_zamknieciu_to_amc(self):
        d = date(2026, 4, 30)
        o, c = _sesja(d)
        assert klasyfikuj(datetime(2026, 4, 30, 16, 30, tzinfo=ET), o, c) == AMC

    def test_przed_otwarciem_to_bmo(self):
        d = date(2026, 4, 2)
        o, c = _sesja(d)
        assert klasyfikuj(datetime(2026, 4, 2, 6, 5, tzinfo=ET), o, c) == BMO

    def test_w_trakcie_sesji(self):
        d = date(2026, 4, 30)
        o, c = _sesja(d)
        assert klasyfikuj(datetime(2026, 4, 30, 12, 3, tzinfo=ET), o, c) == SRODSESYJNE

    def test_dzien_bez_sesji(self):
        assert klasyfikuj(datetime(2021, 4, 2, 8, 38, tzinfo=ET), None, None) == POZA_SESJA

    def test_dzien_skrocony_publikacja_o_13_30_to_amc(self):
        """Sedno uzycia zaobserwowanych granic zamiast stalych 09:30-16:00.

        W dzien skrocony sesja konczy sie o 13:00 ET. Publikacja o 13:30 jest
        wtedy PO zamknieciu. Klasyfikator ze sztywna 16:00 uznalby ja za
        srodsesyjna i przypisal reakcje do zlej sesji.
        """
        d = date(2024, 11, 29)                     # dzien po Swiecie Dziekczynienia
        o, c = _sesja(d, zamkniecie=(12, 59))
        assert klasyfikuj(datetime(2024, 11, 29, 13, 30, tzinfo=ET), o, c) == AMC

    def test_granice_sa_domkniete_po_stronie_sesji(self):
        """Bar otwarcia i bar zamkniecia naleza do sesji, nie do BMO/AMC."""
        d = date(2026, 4, 30)
        o, c = _sesja(d)
        assert klasyfikuj(o, o, c) == SRODSESYJNE
        assert klasyfikuj(c, o, c) == SRODSESYJNE


class TestSesjaReakcji:
    SESJE = frozenset({date(2026, 4, 29), date(2026, 4, 30), date(2026, 5, 1),
                       date(2026, 5, 4)})

    def test_amc_reaguje_nastepnej_sesji(self):
        assert sesja_reakcji(date(2026, 4, 30), AMC, self.SESJE) == date(2026, 5, 1)

    def test_bmo_reaguje_tego_samego_dnia(self):
        assert sesja_reakcji(date(2026, 4, 30), BMO, self.SESJE) == date(2026, 4, 30)

    def test_amc_w_piatek_przeskakuje_weekend(self):
        assert sesja_reakcji(date(2026, 5, 1), AMC, self.SESJE) == date(2026, 5, 4)

    def test_poza_sesja_trafia_do_najblizszej(self):
        assert sesja_reakcji(date(2026, 5, 2), POZA_SESJA, self.SESJE) == date(2026, 5, 4)

    def test_brak_kolejnej_sesji_zwraca_none(self):
        """Koniec probki. None wymusza jawne odrzucenie zamiast zlej daty."""
        assert sesja_reakcji(date(2026, 5, 4), AMC, self.SESJE) is None


class TestParserSubmissions:
    BLOK = {
        "form": ["8-K", "8-K", "10-Q", "8-K", "8-K"],
        "items": ["2.02,9.01", "5.02", "", "7.01,8.01", "12.02"],
        "accessionNumber": ["a-1", "a-2", "a-3", "a-4", "a-5"],
        "filingDate": ["2026-04-30"] * 5,
        "reportDate": ["2026-04-30"] * 5,
        "acceptanceDateTime": ["2026-04-30T20:30:41.000Z"] * 5,
    }

    def test_bierze_tylko_8k_z_pozycja_2_02(self):
        p = parsuj_submissions(self.BLOK, "AAPL")
        assert [x.accession for x in p] == ["a-1"]

    def test_pozycja_12_02_nie_jest_2_02(self):
        """Test podciagu dalby tu falszywe trafienie — stad rozbicie po przecinku."""
        p = parsuj_submissions(self.BLOK, "AAPL")
        assert "a-5" not in [x.accession for x in p]

    def test_pusty_blok(self):
        assert parsuj_submissions({}, "AAPL") == []

    def test_wypelnia_cik_ze_slownika(self):
        assert parsuj_submissions(self.BLOK, "AAPL")[0].cik == CIK["AAPL"]

    def test_nie_ustawia_czasu_akceptacji(self):
        """Parser submissions NIE jest zrodlem czasu — patrz docstring modulu."""
        assert parsuj_submissions(self.BLOK, "AAPL")[0].akceptacja_et is None


class TestParserStronyIndeksu:
    HTML = (
        '<div class="infoHead">Accepted</div>'
        '<div class="info">2026-04-30 16:30:41</div>'
    )

    def test_wyluskuje_czas_et(self):
        t = parsuj_akceptacje(self.HTML)
        assert t == datetime(2026, 4, 30, 16, 30, 41, tzinfo=ET)

    def test_brak_pola_zwraca_none(self):
        """Cicha wartosc domyslna oznaczalaby zla godzine, a nie brak danych."""
        assert parsuj_akceptacje("<div>nic tu nie ma</div>") is None

    def test_znosi_biale_znaki(self):
        html = 'Accepted</div>\n   <div class="info">\n2026-04-30 16:30:41</div>'
        assert parsuj_akceptacje(html) is not None


class TestNiespojnoscStrefyWSubmissions:
    """Regresja na realnej pulapce: `acceptanceDateTime` bywa ET z sufiksem Z.

    Oba przypadki to prawdziwe zlozenia. AAPL ma znacznik przeliczony poprawnie,
    MSFT nie — i wlasnie dlatego czas bierzemy ze strony indeksu.
    """

    def test_aapl_znacznik_json_jest_prawdziwym_utc(self):
        p = Publikacja(
            symbol="AAPL", cik=CIK["AAPL"], accession="0000320193-26-000011",
            data_zlozenia=date(2026, 4, 30), okres="2026-04-30",
            znacznik_json="2026-04-30T20:30:41.000Z",
            akceptacja_et=datetime(2026, 4, 30, 16, 30, 41, tzinfo=ET),
        )
        assert p.json_zgodny is True

    def test_msft_znacznik_json_jest_czasem_et_z_sufiksem_z(self):
        p = Publikacja(
            symbol="MSFT", cik=CIK["MSFT"], accession="0001193125-26-323632",
            data_zlozenia=date(2026, 7, 29), okres="2026-07-29",
            znacznik_json="2026-07-29T16:04:53.000Z",
            akceptacja_et=datetime(2026, 7, 29, 16, 4, 53, tzinfo=ET),
        )
        assert p.json_zgodny is False

    def test_bledna_strefa_przesunelaby_msft_w_srodek_sesji(self):
        """Konsekwencja bledu, gdyby go nie wykryc — 16:04 ET staje sie 12:04 ET."""
        zle = datetime.fromisoformat("2026-07-29T16:04:53+00:00").astimezone(ET)
        assert zle.hour == 12
        o, c = _sesja(date(2026, 7, 29))
        assert klasyfikuj(zle, o, c) == SRODSESYJNE
        assert klasyfikuj(datetime(2026, 7, 29, 16, 4, 53, tzinfo=ET), o, c) == AMC

    def test_brak_znacznika_daje_none_a_nie_falsz(self):
        p = Publikacja(symbol="AAPL", cik=CIK["AAPL"], accession="x",
                       data_zlozenia=date(2026, 4, 30), okres="")
        assert p.json_zgodny is None


@pytest.fixture(scope="module")
def kalendarz():
    """Zbudowany kalendarz. Testy pomijane, gdy pliku jeszcze nie ma."""
    import csv
    from pathlib import Path

    p = Path("data/clean/earnings.csv")
    if not p.exists():
        pytest.skip("brak data/clean/earnings.csv — uruchom scripts/build_earnings.py")
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestKalendarzNaRealnychDanych:
    def test_kazda_spolka_ma_okolo_czterech_publikacji_rocznie(self, kalendarz):
        from collections import Counter

        c = Counter(r["symbol"] for r in kalendarz)
        assert set(c) == set(CIK), "brakuje spolki w kalendarzu"
        for symbol in CIK:
            assert c[symbol] >= 25, f"{symbol}: tylko {c[symbol]} publikacji"

    def test_zadnej_publikacji_w_srodku_sesji(self, kalendarz):
        """Megacapy publikuja poza sesja. Srodsesyjne = podejrzenie bledu strefy."""
        srod = [r for r in kalendarz if r["klasa"] == SRODSESYJNE]
        assert not srod, f"{len(srod)} publikacji srodsesyjnych — sprawdz strefy czasowe"

    def test_amc_reaguje_pozniej_niz_publikacja(self, kalendarz):
        for r in kalendarz:
            if r["klasa"] == AMC and r["sesja_reakcji"]:
                dzien = datetime.fromisoformat(r["akceptacja_et"]).date()
                assert date.fromisoformat(r["sesja_reakcji"]) > dzien

    def test_bmo_reaguje_tego_samego_dnia(self, kalendarz):
        for r in kalendarz:
            if r["klasa"] == BMO and r["sesja_reakcji"]:
                dzien = datetime.fromisoformat(r["akceptacja_et"]).date()
                assert date.fromisoformat(r["sesja_reakcji"]) == dzien

    def test_publikacje_amc_sa_po_zamknieciu(self, kalendarz):
        for r in kalendarz:
            if r["klasa"] == AMC:
                t = datetime.fromisoformat(r["akceptacja_et"])
                assert t.hour >= 13, f"{r['symbol']} {r['akceptacja_et']} — AMC przed 13:00"
