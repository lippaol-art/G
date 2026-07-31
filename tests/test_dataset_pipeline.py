"""Testy pipeline'u raw -> clean — PLAN.pdf rozdz. 4.2.

Fixture'y kontraktow budowane recznie: dwie nogi kontraktowe z rolowaniem,
zeby sprawdzic wszystkie osiem krokow bez czekania na realne dane.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from engine.dataset import build_continuous, normalize_databento
from engine.loader import REQUIRED_COLUMNS
from engine.sessions import SessionCalendar


def _bars(contract: str, start: datetime, n: int, px: float, vol: int) -> list[dict]:
    """n kolejnych barow minutowych jednego kontraktu."""
    out = []
    for i in range(n):
        c = px + i * 0.25
        out.append({
            "ts_utc": start + timedelta(minutes=i),
            "open": c, "high": c + 1.0, "low": c - 1.0, "close": c,
            "volume": vol, "contract": contract,
        })
    return out


@pytest.fixture
def dwa_kontrakty() -> pl.DataFrame:
    """MNQH5 traci plynnosc, MNQM5 przejmuje. Rolowanie w drugim dniu."""
    d1 = datetime(2025, 3, 11, 14, 30, tzinfo=UTC)   # RTH
    d2 = datetime(2025, 3, 12, 14, 30, tzinfo=UTC)

    rows = (
        _bars("MNQH5", d1, 30, 20000.0, 900)     # dzien 1: stary dominuje
        + _bars("MNQM5", d1, 30, 20100.0, 100)
        + _bars("MNQH5", d2, 30, 20010.0, 200)   # dzien 2: nowy przejmuje
        + _bars("MNQM5", d2, 30, 20115.0, 800)
    )
    return pl.DataFrame(rows)


class TestPipeline:
    def test_schemat_wyjsciowy_jest_kompletny(self, dwa_kontrakty):
        """Pipeline musi wyprodukowac wszystkie kolumny wymagane przez loader."""
        df, _ = build_continuous(dwa_kontrakty)
        brakuje = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        assert not brakuje, f"brak kolumn: {brakuje}"

    def test_wykrywa_rolowanie(self, dwa_kontrakty):
        _, rep = build_continuous(dwa_kontrakty)
        assert len(rep.roll_events) == 1
        ev = rep.roll_events[0]
        assert ev.from_contract == "MNQH5"
        assert ev.to_contract == "MNQM5"

    def test_zostaje_tylko_kontrakt_aktywny(self, dwa_kontrakty):
        """W kazdym dniu sesyjnym dokladnie jeden kontrakt — inaczej duplikaty barow."""
        df, _ = build_continuous(dwa_kontrakty)
        per_dzien = df.group_by("trade_date").agg(pl.col("contract").n_unique().alias("n"))
        assert (per_dzien["n"] == 1).all(), "wiecej niz jeden kontrakt w dniu sesyjnym"

    def test_px_raw_i_px_adj_roznia_sie_przed_rolowaniem(self, dwa_kontrakty):
        """Rozdzielenie serii (rozdz. 4.3) — bez niego poziomy licza sie zle."""
        df, _ = build_continuous(dwa_kontrakty)
        stary = df.filter(pl.col("contract") == "MNQH5")
        if stary.height:
            assert (stary["px_raw"] != stary["px_adj"]).any(), \
                "back-adjust nie zostal zastosowany do starszego kontraktu"

    def test_px_adj_zachowuje_roznice(self, dwa_kontrakty):
        """Back-adjust roznicowy: P&L w punktach musi byc nietkniety."""
        df, _ = build_continuous(dwa_kontrakty)
        stary = df.filter(pl.col("contract") == "MNQH5").sort("ts_utc")
        if stary.height >= 2:
            d_raw = stary["px_raw"][1] - stary["px_raw"][0]
            d_adj = stary["px_adj"][1] - stary["px_adj"][0]
            assert d_raw == pytest.approx(d_adj)

    def test_dedup_usuwa_duplikaty(self):
        d = datetime(2025, 3, 11, 14, 30, tzinfo=UTC)
        rows = _bars("MNQH5", d, 5, 20000.0, 100)
        df = pl.DataFrame(rows + rows)          # kazdy bar dwa razy
        _, rep = build_continuous(df)
        assert rep.n_raw == 10
        assert rep.n_after_dedup == 5

    def test_odrzuca_bary_o_niemozliwym_ohlc(self):
        """low > high jest fizycznie niemozliwe — sygnal problemu u dostawcy."""
        d = datetime(2025, 3, 11, 14, 30, tzinfo=UTC)
        rows = _bars("MNQH5", d, 5, 20000.0, 100)
        rows.append({"ts_utc": d + timedelta(minutes=10), "open": 100.0,
                     "high": 90.0, "low": 110.0, "close": 100.0,
                     "volume": 50, "contract": "MNQH5"})
        _, rep = build_continuous(pl.DataFrame(rows))
        assert rep.ohlc_violations == 1

    def test_odrzuca_ujemny_wolumen(self):
        d = datetime(2025, 3, 11, 14, 30, tzinfo=UTC)
        rows = _bars("MNQH5", d, 5, 20000.0, 100)
        rows.append({"ts_utc": d + timedelta(minutes=10), "open": 100.0,
                     "high": 101.0, "low": 99.0, "close": 100.0,
                     "volume": -5, "contract": "MNQH5"})
        _, rep = build_continuous(pl.DataFrame(rows))
        assert rep.negative_volume == 1

    def test_segmenty_i_dzien_sesyjny(self, dwa_kontrakty):
        df, _ = build_continuous(dwa_kontrakty)
        assert df["segment"].is_not_null().all()
        assert df["trade_date"].is_not_null().all()
        assert "rth_open" in df["segment"].to_list() or "midday" in df["segment"].to_list()

    def test_luka_weekendowa_jest_expected_nie_anomaly(self):
        """Najwazniejszy test klasyfikacji: brak barow przez weekend to NORMA.

        Pipeline, ktory tego nie rozroznia, zaleje sanity-report falszywymi
        alarmami i ukryje prawdziwe problemy (rozdz. 4.2).

        UWAGA NA KONSTRUKCJE FIXTURE'U: rynek handluje do 17:00 ET w piatek
        i wznawia o 18:00 ET w niedziele. Zeby luka byla w calosci oczekiwana,
        ostatni bar piatkowy musi lezec tuz przed zamknieciem, a pierwszy
        kolejny — dokladnie po wznowieniu. Fixture konczacy piatek o 15:00 ET
        zostawia dwie godziny realnego czasu handlu i JEST anomalia (test nizej).
        """
        piatek = datetime(2025, 3, 14, 20, 56, tzinfo=UTC)     # do 16:59 ET (zamkniecie 17:00)
        niedziela = datetime(2025, 3, 16, 22, 0, tzinfo=UTC)   # 18:00 ET, wznowienie
        rows = _bars("MNQH5", piatek, 4, 20000.0, 100) + \
               _bars("MNQH5", niedziela, 5, 20000.0, 100)
        _, rep = build_continuous(pl.DataFrame(rows))
        assert rep.expected_gaps >= 1
        assert not rep.anomaly_gaps, f"weekend zgloszony jako anomalia: {rep.anomaly_gaps}"

    def test_brakujaca_koncowka_piatku_jest_anomalia(self):
        """Kontrola pozytywna: piatek po 15:00 ET to nadal czas handlu.

        Brak barow miedzy 15:00 a 17:00 ET w piatek NIE jest weekendem — to luka
        w danych i musi zostac zgloszona.
        """
        piatek = datetime(2025, 3, 14, 19, 0, tzinfo=UTC)      # 15:00 ET
        poniedzialek = datetime(2025, 3, 17, 14, 30, tzinfo=UTC)
        rows = _bars("MNQH5", piatek, 5, 20000.0, 100) + \
               _bars("MNQH5", poniedzialek, 5, 20000.0, 100)
        _, rep = build_continuous(pl.DataFrame(rows))
        assert rep.anomaly_gaps, "brakujaca koncowka piatku nie zostala wykryta"

    def test_luka_w_srodku_rth_to_anomalia(self):
        """Kontrola pozytywna: prawdziwa dziura MUSI zostac zgloszona."""
        d = datetime(2025, 3, 11, 14, 30, tzinfo=UTC)
        rows = _bars("MNQH5", d, 5, 20000.0, 100) + \
               _bars("MNQH5", d + timedelta(minutes=45), 5, 20000.0, 100)
        _, rep = build_continuous(pl.DataFrame(rows))
        assert rep.anomaly_gaps, "40-minutowa dziura w RTH nie zostala wykryta"

    def test_flagi_sa_ustawione(self, dwa_kontrakty):
        df, _ = build_continuous(dwa_kontrakty)
        for kol in ("halt_window", "short_day", "days_to_roll", "dst_transition"):
            assert kol in df.columns
        assert df["days_to_roll"].is_not_null().all()

    def test_dzien_skrocony_z_kalendarza(self):
        from datetime import date
        d = datetime(2025, 11, 28, 14, 30, tzinfo=UTC)
        cal = SessionCalendar(short_days=frozenset({date(2025, 11, 28)}))
        df, _ = build_continuous(pl.DataFrame(_bars("MNQZ5", d, 5, 20000.0, 100)),
                                 calendar=cal)
        assert df["short_day"].any()

    def test_raport_podsumowuje_budowe(self, dwa_kontrakty):
        _, rep = build_continuous(dwa_kontrakty)
        assert rep.n_final > 0
        assert rep.n_contracts == 2
        assert "rolowan" in rep.summary()


class TestNormalizacja:
    def test_ceny_calkowite_dzielone_przez_1e9(self):
        """Databento zwraca ceny jako liczby calkowite w jednostkach 1e-9."""
        df = pl.DataFrame({
            "ts_event": [datetime(2025, 3, 11, tzinfo=UTC)],
            "open": [20000_000_000_000], "high": [20010_000_000_000],
            "low": [19990_000_000_000], "close": [20005_000_000_000],
            "volume": [100], "symbol": ["MNQH5"],
        })
        out = normalize_databento(df)
        assert out["open"][0] == pytest.approx(20000.0)
        assert out["close"][0] == pytest.approx(20005.0)

    def test_mapowanie_nazw_kolumn(self):
        df = pl.DataFrame({
            "ts_event": [datetime(2025, 3, 11, tzinfo=UTC)],
            "open": [1.0], "high": [2.0], "low": [0.5], "close": [1.5],
            "volume": [10], "symbol": ["MNQH5"],
        })
        out = normalize_databento(df)
        assert "ts_utc" in out.columns and "contract" in out.columns
        assert "ts_event" not in out.columns and "symbol" not in out.columns

    def test_ceny_zmiennoprzecinkowe_nie_sa_dzielone(self):
        """Gdy dostawca zwroci juz float, nie wolno dzielic drugi raz."""
        df = pl.DataFrame({
            "ts_event": [datetime(2025, 3, 11, tzinfo=UTC)],
            "open": [20000.0], "high": [20010.0], "low": [19990.0], "close": [20005.0],
            "volume": [100], "symbol": ["MNQH5"],
        })
        assert normalize_databento(df)["open"][0] == pytest.approx(20000.0)


class TestSpready:
    """Spready kalendarzowe w strumieniu Databento — pulapka wykryta na realnych danych.

    CME notuje spready jako 'MNQM9-MNQU9' i Databento zwraca je razem z kontraktami
    outright. Ich ceny to ROZNICE (14-31 pkt), nie poziomy indeksu (7000-23000).
    W danych MNQ za 2019 rok bylo ich 582.
    """

    def test_spread_jest_rozpoznawany(self):
        from engine.dataset import is_spread_symbol
        assert is_spread_symbol("MNQM9-MNQU9")
        assert is_spread_symbol("MNQZ9-MNQH0")
        assert not is_spread_symbol("MNQH5")
        assert not is_spread_symbol("MNQU9")

    def test_normalizacja_odfiltrowuje_spready(self):
        df = pl.DataFrame({
            "ts_event": [datetime(2019, 5, 10, 20, 36, tzinfo=UTC)] * 3,
            "open": [7748.75, 28.50, 7749.0],
            "high": [7748.75, 28.50, 7749.0],
            "low": [7748.75, 28.50, 7749.0],
            "close": [7748.75, 28.50, 7749.0],
            "volume": [1, 1, 5],
            "symbol": ["MNQM9", "MNQM9-MNQU9", "MNQU9"],
        })
        out = normalize_databento(df)
        assert out.height == 2, "spread nie zostal odfiltrowany"
        assert "MNQM9-MNQU9" not in out["contract"].to_list()

    def test_spread_wpuszczony_wygladalby_jak_krach(self):
        """Dokumentuje SKALE problemu: bar spreadu obok baru kontraktu to
        pozorny spadek o ponad 99% i natychmiastowe odbicie."""
        cena_kontraktu, cena_spreadu = 7748.75, 28.50
        pozorny_spadek = (cena_spreadu - cena_kontraktu) / cena_kontraktu
        assert pozorny_spadek < -0.99, \
            f"pozorny ruch {100*pozorny_spadek:.1f}% — strategia 'kupuj spadki' zrobilaby fortune"
