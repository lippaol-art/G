"""Testy sanity-reportu — PLAN.pdf rozdz. 4.6.

Raport jest narzedziem do znajdowania rzeczy, ktorych nie rozumiemy w danych.
Testy sprawdzaja wiec przede wszystkim, czy ZNAJDUJE — raport, ktory na
zepsutych danych milczy, jest gorszy niz brak raportu.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import polars as pl
import pytest

from engine.calendar_cme import build_calendar
from engine.clean import build_continuous
from engine.sanity import (
    build_report,
    ciaglosc_rolowania,
    luki,
    outliery_zakresu,
    pokrycie_zdarzen,
    rozjazd_raw_adj,
    wolumen_zero,
    zgodnosc_z_kalendarzem,
)
from engine.sessions import SessionCalendar

KALENDARZ = build_calendar(2024, 2025)


def czysta_ramka(n_dni: int = 3, *, volume: int = 100) -> pl.DataFrame:
    """Oczyszczona ramka przechodzaca przez prawdziwy pipeline."""
    czesci = []
    dni = [date(2024, 12, 9) + timedelta(days=i) for i in range(n_dni)]
    for i, d in enumerate(dni):
        start = datetime(d.year, d.month, d.day, 15, 0, tzinfo=UTC)   # 10:00 ET
        for symbol, cena, vol in (
            ("MNQZ4", 21000.0, 1000 if i == 0 else 10),
            ("MNQH5", 21025.0, 10 if i == 0 else 1000),
        ):
            czesci.append(pl.DataFrame({
                "ts_event": [start + timedelta(minutes=m) for m in range(30)],
                "symbol": [symbol] * 30,
                "open": [cena + m * 0.25 for m in range(30)],
                "high": [cena + m * 0.25 + 1.0 for m in range(30)],
                "low": [cena + m * 0.25 - 1.0 for m in range(30)],
                "close": [cena + m * 0.25 + 0.25 for m in range(30)],
                "volume": [volume if vol > 100 else vol] * 30,
            }).with_columns(pl.col("ts_event").dt.replace_time_zone("UTC")))
    df, _ = build_continuous(pl.concat(czesci), KALENDARZ)
    return df


def test_raport_sklada_sie_z_kompletu_sekcji():
    raport = build_report(czysta_ramka(), KALENDARZ)
    tytuly = [s.tytul for s in raport.sekcje]

    for wymagana in ("Metadane zbioru", "Klasyfikacja luk", "Bary o zerowym wolumenie",
                     "Ciaglosc serii w dniach rolowan", "Rozdzielenie serii px_raw / px_adj",
                     "Zgodnosc z kalendarzem CME", "Pokrycie kalendarza zdarzen"):
        assert wymagana in tytuly


def test_raport_renderuje_sie_do_markdowna():
    tekst = build_report(czysta_ramka(), KALENDARZ).render()

    assert tekst.startswith("# Raport jakosci danych")
    assert "## Klasyfikacja luk" in tekst
    assert "Do przegladu" in tekst


def test_bary_o_zerowym_wolumenie_sa_zglaszane():
    df = czysta_ramka().with_columns(
        pl.when(pl.int_range(pl.len()) < 3).then(0).otherwise(pl.col("volume")).alias("volume")
    )
    sekcja = wolumen_zero(df)

    assert not sekcja.ok
    assert "forward-fill" in sekcja.do_przegladu[0]


def test_czyste_dane_nie_generuja_falszywego_alarmu_o_wolumenie():
    assert wolumen_zero(czysta_ramka()).ok


def test_outliery_zakresu_z_lista_dat():
    df = czysta_ramka()
    df = df.with_columns(
        pl.when(pl.int_range(pl.len()) == 5)
        .then(pl.col("high") + 500.0).otherwise(pl.col("high")).alias("high")
    )
    sekcja = outliery_zakresu(df)

    assert not sekcja.ok
    assert "zakresie >" in sekcja.do_przegladu[0]


def test_skok_w_dniu_rolowania_jest_zglaszany():
    """Bez back-adjustu seria ma w dniu rolowania skok o spread miedzy kontraktami."""
    df = czysta_ramka()
    # Cofamy adjustment: kazdy kontrakt wraca do swojej ceny surowej.
    bez_korekty = df.with_columns(
        pl.col("px_raw").alias("close"),
        (pl.col("open") + pl.col("px_raw_offset")).alias("open"),
    )
    sekcja = ciaglosc_rolowania(bez_korekty)

    assert not sekcja.ok
    assert "back-adjust nie zadzialal" in sekcja.do_przegladu[0]


def test_poprawna_seria_ciagla_nie_ma_skokow():
    assert ciaglosc_rolowania(czysta_ramka()).ok


def test_plywajacy_offset_jest_zglaszany():
    """Offset px_raw-px_adj musi byc stala w obrebie kontraktu (rozdz. 4.3)."""
    df = czysta_ramka()
    df = df.with_columns(
        pl.when(pl.int_range(pl.len()) == 2)
        .then(pl.col("px_raw") + 7.0).otherwise(pl.col("px_raw")).alias("px_raw")
    )
    sekcja = rozjazd_raw_adj(df)

    assert not sekcja.ok
    assert "nie jest stala" in sekcja.do_przegladu[0]


def test_bary_w_dniu_bez_sesji_sa_zglaszane():
    df = czysta_ramka()
    kalendarz_z_dodatkowym_swietem = SessionCalendar(
        holidays=frozenset({date(2024, 12, 10)}), verified=True
    )
    sekcja = zgodnosc_z_kalendarzem(df, kalendarz_z_dodatkowym_swietem)

    assert not sekcja.ok
    assert any("brak sesji" in p for p in sekcja.do_przegladu)


def test_niezweryfikowany_kalendarz_jest_pozycja_do_przegladu():
    sekcja = zgodnosc_z_kalendarzem(czysta_ramka(), KALENDARZ)

    assert not KALENDARZ.verified
    assert any("nie zostal porownany" in p for p in sekcja.do_przegladu)


def test_brak_kalendarza_zdarzen_jest_pozycja_do_przegladu():
    sekcja = pokrycie_zdarzen(None, date(2024, 1, 1), date(2024, 3, 31))

    assert not sekcja.ok
    assert "rozdz. 4.5" in sekcja.do_przegladu[0]


def test_dziura_w_kalendarzu_zdarzen_jest_wykrywana():
    """Brak CPI w miesiacu nie objawia sie jako blad, tylko jako hipoteza,
    ktora 'nie dziala' akurat w tym miesiacu."""
    events = pl.DataFrame({
        "ts_utc": [datetime(2024, 1, 11, 13, 30, tzinfo=UTC),
                   datetime(2024, 1, 5, 13, 30, tzinfo=UTC),
                   datetime(2024, 2, 2, 13, 30, tzinfo=UTC)],
        "kind": ["macro"] * 3,
        "rank": [1, 1, 1],
        "name": ["CPI", "NFP", "NFP"],
    })
    sekcja = pokrycie_zdarzen(events, date(2024, 1, 1), date(2024, 2, 29))

    assert any("2024-02: brak zdarzenia CPI" in p for p in sekcja.do_przegladu)
    assert not any("2024-01" in p for p in sekcja.do_przegladu)


def test_luki_anomalne_trafiaja_do_przegladu():
    df = czysta_ramka().with_columns(
        pl.when(pl.int_range(pl.len()) == 4)
        .then(pl.lit("anomaly")).otherwise(pl.col("gap_kind")).alias("gap_kind")
    )
    sekcja = luki(df)

    assert not sekcja.ok
    assert "luka bez wyjasnienia" in sekcja.do_przegladu[0]


def test_raport_na_zdrowych_danych_wskazuje_tylko_kroki_reczne():
    """Nawet czyste dane nie dostaja zielonego stempla: weryfikacja krzyzowa
    i potwierdzenie kalendarza sa krokami czlowieka, nie kodu."""
    raport = build_report(czysta_ramka(), KALENDARZ)

    assert not raport.ok
    reczne = [p for p in raport.do_przegladu
              if "weryfikacja krzyzowa" in p or "kalendarz CME nie zostal" in p]
    assert len(reczne) == 2


def test_metadane_bez_wersji_schematu_sa_pozycja_do_przegladu():
    raport = build_report(czysta_ramka(), KALENDARZ)

    assert any("schema_version" in p for p in raport.do_przegladu)

    z_metadanymi = build_report(
        czysta_ramka(), KALENDARZ,
        meta={"schema_version": "GLBX.MDP3 v3", "downloaded": "2026-08-01", "sha256": "abc"},
    )
    assert not any("schema_version" in p for p in z_metadanymi.do_przegladu)


def test_bary_per_segment_licza_kazdy_segment_osobno():
    """Wspolna srednia dobowa zamazalaby i RTH, i sesje azjatycka."""
    raport = build_report(czysta_ramka(), KALENDARZ)
    sekcja = next(s for s in raport.sekcje if s.tytul.startswith("Bary na dzien"))

    assert "segment" in sekcja.tresc
    assert "rth_open" in sekcja.tresc or "midday" in sekcja.tresc


@pytest.mark.needs_data
def test_raport_na_prawdziwych_danych():
    """Odblokuje sie automatycznie, gdy pojawi sie data/clean/mnq_1m_cont.parquet."""
    from engine.calendar_cme import PROJECT_CALENDAR
    from engine.loader import is_available, load_continuous

    if not is_available("mnq"):
        pytest.skip("brak danych — Etap 1 (patrz HANDOFF.md)")

    raport = build_report(load_continuous("mnq"), PROJECT_CALENDAR)
    assert raport.render()
