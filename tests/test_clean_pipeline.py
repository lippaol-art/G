"""Testy pipeline'u raw -> clean — PLAN.pdf rozdz. 4.2, 4.3, 4.4.

Ramki wejsciowe sa budowane recznie. To fixture'y do dowodzenia poprawnosci
transformacji, nie material badawczy — zaden wniosek o rynku nie moze z nich
wyniknac i zaden tu nie zapada.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import polars as pl
import pytest

from engine.calendar_cme import build_calendar
from engine.clean import (
    RawDataError,
    active_contract_map,
    annotate_time,
    build_continuous,
    classify_gaps,
    contract_order,
    dedup_and_sort,
    parse_contract,
    validate_bars,
)
from engine.roll import RollEvent
from engine.sessions import SessionCalendar, segment_of, trade_date

KALENDARZ = build_calendar(2024, 2025)


def bary(symbol: str, start: datetime, n: int, *, cena: float, volume: int) -> pl.DataFrame:
    """n kolejnych barow minutowych jednej nogi kontraktowej."""
    return pl.DataFrame({
        "ts_event": [start + timedelta(minutes=i) for i in range(n)],
        "symbol": [symbol] * n,
        "open": [cena + i * 0.25 for i in range(n)],
        "high": [cena + i * 0.25 + 1.0 for i in range(n)],
        "low": [cena + i * 0.25 - 1.0 for i in range(n)],
        "close": [cena + i * 0.25 + 0.25 for i in range(n)],
        "volume": [volume] * n,
    }).with_columns(pl.col("ts_event").dt.replace_time_zone("UTC"))


# --------------------------------------------------------------------------
# [1] dedup + sortowanie
# --------------------------------------------------------------------------

def test_dedup_usuwa_powtorzone_bary():
    start = datetime(2024, 12, 10, 15, 0, tzinfo=UTC)
    df = pl.concat([bary("MNQZ4", start, 5, cena=100, volume=10)] * 2)

    out = dedup_and_sort(df)

    assert out.height == 5
    assert out["ts_event"].is_sorted()


def test_brak_wymaganej_kolumny_konczy_sie_bledem():
    with pytest.raises(RawDataError, match="kolumn"):
        dedup_and_sort(pl.DataFrame({"ts_event": [], "symbol": []}))


# --------------------------------------------------------------------------
# [2] walidacja — bledow NIE naprawiamy po cichu
# --------------------------------------------------------------------------

def test_niespojne_ohlc_jest_zglaszane_a_nie_naprawiane():
    start = datetime(2024, 12, 10, 15, 0, tzinfo=UTC)
    df = bary("MNQZ4", start, 3, cena=100, volume=10).with_columns(
        pl.when(pl.int_range(pl.len()) == 1).then(pl.lit(999.0)).otherwise(pl.col("low")).alias("low")
    )

    naruszenia = validate_bars(df)

    assert len(naruszenia) == 1
    assert "OHLC niespojne" in naruszenia[0]


def test_ujemny_wolumen_jest_naruszeniem():
    start = datetime(2024, 12, 10, 15, 0, tzinfo=UTC)
    df = bary("MNQZ4", start, 2, cena=100, volume=-1)

    assert any("ujemnym wolumenem" in n for n in validate_bars(df))


# --------------------------------------------------------------------------
# [3] klasyfikacja luk — brak bara nie jest luka w danych
# --------------------------------------------------------------------------

def test_przerwa_serwisowa_jest_luka_oczekiwana():
    # 21:00 UTC = 16:00 ET (koniec sesji) -> 23:00 UTC = 18:00 ET (Globex).
    ts = [
        datetime(2024, 12, 10, 21, 59, tzinfo=UTC),
        datetime(2024, 12, 10, 23, 1, tzinfo=UTC),
    ]
    assert classify_gaps(ts, KALENDARZ) == ["none", "expected"]


def test_weekend_jest_luka_oczekiwana():
    ts = [
        datetime(2024, 12, 13, 21, 59, tzinfo=UTC),   # piatek 16:59 ET
        datetime(2024, 12, 15, 23, 1, tzinfo=UTC),    # niedziela 18:01 ET
    ]
    assert classify_gaps(ts, KALENDARZ)[1] == "expected"


def test_dziura_w_srodku_sesji_jest_anomalia():
    ts = [
        datetime(2024, 12, 10, 15, 0, tzinfo=UTC),    # 10:00 ET
        datetime(2024, 12, 10, 16, 30, tzinfo=UTC),   # 11:30 ET — 90 minut ciszy w RTH
    ]
    assert classify_gaps(ts, KALENDARZ)[1] == "anomaly"


def test_swieto_jest_luka_oczekiwana():
    # Wielki Piatek 2025 = 18 kwietnia; rynek zamkniety caly dzien. Ostatni bar
    # to czwartek 16:59 ET, pierwszy nastepny — niedziela 18:01 ET (kwiecien: EDT).
    ts = [
        datetime(2025, 4, 17, 20, 59, tzinfo=UTC),
        datetime(2025, 4, 20, 22, 1, tzinfo=UTC),
    ]
    assert classify_gaps(ts, KALENDARZ)[1] == "expected"


def test_cisza_w_sesji_azjatyckiej_nie_jest_anomalia():
    """Brak transakcji w cienkiej godzinie to poprawny opis rynku (rozdz. 4.2)."""
    ts = [
        datetime(2024, 12, 11, 6, 0, tzinfo=UTC),    # 01:00 ET, sesja azjatycka
        datetime(2024, 12, 11, 6, 40, tzinfo=UTC),   # 40 minut bez transakcji
    ]
    assert classify_gaps(ts, KALENDARZ)[1] == "expected"

    # Ta sama cisza w otwarciu RTH to juz sygnal do przejrzenia.
    rth = [
        datetime(2024, 12, 11, 14, 40, tzinfo=UTC),  # 09:40 ET
        datetime(2024, 12, 11, 15, 20, tzinfo=UTC),
    ]
    assert classify_gaps(rth, KALENDARZ)[1] == "anomaly"


def test_luka_jednominutowa_nie_jest_luka():
    ts = [
        datetime(2024, 12, 10, 15, 0, tzinfo=UTC),
        datetime(2024, 12, 10, 15, 1, tzinfo=UTC),
    ]
    assert classify_gaps(ts, KALENDARZ) == ["none", "none"]


# --------------------------------------------------------------------------
# [4] kontrakty
# --------------------------------------------------------------------------

def test_parsowanie_symbolu_kontraktu():
    assert parse_contract("MNQH5", 2024) == ("MNQ", 2025, 3)
    assert parse_contract("MNQZ4", 2024) == ("MNQ", 2024, 12)
    assert parse_contract("MNQM25", 2024) == ("MNQ", 2025, 6)


def test_rok_jednocyfrowy_nie_moze_wypasc_przed_poczatkiem_historii():
    """Cyfra 1 przy historii od 2019 to rok 2021, nie 2011."""
    assert parse_contract("MNQH1", 2019)[1] == 2021


def test_nierozpoznany_symbol_failuje_glosno():
    with pytest.raises(RawDataError, match="Nierozpoznany symbol"):
        parse_contract("MNQ-FRONT", 2024)


def test_kolejnosc_kontraktow_wg_wygasniecia():
    assert contract_order(["MNQH5", "MNQZ4", "MNQM5"], 2024) == ["MNQZ4", "MNQH5", "MNQM5"]


def test_mapa_aktywnego_kontraktu():
    rolls = [RollEvent(date(2024, 12, 12), "MNQZ4", "MNQH5", spread=25.0)]
    dni = [date(2024, 12, 11), date(2024, 12, 12), date(2024, 12, 13)]

    mapa = active_contract_map(rolls, ["MNQZ4", "MNQH5"], dni)

    assert mapa[date(2024, 12, 11)] == "MNQZ4"
    assert mapa[date(2024, 12, 12)] == "MNQH5", "od dnia rolowania handlujemy nowa noga"
    assert mapa[date(2024, 12, 13)] == "MNQH5"


# --------------------------------------------------------------------------
# [6][7] czas i segmenty — dwie implementacje musza dawac to samo
# --------------------------------------------------------------------------

def test_segmenty_wektorowe_zgadzaja_sie_ze_skalarnymi():
    """Rozjazd o jedna minute miedzy definicjami = niepowtarzalny wynik badania."""
    start = datetime(2024, 12, 10, 0, 0, tzinfo=UTC)
    ts = [start + timedelta(minutes=7 * i) for i in range(400)]
    df = annotate_time(pl.DataFrame({"ts_event": ts}))

    assert df["segment"].to_list() == [segment_of(t) for t in ts]
    assert df["trade_date"].to_list() == [trade_date(t) for t in ts]


def test_dzien_sesyjny_zaczyna_sie_o_18_et():
    ts = [
        datetime(2024, 12, 10, 22, 59, tzinfo=UTC),   # 17:59 ET — jeszcze 10 grudnia
        datetime(2024, 12, 10, 23, 1, tzinfo=UTC),    # 18:01 ET — juz 11 grudnia
        datetime(2024, 12, 15, 23, 30, tzinfo=UTC),   # niedziela wieczor -> poniedzialek
    ]
    df = annotate_time(pl.DataFrame({"ts_event": ts}))

    assert df["trade_date"].to_list() == [date(2024, 12, 10), date(2024, 12, 11), date(2024, 12, 16)]


def test_flaga_tygodnia_przejsciowego_dst():
    """USA zmienia czas 10.03.2024, Europa dopiero 31.03 — miedzy nimi flaga."""
    zwykly = datetime(2024, 2, 20, 15, 0, tzinfo=UTC)
    przejsciowy = datetime(2024, 3, 20, 15, 0, tzinfo=UTC)
    df = annotate_time(pl.DataFrame({"ts_event": [zwykly, przejsciowy]}))

    assert df["dst_transition"].to_list() == [False, True]


def test_flaga_historycznego_haltu():
    # 15:15-15:30 CT = 20:15-20:30 UTC zima; halt zniesiony 27.06.2021.
    przed = datetime(2021, 3, 10, 21, 20, tzinfo=UTC)     # 15:20 CT
    po = datetime(2022, 3, 10, 21, 20, tzinfo=UTC)
    df = annotate_time(pl.DataFrame({"ts_event": [przed, po]}))

    assert df["halt_window"].to_list() == [True, False]


# --------------------------------------------------------------------------
# [5] pelny przebieg: sklejenie i back-adjust
# --------------------------------------------------------------------------

def _raw_z_rolowaniem() -> pl.DataFrame:
    """Trzy dni sesyjne, dwie nogi; wolumen przenosi sie drugiego dnia.

    Nowy kontrakt notuje 25 punktow wyzej — bez back-adjustu seria ciagla
    mialaby w dniu rolowania skok, na ktorym strategia "kupuj spadki"
    zarabialaby na luce niemozliwej do przehandlowania.
    """
    czesci = []
    for i, d in enumerate([date(2024, 12, 10), date(2024, 12, 11), date(2024, 12, 12)]):
        start = datetime(d.year, d.month, d.day, 15, 0, tzinfo=UTC)   # 10:00 ET
        stary_vol, nowy_vol = (1000, 10) if i == 0 else (10, 1000)
        czesci.append(bary("MNQZ4", start, 30, cena=21000.0, volume=stary_vol))
        czesci.append(bary("MNQH5", start, 30, cena=21025.0, volume=nowy_vol))
    return pl.concat(czesci)


def test_pelny_przebieg_buduje_kontrakt_ciagly():
    df, report = build_continuous(_raw_z_rolowaniem(), KALENDARZ)

    assert report.n_clean == df.height
    assert len(report.rolls) == 1
    roll = report.rolls[0]
    assert roll.from_contract == "MNQZ4" and roll.to_contract == "MNQH5"
    assert roll.spread == pytest.approx(25.0)

    # W kazdej minucie zostaje dokladnie jedna noga.
    assert df.group_by("ts_utc").len()["len"].max() == 1
    assert set(df["contract"].unique()) == {"MNQZ4", "MNQH5"}


def test_back_adjust_usuwa_skok_z_dnia_rolowania():
    df, report = build_continuous(_raw_z_rolowaniem(), KALENDARZ)
    spread = report.rolls[0].spread

    # Historia sprzed rolowania jest przesunieta o spread, wiec sklejenie
    # jest gladkie: close ostatniego bara starej nogi i pierwszego bara nowej
    # roznia sie o ruch rynku, nie o roznice kontraktow.
    przed = df.filter(pl.col("contract") == "MNQZ4")
    po = df.filter(pl.col("contract") == "MNQH5")
    skok = po["open"].first() - przed["close"].last()

    assert abs(skok) < spread / 2, f"skok {skok} zbyt bliski spreadowi {spread}"


def test_rozdzielenie_serii_px_raw_i_px_adj():
    df, _ = build_continuous(_raw_z_rolowaniem(), KALENDARZ)

    # px_adj to seria, na ktorej liczymy P&L; px_raw to cena, ktora realnie
    # byla na tablicy. Roznica jest stala w obrebie kontraktu i zerowa dla nogi
    # najnowszej (rozdz. 4.3).
    stary = df.filter(pl.col("contract") == "MNQZ4")
    nowy = df.filter(pl.col("contract") == "MNQH5")

    assert (nowy["px_raw"] - nowy["px_adj"]).abs().max() == pytest.approx(0.0)
    assert stary["px_raw_offset"].n_unique() == 1
    assert stary["px_raw_offset"].first() == pytest.approx(-25.0)
    # Kazda cena surowa da sie odtworzyc: raw = adj + px_raw_offset.
    assert (stary["close"] + stary["px_raw_offset"] - stary["px_raw"]).abs().max() == \
        pytest.approx(0.0)


def test_schemat_wyjsciowy_spelnia_kontrakt_loadera():
    from engine.loader import REQUIRED_COLUMNS, validate_schema

    df, _ = build_continuous(_raw_z_rolowaniem(), KALENDARZ)

    validate_schema(df.columns)
    assert set(REQUIRED_COLUMNS) <= set(df.columns)


def test_tryb_strict_przerywa_na_niespojnych_danych():
    zle = bary("MNQZ4", datetime(2024, 12, 10, 15, 0, tzinfo=UTC), 3, cena=100, volume=10)
    zle = zle.with_columns(pl.lit(999.0).alias("low"))

    with pytest.raises(RawDataError, match="walidacji"):
        build_continuous(zle, KALENDARZ)


def test_kalendarz_pusty_zamienia_swieta_w_anomalie():
    """Dowod, ze kalendarz jest potrzebny: bez niego swieto wyglada jak awaria."""
    weekend = [
        datetime(2024, 12, 13, 21, 59, tzinfo=UTC),   # piatek 16:59 ET
        datetime(2024, 12, 15, 23, 1, tzinfo=UTC),    # niedziela 18:01 ET
    ]
    assert classify_gaps(weekend, SessionCalendar())[1] == "expected", (
        "weekend jest oczekiwany nawet bez kalendarza"
    )

    # Ale juz Wielki Piatek w srodku tygodnia — bez kalendarza wyglada jak awaria feedu.
    swieto = [
        datetime(2025, 4, 17, 20, 59, tzinfo=UTC),
        datetime(2025, 4, 18, 15, 0, tzinfo=UTC),
    ]
    assert classify_gaps(swieto, SessionCalendar())[1] == "anomaly"
    assert classify_gaps(swieto, KALENDARZ)[1] == "expected"
