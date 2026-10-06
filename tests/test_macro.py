"""Testy kalendarza makro — engine/macro.py.

Kazdy przypadek pochodzi z REALNEJ pulapki, ktora wystapila przy budowie
kalendarza. Fixture'y sa fragmentami prawdziwych stron BLS i Fedu, przyciete
do minimum — nie sa danymi rynkowymi, tylko przypadkami brzegowymi parsera.
"""

from __future__ import annotations

from datetime import date, time

from engine.macro import (
    CPI,
    FOMC,
    NFP,
    Zdarzenie,
    okno_rownowagi,
    parsuj_godzine_komunikatu,
    parsuj_harmonogram_bls,
    parsuj_posiedzenia_fomc,
    sesja_reakcji,
)


def _wiersz(data: str, godzina: str, nazwa: str) -> str:
    return (f"<tr><td><p>{data}</p></td><td><p>{godzina}</p></td>"
            f"<td><strong>{nazwa}</strong></td></tr>")


class TestHarmonogramBLS:
    HTML = (
        "<table>"
        + _wiersz("Friday, January 05, 2024", "08:30 AM", "Employment Situation for December 2023")
        + _wiersz("Tuesday, January 11, 2024", "08:30 AM", "Consumer Price Index for December 2023")
        + _wiersz("Wednesday, March 20, 2024", "10:00 AM",
                  "Employment Situation of Veterans for Annual 2023")
        + _wiersz("Thursday, April 11, 2024", "08:30 AM", "Producer Price Index for March 2024")
        + "</table>"
    )

    def test_wyluskuje_publikacje_miesieczne(self):
        z = parsuj_harmonogram_bls(self.HTML, 2024)
        assert {x.typ for x in z} == {NFP, CPI, "PPI"}

    def test_odrzuca_publikacje_roczna_o_podobnej_nazwie(self):
        """REGRESJA. `startswith("Employment Situation")` wpuszczal publikacje
        "Employment Situation OF VETERANS for Annual 2023" — inny raport, inna
        godzina (10:00), inna czestotliwosc. Ta sama klasa bledu co pozycja
        "12.02" zawierajaca "2.02" w engine/earnings.py."""
        z = parsuj_harmonogram_bls(self.HTML, 2024)
        assert all(x.data != date(2024, 3, 20) for x in z)
        assert all(x.planowany_et.hour == 8 for x in z)

    def test_godzina_i_strefa(self):
        z = [x for x in parsuj_harmonogram_bls(self.HTML, 2024) if x.typ == CPI][0]
        assert (z.planowany_et.hour, z.planowany_et.minute) == (8, 30)
        assert z.planowany_et.tzinfo is not None
        assert z.planowany_et.utcoffset() is not None

    def test_ignoruje_inny_rok(self):
        assert parsuj_harmonogram_bls(self.HTML, 2023) == []

    def test_okres_referencyjny(self):
        z = [x for x in parsuj_harmonogram_bls(self.HTML, 2024) if x.typ == NFP][0]
        assert z.okres == "December 2023"


class TestPosiedzeniaFOMC:
    HIST = (
        '<h5 class="panel-heading">January 28-29 Meeting - 2020</h5>'
        '<p><a href="/newsevents/pressreleases/monetary20200129a.htm">Statement</a></p>'
        '<h5 class="panel-heading">March 2 (unscheduled) Meeting - 2020</h5>'
        '<p><a href="/newsevents/pressreleases/monetary20200303a.htm">Statement</a></p>'
        '<h5 class="panel-heading">March 17-18 (cancelled) Meeting - 2020</h5>'
        '<h5 class="panel-heading">March 23 (notation vote) - 2020</h5>'
        '<p><a href="/newsevents/pressreleases/monetary20200323a.htm">Statement</a></p>'
        '<h5 class="panel-heading">April 28-29 Meeting - 2020</h5>'
        '<p><a href="/newsevents/pressreleases/monetary20200429a.htm">Statement</a></p>'
    )
    BIEZ = (
        '<div class="fomc-meeting__month"><strong>January</strong></div>'
        '<div class="fomc-meeting__date">27-28</div>'
        '<a href="/newsevents/pressreleases/monetary20260128a.htm">HTML</a>'
        '<div class="fomc-meeting__month"><strong>August 22 (notation vote)</strong></div>'
        '<div class="fomc-meeting__date">22</div>'
        '<a href="/newsevents/pressreleases/monetary20250822a.htm">HTML</a>'
        '<div class="fomc-meeting__month"><strong>March</strong></div>'
        '<div class="fomc-meeting__date">17-18</div>'
        '<a href="/newsevents/pressreleases/monetary20260318a.htm">HTML</a>'
    )

    def test_uklad_historyczny_bierze_tylko_planowe(self):
        d = parsuj_posiedzenia_fomc(self.HIST)
        assert d == {date(2020, 1, 29), date(2020, 4, 29)}

    def test_odrzuca_nadzwyczajne_mimo_konferencji(self):
        """Marcowe ciecia awaryjne 2020 MIALY konferencje prasowa, wiec
        klasyfikacja po jej obecnosci dawalaby zly wynik. Rozroznienie musi
        pochodzic z etykiety Fedu."""
        assert date(2020, 3, 3) not in parsuj_posiedzenia_fomc(self.HIST)

    def test_odrzuca_odwolane_i_glosowania_obiegowe(self):
        d = parsuj_posiedzenia_fomc(self.HIST)
        assert date(2020, 3, 23) not in d

    def test_uklad_biezacy(self):
        d = parsuj_posiedzenia_fomc(self.BIEZ)
        assert date(2026, 1, 28) in d
        assert date(2026, 3, 18) in d

    def test_uklad_biezacy_odrzuca_glosowanie_obiegowe(self):
        """REGRESJA. Wiersz "August 22 (notation vote)" ma w ukladzie biezacym
        te sama strukture co posiedzenie i wchodzil do proby jako posiedzenie
        sierpniowe, ktorego nie ma."""
        assert date(2025, 8, 22) not in parsuj_posiedzenia_fomc(self.BIEZ)

    def test_data_pochodzi_z_odnosnika_nie_z_nazwy_miesiaca(self):
        """Posiedzenia na przelomie miesiecy ("April 30-May 1") lamaly parsowanie
        nazw. Odnosnik do komunikatu zawiera pelna date i nie ma tego problemu."""
        h = ('<h5 class="panel-heading">April 30-May 1 Meeting - 2019</h5>'
             '<a href="/newsevents/pressreleases/monetary20190501a.htm">Statement</a>')
        assert parsuj_posiedzenia_fomc(h) == {date(2019, 5, 1)}


class TestGodzinaKomunikatu:
    def test_popoludniowa(self):
        assert parsuj_godzine_komunikatu(
            "<p>For release at 2:00 p.m. EDT</p>") == time(14, 0)

    def test_bez_kropek(self):
        assert parsuj_godzine_komunikatu("For release at 2:00 pm EST") == time(14, 0)

    def test_brak_frazy_daje_none(self):
        """Godzina jest podstawa calego pomiaru karty — zgadywanie jej byloby
        najgorszym skrotem, wiec brak musi byc jawny."""
        assert parsuj_godzine_komunikatu("<p>Nic tu nie ma</p>") is None

    def test_polnoc_i_poludnie(self):
        assert parsuj_godzine_komunikatu("For release at 12:00 p.m.") == time(12, 0)
        assert parsuj_godzine_komunikatu("For release at 12:30 a.m.") == time(0, 30)


class TestSesjaReakcji:
    SESJE = frozenset({date(2024, 4, 10), date(2024, 4, 11), date(2024, 4, 12)})

    def test_publikacja_w_dzien_sesyjny_reaguje_tego_samego_dnia(self):
        assert sesja_reakcji(date(2024, 4, 11), self.SESJE) == date(2024, 4, 11)

    def test_publikacja_w_dzien_bez_sesji_daje_none(self):
        """NFP wychodzi czasem w Wielki Piatek, gdy rynek jest zamkniety."""
        assert sesja_reakcji(date(2024, 3, 29), self.SESJE) is None


class TestOknoRownowagi:
    def test_szerokosc_i_koniec(self):
        z = Zdarzenie(typ=FOMC, planowany_et=None, data=date(2024, 5, 1),  # type: ignore[arg-type]
                      zrodlo="test")
        assert z.typ == FOMC
        from datetime import datetime

        from engine.macro import ET
        t = datetime(2024, 5, 1, 14, 0, tzinfo=ET)
        a, b = okno_rownowagi(t, 60)
        assert b == t
        assert (b - a).total_seconds() == 3600
