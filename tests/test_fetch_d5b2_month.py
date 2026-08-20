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


def _uruchom(argv):
    import sys as _s
    stare = _s.argv
    try:
        _s.argv = ["fetch_d5b2_month.py", *argv]
        return f.main()
    finally:
        _s.argv = stare


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
        komunikat = str(e.value)
        assert "warunek 4" in komunikat
        # Intencja, nie dosłowne brzmienie: ma byc jasne, ze to TRZECI zakup.
        assert "TRZECIE" in komunikat.upper()
        # Od 18.08 komunikat ostrzega tez przed uzyciem flagi jako "odblokowania"
        # sesji, ktorej plik pochodzi ze STAREJ normalizacji — recenzja P2.
        assert "STAREJ normalizacji" in komunikat
        assert "§5f" in komunikat

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

    08.08.2026 wszystkie 22 sesje urosly o 1,67-3,06% miedzy dwoma
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

    def test_furtka_przyjmuje_rozjazd_i_archiwizuje(self, dane):
        """Bez jawnej furtki jedyna droga przyjecia nowych liczb bylaby reczna
        edycja manifestu — obejscie straznika bez sladu i bez testu."""
        cel = dane.parent / "manifests" / f.MANIFEST
        cel.parent.mkdir(parents=True, exist_ok=True)
        cel.write_text(json.dumps({"plan": [
            {"sesja": "2026-07-01", "rekordow": 39297265}]}), encoding="utf-8")

        plan = [{"sesja": "2026-07-01", "rekordow": 40286094}]
        wynik = f.sprawdz_dryf_rekordow(plan, {"2026-07-01": 39297265},
                                        akceptuj=True)
        assert "PRZYJETY" in wynik
        kopie = list(cel.parent.glob("manifest_d5b2_przed_*.json"))
        assert len(kopie) == 1, "stary manifest musi zostac ZARCHIWIZOWANY"
        assert json.loads(kopie[0].read_text(encoding="utf-8"))["plan"][0][
            "rekordow"] == 39297265
        assert cel.exists(), "oryginal nie moze zniknac przy archiwizacji"

    def test_furtka_z_wycena_jest_odrzucana(self):
        """Archiwum manifestu w trybie, ktory nic nie kupuje, zostawia slad
        decyzji, ktora nie zapadla."""
        with pytest.raises(SystemExit) as e:
            _uruchom(["--wycena", "--akceptuj-rozjazd"])
        assert "nie ma sensu" in str(e.value)

    def test_furtka_domyslnie_wylaczona(self, dane):
        """Straznik ma dzialac bez podawania flagi — inaczej nie jest strazą."""
        plan = [{"sesja": "2026-07-01", "rekordow": 205}]
        with pytest.raises(SystemExit):
            f.sprawdz_dryf_rekordow(plan, {"2026-07-01": 200})

    def test_uszkodzony_manifest_przerywa_czysto(self, dane):
        """Traceback tuz przed zakupem za kilkadziesiat USD to zly komunikat."""
        cel = dane.parent / "manifests" / f.MANIFEST
        cel.parent.mkdir(parents=True, exist_ok=True)
        cel.write_text("{nie JSON", encoding="utf-8")
        with pytest.raises(SystemExit) as e:
            f.sprawdz_manifest([])
        assert "warunek 3" in str(e.value)

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
        zadeklarowane = set(re.findall(r"^  (\d+)\. ", doc, re.MULTILINE))
        zaimplementowane = set(re.findall(r"STOP \(warunek (\d+)\)", zrodlo))
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
        # Koniec = nastepny naglowek sekcji, a nie konkretny akapit, ktory
        # ktos moze przepisac. Pierwsza wersja kotwiczyla na "**Czego skryptu",
        # druga cieła na pierwszym wierszu spoza tabeli — czyli na akapicie
        # wstepnym, PRZED tabela. Naglowek jest jedyna stabilna granica.
        m2 = re.search(r"^#{2,3} ", ogon[len(m.group(0)):], re.MULTILINE)
        koniec = len(m.group(0)) + m2.start() if m2 else len(ogon)
        w_dok = set(re.findall(r"^\| (\d+) \| ", ogon[:koniec], re.MULTILINE))
        w_docstring = set(re.findall(r"^  (\d+)\. ", f.__doc__ or "", re.MULTILINE))
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


class TestEpokaNormalizacji:
    """Znacznik wersji normalizacji GLBX.MDP3 w manifescie.

    Powod istnienia: dostawca potwierdzil 11.08.2026, ze *"the old data is not
    available anymore in our API"*. Dwie wersje serwowania roznia sie rekordami
    `action=N` w zdarzeniach wielopakietowych, ale **w samych danych nie widac,
    ktora to wersja**. Skoro starej nie da sie juz pobrac, znacznik w manifescie
    jest jedynym sposobem, zeby kolejna sesja nie zmieszala ich na slepo.
    """

    def test_przed_przelomem(self):
        assert f.epoka_normalizacji(
            dt.datetime(2026, 8, 6, 22, 5, 38, tzinfo=dt.UTC)
        ) == "przed-2026-08-08"

    def test_po_przelomie(self):
        assert f.epoka_normalizacji(
            dt.datetime(2026, 8, 8, 12, 15, tzinfo=dt.UTC)
        ) == "po-2026-08-08"

    def test_dzisiejsze_pobranie_jest_nowa_normalizacja(self):
        assert f.epoka_normalizacji(
            dt.datetime.now(dt.UTC)) == "po-2026-08-08"

    @pytest.mark.parametrize("kiedy", [
        dt.datetime(2026, 8, 6, 22, 5, 39, tzinfo=dt.UTC),
        dt.datetime(2026, 8, 7, 12, 0, tzinfo=dt.UTC),
        dt.datetime(2026, 8, 8, 12, 14, 59, tzinfo=dt.UTC),
    ])
    def test_w_przedziale_przelomu_NIE_ZGADUJEMY(self, kiedy):
        """Granica jest przedzialem, nie punktem — i tak ma zostac.

        Zgadniecie tutaj dawaloby plik opisany jako jednorodny, ktory jednorodny
        nie jest, a blad wyszedlby dopiero w wynikach badania. Lepiej miec
        w manifescie jawne NIEUSTALONA niz cicha nieprawde.
        """
        assert f.epoka_normalizacji(kiedy) == "NIEUSTALONA"

    def test_granice_pochodza_z_udokumentowanych_pomiarow(self):
        """Obie daty musza zgadzac sie z osia czasu z D5_DRYF_METADANYCH.

        Lewy kraniec to `pobrano_utc` z manifestu, prawy to wycena, ktora
        pierwsza pokazala nowe liczby. Przesuniecie ich "na oko" uniewaznia
        klasyfikacje wszystkich plikow naraz.
        """
        assert f.NORMALIZACJA_OSTATNIA_STARA < f.NORMALIZACJA_PIERWSZA_NOWA
        assert f.NORMALIZACJA_OSTATNIA_STARA.isoformat() == \
            "2026-08-06T22:05:38+00:00"
        assert f.NORMALIZACJA_PIERWSZA_NOWA.isoformat() == \
            "2026-08-08T12:15:00+00:00"


class TestPrzeniesienieWynikow:
    """Manifest nie moze zgubic pochodzenia sesji, ktorych biezacy bieg nie tyka.

    Zapis manifestu opisywal wylacznie biezacy bieg. Nastepny bieg zakupowy
    (a taki bedzie — zostalo 17 sesji) nadpisalby plik tak, ze `sha256`,
    `pobrano_utc` i `normalizacja` pieciu sesji ze STAREJ normalizacji
    zniknelyby z aktywnego manifestu. Skoro starej wersji nie da sie juz
    pobrac, a w danych jej nie widac, byloby to bezpowrotne zatarcie jedynej
    informacji o tym, co lezy na dysku.
    """

    def _manifest(self, tmp_path, monkeypatch, tresc: dict):
        cel = tmp_path / "manifests" / f.MANIFEST
        cel.parent.mkdir(parents=True, exist_ok=True)
        cel.write_text(json.dumps(tresc), encoding="utf-8")
        monkeypatch.setattr(f, "sciezka_manifestu", lambda: cel)
        return cel

    def test_przenosi_wpisy_sesji_pomijanych(self, tmp_path, monkeypatch):
        self._manifest(tmp_path, monkeypatch, {
            "pobrano_utc": "2026-08-06T22:05:38+00:00",
            "wyniki": [
                {"sesja": "2026-07-01", "sha256": "aaa", "kompletny": True,
                 "pobrano_utc": "2026-08-06T20:00:00+00:00",
                 "normalizacja": "przed-2026-08-08"},
                {"sesja": "2026-07-08", "sha256": "bbb", "kompletny": True},
            ]})
        out = f.przeniesione_wyniki(["2026-07-01"])
        assert [w["sesja"] for w in out] == ["2026-07-01"]
        assert out[0]["sha256"] == "aaa"
        assert out[0]["normalizacja"] == "przed-2026-08-08"
        assert out[0]["z_poprzedniego_biegu"] is True

    def test_backfill_epoki_z_wlasnego_znacznika(self, tmp_path, monkeypatch):
        """Wpisy sprzed wprowadzenia pola dostaja je wyliczone, nie zgadniete."""
        self._manifest(tmp_path, monkeypatch, {
            "pobrano_utc": "2026-08-09T10:00:00+00:00",
            "wyniki": [{"sesja": "2026-07-02", "sha256": "ccc",
                        "pobrano_utc": "2026-08-06T22:05:38+00:00"}]})
        out = f.przeniesione_wyniki(["2026-07-02"])
        assert out[0]["normalizacja"] == "przed-2026-08-08"

    def test_backfill_z_manifestu_gdy_wpis_nie_ma_znacznika(
            self, tmp_path, monkeypatch):
        self._manifest(tmp_path, monkeypatch, {
            "pobrano_utc": "2026-08-06T22:05:38+00:00",
            "wyniki": [{"sesja": "2026-07-03", "sha256": "ddd"}]})
        out = f.przeniesione_wyniki(["2026-07-03"])
        assert out[0]["normalizacja"] == "przed-2026-08-08"

    def test_bez_znacznika_NIE_ZGADUJEMY(self, tmp_path, monkeypatch):
        self._manifest(tmp_path, monkeypatch, {
            "wyniki": [{"sesja": "2026-07-03", "sha256": "eee"}]})
        assert f.przeniesione_wyniki(["2026-07-03"])[0]["normalizacja"] == \
            "NIEUSTALONA"

    def test_brak_manifestu_i_smiec_nie_wywalaja_biegu(
            self, tmp_path, monkeypatch):
        """Zakup nie moze paesc przez uszkodzony manifest — to zablokowaloby
        pobranie, za ktore juz zaplacono wycena."""
        cel = tmp_path / "manifests" / f.MANIFEST
        monkeypatch.setattr(f, "sciezka_manifestu", lambda: cel)
        assert f.przeniesione_wyniki(["2026-07-01"]) == []
        cel.parent.mkdir(parents=True, exist_ok=True)
        cel.write_text("{to nie jest json", encoding="utf-8")
        assert f.przeniesione_wyniki(["2026-07-01"]) == []


class TestPlikZeStarejNormalizacji:
    """Plik zgodny z MANIFESTEM jest kompletny — nawet gdy API mowi inaczej.

    PULAPKA, KTORA TEN TEST ZAMYKA. Databento zmienilo 08.08.2026 normalizacje:
    te same zapytania zwracaja wiecej rekordow, a starej wersji NIE DA SIE juz
    pobrac. Nasze piec plikow zgadza sie z liczbami sprzed zmiany.

    Gdyby `kompletny()` porownywal je wylacznie z biezaca wycena, przy
    `--akceptuj-rozjazd` kazdy wygladalby na niekompletny. Skutek lancuchowy:
    piec sesji trafia na liste do pobrania -> `out.unlink()` KASUJE jedyny
    istniejacy egzemplarz starej normalizacji -> placimy drugi raz za dane,
    ktore juz mamy. Okolo 17 USD i dane nie do odtworzenia za zadna cene.

    Wykryte przy czytaniu sciezki `--akceptuj-rozjazd` PRZED podaniem
    wlascicielowi komendy zakupu.
    """

    STARE = 39_297_265      # 2026-07-01 w manifescie
    NOWE = 40_286_094       # ta sama sesja wg wyceny z 08.08

    def _plik(self, tmp_path, ile: int) -> Path:
        """Plik, ktory `kompletny()` policzy na `ile` rekordow."""
        p = tmp_path / "mnq_mbo_rth_2026-07-01.dbn.zst"
        p.write_bytes(b"x")
        return p

    def test_plik_ze_stara_liczba_jest_kompletny(self, tmp_path, monkeypatch):
        p = self._plik(tmp_path, self.STARE)
        monkeypatch.setattr(f.db.DBNStore, "from_file",
                            staticmethod(lambda _: range(self.STARE)))
        ok, powod = f.kompletny(p, self.NOWE, oplacone=self.STARE)
        assert ok, f"plik oplacony uznany za niekompletny: {powod}"
        assert "STAREJ normalizacji" in powod

    def test_bez_manifestu_stary_plik_wypada_jako_niekompletny(
            self, tmp_path, monkeypatch):
        """Kontrola: bez `oplacone` zachowanie jest stare — i wlasnie GROZNE.

        Ten test pokazuje, ze poprawka realnie zmienia wynik, a nie tylko
        dokłada parametr, ktory nic nie robi.
        """
        p = self._plik(tmp_path, self.STARE)
        monkeypatch.setattr(f.db.DBNStore, "from_file",
                            staticmethod(lambda _: range(self.STARE)))
        ok, _ = f.kompletny(p, self.NOWE)
        assert not ok

    def test_plik_obciety_nadal_jest_niekompletny(self, tmp_path, monkeypatch):
        """Poprawka NIE MOZE przepuszczac plikow urwanych w locie.

        Gdyby wystarczylo 'cokolwiek innego niz biezaca wycena', obcieta sesja
        przechodzilaby jako kompletna — a to jest dokladnie ten blad, dla
        ktorego `kompletny()` w ogole powstal.
        """
        p = self._plik(tmp_path, 1_867_793)
        monkeypatch.setattr(f.db.DBNStore, "from_file",
                            staticmethod(lambda _: range(1_867_793)))
        ok, powod = f.kompletny(p, self.NOWE, oplacone=self.STARE)
        assert not ok
        assert "1,867,793" in powod

    def test_kwalifikacja_pomija_wszystkie_piec_starych_sesji(self, monkeypatch):
        """Calosciowo: przy przyjetym rozjezdzie zadna ze starych sesji nie
        moze trafic na liste do pobrania."""
        stare = {s: 1000 + i for i, s in enumerate(f.SESJE_STARA_NORMALIZACJA)}
        for sesja, ile in stare.items():
            monkeypatch.setattr(f.db.DBNStore, "from_file",
                                staticmethod(lambda _, n=ile: range(n)))
            ok, _ = f.kompletny(Path(__file__), 9_999_999, oplacone=ile)
            assert ok, f"{sesja}: plik oplacony trafilby do ponownego zakupu"


class TestOchronaPrzezywaNadpisanieManifestu:
    """Ochrona starych plikow musi dzialac takze PO pierwszym biegu zakupowym.

    ZARZUT RECENZJI P2, potwierdzony w zrodle. Poprawka z 37ccfa2 czytala
    oplacone liczby przez `rekordy_z_manifestu()`, czyli z `plan[]`. Bieg
    zakupowy nadpisuje `plan[]` nowymi liczbami, a zapis manifestu wykonuje sie
    TAKZE PO `break` — po braku miejsca, bledzie pobierania albo warunku 6.

    Skutek: po pierwszym biegu, chocby przerwanym, "oplacone" stawalo sie rowne
    biezacej wycenie. Piec starych plikow znow wypadaloby jako niekompletne,
    a obrona przy `unlink()` porownywalaby z nowa liczba i nie zadzialalaby.
    Obie ochrony ginely dokladnie w biegu wznowieniowym — tym, w ktorym sa
    najbardziej potrzebne. Historia projektu: 2 z ~6 pobran zostaly przerwane,
    a ten bieg ma ich 17.
    """

    STARE = 39_297_265
    NOWE = 40_286_094
    SESJA = "2026-07-01"

    def _manifest_po_biegu(self, tmp_path, monkeypatch):
        """Manifest w stanie PO biegu: plan na nowych liczbach, stare wpisy
        przeniesione w `wyniki` przez `przeniesione_wyniki()`."""
        cel = tmp_path / "manifests" / f.MANIFEST
        cel.parent.mkdir(parents=True, exist_ok=True)
        cel.write_text(json.dumps({
            "pobrano_utc": "2026-08-18T12:00:00+00:00",
            "plan": [{"sesja": self.SESJA, "rekordow": self.NOWE},
                     {"sesja": "2026-07-08", "rekordow": 46_050_560}],
            "wyniki": [
                {"sesja": self.SESJA, "rekordow": self.STARE,
                 "kompletny": True, "z_poprzedniego_biegu": True,
                 "normalizacja": "przed-2026-08-08"},
                {"sesja": "2026-07-08", "rekordow": 46_050_560,
                 "kompletny": True},
            ]}), encoding="utf-8")
        monkeypatch.setattr(f, "sciezka_manifestu", lambda: cel)
        return cel

    def test_wyniki_maja_pierwszenstwo_przed_planem(self, tmp_path, monkeypatch):
        """Sedno naprawy: `wyniki[]` opisuje PLIK, `plan[]` tylko oczekiwanie."""
        self._manifest_po_biegu(tmp_path, monkeypatch)
        assert f.liczby_oplacone()[self.SESJA] == self.STARE, (
            "po nadpisaniu planu ochrona czytalaby nowa liczbe — to jest "
            "dokladnie ten blad, ktory zglosila recenzja P2")

    def test_stary_plik_nadal_kompletny_po_biegu(self, tmp_path, monkeypatch):
        """Warunek rozstrzygniecia recenzji: piec starych plikow kwalifikuje sie
        jako kompletne takze w biegu wznowieniowym."""
        self._manifest_po_biegu(tmp_path, monkeypatch)
        monkeypatch.setattr(f.db.DBNStore, "from_file",
                            staticmethod(lambda _: range(self.STARE)))
        ok, powod = f.kompletny(Path(__file__), self.NOWE,
                                f.liczby_oplacone().get(self.SESJA))
        assert ok, f"wznowienie kupiloby oplacona sesje ponownie: {powod}"

    def test_obrona_przy_unlink_nadal_rozpoznaje_oplacony_plik(
            self, tmp_path, monkeypatch):
        """Druga linia obrony porownuje z ta sama liczba, co kwalifikacja."""
        self._manifest_po_biegu(tmp_path, monkeypatch)
        assert f.liczby_oplacone().get(self.SESJA) == self.STARE

    def test_sesja_d5c_bierze_liczbe_z_wlasnego_manifestu(
            self, tmp_path, monkeypatch):
        """07-30 nigdy nie trafia do `wyniki` kampanii — jej liczba pochodzi
        z `data/manifest_d5c.json`, sledzonego w repo i nietykanego przez bieg."""
        self._manifest_po_biegu(tmp_path, monkeypatch)
        kanoniczny = json.loads(
            (KORZEN / "data" / "manifest_d5c.json").read_text(encoding="utf-8"))
        assert f.liczby_oplacone()[f.SESJA_D5C] == \
            kanoniczny["rekordow_wg_metadata"]

    def test_wpis_nieudanego_pobrania_nie_liczy_sie_jako_oplacony(
            self, tmp_path, monkeypatch):
        """`kompletny: false` to zapis PORAZKI — nie moze uwiarygodnic pliku."""
        cel = tmp_path / "manifests" / f.MANIFEST
        cel.parent.mkdir(parents=True, exist_ok=True)
        cel.write_text(json.dumps({
            "plan": [{"sesja": "2026-07-07", "rekordow": 48_848_835}],
            "wyniki": [{"sesja": "2026-07-07", "rekordow": 1_867_793,
                        "kompletny": False}]}), encoding="utf-8")
        monkeypatch.setattr(f, "sciezka_manifestu", lambda: cel)
        assert f.liczby_oplacone()["2026-07-07"] == 48_848_835


class TestDiagnostykaWynikow:
    """`scripts/diag_wyniki.py` — read-only odpowiedz na jedno pytanie: czy
    ochrona piaciu starych plikow przezyje bieg zakupowy.

    Skrypt istnieje po to, zeby wlasciciel nie musial czytac JSON-a recznie
    i zeby werdykt nie zalezal od tego, czy ktos poprawnie zinterpretuje
    `plan[]` kontra `wyniki[]`. Testy pilnuja, ze werdykt jest odwrotny
    w dwoch stanach, ktore roznia sie dokladnie tym jednym.

    Skrypt NIE moze siegac po `DATABENTO_API_KEY` ani po siec — dlatego
    osobny test na sam import.
    """

    LIPCOWE = ("2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06")

    def _diag(self, monkeypatch, cel: Path):
        from scripts import diag_wyniki as d
        monkeypatch.setattr(f, "sciezka_manifestu", lambda: cel)
        monkeypatch.setattr(d, "sciezka_manifestu", lambda: cel)
        return d

    def _zapisz(self, tmp_path, tresc: dict) -> Path:
        cel = tmp_path / "manifests" / f.MANIFEST
        cel.parent.mkdir(parents=True, exist_ok=True)
        cel.write_text(json.dumps(tresc), encoding="utf-8")
        return cel

    def test_sam_plan_przechodzi_bo_synteza_utrwali(self, tmp_path, monkeypatch,
                                                    capsys):
        """Stan zmierzony u wlasciciela: liczby wylacznie w `plan[]`.

        Do czasu poprawki P1 byla to blokada. Po niej nie jest: `oplacone`
        czyta stary `plan[]` PRZED petla zakupu, a `syntetyzuj_wyniki()`
        przenosi te liczby do `wyniki[]` w tym samym zapisie manifestu,
        ktory `plan[]` nadpisuje. Werdykt musi to odrozniac od braku liczby,
        bo inaczej diagnostyka blokowalaby zakup, ktory jest juz bezpieczny.
        """
        cel = self._zapisz(tmp_path, {
            "plan": [{"sesja": s, "rekordow": 100} for s in self.LIPCOWE],
            "wyniki": []})
        d = self._diag(monkeypatch, cel)
        assert d.main() == 0
        wyj = capsys.readouterr().out
        assert "mozna uruchomic zakup" in wyj
        assert "BLOKADA" not in wyj
        for s in self.LIPCOWE:
            assert s in wyj

    def test_brak_liczby_to_blokada(self, tmp_path, monkeypatch, capsys):
        """Sesja nieobecna ani w `plan[]`, ani w `wyniki[]` — nie ma z czym
        porownac pliku, wiec zadna z dwoch ochron nie ma na czym stanac."""
        cel = self._zapisz(tmp_path, {"plan": [], "wyniki": []})
        d = self._diag(monkeypatch, cel)
        assert d.main() == 1
        wyj = capsys.readouterr().out
        assert "BLOKADA" in wyj
        for s in self.LIPCOWE:
            assert s in wyj

    def test_wyniki_kompletne_daja_zielone_swiatlo(self, tmp_path, monkeypatch,
                                                  capsys):
        """Te same sesje, ale liczba pochodzi z `wyniki[]` — przezyje bieg."""
        cel = self._zapisz(tmp_path, {
            "plan": [{"sesja": s, "rekordow": 999} for s in self.LIPCOWE],
            "wyniki": [{"sesja": s, "rekordow": 100, "kompletny": True}
                       for s in self.LIPCOWE]})
        d = self._diag(monkeypatch, cel)
        assert d.main() == 0
        assert "ochrona trwala" in capsys.readouterr().out

    def test_wpis_nieudany_nie_liczy_sie_jako_trwaly(self, tmp_path,
                                                     monkeypatch, capsys):
        """`kompletny: false` to zapis PORAZKI — nie moze uchodzic za trwale
        zrodlo, mimo ze siedzi w `wyniki[]`.

        Sesja ma wtedy spasc do `plan[]` (czyli do syntezy), a nie zostac
        zaliczona jako "ochrona trwala" — bo wpis nieudanego pobrania niesie
        liczbe OCZEKIWANA, nie liczbe pliku lezacego na dysku.
        """
        cel = self._zapisz(tmp_path, {
            "plan": [{"sesja": s, "rekordow": 999} for s in self.LIPCOWE],
            "wyniki": [{"sesja": s, "rekordow": 100, "kompletny": False}
                       for s in self.LIPCOWE]})
        d = self._diag(monkeypatch, cel)
        assert d.main() == 0
        wyj = capsys.readouterr().out
        assert "ochrona trwala" not in wyj
        assert "synteza go utrwali" in wyj
        assert "999" in wyj, "liczba ma pochodzic z `plan[]`, nie z wpisu porazki"

    def test_brak_manifestu_nie_jest_zielony(self, tmp_path, monkeypatch,
                                             capsys):
        """Brak zapisu to brak dowodu, a nie dowod braku ryzyka."""
        d = self._diag(monkeypatch, tmp_path / "nie_ma.json")
        assert d.main() == 1
        assert "BRAK MANIFESTU" in capsys.readouterr().out

    def test_import_nie_czyta_klucza(self):
        """Import modulu nie moze dotknac `DATABENTO_API_KEY` — inaczej
        diagnostyka read-only wymagalaby sekretu, ktorego nie potrzebuje."""
        zrodlo = (KORZEN / "scripts" / "diag_wyniki.py").read_text(
            encoding="utf-8")
        # Wystapienie dopuszczalne wylacznie w docstringu, nie w kodzie.
        kod = [w for w in zrodlo.splitlines()
               if "DATABENTO_API_KEY" in w and not w.lstrip().startswith("#")]
        assert all("`DATABENTO_API_KEY`" in w for w in kod), \
            f"klucz uzyty w kodzie diagnostyki: {kod}"

    def test_skrypt_niczego_nie_zapisuje(self):
        """Read-only znaczy read-only — zadnego zapisu ani kasowania.

        Sprawdzane po drzewie skladniowym, nie po tekscie: dokumentacja tego
        skryptu MUSI wymieniac `out.unlink()`, bo to jest wlasnie ta operacja,
        przed ktora chroni. Straznik tekstowy zabranialby jej opisania.
        """
        import ast
        zrodlo = (KORZEN / "scripts" / "diag_wyniki.py").read_text(
            encoding="utf-8")
        zakazane = {"write_text", "write_bytes", "unlink", "mkdir", "rmdir",
                    "open", "rename", "replace", "touch"}
        znalezione = [
            w.func.attr if isinstance(w.func, ast.Attribute) else w.func.id
            for w in ast.walk(ast.parse(zrodlo))
            if isinstance(w, ast.Call)
            and (isinstance(w.func, ast.Attribute) and w.func.attr in zakazane
                 or isinstance(w.func, ast.Name) and w.func.id in zakazane)]
        assert not znalezione, \
            f"diagnostyka read-only wywoluje: {sorted(set(znalezione))}"


class TestSyntezaWynikow:
    """Domkniecie luki P1: liczby oplacone przenoszone z `plan[]` do `wyniki[]`.

    STAN, KTORY TO WYWOLAL — zmierzony na maszynie wlasciciela, nie zalozony:
    manifest mial 22 wpisy w `plan[]` i **ZERO** w `wyniki[]`, bo powstal
    w biegu, ktory niczego nie pobral. Cztery sesje lipcowe ze starej
    normalizacji stały wiec wylacznie na `plan[]` — a bieg zakupowy `plan[]`
    nadpisuje, takze po `break`.

    Skutek bez tej poprawki, dokladnie w biegu wznowieniowym: `kompletny()`
    przestaje uznawac te pliki, wiec trafiaja na liste do pobrania; druga linia
    obrony przy `unlink()` porownuje z NOWA liczba, wiec nie zatrzymuje;
    kasujemy jedyny egzemplarz starej normalizacji i placimy za niego drugi raz.
    """

    SESJA = "2026-07-01"
    STARE = 39_297_265      # liczba oplacona, plik na dysku
    NOWE = 40_286_094       # ta sama sesja wg wyceny po zmianie normalizacji
    MANIFEST_UTC = "2026-08-06T22:05:38+00:00"

    def _plan(self):
        return [dict(sesja=self.SESJA, start_utc="2026-07-01T13:30:00Z",
                     end_utc="2026-07-01T20:00:00Z", koszt_usd=1.2345,
                     koszt_dokladny=1.2345, rekordow=self.NOWE)]

    def _stary_manifest(self, tmp_path, monkeypatch, wyniki=None):
        cel = tmp_path / "manifests" / f.MANIFEST
        cel.parent.mkdir(parents=True, exist_ok=True)
        cel.write_text(json.dumps({
            "pobrano_utc": self.MANIFEST_UTC,
            "plan": [{"sesja": self.SESJA, "rekordow": self.STARE}],
            "wyniki": wyniki or []}), encoding="utf-8")
        monkeypatch.setattr(f, "sciezka_manifestu", lambda: cel)
        return cel

    def _sciezka(self, tmp_path, monkeypatch) -> Path:
        p = tmp_path / f"mnq_mbo_rth_{self.SESJA}.dbn.zst"
        p.write_bytes(b"x")
        monkeypatch.setattr(f, "sciezka_istniejaca", lambda _s: p)
        return p

    # ------------------------------------------------ pomiar w kompletny --

    def test_kompletny_odklada_zmierzona_liczbe(self, tmp_path, monkeypatch):
        """`zmierzone` niesie POMIAR — inaczej synteza musialaby zgadywac,
        ktora z dwoch dopuszczalnych liczb pasowala do pliku."""
        p = self._sciezka(tmp_path, monkeypatch)
        monkeypatch.setattr(f.db.DBNStore, "from_file",
                            staticmethod(lambda _: range(self.STARE)))
        zm: dict[str, int] = {}
        ok, _ = f.kompletny(p, self.NOWE, self.STARE, zmierzone=zm)
        assert ok
        assert zm[str(p)] == self.STARE

    def test_zmierzone_nie_zmienia_werdyktu(self, tmp_path, monkeypatch):
        """Parametr jest wylacznie obserwacyjny — nie wolno mu niczego uznac."""
        p = self._sciezka(tmp_path, monkeypatch)
        monkeypatch.setattr(f.db.DBNStore, "from_file",
                            staticmethod(lambda _: range(123)))
        bez = f.kompletny(p, self.NOWE, self.STARE)
        z = f.kompletny(p, self.NOWE, self.STARE, zmierzone={})
        assert bez == z
        assert bez[0] is False

    # ------------------------------------------------------- synteza -----

    def test_syntetyzuje_wpis_gdy_wyniki_puste(self, tmp_path, monkeypatch):
        """Wlasciwy stan z maszyny wlasciciela: `wyniki[]` puste."""
        self._stary_manifest(tmp_path, monkeypatch)
        p = self._sciezka(tmp_path, monkeypatch)
        out = f.syntetyzuj_wyniki([self.SESJA], self._plan(),
                                  {str(p): self.STARE}, [])
        assert len(out) == 1
        w = out[0]
        assert w["sesja"] == self.SESJA
        assert w["kompletny"] is True
        assert w["rekordow"] == self.STARE, \
            "wpis musi niesc liczbe ZMIERZONA w pliku"
        assert w["pochodzenie"], "brak jawnego znacznika pochodzenia"

    def test_zapisuje_pomiar_a_nie_liczbe_z_planu(self, tmp_path, monkeypatch):
        """Trzy rozne liczby w grze — wpis musi wziac te z pliku.

        `plan[]` niesie oczekiwanie biezacej wyceny, `oplacone` jedna z dwoch
        liczb dopuszczalnych. Tylko pomiar opisuje plik, a wpis mowi
        `kompletny: true` wlasnie o pliku.
        """
        self._stary_manifest(tmp_path, monkeypatch)
        p = self._sciezka(tmp_path, monkeypatch)
        out = f.syntetyzuj_wyniki([self.SESJA], self._plan(),
                                  {str(p): self.STARE}, [])
        assert out[0]["rekordow"] != self.NOWE

    def test_nie_dubluje_sesji_opisanej_przez_przeniesienie(
            self, tmp_path, monkeypatch):
        """Gdy stary manifest ma juz wpis, synteza milczy."""
        self._stary_manifest(tmp_path, monkeypatch)
        p = self._sciezka(tmp_path, monkeypatch)
        przeniesione = [{"sesja": self.SESJA, "rekordow": self.STARE,
                         "kompletny": True}]
        out = f.syntetyzuj_wyniki([self.SESJA], self._plan(),
                                  {str(p): self.STARE}, przeniesione)
        assert out == []

    def test_brak_pomiaru_nie_produkuje_wpisu(self, tmp_path, monkeypatch,
                                              capsys):
        """Bez pomiaru NIE zmyslamy liczby — lepiej brak wpisu i ostrzezenie."""
        self._stary_manifest(tmp_path, monkeypatch)
        self._sciezka(tmp_path, monkeypatch)
        out = f.syntetyzuj_wyniki([self.SESJA], self._plan(), {}, [])
        assert out == []
        assert "UWAGA" in capsys.readouterr().out

    def test_backfill_normalizacji_z_manifestu(self, tmp_path, monkeypatch):
        """Znacznik epoki bierzemy z `pobrano_utc` manifestu — nie zgadujemy."""
        self._stary_manifest(tmp_path, monkeypatch)
        p = self._sciezka(tmp_path, monkeypatch)
        out = f.syntetyzuj_wyniki([self.SESJA], self._plan(),
                                  {str(p): self.STARE}, [])
        assert out[0]["normalizacja"] == "przed-2026-08-08"

    def test_bez_pobrano_utc_epoka_nieustalona(self, tmp_path, monkeypatch):
        """Brak znacznika to "NIEUSTALONA", a nie domysl."""
        cel = tmp_path / "manifests" / f.MANIFEST
        cel.parent.mkdir(parents=True, exist_ok=True)
        cel.write_text(json.dumps({"plan": [], "wyniki": []}),
                       encoding="utf-8")
        monkeypatch.setattr(f, "sciezka_manifestu", lambda: cel)
        p = self._sciezka(tmp_path, monkeypatch)
        out = f.syntetyzuj_wyniki([self.SESJA], self._plan(),
                                  {str(p): self.STARE}, [])
        assert out[0]["normalizacja"] == "NIEUSTALONA"

    # ------------------------------------------- regresja end-to-end -----

    def test_po_syntezie_ochrona_przezywa_nadpisanie_planu(
            self, tmp_path, monkeypatch):
        """SEDNO. Manifest po biegu ma `plan[]` z NOWYMI liczbami — a ochrona
        starego pliku ma nadal dzialac.

        Odtwarza dokladnie stan z maszyny wlasciciela: `wyniki[]` puste,
        liczba wylacznie w `plan[]`. Po zapisie manifestu z synteza liczba
        siedzi w `wyniki[]` i nadpisany `plan[]` juz jej nie dotyczy.
        """
        cel = self._stary_manifest(tmp_path, monkeypatch)
        p = self._sciezka(tmp_path, monkeypatch)

        przeniesione = f.przeniesione_wyniki([self.SESJA])
        assert przeniesione == [], "warunek wyjsciowy: stare `wyniki[]` puste"
        syntetyczne = f.syntetyzuj_wyniki([self.SESJA], self._plan(),
                                          {str(p): self.STARE}, przeniesione)

        # Zapis manifestu tak, jak robi to bieg zakupowy: `plan[]` NADPISANY
        # nowymi liczbami, `wyniki[]` = przeniesione + syntetyczne + pobrane.
        cel.write_text(json.dumps({
            "pobrano_utc": "2026-08-20T10:00:00+00:00",
            "plan": [{"sesja": self.SESJA, "rekordow": self.NOWE}],
            "wyniki": przeniesione + syntetyczne}), encoding="utf-8")

        assert f.liczby_oplacone()[self.SESJA] == self.STARE, \
            ("po nadpisaniu `plan[]` ochrona czytalaby nowa liczbe — to jest "
             "dokladnie ta luka, ktora zglosila recenzja P1")

        monkeypatch.setattr(f.db.DBNStore, "from_file",
                            staticmethod(lambda _: range(self.STARE)))
        ok, powod = f.kompletny(p, self.NOWE,
                                f.liczby_oplacone().get(self.SESJA))
        assert ok, f"bieg wznowieniowy kupilby oplacona sesje ponownie: {powod}"

    def test_bez_syntezy_ochrona_ginie(self, tmp_path, monkeypatch):
        """Kontrola przeciwna: poprawka realnie zmienia wynik.

        Ten sam scenariusz z pustym `syntetyczne` — plik wypada jako
        niekompletny, czyli trafia pod `out.unlink()`.
        """
        cel = self._stary_manifest(tmp_path, monkeypatch)
        p = self._sciezka(tmp_path, monkeypatch)
        cel.write_text(json.dumps({
            "plan": [{"sesja": self.SESJA, "rekordow": self.NOWE}],
            "wyniki": []}), encoding="utf-8")

        assert f.liczby_oplacone()[self.SESJA] == self.NOWE
        monkeypatch.setattr(f.db.DBNStore, "from_file",
                            staticmethod(lambda _: range(self.STARE)))
        ok, _ = f.kompletny(p, self.NOWE, f.liczby_oplacone().get(self.SESJA))
        assert not ok, ("bez syntezy plik MUSI wypasc jako niekompletny — "
                        "inaczej test nie dowodzi, ze poprawka cokolwiek robi")
