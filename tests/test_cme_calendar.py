"""Kalendarz CME — dni skrocone i swieta.

DEFEKT, KTORY TE TESTY ZAMYKAJA: `build_continuous` wolal `SessionCalendar()`
bez argumentow, wiec `short_days` bylo PUSTE i flaga `short_day` wychodzila
False dla wszystkich 2 551 265 barow zbioru. Flaga istniala, ale nic nie
znaczyla.

ZRODLO PRAWDY: opublikowane reguly CME dla kontraktow Equity Index, zapisane
jawnie w `engine/cme_calendar.py`. Dane sluza WYLACZNIE do weryfikacji tych
regul (`test_zgodnosc_z_danymi`), nigdy do ich wyprowadzania — mniejsza liczba
barow sama w sobie nie czyni dnia skroconym.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl
import pytest

from engine.cme_calendar import (
    CLOSE_1300,
    CLOSE_1315,
    cme_calendar,
    good_friday,
    independence_observed,
)
from engine.sessions import is_rth

PARQUET = Path("data/clean/mnq_1m_cont.parquet")
_ET = ZoneInfo("America/New_York")


def _et(y: int, m: int, d: int, hh: int, mm: int) -> dt.datetime:
    return dt.datetime(y, m, d, hh, mm, tzinfo=_ET)


# --------------------------------------------------------------- reguly ----
class TestReguly:
    def test_2026_07_03_jest_dniem_skroconym(self):
        """Defekt zgloszony przez wlasciciela projektu — sesja z D5-B."""
        cal = cme_calendar(2026, 2026)
        d = dt.date(2026, 7, 3)
        assert d in cal.short_days
        assert cal.close_time(d) == CLOSE_1300

    def test_2026_07_03_to_swieto_obserwowane_nie_dzien_przed(self):
        """4 lipca 2026 wypada w SOBOTE, wiec swieto obserwowane jest w piatek
        3 lipca. To sesja swiateczna (13:00), nie przeddzien swieta (13:15)."""
        assert independence_observed(2026) == dt.date(2026, 7, 3)
        assert cme_calendar(2026, 2026).close_time(dt.date(2026, 7, 3)) == CLOSE_1300

    def test_przesuwanie_4_lipca(self):
        assert independence_observed(2026) == dt.date(2026, 7, 3)   # sobota -> piatek
        assert independence_observed(2021) == dt.date(2021, 7, 5)   # niedziela -> pon.
        assert independence_observed(2025) == dt.date(2025, 7, 4)   # piatek
        assert independence_observed(2019) == dt.date(2019, 7, 4)   # czwartek

    def test_przeddzien_4_lipca_zamyka_o_1315(self):
        """3 lipca jest dniem skroconym o 13:15 TYLKO gdy sam nie jest swietem."""
        cal = cme_calendar(2019, 2025)
        assert cal.close_time(dt.date(2019, 7, 3)) == CLOSE_1315
        assert cal.close_time(dt.date(2025, 7, 3)) == CLOSE_1315
        assert cal.close_time(dt.date(2019, 7, 4)) == CLOSE_1300

    def test_dzien_po_swiecie_dziekczynienia(self):
        cal = cme_calendar(2024, 2024)
        assert cal.close_time(dt.date(2024, 11, 28)) == CLOSE_1300   # czwartek
        assert cal.close_time(dt.date(2024, 11, 29)) == CLOSE_1315   # piatek

    def test_wigilia(self):
        cal = cme_calendar(2024, 2025)
        assert cal.close_time(dt.date(2024, 12, 24)) == CLOSE_1315
        assert cal.close_time(dt.date(2025, 12, 24)) == CLOSE_1315

    def test_wigilia_w_weekend_nie_jest_sesja(self):
        """24.12.2022 to sobota — nie moze byc dniem skroconym."""
        assert dt.date(2022, 12, 24) not in cme_calendar(2022, 2022).short_days

    def test_juneteenth_dopiero_od_2022(self):
        assert dt.date(2021, 6, 18) not in cme_calendar(2021, 2021).short_days
        assert dt.date(2022, 6, 20) in cme_calendar(2022, 2022).short_days
        assert dt.date(2025, 6, 19) in cme_calendar(2025, 2025).short_days

    def test_swieta_pelne_nie_sa_dniami_skroconymi(self):
        cal = cme_calendar(2024, 2024)
        for d in (dt.date(2024, 1, 1), dt.date(2024, 3, 29), dt.date(2024, 12, 25)):
            assert d in cal.holidays
            assert d not in cal.short_days
            assert not cal.is_trading_day(d)

    def test_wielki_piatek(self):
        assert good_friday(2024) == dt.date(2024, 3, 29)
        assert good_friday(2025) == dt.date(2025, 4, 18)
        assert good_friday(2026) == dt.date(2026, 4, 3)

    def test_zwykly_dzien_nietkniety(self):
        cal = cme_calendar(2026, 2026)
        d = dt.date(2026, 7, 6)
        assert d not in cal.short_days
        assert cal.close_time(d) == dt.time(16, 0)


# ------------------------------------------------------- integracja RTH ----
class TestRTH:
    def test_is_rth_respektuje_1315(self):
        """Regresja: `close_time` zwracalo stale 13:00, wiec ostatnie 15 minut
        sesji 24 grudnia i piatku po Swiecie Dziekczynienia wypadalo poza RTH."""
        cal = cme_calendar(2024, 2024)
        assert is_rth(_et(2024, 12, 24, 13, 10), cal)
        assert not is_rth(_et(2024, 12, 24, 13, 20), cal)

    def test_is_rth_dzien_swiateczny_konczy_sie_o_13(self):
        cal = cme_calendar(2024, 2024)
        assert is_rth(_et(2024, 11, 28, 12, 50), cal)
        assert not is_rth(_et(2024, 11, 28, 13, 10), cal)


# ------------------------------------------------ weryfikacja na danych ----
@pytest.mark.skipif(not PARQUET.exists(), reason="brak danych rynkowych")
class TestZgodnoscZDanymi:
    """Reguly kontra rzeczywistosc. Dane WERYFIKUJA regule, nie tworza jej.

    Dni oznaczone jako `degraded` sa wykluczone — brak transakcji z powodu
    defektu danych nie jest dniem skroconym i nie wolno go tak klasyfikowac.
    """

    @staticmethod
    def _zdegradowane() -> set[dt.date]:
        import json
        return {dt.date.fromisoformat(k) for k in json.loads(
            Path("data/clean/degraded_days.json").read_text(encoding="utf-8"))}

    @classmethod
    def _ostatnie_bary(cls) -> dict[dt.date, dt.time]:
        zdegradowane = {d.isoformat() for d in cls._zdegradowane()}
        d = (pl.read_parquet(PARQUET)
             .filter(pl.col("volume") > 0)
             .with_columns(pl.col("ts_utc")
                           .dt.convert_time_zone("America/New_York").alias("et")))
        d = d.filter((pl.col("et").dt.time() >= dt.time(9, 30))
                     & (pl.col("et").dt.time() < dt.time(16, 0)))
        g = d.group_by("trade_date").agg(pl.col("et").max().alias("ostatni"))
        return {r["trade_date"]: r["ostatni"].time()
                for r in g.iter_rows(named=True)
                if r["trade_date"].isoformat() not in zdegradowane}

    def test_kazdy_dzien_skrocony_konczy_sie_zgodnie_z_regula(self):
        ostatnie = self._ostatnie_bary()
        cal = cme_calendar(2019, 2026)
        bledy = []
        for d, ost in sorted(ostatnie.items()):
            if d not in cal.short_days:
                continue
            oczek = cal.close_time(d)
            # ostatni bar minutowy zaczyna sie minute przed zamknieciem
            if ost.hour * 60 + ost.minute != oczek.hour * 60 + oczek.minute - 1:
                bledy.append(f"{d}: ostatni {ost}, regula {oczek}")
        assert not bledy, "regula niezgodna z danymi: " + "; ".join(bledy)

    def test_zaden_dzien_pelny_nie_konczy_sie_wczesnie(self):
        """Odwrotny kierunek: dzien spoza kalendarza nie moze konczyc sie
        systematycznie wczesnie. To lapie swieta, o ktorych regula nie wie."""
        ostatnie = self._ostatnie_bary()
        cal = cme_calendar(2019, 2026)
        bledy = [f"{d}: ostatni {ost}" for d, ost in sorted(ostatnie.items())
                 if d not in cal.short_days
                 and ost.hour * 60 + ost.minute < 15 * 60]
        assert not bledy, "dni skrocone spoza kalendarza: " + "; ".join(bledy)

    def test_swieta_nie_maja_sesji_rth(self):
        ostatnie = self._ostatnie_bary()
        cal = cme_calendar(2019, 2026)
        obecne = [d for d in ostatnie if d in cal.holidays]
        assert not obecne, f"swieta z sesja RTH: {obecne}"

    def test_wszystkie_swieta_kalendarza_sa_w_danych_nieobecne(self):
        """Kierunek odwrotny do `test_swieta_nie_maja_sesji_rth`: kazdy dzien
        roboczy bez sesji RTH musi byc w kalendarzu. Inaczej mamy swieto,
        o ktorym regula nie wie."""
        ostatnie = self._ostatnie_bary()
        # Dni zdegradowane sa wykluczone z `ostatnie`, wiec ich brak NIE jest
        # dowodem swieta — to defekt danych. Pominiecie tego kroku dalo
        # falszywy alarm na dziewieciu dniach, w tym na 2025-11-28, ktory
        # sesje ma (225 barow), tylko oznaczona jako `degraded`.
        pomijane = self._zdegradowane()
        cal = cme_calendar(2019, 2026)
        lo, hi = min(ostatnie), max(ostatnie)
        brak, c = [], lo
        while c <= hi:
            if (c.weekday() < 5 and c not in ostatnie
                    and c not in cal.holidays and c not in pomijane):
                brak.append(c)
            c += dt.timedelta(days=1)
        assert not brak, f"dni robocze bez sesji, spoza kalendarza: {brak}"
