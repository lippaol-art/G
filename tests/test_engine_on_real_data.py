"""BRAMKA SILNIKA na realnych danych — PLAN.pdf rozdz. 5.6.

    "Silnik, ktoremu nie udowodniono poprawnosci, produkuje smieci
     z dokladnoscia do szesciu miejsc po przecinku."

Testy jednostkowe (pozostale pliki w tests/) dowodza, ze pojedyncze funkcje
robia to, co napisano w tabelach. Ten plik dowodzi czegos innego i mocniejszego:
ze ZLOZENIE tych funkcji, przepuszczone przez 2.5 mln realnych barow MNQ,
mierzy rynek, a nie samo siebie. Fixture'y testowe tego nie wykryja — przeciek
informacji, blad znaku w P&L czy zgubione koszty ujawniaja sie dopiero na skali
i na danych, ktorych nikt nie skonstruowal pod teze.

Cztery testy, kazdy z rozdz. 5.6:

  1. ZEROWA PRZEWAGA — losowe wejscia musza dac wynik nieodroznialny od zera
     przed kosztami. Kazda dodatnia przewaga w tym miejscu jest przeciekiem
     informacji z przyszlosci, bo moneta nie wie nic o rynku.
  2. ZNANY EFEKT — asymetria overnight/intraday na indeksach US jest jednym
     z najlepiej udokumentowanych faktow empirycznych. To nie jest nasza
     strategia; to linijka, ktora sprawdza, czy silnik w ogole mierzy.
  3. SYMETRIA — odwrocenie kazdej reguly long<->short musi dac wynik lustrzany
     przed kosztami. Rozjazd oznacza asymetryczny blad w ksiegowaniu stron.
  4. DETERMINIZM — dwa przebiegi z tym samym ziarnem bitowo identyczne.

BEZ KOMPLETU ZIELONYCH NIE RUSZAMY DALEJ. Zaden backtest hipotezy nie ma prawa
powstac przed ta bramka — wynik z niesprawdzonego silnika jest gorszy niz brak
wyniku, bo wyglada na wiedze.
"""

from __future__ import annotations

import hashlib
from datetime import timedelta

import numpy as np
import pytest

from engine.backtest import (
    CostModel,
    Order,
    RiskLimits,
    run_backtest,
)
from engine.loader import is_available, load_continuous, to_bars

pytestmark = pytest.mark.needs_data

SYMBOL = "MNQ"

if not is_available(SYMBOL):
    pytest.skip(
        f"Brak data/clean/{SYMBOL.lower()}_1m_cont.parquet — bramka 5.6 wymaga "
        "realnych danych. Procedura pobrania: HANDOFF.md, sekcja 'Etap 1'.",
        allow_module_level=True,
    )


# ==========================================================================
# Wspolne: dane i tryb "przed kosztami"
# ==========================================================================

@pytest.fixture(scope="module")
def bars():
    """2.5 mln barow M1 MNQ na serii SKORYGOWANEJ (px_adj).

    Zakres modulowy, bo budowa listy to ~35 s — powtarzanie jej dla kazdego
    testu zamienialoby bramke w test cierpliwosci.
    """
    return to_bars(load_continuous(SYMBOL), price="adj")


#: Tryb "przed kosztami" z rozdz. 5.6. Zero prowizji i zero poslizgu.
#: Wystepuje WYLACZNIE w tym pliku: testy 1 i 3 pytaja o wlasnosci samego
#: pomiaru, a te musza byc widoczne bez warstwy kosztow, ktora je maskuje.
PRZED_KOSZTAMI = dict(
    cost_model=CostModel(commission_rt=0.0),
    slippage_model=lambda bar: 0.0,
)

#: Limity ryzyka wylaczone. Strategia losowa nie jest strategia — gdyby limit
#: -2R uciszal ja po zlej serii, mierzylibysmy limit, nie silnik.
BEZ_LIMITOW = RiskLimits(daily_stop_r=1e9, weekly_stop_r=1e9, require_stop=False)


class LosoweWejscia:
    """Moneta: kierunek losowy, SL/TP losowe i symetryczne (rozdz. 5.6 pkt 2).

    Nie patrzy na nic poza wlasnym generatorem — z zalozenia nie moze miec
    przewagi. `flip` odwraca kazda regule kierunkowa, nie zmieniajac ani jednego
    losowania: to warunek konieczny testu symetrii, bo inaczej porownywalibysmy
    dwa rozne zbiory wejsc.
    """

    def __init__(self, seed: int, p: float = 0.001, *, bracket: bool = True,
                 flip: bool = False, zakres: tuple[float, float] = (10.0, 40.0)):
        self.rng = np.random.default_rng(seed)
        self.p = p
        self.bracket = bracket
        self.flip = flip
        self.zakres = zakres

    def on_bar(self, bar, history, state):
        if state.get("position_side") is not None:
            return []
        if self.rng.random() >= self.p:
            return []
        long = self.rng.random() < 0.5
        d = float(self.rng.uniform(*self.zakres))   # losujemy zawsze — inaczej
        if self.flip:                               # strumien rng rozjechalby sie
            long = not long                         # miedzy wariantem i lustrem
        side = "long" if long else "short"
        if not self.bracket:
            return [Order(side=side, sl=None, tag="rnd")]
        px = bar.close
        return [Order(side=side,
                      sl=px - d if long else px + d,
                      tp=px + d if long else px - d,
                      tag="rnd")]


class NogaSegmentu:
    """Wejscie na PIERWSZYM barze segmentu `wejscie`; wyjscie przez `force_flat`.

    Rozpoznanie "pierwszy bar segmentu" opiera sie na segmencie bara poprzedniego
    zapamietanym w stanie — nie na zagladaniu w przod. Silnik i tak fizycznie
    na to nie pozwala (HistoryView), ale regula musi byc poprawna takze wtedy,
    gdyby ktos ja przeniosl do petli live.
    """

    def __init__(self, wejscie: str):
        self.wejscie = wejscie

    def on_bar(self, bar, history, state):
        poprzedni = state.get("prev_seg")
        state["prev_seg"] = bar.segment
        if state.get("position_side") is not None:
            return []
        if bar.segment == self.wejscie and poprzedni != self.wejscie:
            return [Order(side="long", sl=None, tag=self.wejscie)]
        return []


def _flat_na(segment: str):
    return lambda bar, pos: bar.segment == segment


def _odcisk(result) -> str:
    """Skrot pelnej listy transakcji — podstawa testu determinizmu.

    Porownanie sum bylo by za slabe: dwa rozne zbiory transakcji moga dac ten sam
    wynik. Skrot obejmuje kazde pole kazdej transakcji w `repr` zmiennoprzecinkowym,
    wiec rownosc skrotow oznacza rownosc bitowa.
    """
    tresc = "".join(
        f"{t.side}|{t.entry_ts}|{t.entry_px!r}|{t.exit_ts}|{t.exit_px!r}|"
        f"{t.pnl_points!r}|{t.pnl_usd!r}|{t.r_multiple!r}|{t.exit_reason}\n"
        for t in result.trades
    )
    return hashlib.sha256(tresc.encode()).hexdigest()


# ==========================================================================
# TEST 1 — ZEROWA PRZEWAGA
# ==========================================================================

class TestZerowaPrzewaga:
    """Moneta nie moze zarabiac. Jesli zarabia, silnik zna przyszlosc."""

    SEEDS = (1, 2, 3, 7, 42)

    @staticmethod
    @pytest.fixture(scope="class")
    def przebiegi(bars):
        return [
            run_backtest(bars, LosoweWejscia(s), risk=BEZ_LIMITOW, **PRZED_KOSZTAMI)
            for s in TestZerowaPrzewaga.SEEDS
        ]

    def test_proba_jest_dostatecznie_liczna(self, przebiegi):
        """Ponizej podlogi z rozdz. 6.4 test nie ma mocy odrzucic niczego."""
        for seed, r in zip(TestZerowaPrzewaga.SEEDS, przebiegi, strict=True):
            assert len(r.trades) >= 400, (
                f"seed {seed}: {len(r.trades)} transakcji to za malo, by test "
                "cokolwiek wykryl (podloga 400 z rozdz. 6.4)"
            )

    def test_brak_dodatniej_przewagi_w_zadnym_ziarnie(self, przebiegi):
        """Kluczowa asercja calej bramki.

        Jednostronnie: szukamy PRZECIEKU, a przeciek zawsze objawia sie zyskiem.
        Wynik lekko ujemny jest oczekiwany i pozadany — regula "SL wygrywa"
        w barze spornym oraz wymog przebicia limitu o tick to swiadome
        konserwatyzmy z tabeli 5.4, ktore musza ciagnac wynik w dol.
        """
        for seed, r in zip(TestZerowaPrzewaga.SEEDS, przebiegi, strict=True):
            p = np.array([t.pnl_usd_gross for t in r.trades])
            t_stat = p.mean() / p.std(ddof=1) * np.sqrt(len(p))
            assert t_stat < 2.5, (
                f"seed {seed}: losowe wejscia daja t={t_stat:.2f} — moneta nie ma "
                f"prawa zarabiac. To sygnatura przecieku informacji (lookahead, "
                f"zle przypisany bar wykonania, wyjscie po cenie z przyszlosci)."
            )

    def test_lacznie_po_ziarnach_wynik_nieodrozninalny_od_zera(self, przebiegi):
        """Pojedyncze ziarno moze trafic w ogon; pieciokrotna proba juz nie."""
        p = np.concatenate([[t.pnl_usd_gross for t in r.trades] for r in przebiegi])
        t_stat = p.mean() / p.std(ddof=1) * np.sqrt(len(p))
        assert abs(t_stat) < 3.0, (
            f"lacznie {len(p)} losowych transakcji daje t={t_stat:.2f}. "
            "Odchylenie w KAZDA strone jest podejrzane: dodatnie to przeciek, "
            "silnie ujemne oznacza, ze cos oprocz konserwatyzmow zjada wynik."
        )

    def test_koszty_naliczaja_sie_co_do_centa(self, bars):
        """Tozsamosc ksiegowa: netto = brutto - prowizja x liczba transakcji.

        Test celowo NIE korzysta z trybu przed kosztami — sprawdza wlasnie te
        warstwe, ktora tamten tryb wylacza.
        """
        r = run_backtest(bars, LosoweWejscia(5), risk=BEZ_LIMITOW)
        n = len(r.trades)
        assert n > 0
        assert r.commission_usd == pytest.approx(1.20 * n, abs=1e-6), \
            "prowizja musi byc naliczona dokladnie raz na transakcje (rozdz. 3.2)"
        assert r.net_usd == pytest.approx(r.gross_usd - 1.20 * n, abs=1e-6)
        assert r.net_usd < r.gross_usd, "koszty nie moga poprawiac wyniku"

    def test_poslizg_zawsze_pogarsza_wykonanie(self, bars, przebiegi):
        """Ten sam zbior wejsc z poslizgiem musi dac wynik gorszy, nigdy lepszy.

        Poslizg zyje w cenach wejscia i wyjscia, nie w oplacie — blad znaku
        w jednym z tych dwoch miejsc jest niewidoczny w testach jednostkowych,
        bo tam kwoty sa male i moga sie przypadkiem znosic.
        """
        z_poslizgiem = run_backtest(
            bars, LosoweWejscia(1), risk=BEZ_LIMITOW,
            cost_model=CostModel(commission_rt=0.0),
        )
        bez = przebiegi[0]
        assert len(z_poslizgiem.trades) == len(bez.trades), \
            "poslizg nie moze zmieniac liczby transakcji, tylko ich ceny"
        assert z_poslizgiem.gross_usd < bez.gross_usd, (
            f"z poslizgiem {z_poslizgiem.gross_usd:.0f} USD, bez {bez.gross_usd:.0f} USD "
            "— poslizg poprawil wynik, czyli ma odwrocony znak"
        )

    def test_pozycja_nigdy_nie_zamyka_sie_w_barze_wejscia(self, przebiegi):
        """Regula z tabeli 5.4: w barze wejscia znamy fakt wypelnienia,
        ale nie trajektorie ceny po nim. Zamkniecie w tym samym barze byloby
        zgadywaniem kolejnosci, ktorej dane M1 nie zawieraja."""
        for r in przebiegi:
            for t in r.trades:
                assert t.exit_ts > t.entry_ts, (
                    f"transakcja zamknieta w barze wejscia ({t.entry_ts}) — "
                    "silnik zgaduje kolejnosc zdarzen wewnatrz minuty"
                )


# ==========================================================================
# TEST 2 — ZNANY EFEKT (linijka, nie strategia)
# ==========================================================================

class TestZnanegoEfektu:
    """Asymetria overnight/intraday na indeksach US.

    Fakt empiryczny udokumentowany niezaleznie wiele razy (Cooper-Cliff-Gulen
    2008; Lou-Polk-Skouras 2019; NY Fed): praktycznie caly zwrot indeksow
    akcyjnych USA powstaje POZA sesja kasowa. Nie testujemy tu, czy da sie na
    tym zarobic — testujemy, czy silnik potrafi ten ksztalt w ogole zmierzyc.

    UWAGA METODOLOGICZNA: to NIE jest test hipotezy H004 i nie zuzywa licznika
    prob. Pytanie, czy dryf nocny wygasl po 2020 roku (teza z audytu 3), nalezy
    do badania W001 i wymaga rozbicia na lata — tutaj patrzymy na caly zakres,
    bo linijka ma byc stabilna, nie czula na rezim.
    """

    @staticmethod
    @pytest.fixture(scope="class")
    def nogi(bars):
        overnight = run_backtest(
            bars, NogaSegmentu("after_hours"), risk=BEZ_LIMITOW,
            force_flat=_flat_na("rth_open"), **PRZED_KOSZTAMI,
        )
        intraday = run_backtest(
            bars, NogaSegmentu("rth_open"), risk=BEZ_LIMITOW,
            force_flat=_flat_na("after_hours"), **PRZED_KOSZTAMI,
        )
        return overnight, intraday

    def test_obie_nogi_pokrywaja_caly_zakres_danych(self, nogi):
        overnight, intraday = nogi
        for nazwa, r in (("overnight", overnight), ("intraday", intraday)):
            assert len(r.trades) > 1500, \
                f"noga {nazwa}: {len(r.trades)} dni to nie jest caly zakres 2019-2026"
        assert abs(len(overnight.trades) - len(intraday.trades)) <= 5, \
            "nogi musza obejmowac te same dni sesyjne, inaczej porownanie jest pozorne"

    def test_dryf_nocny_dominuje_nad_sesyjnym(self, nogi):
        """Znak asymetrii — najmocniejsza czesc linijki.

        Odwrocony znak oznacza, ze silnik myli otwarcie z zamknieciem albo
        strone pozycji. Zaden test jednostkowy tego nie zlapie, bo na trzech
        recznych barach obie pomylki wygladaja poprawnie.
        """
        overnight, intraday = nogi
        on = sum(t.pnl_points for t in overnight.trades)
        idd = sum(t.pnl_points for t in intraday.trades)
        assert on > 0, f"dryf nocny wyszedl ujemny ({on:.0f} pkt) — sprzeczne z literatura"
        assert on > idd, (
            f"overnight {on:.0f} pkt vs intraday {idd:.0f} pkt — silnik nie odtwarza "
            "asymetrii, ktora jest jednym z najlepiej udokumentowanych faktow "
            "empirycznych o indeksach USA"
        )

    def test_rzad_wielkosci_zgodny_z_literatura(self, nogi):
        """Nie tylko znak: udzial nocy w calosci ruchu musi byc DUZY.

        Przedzial [0.5, 1.5] jest szeroki celowo — waski bylby dopasowaniem
        do naszej probki, a nie sprawdzianem silnika. Wartosci powyzej 1.0 sa
        dopuszczalne i wystepuja w literaturze: przy ujemnej nodze sesyjnej
        noc odpowiada za wiecej niz 100% zwrotu.
        """
        overnight, intraday = nogi
        on = sum(t.pnl_points for t in overnight.trades)
        idd = sum(t.pnl_points for t in intraday.trades)
        udzial = on / (on + idd)
        assert 0.5 <= udzial <= 1.5, (
            f"noc odpowiada za {udzial:.0%} lacznego ruchu — poza rzedem wielkosci "
            "raportowanym w literaturze dla indeksow USA"
        )

    def test_efekt_jest_widoczny_statystycznie(self, nogi):
        """Efekt o t < 1 na siedmiu latach danych bylby podejrzany jako linijka —
        oznaczalby, ze mierzymy szum, a nie udokumentowany fakt."""
        overnight, _ = nogi
        p = np.array([t.pnl_points for t in overnight.trades])
        t_stat = p.mean() / p.std(ddof=1) * np.sqrt(len(p))
        assert t_stat > 1.0, f"dryf nocny t={t_stat:.2f} — ponizej progu widocznosci"

    def test_wynik_silnika_zgadza_sie_z_rachunkiem_niezaleznym(self, bars, nogi):
        """NAJMOCNIEJSZY TEST W CALYM PLIKU.

        Ta sama regula policzona drugi raz, poza silnikiem, wprost na tablicy
        barow. Jesli silnik ma blad w ksiegowaniu — zla cena wejscia, przesuniety
        bar wykonania, zgubiona transakcja — obie liczby sie rozjada. Zgodnosc
        co do grosza na 1800 transakcjach nie moze byc przypadkiem.
        """
        overnight, _ = nogi

        # Odtworzenie reguly "wejscie po open bara PO pierwszym barze after_hours,
        # wyjscie po close pierwszego bara rth_open" — bez uzycia silnika.
        wejscia: list[float] = []
        wyjscia: list[float] = []
        czeka = False
        w_pozycji = False
        poprzedni_seg = None
        for b in bars:
            if czeka and b.volume > 0:
                wejscia.append(b.open)
                czeka, w_pozycji = False, True
            elif czeka:
                czeka = False
            if w_pozycji and b.segment == "rth_open" and len(wyjscia) < len(wejscia):
                wyjscia.append(b.close)
                w_pozycji = False
            if (not w_pozycji and not czeka
                    and b.segment == "after_hours" and poprzedni_seg != "after_hours"):
                czeka = True
            poprzedni_seg = b.segment

        n = len(wyjscia)
        recznie = sum(wyjscia[i] - wejscia[i] for i in range(n))
        silnik = sum(t.pnl_points for t in overnight.trades[:n])
        assert n == len(overnight.trades), \
            f"rachunek niezalezny widzi {n} transakcji, silnik {len(overnight.trades)}"
        assert recznie == pytest.approx(silnik, abs=0.01), (
            f"silnik: {silnik:.2f} pkt, rachunek niezalezny: {recznie:.2f} pkt — "
            "rozjazd oznacza blad w ksiegowaniu wykonania"
        )


# ==========================================================================
# TEST 3 — SYMETRIA
# ==========================================================================

class TestSymetrii:
    """long <-> short musi dac wynik lustrzany PRZED kosztami.

    Test uzywa wyjscia czasowego, bez SL i TP — i to jest decyzja projektowa,
    nie uproszczenie. Z bracketem lustro NIE moglo by byc dokladne: bar dotykajacy
    obu poziomow rozstrzygamy na korzysc stopa (tabela 5.4), wiec ten sam bar
    daje strate ZAROWNO longowi, jak i shortowi. Ta asymetria jest zamierzona
    i konserwatywna; mieszanie jej z testem symetrii ksiegowania zamazaloby
    obie rzeczy naraz.
    """

    @staticmethod
    @pytest.fixture(scope="class")
    def para(bars):
        wspolne = dict(
            risk=BEZ_LIMITOW,
            force_flat=lambda bar, pos: (bar.ts - pos.entry_ts) >= timedelta(minutes=30),
            **PRZED_KOSZTAMI,
        )
        a = run_backtest(bars, LosoweWejscia(11, 0.0008, bracket=False), **wspolne)
        b = run_backtest(bars, LosoweWejscia(11, 0.0008, bracket=False, flip=True), **wspolne)
        return a, b

    def test_te_same_wejscia_w_obu_wariantach(self, para):
        """Warunek konieczny: lustro ma odwracac strone, a nie zbior wejsc."""
        a, b = para
        assert len(a.trades) == len(b.trades) > 400
        for x, y in zip(a.trades, b.trades, strict=True):
            assert x.entry_ts == y.entry_ts
            assert x.exit_ts == y.exit_ts
            assert x.side != y.side, "lustro nie odwrocilo strony"

    def test_wynik_jest_dokladnie_lustrzany(self, para):
        """Rownosc DOKLADNA, nie przyblizona.

        Przy zerowym poslizgu obie strony wchodza i wychodza po tych samych
        cenach, wiec P&L musi sie znosic co do bitu. Tolerancja w tym miejscu
        przepuscilaby drobny blad znaku, ktory na dlugiej serii urosnie.
        """
        a, b = para
        pa = np.array([t.pnl_usd_gross for t in a.trades])
        pb = np.array([t.pnl_usd_gross for t in b.trades])
        assert np.abs(pa + pb).max() == 0.0, (
            f"maksymalny rozjazd lustra: {np.abs(pa + pb).max()} USD — "
            "ksiegowanie strony long i short nie jest symetryczne"
        )
        assert a.gross_usd + b.gross_usd == 0.0

    def test_lustro_nie_jest_trywialne(self, para):
        """Dwa zerowe wyniki tez sa lustrzane. Test bez tej asercji nie dowodzi
        niczego — musi istniec cos, co mialo szanse sie rozjechac."""
        a, _ = para
        assert abs(a.gross_usd) > 0.0
        assert np.count_nonzero([t.pnl_usd_gross for t in a.trades]) > 300


# ==========================================================================
# TEST 4 — DETERMINIZM
# ==========================================================================

class TestDeterminizmu:
    """Wynik nieodtwarzalny nie jest wynikiem.

    Cala konstrukcja DSR opiera sie na zliczaniu prob. Jesli ta sama proba
    uruchomiona dwa razy daje dwie liczby, licznik prob mierzy fikcje,
    a wraz z nim caly aparat z rozdz. 6.5.
    """

    def test_dwa_przebiegi_z_tym_samym_ziarnem_sa_identyczne(self, bars):
        wspolne = dict(risk=BEZ_LIMITOW, **PRZED_KOSZTAMI)
        a = run_backtest(bars, LosoweWejscia(2024), **wspolne)
        b = run_backtest(bars, LosoweWejscia(2024), **wspolne)
        assert _odcisk(a) == _odcisk(b), "ten sam seed dal inne transakcje"
        assert a.equity == b.equity, "krzywa kapitalu rozni sie miedzy przebiegami"
        assert (a.ambiguous_bars, a.skipped_zero_volume, a.rejected_orders) == \
               (b.ambiguous_bars, b.skipped_zero_volume, b.rejected_orders)

    def test_inne_ziarno_daje_inny_wynik(self, bars):
        """Kontrola przeciwna: gdyby silnik ignorowal ziarno, poprzedni test
        przechodzilby zawsze — takze wtedy, gdy strategia nic nie losuje."""
        wspolne = dict(risk=BEZ_LIMITOW, **PRZED_KOSZTAMI)
        a = run_backtest(bars, LosoweWejscia(2024), **wspolne)
        c = run_backtest(bars, LosoweWejscia(2025), **wspolne)
        assert _odcisk(a) != _odcisk(c), "zmiana ziarna nie zmienila nic — seed jest martwy"
