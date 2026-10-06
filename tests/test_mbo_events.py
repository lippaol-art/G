"""Rekonstrukcja akcji agresywnych — przypadki budowane recznie.

Fixture'y testowe, nie dane rynkowe. Rozroznienie obowiazujace w calym
projekcie: zaden wniosek o rynku nie powstaje z danych innych niz realne, ale
bez recznie skonstruowanych rekordow nie da sie udowodnic poprawnosci regul
brzegowych — one wystepuja w danych rzadko i nie da sie ich wywolac na zadanie.

Kazdy przypadek odpowiada jednej regule z `docs/D5_ETAP4_SPEC.md` §1.
"""

from __future__ import annotations

from engine.mbo_events import F_LAST, AkcjaAgresywna, RekordMBO, rekonstruuj

MIN = 60_000_000_000        # nanosekundy w minucie


def r(action: str, side: str = "B", *, px: int = 100, sz: int = 1,
      oid: int = 1, ts: int = 0, last: bool = False) -> RekordMBO:
    return RekordMBO(ts_recv=ts, action=action, side=side, price=px, size=sz,
                     order_id=oid, flags=F_LAST if last else 0)


def akcje(*rek: RekordMBO) -> list[AkcjaAgresywna]:
    return list(rekonstruuj(rek))


class TestJedenTradeWieleFill:
    """Przypadek podstawowy: jeden agresor zdejmuje kilka zlecen pasywnych."""

    def test_fill_przypisane_do_poprzedzajacego_trade(self):
        a = akcje(
            r("T", "B", sz=3, oid=10),
            r("F", "A", sz=1, oid=20),
            r("F", "A", sz=1, oid=21),
            r("F", "A", sz=1, oid=22, last=True),
        )
        assert len(a) == 1
        assert a[0].order_id == 10
        assert a[0].side == "B"
        assert a[0].n_trade == 1
        assert a[0].rozmiar == 3
        assert a[0].n_pasywnych == 3
        assert a[0].rozmiar_pasywnych == 3

    def test_niezmiennik_sumy_pasywnych(self):
        a = akcje(r("T", "B", sz=2, oid=10), r("F", "A", sz=2, oid=20, last=True))
        assert a[0].rozmiar_pasywnych == a[0].rozmiar


class TestSweepWielopoziomowy:
    """Regula 2: kolejne Trade tego samego agresora lacza sie w jedna akcje."""

    def test_trzy_poziomy_to_jedna_akcja(self):
        a = akcje(
            r("T", "B", px=100, sz=1, oid=10),
            r("F", "A", sz=1, oid=20),
            r("T", "B", px=101, sz=2, oid=10),
            r("F", "A", sz=2, oid=21),
            r("T", "B", px=102, sz=3, oid=10),
            r("F", "A", sz=3, oid=22, last=True),
        )
        assert len(a) == 1, "sweep jednego agresora to JEDNA akcja"
        assert a[0].n_trade == 3
        assert a[0].rozmiar == 6
        assert a[0].poziomy == 3
        assert a[0].rozmiar_pasywnych == 6

    def test_ten_sam_poziom_nie_zwieksza_licznika_poziomow(self):
        a = akcje(
            r("T", "B", px=100, oid=10),
            r("T", "B", px=100, oid=10, last=True),
        )
        assert a[0].n_trade == 2
        assert a[0].poziomy == 1

    def test_zmiana_strony_przerywa_sweep(self):
        """Ten sam `order_id`, ale inna strona — to nie moze byc ten sam sweep."""
        a = akcje(
            r("T", "B", oid=10),
            r("T", "A", oid=10, last=True),
        )
        assert len(a) == 2


class TestDwochAgresorowWKopercie:
    """2,4% kopert w realnych danych zawiera wiecej niz jednego agresora."""

    def test_dwie_osobne_akcje(self):
        a = akcje(
            r("T", "B", sz=1, oid=10),
            r("F", "A", sz=1, oid=20),
            r("T", "A", sz=1, oid=30),
            r("F", "B", sz=1, oid=31, last=True),
        )
        assert len(a) == 2
        assert [x.order_id for x in a] == [10, 30]
        assert [x.side for x in a] == ["B", "A"]

    def test_kazda_akcja_ma_swoje_pasywne(self):
        a = akcje(
            r("T", "B", sz=2, oid=10),
            r("F", "A", sz=2, oid=20),
            r("T", "A", sz=5, oid=30),
            r("F", "B", sz=5, oid=31, last=True),
        )
        assert a[0].rozmiar_pasywnych == 2
        assert a[1].rozmiar_pasywnych == 5


class TestZmianaRoliOrderId:
    """Ustalenie z D5-C: zlecenie agresujace w jednej transakcji potrafi byc
    strona PASYWNA w drugiej, w tej samej kopercie. To wlasnie na tym poleglo
    osiem zdarzen przy pierwszym liczeniu mianownika."""

    def test_agresor_staje_sie_pasywny(self):
        a = akcje(
            r("T", "B", sz=1, oid=70),      # 70 agresuje
            r("F", "A", sz=1, oid=64),
            r("T", "A", sz=1, oid=31),      # inny agresor
            r("F", "B", sz=1, oid=70, last=True),   # 70 jest tu PASYWNE
        )
        assert len(a) == 2
        assert a[0].order_id == 70
        assert a[0].n_pasywnych == 1 and a[0].n_wlasnych == 0
        # w drugiej akcji `70` MUSI liczyc sie jako pasywne
        assert a[1].order_id == 31
        assert a[1].n_pasywnych == 1
        assert a[1].rozmiar_pasywnych == 1
        assert a[1].rozmiar_pasywnych == a[1].rozmiar

    def test_wlasny_fill_agresora_nie_jest_pasywny(self):
        """W 0,87% zdarzen `Fill` dostaje takze zlecenie agresora."""
        a = akcje(
            r("T", "A", sz=1, oid=628),
            r("F", "A", sz=1, oid=628),     # wlasny fill agresora
            r("F", "B", sz=1, oid=923, last=True),
        )
        assert len(a) == 1
        assert a[0].n_wlasnych == 1
        assert a[0].n_pasywnych == 1
        assert a[0].rozmiar_pasywnych == a[0].rozmiar == 1


class TestPowrotAgresora:
    """Regula 3: ten sam `order_id` po innym agresorze to NOWA akcja."""

    def test_powrot_po_innym_agresorze_nie_jest_scalany(self):
        a = akcje(
            r("T", "B", sz=1, oid=10),
            r("T", "B", sz=1, oid=99),      # inny agresor przerywa
            r("T", "B", sz=1, oid=10, last=True),   # 10 wraca
        )
        assert len(a) == 3, "powrot po przerwie to nowa akcja, nie kontynuacja"
        assert [x.order_id for x in a] == [10, 99, 10]

    def test_bez_przerwy_scalone(self):
        a = akcje(
            r("T", "B", sz=1, oid=10),
            r("T", "B", sz=1, oid=10, last=True),
        )
        assert len(a) == 1
        assert a[0].n_trade == 2


class TestGranicaMinuty:
    """§2.1: akcja trafia w CALOSCI do minuty ostatniego `ts_recv`."""

    def test_akcja_przecinajaca_minute_nie_jest_dzielona(self):
        a = akcje(
            r("T", "B", sz=1, oid=10, ts=MIN - 1),      # koniec minuty 0
            r("F", "A", sz=1, oid=20, ts=MIN + 5),      # juz minuta 1
            r("T", "B", sz=1, oid=10, ts=MIN + 9, last=True),
        )
        assert len(a) == 1, "akcja nigdy nie jest dzielona miedzy okna"
        assert a[0].ts_recv_pierwszy == MIN - 1
        assert a[0].ts_recv_ostatni == MIN + 9
        assert a[0].minuta == 1, "decyduje OSTATNI rekord, nie pierwszy"

    def test_akcja_w_jednej_minucie(self):
        a = akcje(r("T", "B", oid=10, ts=5), r("F", "A", oid=20, ts=9, last=True))
        assert a[0].minuta == 0

    def test_fill_przesuwa_znacznik_konca(self):
        a = akcje(
            r("T", "B", oid=10, ts=MIN - 10),
            r("F", "A", oid=20, ts=MIN + 1, last=True),
        )
        assert a[0].minuta == 1


class TestKopertaFLast:
    """Akcja nie przekracza granicy koperty, nawet przy tym samym agresorze."""

    def test_flast_zamyka_akcje(self):
        a = akcje(
            r("T", "B", sz=1, oid=10, last=True),
            r("T", "B", sz=1, oid=10, last=True),
        )
        assert len(a) == 2, "ten sam agresor w dwoch kopertach to dwie akcje"
        assert a[0].koperta == 0 and a[1].koperta == 1

    def test_flast_po_wielu_trade(self):
        a = akcje(
            r("T", "B", sz=1, oid=10),
            r("T", "A", sz=1, oid=20),
            r("T", "B", sz=1, oid=30, last=True),
        )
        assert len(a) == 3
        assert {x.koperta for x in a} == {0}

    def test_ogon_bez_flast_nie_ginie(self):
        a = akcje(r("T", "B", sz=1, oid=10))
        assert len(a) == 1


class TestRekordyNone:
    """Rekordy `action=N` — dokladna GRANICA odpornosci tego modulu.

    Mikro-diff z 09.08 (`docs/D5_DRYF_METADANYCH.md` §3b) pokazal, ze dostawca
    serwuje dzis 18 152 rekordow `action=N` w 30 minutach sesji, ktorych nasze
    starsze pliki nie maja: `order_id=0`, `side=N`, `size=0`, `price` rowne
    UNDEF_PRICE. Zero tresci ekonomicznej.

    Pomiar `--flagi` z 09.08 odpowiedzial na pytanie o flagi: **wszystkie
    18 152 rekordow `N` niesie `F_LAST`** — ale laczna liczba kopert jest po
    obu stronach IDENTYCZNA (698 358). Nadwyzka `F_LAST` po naszej stronie
    rozklada sie na A (+7 506), C (+8 337) i M (+2 309), co sumuje sie dokladnie
    do 18 152. Bit nie zostal DODANY, tylko PRZENIESIONY: koperte zamyka teraz
    osobny rekord `N` na koncu zamiast ostatniego rekordu realnego.

    Ponizsze testy rozdzielaja dwa scenariusze, ktore latwo pomylic, a maja
    przeciwne skutki:

      * granica PRZENIESIONA na koncowy `N` — akcje bez zmian,
      * granica WSTAWIONA w srodek ciagu — akcje sie rozpadaja.

    Dane mowia, ze zaszedl pierwszy. Drugi jest tu po to, zeby bylo widac,
    ze test umie wykryc roznice, gdyby zaszedl.
    """

    #: Wypelniacz dokladnie taki, jak w probce od dostawcy.
    @staticmethod
    def pusty(ts: int = 0, last: bool = False) -> RekordMBO:
        return RekordMBO(ts_recv=ts, action="N", side="N",
                         price=9223372036854775807, size=0, order_id=0,
                         flags=F_LAST if last else 0)

    def test_bez_flag_nie_zmieniaja_niczego(self):
        """Wstawione miedzy KAZDA pare rekordow — wynik bit w bit ten sam."""
        rek = [
            r("T", "B", sz=3, oid=10),
            r("F", "A", sz=1, oid=20),
            r("T", "A", sz=2, oid=30),
            r("F", "B", sz=2, oid=40, last=True),
        ]
        zasmiecone: list[RekordMBO] = []
        for x in rek:
            zasmiecone += [self.pusty(), x]
        zasmiecone.append(self.pusty())

        assert [vars(x) for x in rekonstruuj(zasmiecone)] == [
            vars(x) for x in rekonstruuj(rek)]

    def test_granica_przeniesiona_na_koncowy_n_nie_zmienia_akcji(self):
        """SCENARIUSZ ZMIERZONY — `F_LAST` zdjety z ostatniego rekordu realnego
        i przeniesiony na dolozony za nim rekord `N`.

        To jest dokladnie to, co pokazal pomiar `--flagi`, i to jest powod,
        dla ktorego audyt D5-C nie wymaga powtorzenia: koperta zamyka sie
        w tym samym miejscu STRUMIENIA, tylko innym rekordem.
        """
        po_staremu = akcje(
            r("T", "B", sz=1, oid=10),
            r("T", "B", sz=1, oid=10),
            r("F", "A", sz=2, oid=20, last=True),
        )
        po_nowemu = akcje(
            r("T", "B", sz=1, oid=10),
            r("T", "B", sz=1, oid=10),
            r("F", "A", sz=2, oid=20),          # juz BEZ F_LAST
            self.pusty(last=True),              # koperte zamyka wypelniacz
        )
        assert [vars(x) for x in po_staremu] == [vars(x) for x in po_nowemu]

    def test_granica_wstawiona_w_srodek_ciagu_rozbija_akcje(self):
        """SCENARIUSZ KONTROLNY — gdyby `N` z `F_LAST` trafil w srodek ciagu.

        Nie zaszedl, ale bez tego testu poprzedni niczego by nie dowodzil:
        pokazywalby tylko, ze porownanie jest slepe na wszystko.
        """
        bez = akcje(
            r("T", "B", sz=1, oid=10),
            r("T", "B", sz=1, oid=10, last=True),
        )
        z_flaga = akcje(
            r("T", "B", sz=1, oid=10),
            self.pusty(last=True),
            r("T", "B", sz=1, oid=10, last=True),
        )
        assert len(bez) == 1 and bez[0].n_trade == 2
        assert len(z_flaga) == 2
        assert [x.koperta for x in z_flaga] == [0, 1]

    def test_same_wypelniacze_nie_tworza_akcji(self):
        assert akcje(self.pusty(), self.pusty(), self.pusty(last=True)) == []


class TestNiezmiennikiOgolne:
    def test_fill_bez_poprzedzajacego_trade_jest_ignorowany(self):
        """Rekordy `Fill` na poczatku koperty, bez `Trade`, nie tworza akcji."""
        a = akcje(r("F", "A", oid=20), r("F", "A", oid=21, last=True))
        assert a == []

    def test_akcje_pomijaja_add_cancel_modify(self):
        a = akcje(
            r("A", "B", oid=50),
            r("T", "B", sz=1, oid=10),
            r("C", "B", oid=51),
            r("M", "B", oid=52, last=True),
        )
        assert len(a) == 1
        assert a[0].n_trade == 1

    def test_determinizm(self):
        rek = [r("T", "B", sz=1, oid=10), r("F", "A", sz=1, oid=20, last=True)]
        assert [vars(x) for x in rekonstruuj(rek)] == [
            vars(x) for x in rekonstruuj(rek)]

    def test_liczba_trade_rozliczona(self):
        """Suma `n_trade` po akcjach == liczba rekordow Trade na wejsciu."""
        rek = [
            r("T", "B", oid=10), r("F", "A", oid=20),
            r("T", "B", oid=10), r("T", "A", oid=30),
            r("T", "B", oid=10, last=True),
        ]
        a = list(rekonstruuj(rek))
        assert sum(x.n_trade for x in a) == sum(1 for x in rek if x.action == "T")
