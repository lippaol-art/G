"""Sklejanie tickerow i korekta splitow — PLAN.pdf rozdz. 4.7.

Testy budowane wokol JEDNEGO pytania: czy da sie odroznic split od krachu?

Odpowiedz nie jest oczywista, bo oba wygladaja identycznie w cenie. Meta spadla
3 lutego 2022 o 26% po wynikach — a 26% to prawie dokladnie split 4:3. Reguła
oparta na samej wielkosci ruchu "poprawilaby" ten krach, kasujac zdarzenie,
ktore dla karty H013 jest najciekawszym punktem danych w calej historii.

Fixture'y sa recznie skonstruowane. Zasada "zero danych syntetycznych" dotyczy
wnioskow o rynku; zaden wniosek o rynku z tego pliku nie wynika.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

from engine.equities import (
    POPRZEDNIE_TICKERY,
    data_zmiany_tickera,
    dopasuj_wspolczynnik,
    nalezy_do_szeregu,
    scal_tickery,
    skoryguj_ceny,
    wykryj_splity,
)

D0 = date(2022, 1, 3)


def dni(n: int) -> list[date]:
    return [D0 + timedelta(days=i) for i in range(n)]


def szereg(n: int = 40, cena: float = 100.0, wol: float = 1e6):
    return np.full(n, cena), np.full(n, wol)


def wstaw_split(close, volume, i: int, k: float):
    """Split k:1 w dniu i — cena spada k razy, wolumen rosnie k razy."""
    close = close.copy()
    volume = volume.copy()
    close[i:] /= k
    volume[i:] *= k
    return close, volume


class TestDopasowaniaWspolczynnika:
    def test_typowe_splity_sa_rozpoznawane(self):
        for k in (2.0, 3.0, 4.0, 5.0, 10.0, 20.0):
            assert dopasuj_wspolczynnik(k) == pytest.approx(k)

    def test_split_odwrotny_tez(self):
        """Reverse split podnosi cene — wystepuje u spolek po duzych spadkach."""
        assert dopasuj_wspolczynnik(1 / 10) == pytest.approx(0.1)

    def test_maly_szum_wokol_wspolczynnika_jest_tolerowany(self):
        """Cena zamkniecia nie dzieli sie idealnie — tolerancja musi na to pozwalac."""
        assert dopasuj_wspolczynnik(3.98) == pytest.approx(4.0)
        assert dopasuj_wspolczynnik(20.4) == pytest.approx(20.0)

    def test_wartosc_daleka_od_kazdego_wspolczynnika_jest_odrzucana(self):
        """Sama cena wystarcza tylko wtedy, gdy stosunek jest DALEKO od kazdego k."""
        assert dopasuj_wspolczynnik(1.22) is None    # -18%, 39% od najblizszego (2.0)
        assert dopasuj_wspolczynnik(1.36) is None    # krach META, 32% od 2.0
        assert dopasuj_wspolczynnik(12.0) is None    # miedzy 10 a 15, 20% od obu

    def test_sama_cena_NIE_wystarcza_blisko_wspolczynnika(self):
        """Sedno projektu detektora, ujete jako test.

        Stosunek 2.6 lezy 13% od 3.0, czyli w tolerancji — sama cena nie ma
        podstaw go odrzucic. Dopiero wolumen rozstrzyga: przy prawdziwym splicie
        3:1 obrot rosnie okolo trzykrotnie, przy krachu zachowuje sie inaczej.

        Ten test pilnuje, zeby nikt nie "uproscil" detektora do samej ceny.
        """
        assert dopasuj_wspolczynnik(2.6) is not None, \
            "przy tolerancji 15% cena sama nie rozstrzyga — i tak ma byc"
        assert dopasuj_wspolczynnik(2.6, 2.9) is not None, "obrot x2.9 potwierdza split 3:1"
        assert dopasuj_wspolczynnik(2.6, 1.1) is None, "obrot bez zmian wyklucza split"
        assert dopasuj_wspolczynnik(2.6, 9.0) is None, "obrot x9 przy cenie x2.6 to nie split"


class TestNaZmierzonychZdarzeniach:
    """REGRESJA NA REALNYCH DANYCH — wszystkie liczby zmierzone w naszym zbiorze.

    Detektor przeszedl testy na fixture'ach, a mimo to przeoczyl trzy z osmiu
    prawdziwych splitow przy pierwszym uruchomieniu na realnych danych. Powod:
    fixture'y zakladaly, ze w dniu splitu cena nie robi nic innego, a TSLA
    urosla wtedy o 12.6%.

    Te przypadki sa wiec czyms wiecej niz testem jednostkowym — sa pamiecia
    o tym, czego reczna konstrukcja danych nie przewidziala.

    Uwaga metodologiczna: to jest strojenie DETEKTORA CZYSZCZACEGO wzgledem
    znanej prawdy (opublikowane splity), a nie strojenie strategii wzgledem
    zwrotow. Nie zuzywa licznika prob i nie podlega bramce DSR.
    """

    SPLITY = [
        ("AAPL 2020-08-31, split 4:1", 3.871, 4.44, 4.0),
        ("TSLA 2020-08-31, split 5:1", 4.441, 5.49, 5.0),
        ("NVDA 2021-07-20, split 4:1", 4.038, 2.32, 4.0),
        ("AMZN 2022-06-06, split 20:1", 19.600, 13.04, 20.0),
        ("GOOGL 2022-07-18, split 20:1", 20.514, 18.91, 20.0),
        ("TSLA 2022-08-25, split 3:1", 3.010, 2.38, 3.0),
        ("SOXX 2024-03-07, split 3:1", 2.900, 2.94, 3.0),
        ("NVDA 2024-06-10, split 10:1", 9.935, 5.62, 10.0),
    ]

    NIE_SPLITY = [
        ("META 2022-02-03, -26% po wynikach", 1.358, 4.08),
        ("META 2022-10-27, -25% po wynikach", 1.326, 2.76),
        ("AVGO 2020-03-16, krach covidowy", 1.249, 1.41),
        ("TSLA 2020-09-08, -21% po wykluczeniu z S&P", 1.267, 0.72),
        ("hipotetyczny krach -50% z wybuchem obrotu", 2.000, 4.50),
    ]

    @pytest.mark.parametrize("opis,cena,wolumen,oczekiwany", SPLITY)
    def test_prawdziwy_split_jest_wykryty(self, opis, cena, wolumen, oczekiwany):
        got = dopasuj_wspolczynnik(cena, wolumen)
        assert got == pytest.approx(oczekiwany), (
            f"{opis}: wykryto {got}, oczekiwano {oczekiwany}. "
            "Przeoczony split zostawia w szeregu skok rzedu -75%."
        )

    @pytest.mark.parametrize("opis,cena,wolumen", NIE_SPLITY)
    def test_ruch_rynku_nie_jest_brany_za_split(self, opis, cena, wolumen):
        got = dopasuj_wspolczynnik(cena, wolumen)
        assert got is None, (
            f"{opis}: zaklasyfikowane jako split {got}. "
            "Korekta skasowalaby prawdziwe zdarzenie rynkowe — dla H013 "
            "wlasnie te zdarzenia sa przedmiotem badania."
        )

    def test_wolumen_rozstrzyga_gdy_cena_nie_rozstrzyga(self):
        """TSLA 2020-08-31: cena x4.441 pasuje i do 4 (blad 11.0%), i do 5
        (blad 11.2%). Sama cena wskazalaby 4. Wolumen x5.49 daje iloraz 1.10
        przy k=5 wobec 1.37 przy k=4 — i to on decyduje."""
        assert dopasuj_wspolczynnik(4.441) == pytest.approx(4.0), \
            "bez wolumenu cena faktycznie wskazuje 4"
        assert dopasuj_wspolczynnik(4.441, 5.49) == pytest.approx(5.0), \
            "z wolumenem musi wyjsc 5"


class TestOdrozniniaSplituOdKrachu:
    """Rdzen modulu. Bez tego rozroznienia korekta niszczy dane."""

    def test_split_jest_wykryty(self):
        c, v = szereg()
        c, v = wstaw_split(c, v, 20, 4.0)
        rep = wykryj_splity(dni(40), c, v, symbol="TEST")
        assert len(rep.przyjete) == 1
        assert rep.przyjete[0].wspolczynnik == pytest.approx(4.0)

    def test_krach_o_wielkosci_splitu_NIE_jest_wykryty(self):
        """Spadek 26% trafia niemal dokladnie we wspolczynnik 4/3.

        Odroznia go WYLACZNIE wolumen: przy krachu liczba akcji w obrocie nie
        rosnie proporcjonalnie do spadku ceny, przy splicie rosnie z definicji.
        """
        c, v = szereg()
        c[20:] *= 0.74                    # -26%, jak META 03.02.2022
        v[20:23] *= 1.3                   # obrot rosnie, ale nie 1.35x trwale
        rep = wykryj_splity(dni(40), c, v, symbol="META")
        assert not rep.przyjete, (
            f"krach zaklasyfikowany jako split: {rep.przyjete}. "
            "Korekta skasowalaby prawdziwe zdarzenie rynkowe."
        )
        assert len(rep.odrzucone) == 1
        # Odrzucic moze go KTORYKOLWIEK z dwoch niezaleznych warunkow. Po
        # usunieciu ulamkow ponizej 1.5 wystarcza sam warunek cenowy — wolumen
        # jest wtedy druga linia obrony, nie jedyna. Test nie przywiazuje sie
        # do tego, ktora zadziala, bo obie sa poprawne.
        powod = rep.odrzucone[0].powod
        assert ("nie odpowiada" in powod) or ("wolumen" in powod), powod

    def test_krach_o_nietypowej_wielkosci_odrzucony_juz_na_cenie(self):
        c, v = szereg()
        c[20:] *= 0.62                    # -38%, nie odpowiada zadnemu splitowi
        v[20:] *= 3.0                     # nawet przy duzym wzroscie obrotu
        rep = wykryj_splity(dni(40), c, v, symbol="TEST")
        assert not rep.przyjete
        assert "nie odpowiada" in rep.odrzucone[0].powod

    def test_zwykla_zmiennosc_nie_generuje_kandydatow(self):
        rng = np.random.default_rng(7)
        c = 100 * np.exp(np.cumsum(rng.normal(0, 0.015, 200)))
        v = np.full(200, 1e6)
        rep = wykryj_splity(dni(200), c, v, symbol="TEST")
        assert not rep.kandydaci, f"falszywe alarmy na zwyklej zmiennosci: {rep.kandydaci}"


class TestKorekty:
    def test_korekta_usuwa_skok_ze_zwrotow(self):
        """Po korekcie dzienne zwroty nie moga zawierac sladu splitu —
        to jest caly cel operacji."""
        c, v = szereg(40, 400.0)
        c, v = wstaw_split(c, v, 20, 4.0)
        c_adj, _, rep = skoryguj_ceny(dni(40), c, v, symbol="TEST")
        zwroty = np.diff(np.log(c_adj))
        assert len(rep.przyjete) == 1
        assert np.abs(zwroty).max() < 1e-9, \
            f"po korekcie zostal skok {np.abs(zwroty).max():.4f}"

    def test_korekta_jest_multiplikatywna_nie_roznicowa(self):
        """Przy futures przesuwamy o staly spread, przy akcjach DZIELIMY.
        Pomylenie tych dwoch daje ceny ujemne albo bezsensowne stosunki."""
        c, v = szereg(40, 400.0)
        c, v = wstaw_split(c, v, 20, 4.0)
        c_adj, _, _ = skoryguj_ceny(dni(40), c, v, symbol="TEST")
        assert c_adj[0] == pytest.approx(c_adj[-1]), \
            "cena przed i po splicie musi byc ta sama po korekcie"
        assert (c_adj > 0).all()

    def test_wolumen_korygowany_w_przeciwna_strone_niz_cena(self):
        c, v = szereg(40, 400.0, 1e6)
        c, v = wstaw_split(c, v, 20, 4.0)
        _, v_adj, _ = skoryguj_ceny(dni(40), c, v, symbol="TEST")
        assert v_adj[0] == pytest.approx(v_adj[-1]), \
            "historyczny wolumen musi byc przeliczony na dzisiejsze akcje"

    def test_dwa_splity_skladaja_sie_multiplikatywnie(self):
        """NVDA miala 4:1 w 2021 i 10:1 w 2024 — historia sprzed obu musi byc
        podzielona przez 40, nie przez 14."""
        c, v = szereg(60, 4000.0)
        c, v = wstaw_split(c, v, 20, 4.0)
        c, v = wstaw_split(c, v, 40, 10.0)
        c_adj, _, rep = skoryguj_ceny(dni(60), c, v, symbol="NVDA")
        assert len(rep.przyjete) == 2
        assert c_adj[0] == pytest.approx(c_adj[-1], rel=1e-9)

    def test_brak_splitu_nie_zmienia_niczego(self):
        c, v = szereg(40, 100.0)
        c_adj, v_adj, rep = skoryguj_ceny(dni(40), c, v, symbol="TEST")
        assert not rep.kandydaci
        assert np.allclose(c_adj, c) and np.allclose(v_adj, v)


class TestSklejaniaTickerow:
    def test_meta_ma_poprzednika(self):
        assert scal_tickery("META") == ["FB", "META"]
        assert data_zmiany_tickera("META") == date(2022, 6, 9)

    def test_spolka_bez_zmiany_nazwy(self):
        assert scal_tickery("AAPL") == ["AAPL"]
        assert data_zmiany_tickera("AAPL") is None

    def test_mapa_poprzednikow_ma_spojne_wpisy(self):
        for nowy, (stary, kiedy) in POPRZEDNIE_TICKERY.items():
            assert nowy != stary
            assert isinstance(kiedy, date)


class TestOchronyZdarzenEarningsowych:
    """H013 bada reakcje indeksu na wyniki megacapow. Detektor splitow, ktory
    kasuje te reakcje, niszczy przedmiot badania — i robi to niewidocznie.

    Te testy pilnuja granicy, ktora latwo przesunac przy "ulepszaniu" detektora.
    """

    @pytest.mark.parametrize("spadek,opis", [
        (0.74, "META -26% po wynikach, 03.02.2022 (blisko splitu 4:3)"),
        (0.80, "-20% po wynikach (blisko splitu 5:4)"),
        (0.65, "-35% po wynikach (blisko splitu 3:2)"),
        (0.72, "-28% po wynikach"),
    ])
    def test_reakcja_na_wyniki_nie_jest_brana_za_split(self, spadek, opis):
        c, v = szereg(40, 300.0)
        c[20:] *= spadek
        v[18:24] *= 2.5          # obrot po wynikach rosnie SILNIE, ale przejsciowo
        rep = wykryj_splity(dni(40), c, v, symbol="MEGA")
        assert not rep.przyjete, f"{opis}: zaklasyfikowane jako split — {rep.przyjete}"

    def test_lista_wspolczynnikow_nie_siega_w_zakres_krachow(self):
        """Straznik na przyszlosc: dopisanie 5/4 albo 4/3 do listy przywraca
        dokladnie ten blad, ktory ten modul ma nie popelniac."""
        from engine.equities import DOPUSZCZALNE_WSPOLCZYNNIKI
        assert min(DOPUSZCZALNE_WSPOLCZYNNIKI) >= 1.5, (
            "wspolczynnik ponizej 1.5 odpowiada spadkowi ceny < 33%, czyli "
            "typowej reakcji megacapa na wyniki — patrz komentarz w equities.py"
        )

    def test_prawdziwy_split_2_1_nadal_przechodzi(self):
        """Kontrola przeciwna: zaostrzenie nie moze zepsuc wykrywania splitow."""
        c, v = szereg(40, 300.0)
        c, v = wstaw_split(c, v, 20, 2.0)
        rep = wykryj_splity(dni(40), c, v, symbol="TEST")
        assert len(rep.przyjete) == 1
        assert rep.przyjete[0].wspolczynnik == pytest.approx(2.0)


class TestOdcieciaPoDacie:
    """Ticker jest nazwa, nie tozsamoscia — i gielda go przetwarza.

    Po tym, jak Meta porzucila "FB" w czerwcu 2022, symbol zostal z czasem
    przypisany innej spolce. Widac to w naszych danych: 84 tys. rekordow za 2022
    (do 8 czerwca), zero za 2023-2024 i ponownie kilkaset za 2025-2026.

    Sklejenie po samej nazwie wstawiloby obcy papier w srodek historii Mety —
    bez wyjatku, bez sladu, za to z sygnalem wygladajacym na prawdziwy.
    """

    def test_poprzednik_liczy_sie_tylko_przed_zmiana(self):
        assert nalezy_do_szeregu("META", "FB", date(2022, 6, 8)) is True
        assert nalezy_do_szeregu("META", "FB", date(2019, 1, 2)) is True

    def test_poprzednik_PO_zmianie_jest_odrzucany(self):
        """Rdzen zabezpieczenia: to sa rekordy INNEJ spolki."""
        assert nalezy_do_szeregu("META", "FB", date(2022, 6, 9)) is False
        assert nalezy_do_szeregu("META", "FB", date(2025, 6, 26)) is False
        assert nalezy_do_szeregu("META", "FB", date(2026, 7, 29)) is False

    def test_nazwa_aktualna_liczy_sie_dopiero_od_zmiany(self):
        assert nalezy_do_szeregu("META", "META", date(2022, 6, 9)) is True
        assert nalezy_do_szeregu("META", "META", date(2026, 1, 5)) is True
        assert nalezy_do_szeregu("META", "META", date(2022, 6, 8)) is False

    def test_szereg_jest_ciagly_i_bez_zakladek(self):
        """Kazdy dzien nalezy do DOKLADNIE jednego zrodla — bez dziur i bez
        podwojnego liczenia spolki w sumie wazonej."""
        for d in (date(2019, 5, 6), date(2022, 6, 8), date(2022, 6, 9), date(2026, 7, 29)):
            zrodla = sum(nalezy_do_szeregu("META", s, d) for s in ("FB", "META"))
            assert zrodla == 1, f"{d}: {zrodla} zrodel zamiast jednego"

    def test_spolka_bez_zmiany_nazwy_dziala_normalnie(self):
        assert nalezy_do_szeregu("AAPL", "AAPL", date(2019, 5, 6)) is True
        assert nalezy_do_szeregu("AAPL", "FB", date(2019, 5, 6)) is False
