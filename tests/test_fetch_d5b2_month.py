"""Straznik downloadera miesiaca — testy o cenie w USD.

Kazdy blad w tym pliku kosztuje realne pieniadze i jest NIEODWRACALNY: raz
naliczonego pobrania nie da sie cofnac. Dlatego testy sa tu pisane wokol dwoch
pytan — czy skrypt WIDZI to, co juz mamy, i czy na pewno nie NADPISZE tego,
za co juz zaplacilismy.

Powod powstania: przy wycenie miesiaca skrypt zglosil "kompletnych juz na
dysku: 0" i zaproponowal zakup 22 sesji zamiast 21, bo sesji 2026-07-30
szukal w `d5b2_mbo/`, a ta lezy w `d5c_mbo/` pod ta sama nazwa. Wykryte przed
zakupem; kosztowaloby 3,5961 USD trzeciego naliczenia tej samej doby.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORZEN))

from scripts import fetch_d5b2_month as f  # noqa: E402

SESJA_D5C = "2026-07-30"


@pytest.fixture
def dane(tmp_path, monkeypatch):
    """Podstawia korzen danych na katalog tymczasowy."""
    def raw_dir(*czesci):
        p = tmp_path.joinpath(*czesci)
        (p.parent if p.suffix else p).mkdir(parents=True, exist_ok=True)
        return p
    monkeypatch.setattr(f, "raw_dir", raw_dir)
    return tmp_path


class TestSesjaZD5C:
    def test_plik_z_katalogu_d5c_jest_znaleziony(self, dane):
        """Sedno naprawy: ta sama nazwa, inny katalog."""
        plik = dane / f.KATALOG_D5C / f.nazwa_pliku(SESJA_D5C)
        plik.parent.mkdir(parents=True, exist_ok=True)
        plik.write_bytes(b"x")
        assert f.sciezka_istniejaca(SESJA_D5C) == plik

    def test_wlasny_katalog_ma_pierwszenstwo(self, dane):
        """Gdy sesja jest w obu miejscach, uzywamy swojej kopii."""
        for kat in (f.KATALOG, f.KATALOG_D5C):
            p = dane / kat / f.nazwa_pliku(SESJA_D5C)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"x")
        assert f.sciezka_istniejaca(SESJA_D5C).parent.name == f.KATALOG

    def test_bez_pliku_wskazuje_cel_pobrania(self, dane):
        assert f.sciezka_istniejaca(SESJA_D5C) == f.sciezka_docelowa(SESJA_D5C)


class TestOchronaKanonicznegoPliku:
    def test_pobieranie_nigdy_nie_celuje_w_katalog_d5c(self, dane):
        """NAJWAZNIEJSZY TEST W TYM PLIKU.

        Skrypt kasuje niekompletny plik przed ponownym pobraniem. Gdyby celem
        pobrania mogl byc `d5c_mbo/`, przerwany transfer skasowalby kanoniczny
        plik D5-C — ten, na ktorym stoi caly audyt Etapu 3 (842 757 zdarzen,
        0 niewyjasnionych) i ktorego SHA jest zamrozony w golden baseline.
        """
        for sesja in f.SESJE:
            assert f.sciezka_docelowa(sesja).parent.name == f.KATALOG

    def test_cel_pobrania_nie_zalezy_od_tego_co_lezy_na_dysku(self, dane):
        plik = dane / f.KATALOG_D5C / f.nazwa_pliku(SESJA_D5C)
        plik.parent.mkdir(parents=True, exist_ok=True)
        plik.write_bytes(b"x")
        assert f.sciezka_docelowa(SESJA_D5C).parent.name == f.KATALOG
        assert f.sciezka_istniejaca(SESJA_D5C).parent.name == f.KATALOG_D5C


class TestKompletnosc:
    def test_pusty_plik_nie_jest_kompletny(self, dane):
        p = dane / "pusty.dbn.zst"
        p.write_bytes(b"")
        ok, powod = f.kompletny(p, 100)
        assert not ok and "pusty" in powod

    def test_brak_pliku_nie_jest_kompletny(self, dane):
        ok, powod = f.kompletny(dane / "nie_ma.dbn.zst", 100)
        assert not ok and "brak" in powod

    def test_smiec_nie_udaje_kompletnego(self, dane):
        """Istnienie nie wystarcza — plik musi sie SPARSOWAC."""
        p = dane / "smiec.dbn.zst"
        p.write_bytes(b"to nie jest DBN")
        ok, powod = f.kompletny(p, 100)
        assert not ok and "parsuje" in powod


class TestWarunek3Manifest:
    """Wznowienie musi dotyczyc TEGO SAMEGO zakupu.

    Miesiac zlozony z dwoch roznych definicji zapytania wyglada w danych
    dokladnie jak miesiac poprawny — nic go nie zdradzi poza manifestem.
    """

    def _manifest(self, dane, tresc):
        p = dane.parent / "manifests" / f.MANIFEST
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(tresc), encoding="utf-8")
        return p

    def test_brak_manifestu_to_pierwsze_uruchomienie(self, dane):
        assert "brak" in f.sprawdz_manifest([])

    def test_zgodny_manifest_przechodzi(self, dane):
        plan = [{"sesja": "2026-07-01", "start_utc": "2026-07-01T13:30",
                 "end_utc": "2026-07-01T20:00"}]
        self._manifest(dane, {"zapytanie": f.ZAPYTANIE, "plan": plan})
        assert "zgodny" in f.sprawdz_manifest(plan)

    def test_zmiana_zapytania_przerywa(self, dane):
        self._manifest(dane, {"zapytanie": {**f.ZAPYTANIE, "schema": "trades"},
                              "plan": []})
        with pytest.raises(SystemExit) as e:
            f.sprawdz_manifest([])
        assert "warunek 3" in str(e.value)

    def test_zmiana_okna_rth_przerywa(self, dane):
        stary = [{"sesja": "2026-07-01", "start_utc": "2026-07-01T14:30",
                  "end_utc": "2026-07-01T20:00"}]
        nowy = [{"sesja": "2026-07-01", "start_utc": "2026-07-01T13:30",
                 "end_utc": "2026-07-01T20:00"}]
        self._manifest(dane, {"zapytanie": f.ZAPYTANIE, "plan": stary})
        with pytest.raises(SystemExit) as e:
            f.sprawdz_manifest(nowy)
        assert "warunek 3" in str(e.value)


class TestWarunek4TrzecieNaliczenie:
    """Doba 2026-07-30 byla juz naliczona DWA razy."""

    def test_sesja_d5c_na_liscie_przerywa(self):
        with pytest.raises(SystemExit) as e:
            f.sprawdz_sesje_d5c([{"sesja": f.SESJA_D5C}], pozwol=False)
        assert "warunek 4" in str(e.value)
        assert "trzeci raz" in str(e.value)

    def test_jawna_zgoda_pozwala_ale_ostrzega(self, capsys):
        f.sprawdz_sesje_d5c([{"sesja": f.SESJA_D5C}], pozwol=True)
        assert "TRZECIE naliczenie" in capsys.readouterr().out

    def test_inne_sesje_nie_sa_blokowane(self, capsys):
        """Straznik nie moze blokowac zakupu, dla ktorego skrypt istnieje."""
        wynik = f.sprawdz_sesje_d5c([{"sesja": "2026-07-01"},
                                     {"sesja": "2026-07-02"}], pozwol=False)
        assert wynik is None, "brak odmowy i brak wyjatku"
        assert capsys.readouterr().out == "", "zadnego ostrzezenia bez powodu"


class TestWarunek8DryfMetadanych:
    """Dostawca nie moze zmienic danych w trakcie zakupu.

    06.08.2026 wszystkie 22 sesje urosly o 1,67-3,06% miedzy dwoma
    uruchomieniami. Kazdy oplacony plik zaczal wygladac na niekompletny
    i skrypt zaproponowal zakup calego miesiaca DRUGI RAZ za 80,67 USD.
    Zatrzymal go warunek 4 — ale tylko dlatego, ze 2026-07-30 ma osobna
    ochrone; pozostale 21 sesji przeszloby.
    """

    def test_zgodne_liczby_przechodza(self):
        plan = [{"sesja": "2026-07-01", "rekordow": 100},
                {"sesja": "2026-07-02", "rekordow": 200}]
        wynik = f.sprawdz_dryf_rekordow(
            plan, {"2026-07-01": 100, "2026-07-02": 200})
        assert "zgodne" in wynik

    def test_dryf_choc_jednej_sesji_przerywa(self):
        plan = [{"sesja": "2026-07-01", "rekordow": 100},
                {"sesja": "2026-07-02", "rekordow": 205}]
        with pytest.raises(SystemExit) as e:
            f.sprawdz_dryf_rekordow(plan, {"2026-07-01": 100, "2026-07-02": 200})
        assert "warunek 8" in str(e.value)
        assert "2026-07-02" in str(e.value)

    def test_komunikat_podaje_skale_zmiany(self):
        """Sam fakt rozjazdu nie mowi, czy to rewizja, czy blad — procent mowi."""
        plan = [{"sesja": "2026-07-01", "rekordow": 40286094}]
        with pytest.raises(SystemExit) as e:
            f.sprawdz_dryf_rekordow(plan, {"2026-07-01": 39297265})
        assert "+2.52%" in str(e.value)

    def test_brak_manifestu_nie_blokuje_pierwszego_zakupu(self):
        plan = [{"sesja": "2026-07-01", "rekordow": 100}]
        assert "zgodne" in f.sprawdz_dryf_rekordow(plan, {})

    def test_sesje_spoza_manifestu_sa_pomijane(self):
        """Nowa sesja nie ma z czym sie rozjechac."""
        plan = [{"sesja": "2026-07-01", "rekordow": 100},
                {"sesja": "2026-07-02", "rekordow": 999}]
        assert "zgodne" in f.sprawdz_dryf_rekordow(plan, {"2026-07-01": 100})

    def test_odczyt_rekordow_z_manifestu(self, dane):
        p = dane.parent / "manifests" / f.MANIFEST
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"plan": [
            {"sesja": "2026-07-01", "rekordow": 39297265},
            {"sesja": "2026-07-02", "rekordow": 61279315}]}), encoding="utf-8")
        assert f.rekordy_z_manifestu() == {"2026-07-01": 39297265,
                                           "2026-07-02": 61279315}

    def test_uszkodzony_manifest_nie_wywraca_zakupu(self, dane):
        p = dane.parent / "manifests" / f.MANIFEST
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{nie JSON", encoding="utf-8")
        assert f.rekordy_z_manifestu() == {}


class TestSHAKanoniczny:
    """Zgodna liczba rekordow mowi tylko, ze plik ma wlasciwa dlugosc."""

    def test_niezgodny_sha_przerywa(self, dane, monkeypatch):
        man = dane / "kanoniczny.json"
        man.write_text(json.dumps({"sha256": "0" * 64}), encoding="utf-8")
        monkeypatch.setattr(f, "KANONICZNY_D5C", man)
        plik = dane / "x.dbn.zst"
        plik.write_bytes(b"inna zawartosc, ta sama dlugosc")
        with pytest.raises(SystemExit) as e:
            f.sprawdz_sha_d5c(plik)
        assert "SHA-256" in str(e.value)

    def test_zgodny_sha_przechodzi(self, dane, monkeypatch):
        plik = dane / "x.dbn.zst"
        plik.write_bytes(b"tresc")
        man = dane / "kanoniczny.json"
        man.write_text(json.dumps({"sha256": f.sha_pliku(plik)}), encoding="utf-8")
        monkeypatch.setattr(f, "KANONICZNY_D5C", man)
        assert "zgodny" in f.sprawdz_sha_d5c(plik)

    def test_brak_manifestu_nie_przerywa(self, dane, monkeypatch):
        monkeypatch.setattr(f, "KANONICZNY_D5C", dane / "nie_ma.json")
        assert "pomijam" in f.sprawdz_sha_d5c(dane)

    def test_sha_zgodne_z_manifestem_w_repo(self):
        """Manifest kanoniczny musi miec pole, na ktorym stoi kontrola."""
        d = json.loads(f.KANONICZNY_D5C.read_text(encoding="utf-8"))
        assert d["sesja"] == f.SESJA_D5C
        assert len(d["sha256"]) == 64


class TestDokumentacjaZgodnaZKodem:
    """Docstring deklarowal SIEDEM warunkow, z ktorych dwa nie istnialy.

    Przyszla sesja czytajaca plik zalozylaby ochrony, ktorych nie ma — ta sama
    klasa defektu co nieaktualny HANDOFF, tylko na sciezce wydajacej pieniadze.
    """

    def test_kazdy_warunek_z_docstringu_ma_komunikat_w_kodzie(self):
        zrodlo = (KORZEN / "scripts" / "fetch_d5b2_month.py").read_text(
            encoding="utf-8")
        doc = f.__doc__ or ""
        zadeklarowane = set(re.findall(r"^  (\d)\. ", doc, re.MULTILINE))
        zaimplementowane = set(re.findall(r"STOP \(warunek (\d)\)", zrodlo))
        assert zadeklarowane == zaimplementowane, (
            f"docstring deklaruje {sorted(zadeklarowane)}, kod implementuje "
            f"{sorted(zaimplementowane)}")

    def test_dokumentacja_ma_te_sama_numeracje_co_kod(self):
        """Trzecie zrodlo numeracji: URUCHOMIENIE_LOKALNE §8.

        Rozjazd miedzy docstringiem a dokumentacja zglaszany dwa razy z rzedu
        (raz odsylacz do zlej sekcji, raz nieaktualny opis warunku). Reczne
        pilnowanie trzech list nie dziala.

        UWAGA: §7 to inna lista — osiem WARUNKOW ZGODY wlasciciela, wlasna
        numeracja. Test celowo czyta wylacznie tabele odmow z §8.
        """
        doc = (KORZEN / "docs" / "URUCHOMIENIE_LOKALNE.md").read_text(
            encoding="utf-8")
        # Kotwica NIE zawiera liczebnika ("Siedem"/"Osiem") — pierwsza wersja
        # tego testu go zawierala i zepsula sie przy dodaniu warunku 8, czyli
        # przy dokladnie tej zmianie, ktorej miala pilnowac.
        m = re.search(r"^### \w+ warunk\w+ odmowy", doc, re.MULTILINE)
        assert m, "brak tabeli odmow w URUCHOMIENIE_LOKALNE"
        ogon = doc[m.start():]
        koniec = ogon.find("**Czego skryptu")
        w_dok = set(re.findall(r"^\| (\d) \| ", ogon[:koniec], re.MULTILINE))
        w_docstring = set(re.findall(r"^  (\d)\. ", f.__doc__ or "", re.MULTILINE))
        assert w_dok == w_docstring, (
            f"URUCHOMIENIE_LOKALNE §8 wymienia {sorted(w_dok)}, docstring "
            f"{sorted(w_docstring)}")

    def test_jedna_numeracja_w_calym_pliku(self):
        """Komunikat o miejscu na dysku mowil kiedys 'Warunek 4 z listy zgody',
        a docstring numerowal go inaczej — dwie numeracje w jednym pliku."""
        zrodlo = (KORZEN / "scripts" / "fetch_d5b2_month.py").read_text(
            encoding="utf-8")
        assert "z listy zgody" not in zrodlo


class TestCacheWyceny:
    """Cache ratuje PRZERWANY przebieg, nie zastepuje wyceny.

    Powstal po awarii: 503 na 6. kawalku PIERWSZEJ sesji skasowal cala wycene
    22 sesji (572 wywolania metadanych). Ale nie moze obchodzic reguly
    wlasciciela "wycena bezposrednio przed pobraniem" — stad limit wieku.
    """

    def _wpis(self, godzin_temu: float) -> dict:
        t = dt.datetime.now(dt.UTC) - dt.timedelta(hours=godzin_temu)
        return {"koszt": 3.5, "rekordow": 100,
                "utc": t.isoformat(timespec="seconds")}

    def test_swiezy_wpis_jest_uzywany(self, dane):
        a, b = f.okno("2026-07-01")
        f.zapisz_cache({f.klucz_wyceny(a, b): self._wpis(1.0)})
        c = f.wczytaj_cache()
        assert f.klucz_wyceny(a, b) in c
        assert c[f.klucz_wyceny(a, b)]["wiek_h"] == pytest.approx(1.0, abs=0.1)

    def test_stary_wpis_jest_odrzucany(self, dane):
        a, b = f.okno("2026-07-01")
        f.zapisz_cache({f.klucz_wyceny(a, b): self._wpis(f.WAZNOSC_WYCENY_H + 1)})
        assert f.wczytaj_cache() == {}, "cache starszy niz limit to brak cache"

    def test_zmiana_zapytania_uniewaznia_wpis(self, dane, monkeypatch):
        """Klucz zawiera CALE zapytanie. Gdyby zawieral same daty, zmiana
        schematu podstawilaby ceny z innego zapytania — bez sladu."""
        a, b = f.okno("2026-07-01")
        stary_klucz = f.klucz_wyceny(a, b)
        f.zapisz_cache({stary_klucz: self._wpis(1.0)})
        monkeypatch.setattr(f, "ZAPYTANIE", {**f.ZAPYTANIE, "schema": "trades"})
        assert f.klucz_wyceny(a, b) != stary_klucz
        assert f.klucz_wyceny(a, b) not in f.wczytaj_cache()

    def test_uszkodzony_cache_to_brak_cache(self, dane):
        p = f.sciezka_cache()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{to nie jest JSON", encoding="utf-8")
        assert f.wczytaj_cache() == {}, "uszkodzony cache nie moze wywracac wyceny"

    def test_wpis_z_przyszlosci_jest_odrzucany(self, dane):
        """Zegar cofniety albo plik z innej maszyny — wiek ujemny nie jest
        dowodem swiezosci."""
        a, b = f.okno("2026-07-01")
        f.zapisz_cache({f.klucz_wyceny(a, b): self._wpis(-5.0)})
        assert f.wczytaj_cache() == {}

    def test_zapis_nie_utrwala_pola_pomocniczego(self, dane):
        a, b = f.okno("2026-07-01")
        f.zapisz_cache({f.klucz_wyceny(a, b): self._wpis(1.0)})
        f.zapisz_cache(f.wczytaj_cache())          # round-trip
        surowe = json.loads(f.sciezka_cache().read_text(encoding="utf-8"))
        assert "wiek_h" not in next(iter(surowe.values()))


class TestZamrozoneStale:
    def test_lista_sesji_ma_22_pozycje_lipca_2026(self):
        assert len(f.SESJE) == 22
        assert all(s.startswith("2026-07-") for s in f.SESJE)
        assert SESJA_D5C in f.SESJE, "sesja z D5-C nalezy do miesiaca"

    def test_limit_kosztu_zgodny_ze_specyfikacja(self):
        """Zamrozony w docs/D5_ETAP4_SPEC.md §7 PRZED zakupem."""
        assert f.LIMIT_USD == 82.00

    def test_okno_rth_wyprowadzone_ze_strefy_et(self):
        """Lipiec to czas letni: 09:30 ET = 13:30 UTC."""
        a, b = f.okno("2026-07-15")
        assert a == "2026-07-15T13:30"
        assert b == "2026-07-15T20:00"
