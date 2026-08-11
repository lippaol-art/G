"""Straznik mikro-diffu — testy o cenie w USD i o waznosci werdyktu.

Ten skrypt raz juz wydal 0,0789 USD i na jego wyniku stoi decyzja, ze NIE
odkupujemy czterech sesji za ~13 USD. Testy pilnuja dwoch rzeczy:

  1. **Klucz porownania.** Gdyby wszedl do niego `sequence` (numer wiadomosci
     CME, nie identyfikator zdarzenia), kazda zmiana pakowania komunikatow
     wygladalaby jak inne zdarzenie i test Z GORY dawalby wariant A. Test,
     ktory nie moze dac drugiej odpowiedzi, nie jest testem.

  2. **Tryb `--flagi` jest darmowy.** Ma czytac wylacznie pliki z dysku.
     Gdyby siegnal do sieci, uruchomienie go bez zgody R1 byloby zakupem.

Rekordy w tych testach sa recznie skonstruowane — to fixture'y testowe,
nie dane rynkowe (rozroznienie z `docs/ZALOZENIA.md`). Zaden wniosek o rynku
z nich nie powstaje; sprawdzaja wylacznie poprawnosc kodu.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

KORZEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORZEN))

from scripts import diff_mikro as d  # noqa: E402

UTC = dt.UTC
OD = int(dt.datetime(2026, 7, 3, 13, 30, tzinfo=UTC).timestamp() * 1e9)
DO = int(dt.datetime(2026, 7, 3, 14, 0, tzinfo=UTC).timestamp() * 1e9)

#: UNDEF_PRICE w DBN — tyle nosza rekordy `action=N` z mikro-diffu 09.08.
UNDEF_PRICE = 9223372036854775807


def rekord(ts_recv, *, order_id=1, action="A", side="B", price=100, size=1,
           sequence=0, flags=0):
    return SimpleNamespace(ts_recv=ts_recv, order_id=order_id, action=action,
                           side=side, price=price, size=size,
                           sequence=sequence, flags=flags)


# --- 1. klucz tozsamosci ---------------------------------------------------

def test_klucz_ignoruje_sequence():
    """Dwa rekordy roznjace sie WYLACZNIE `sequence` to ten sam rekord.

    To jest cala roznica miedzy werdyktem B' a bezpodstawnym odkupem za 13 USD.
    """
    a = rekord(OD, sequence=1)
    b = rekord(OD, sequence=999_999)
    assert d.klucz(a) == d.klucz(b)


def test_klucz_ignoruje_flagi():
    """`flags` tez nie wchodzi do klucza — inaczej rekordy N zaburzalyby diff.

    Flagi analizujemy OSOBNO (tryb --flagi), wlasnie dlatego, ze nie sa
    czescia tozsamosci zdarzenia.
    """
    assert d.klucz(rekord(OD, flags=0)) == d.klucz(rekord(OD, flags=128))


@pytest.mark.parametrize("pole,wartosc", [
    ("ts_recv", OD + 1), ("order_id", 2), ("action", "C"),
    ("side", "A"), ("price", 101), ("size", 2),
])
def test_klucz_rozroznia_kazde_pole_tozsamosci(pole, wartosc):
    """Szesc pol klucza musi realnie roznicowac — inaczej diff by je sklejal."""
    inny = rekord(OD)
    setattr(inny, pole, wartosc)
    assert d.klucz(rekord(OD)) != d.klucz(inny)


# --- 2. rozklad flag na bity ------------------------------------------------

def test_opis_flag_rozklada_znane_bity():
    assert d.opis_flag(128) == "F_LAST"
    assert d.opis_flag(128 | 64) == "F_LAST|F_TOB"
    assert d.opis_flag(0) == "(brak bitow)"


def test_opis_flag_nie_gubi_bitu_spoza_slownika():
    """Nieznany bit ma byc WIDOCZNY, a nie po cichu zjedzony.

    Milczace pomijanie bitu, ktorego nie znamy, jest dokladnie tym rodzajem
    bledu, przez ktory przeoczylibysmy zmiane po stronie dostawcy.
    """
    opis = d.opis_flag(128 | 1)
    assert "F_LAST" in opis and "+1" in opis


# --- 3. histogram flag wg akcji --------------------------------------------

def test_flagi_wg_akcji_grupuje_i_tnie_okno(monkeypatch):
    rekordy = [
        rekord(OD, action="A", flags=0),
        rekord(OD + 5, action="A", flags=128),
        rekord(OD + 6, action="N", order_id=0, side="N", size=0,
               price=UNDEF_PRICE, flags=0),
        rekord(DO, action="A", flags=0),        # POZA oknem — do odciecia
        rekord(OD - 1, action="A", flags=0),    # POZA oknem — do odciecia
    ]
    monkeypatch.setattr(d.db.DBNStore, "from_file",
                        staticmethod(lambda p: rekordy))

    wynik = d.flagi_wg_akcji(Path("nieistotne"), OD, DO)

    assert set(wynik) == {"A", "N"}
    assert wynik["A"] == {0: 1, 128: 1}
    assert wynik["N"] == {0: 1}


def test_flagi_pomijaja_rekordy_bez_ts_recv(monkeypatch):
    """Rekord bez `ts_recv` nie ma jak trafic do okna — musi wypasc, nie wybuchnac."""
    monkeypatch.setattr(
        d.db.DBNStore, "from_file",
        staticmethod(lambda p: [SimpleNamespace(action="A", flags=0)]))
    assert d.flagi_wg_akcji(Path("nieistotne"), OD, DO) == {}


# --- 4. tryb --flagi ma byc DARMOWY ----------------------------------------

def test_raport_rekonstrukcji_porownuje_akcje_a_nie_rekordy():
    """Werdykt o audycie D5-C ma zapadac na JEDNOSTCE OBSERWACJI.

    Histogram flag nie widzi kolejnosci rekordow, wiec granica koperty
    przeniesiona na wypelniacz (skutek zerowy) i wstawiona w srodek ciagu
    (skutek powazny) daja w nim te same liczby. Tryb --rekonstrukcja musi
    wiec przechodzic przez `rekonstruuj`, nie przez liczniki.
    """
    import inspect
    zrodlo = inspect.getsource(d.raport_rekonstrukcji)
    assert "rekonstruuj(" in zrodlo and "z_dbn(" in zrodlo


def test_raport_rekonstrukcji_nie_dotyka_sieci():
    import inspect
    zrodlo = inspect.getsource(d.raport_rekonstrukcji).replace(
        d.raport_rekonstrukcji.__doc__, "")
    for zakazane in ("Historical", "get_cost", "get_range", "DATABENTO_API_KEY"):
        assert zakazane not in zrodlo, (
            f"tryb --rekonstrukcja siega po {zakazane} — przestal byc darmowy")


def test_raport_flag_nie_dotyka_sieci():
    """Ani `Historical`, ani `get_cost` nie moga sie pojawic w tej sciezce.

    Test czyta zrodlo, bo alternatywa — uruchomienie funkcji z podstawionym
    klientem — sprawdzalaby tylko ten jeden przebieg. Tu chodzi o wlasnosc
    calej funkcji: ma nie miec czym zaplacic.
    """
    import inspect
    # Docstring odpada — opisuje, czego funkcja NIE robi, i sam zawiera te nazwy.
    zrodlo = inspect.getsource(d.raport_flag).replace(d.raport_flag.__doc__, "")
    for zakazane in ("Historical", "get_cost", "get_range", "DATABENTO_API_KEY"):
        assert zakazane not in zrodlo, (
            f"tryb --flagi siega po {zakazane} — przestal byc darmowy")


def test_limit_pierwszego_okna_zostal_nietkniety():
    """Limit 0,10 USD byl warunkiem 1 zgody z 09.08. Podniesienie go po fakcie
    byloby zmiana specyfikacji po zobaczeniu wyniku (regula R2)."""
    assert d.wybierz_okno("2026-07-03").limit_usd == 0.10


def test_drugie_okno_ma_limit_z_paragrafu_5e():
    """Limit 1,00 USD zapisany w D5_DRYF §5e PRZED biegiem."""
    assert d.wybierz_okno("2026-07-06").limit_usd == 1.00


def test_kazde_okno_ma_wlasny_twardy_limit():
    """Wspolny limit bylby albo bezuzyteczny, albo blokujacy — sesje roznia
    sie rozmiarem dziesieciokrotnie."""
    for sesja in d.OKNA:
        assert d.wybierz_okno(sesja).limit_usd > 0


def test_zakresy_pozostaja_zamrozone():
    """Warunek 2 zgody: 30 minut, granice z rejestru, nie z linii polecen."""
    assert d.wybierz_okno("2026-07-03")[:3] == (
        "2026-07-03", "2026-07-03T13:30", "2026-07-03T14:00")
    assert d.wybierz_okno("2026-07-06")[:3] == (
        "2026-07-06", "2026-07-06T13:30", "2026-07-06T14:00")


@pytest.mark.parametrize("sesja", [
    "2026-07-07", "2026-07-03T13:30", "", "2026-07-03 13:30/20:00"])
def test_okno_spoza_rejestru_jest_TWARDA_ODMOWA(sesja):
    """Parametryzacja NIE moze byc rozluznieniem warunku 2 zgody.

    Zaszycie jednego okna na stale bronilo przed przypadkowym zapytaniem
    o cala sesje (~3 USD zamiast ~0,08). Rejestr ma bronic tak samo: wszystko
    spoza listy konczy sie `SystemExit`, a nie domyslnym oknem.
    """
    with pytest.raises(SystemExit) as e:
        d.wybierz_okno(sesja)
    assert "warunek 2" in str(e.value)


def test_nazwa_pliku_rozroznia_okna():
    """Dwa pomiary NIE moga nadpisac sobie plikow — kazdy kosztowal osobno."""
    a = d.wybierz_okno("2026-07-03").nazwa_pliku
    b = d.wybierz_okno("2026-07-06").nazwa_pliku
    assert a != b
    assert a == "mikro_2026-07-03_1330_1400.dbn.zst"


def test_katalog_diagnostyczny_jest_osobny():
    """Warunek 3 zgody: nie zapisujemy do katalogow zakupowych."""
    assert d.KATALOG_DIAG not in d.KATALOGI_NASZE


def test_sciezka_raportu_rozroznia_okna():
    """Lustro `test_nazwa_pliku_rozroznia_okna` — dla raportu JSON.

    Pliki danych chronila nazwa z sesja, ale raport szedl zawsze pod ta sama
    sciezke. Drugi mikro-diff skasowalby wynik pierwszego, a kazdy kosztowal
    osobno i zaden nie jest odtwarzalny — stara normalizacja jest niedostepna.
    """
    a = d.sciezka_raportu(d.wybierz_okno("2026-07-03"))
    b = d.sciezka_raportu(d.wybierz_okno("2026-07-06"))
    assert a != b


def test_raport_pierwszego_okna_zachowuje_historyczna_nazwe():
    """Plik z 09.08 lezy juz na dysku pod nazwa bez sesji.

    Przemianowanie osierociloby go w chwili, gdy ma trafic do repo — a jest
    jedynym maszynowym sladem pomiaru, ktorego nie da sie powtorzyc.
    """
    assert d.sciezka_raportu(d.wybierz_okno("2026-07-03")) == \
        Path("reports/D5_mikro_diff.json")


def test_kazde_okno_ma_wlasny_raport():
    sciezki = {d.sciezka_raportu(d.wybierz_okno(s)) for s in d.OKNA}
    assert len(sciezki) == len(d.OKNA)
