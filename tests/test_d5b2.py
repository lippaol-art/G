"""Bramka D5-B2 — testy logiki na RECZNIE zbudowanych rekordach.

To sa fixture'y testowe, nie dane rynkowe (rozroznienie z README): zaden
wniosek o rynku z nich nie wynika. Sprawdzaja wylacznie, czy kod robi to,
co mowi zamrozona specyfikacja `docs/D5_ETAP4_SPEC.md`.

Bramka jest jednorazowa: werdyktu nie da sie powtorzyc po zobaczeniu liczb,
wiec kazda regula, ktora go ksztaltuje, ma tu osobny test — w tym te, ktore
wygladaja na oczywiste (przypisanie okna, kolejnosc cen, brakujace okna).
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pytest

from engine import d5b2 as g
from engine.mbo_events import F_LAST, RekordMBO

KORZEN = Path(__file__).resolve().parent.parent
M = g.MIN_NS
LO = 1_000 * M                     # poczatek RTH, wyrownany do minuty
HI = LO + 390 * M                  # 390 okien jak w sesji pelnej
P = 20_000 * 10**9                 # cena w jednostkach DBN


def r(ts, action, side="B", price=P, size=1, oid=1, flags=0, seq=0):
    return (RekordMBO(ts_recv=ts, action=action, side=side, price=price,
                      size=size, order_id=oid, flags=flags), seq)


def akcja(ts, side="B", oid=1, size=1, price=P, seq=0):
    """Najprostsza akcja: Trade + pasywny Fill w jednej kopercie."""
    return [r(ts, "T", side, price, size, oid, seq=seq),
            r(ts, "F", "A" if side == "B" else "B", price, size, oid + 10_000,
              flags=F_LAST, seq=seq)]


# ---------------------------------------------------------------- okna ------
class TestPrzypisanieOkna:
    def test_akcja_trafia_do_minuty_ostatniego_rekordu(self):
        """§1.5 i §2.1: znacznik dostepnosci = `ts_recv` OSTATNIEGO rekordu."""
        rek = [r(LO + 59 * 10**9, "T", "B", oid=7),
               r(LO + 61 * 10**9, "F", "A", oid=8, flags=F_LAST)]
        w = g.przetworz_sesje(rek, (LO, HI))
        m0, m1 = LO // M, LO // M + 1
        assert w.okna[m1].n_buy == 1, "akcja nalezy do minuty ostatniego rekordu"
        assert w.okna[m0].n_buy == 0
        # a rekord `T` liczy sie do bara i momentum we WLASNEJ minucie
        assert w.okna[m0].t_n == 1 and w.okna[m1].t_n == 0

    def test_akcja_nie_jest_dzielona_miedzy_okna(self):
        rek = [r(LO + 59 * 10**9, "T", "B", oid=7),
               r(LO + 59 * 10**9, "T", "B", oid=7),
               r(LO + 61 * 10**9, "F", "A", oid=8, flags=F_LAST)]
        w = g.przetworz_sesje(rek, (LO, HI))
        assert sum(s.n_buy for s in w.okna.values()) == 1

    def test_rekordy_spoza_rth_sa_liczone_i_pomijane(self):
        rek = [*akcja(LO - 1), *akcja(LO), *akcja(HI)]
        w = g.przetworz_sesje(rek, (LO, HI))
        assert w.kontrola["poza_rth"] == 4
        assert w.kontrola["akcji"] == 1
        assert set(w.okna) == {LO // M}


class TestCenyOkna:
    def test_kolejnosc_ts_recv_sequence_a_nie_pliku(self):
        """§4: P_first / P_last w kolejnosci `(ts_recv, sequence)`."""
        rek = [r(LO + 5, "T", price=P + 2, seq=9),
               r(LO + 5, "T", price=P + 1, seq=3),
               r(LO + 9, "T", price=P + 7, seq=1, flags=F_LAST)]
        w = g.przetworz_sesje(rek, (LO, HI))
        s = w.okna[LO // M]
        assert s.t_open == P + 1, "pierwsza wg (ts, seq), nie wg pliku"
        assert s.t_close == P + 7
        assert (s.t_high, s.t_low) == (P + 7, P + 1)

    def test_remis_ts_seq_rozstrzyga_kolejnosc_pliku(self):
        """Jedna wiadomosc CME moze niesc kilka transakcji — ten sam (ts, seq)."""
        rek = [r(LO + 5, "T", price=P + 1, seq=4),
               r(LO + 5, "T", price=P + 2, seq=4),
               r(LO + 5, "T", price=P + 3, seq=4, flags=F_LAST)]
        s = g.przetworz_sesje(rek, (LO, HI)).okna[LO // M]
        assert (s.t_open, s.t_close) == (P + 1, P + 3)

    def test_cena_niezdefiniowana_nie_wchodzi_do_bara(self):
        rek = [r(LO + 1, "T", price=g.UNDEF_PRICE, flags=F_LAST)]
        w = g.przetworz_sesje(rek, (LO, HI))
        assert w.kontrola["trade_cena_niezdefiniowana"] == 1
        assert LO // M not in w.okna or w.okna[LO // M].t_n == 0

    def test_wypelniacz_N_nie_zmienia_okna_ani_ceny(self):
        """Nowa normalizacja: osobny rekord `N` z F_LAST i cena UNDEF.

        Ma zamknac akcje (koperta), ale nie wolno mu przesunac jej do
        nastepnej minuty ani wejsc do bara — §5e D5_DRYF.
        """
        stara = [r(LO + 59 * 10**9, "T", "B", oid=1),
                 r(LO + 59 * 10**9, "F", "A", oid=2, flags=F_LAST)]
        nowa = [r(LO + 59 * 10**9, "T", "B", oid=1),
                r(LO + 59 * 10**9, "F", "A", oid=2),
                r(LO + 61 * 10**9, "N", "N", price=g.UNDEF_PRICE, size=0,
                  oid=0, flags=F_LAST)]
        a = g.przetworz_sesje(stara, (LO, HI))
        b = g.przetworz_sesje(nowa, (LO, HI))
        assert ({m: s.jako_slownik() for m, s in a.okna.items()}
                == {m: s.jako_slownik() for m, s in b.okna.items()})


# ---------------------------------------------------------- obserwacje ------
class TestObserwacje:
    def test_wzory_A_B_C_m(self):
        rek = [*akcja(LO + 1, "B", oid=1, size=3, price=P),
               *akcja(LO + 2, "B", oid=2, size=1, price=P),
               *akcja(LO + 3, "A", oid=3, size=2, price=P + 10**9)]
        o = g.obserwacje(g.przetworz_sesje(rek, (LO, HI)), LO)
        assert o["A_count"][0] == pytest.approx((2 - 1) / 3)
        assert o["B_fill"][0] == pytest.approx((2 - 1) / 3)
        assert o["C_volume"][0] == pytest.approx((4 - 2) / 6)
        assert o["m"][0] == pytest.approx(np.log((P + 10**9) / P))
        assert o["wolumen"][0] == 6
        assert o["kubelek"][0] == 0

    def test_okno_bez_transakcji_jest_brakujace(self):
        """§2.2: brak obserwacji, nie zero."""
        rek = [r(LO + 59 * 10**9, "T", "B", oid=7),
               r(LO + 61 * 10**9, "F", "A", oid=8, flags=F_LAST)]
        o = g.obserwacje(g.przetworz_sesje(rek, (LO, HI)), LO)
        # minuta 0 ma cene, ale nie ma akcji; minuta 1 ma akcje, ale nie ma ceny
        assert len(o["m"]) == 0

    def test_strona_N_wykluczona_ze_znaku(self):
        """Etap 2 §4: akcja bez strony raportowana osobno, nie liczona."""
        rek = [*akcja(LO + 1, "N", oid=1), *akcja(LO + M + 1, "B", oid=2)]
        w = g.przetworz_sesje(rek, (LO, HI))
        assert w.kontrola["akcji_strona_N"] == 1
        o = g.obserwacje(w, LO)
        assert list(o["minuta"]) == [LO // M + 1]

    def test_kubelek_liczony_od_otwarcia_rth(self):
        rek = [*akcja(LO + 29 * M), *akcja(LO + 30 * M, oid=2),
               *akcja(LO + 389 * M, oid=3)]
        o = g.obserwacje(g.przetworz_sesje(rek, (LO, HI)), LO)
        assert list(o["kubelek"]) == [0, 1, 12]

    def test_pusta_sesja_nie_wywraca_straznikow(self):
        o = g.obserwacje(g.przetworz_sesje([], (LO, HI)), LO)
        assert len(o["A_count"]) == 0

    def test_n1_kazdy_trade_przypisany_raz(self):
        rek = [*akcja(LO + 1), *akcja(LO + 2, oid=2),
               r(LO + 3, "T", "A", oid=3), r(LO + 3, "T", "A", oid=3,
                                             flags=F_LAST)]
        k = g.przetworz_sesje(rek, (LO, HI)).kontrola
        assert k["suma_n_trade"] == k["trade"] == 4


# ---------------------------------------------------- kontrola barow §6.5 ----
class TestPorownanieBarow:
    def _okna(self):
        return g.przetworz_sesje([*akcja(LO + 1, size=2, price=P),
                                  *akcja(LO + 2, oid=2, size=3, price=P + 4)],
                                 (LO, HI)).okna

    def test_identyczne_bary_zero_niezgodnosci(self):
        dost = {LO // M: (P, P + 4, P, P + 4, 5)}
        w = g.porownaj_bary(self._okna(), dost)
        assert w["niezgodnych"] == 0 and w["wspolnych"] == 1

    def test_kazda_roznica_jest_liczona(self):
        dost = {LO // M: (P, P + 4, P, P + 3, 5), LO // M + 5: (P, P, P, P, 1)}
        w = g.porownaj_bary(self._okna(), dost)
        assert w["close"] == 1 and w["tylko_dostawcy"] == 1
        assert w["niezgodnych"] == 2


# ------------------------------------------------------------------ VIF -----
def _sesje_fixture(rng, n_sesji=22, okien=390, zalezne=False):
    """Fixture testowy: niezalezne lub zalezne od momentum `I_count`."""
    sesje = {}
    for i in range(n_sesji):
        m = rng.normal(0, 1e-4, okien)
        vol = rng.integers(50, 500, okien)
        if zalezne:
            a = np.clip(np.sign(m) * 0.9 + rng.normal(0, 1e-3, okien), -1, 1)
        else:
            a = np.clip(rng.normal(0, 0.4, okien), -1, 1)
        sesje[f"2026-07-{i + 1:02d}"] = {
            "m": m, "wolumen": vol, "kubelek": np.arange(okien) // 30,
            "A_count": a, "B_fill": np.clip(rng.normal(0, 0.4, okien), -1, 1),
            "C_volume": np.clip(rng.normal(0, 0.4, okien), -1, 1),
            "minuta": np.arange(okien)}
    return sesje


class TestVIF:
    def test_niezalezne_dane_dają_vif_bliskie_jeden(self):
        rng = np.random.default_rng(20260806)
        x = rng.normal(size=(2000, 3))
        assert g.vif(rng.normal(size=2000), x) == pytest.approx(1.0, abs=0.02)

    def test_wspolliniowe_dane_dają_wysoki_vif(self):
        rng = np.random.default_rng(20260806)
        x = rng.normal(size=(2000, 3))
        y = x @ np.array([1.0, -2.0, 0.5]) + rng.normal(0, 0.01, 2000)
        assert g.vif(y, x) > 1000

    def test_stale_y_nie_jest_ponizej_progu(self):
        v = g.vif(np.ones(100), np.random.default_rng(1).normal(size=(100, 2)))
        assert np.isnan(v)
        assert not (v < g.PROG_VIF)


class TestOcena:
    def test_niezalezna_nierownowaga_przechodzi(self):
        o = g.ocen(_sesje_fixture(np.random.default_rng(7)))
        assert all(o["warunki"].values()), o["warunki"]
        assert o["werdykt"] == "D5-B2 GO"

    def test_nierownowaga_rowna_znakowi_momentum_odpada(self):
        """Lekcja z D1: zmienna bedaca funkcja momentum nie jest nowa
        informacja — warunek 1 musi to zlapac."""
        o = g.ocen(_sesje_fixture(np.random.default_rng(7), zalezne=True))
        assert not o["warunki"][1]
        assert o["werdykt"] == "D5-B2 NO-GO"

    def test_sesja_skrocona_poza_dziennym_vif(self):
        sesje = _sesje_fixture(np.random.default_rng(3), n_sesji=5)
        sesje[g.SESJA_SKROCONA] = sesje.pop("2026-07-03")
        o = g.ocen(sesje)
        assert g.SESJA_SKROCONA not in o["wyniki"]["A_count"]["dzienne_vif"]
        assert g.SESJA_SKROCONA in o["okien_na_sesje"], "ale zostaje w probie"

    def test_jedna_sesja_dominujaca_lamie_warunek_6(self):
        rng = np.random.default_rng(11)
        sesje = _sesje_fixture(rng)
        s = sesje["2026-07-05"]
        s["A_count"] = np.where(np.arange(390) % 2 == 0, 1.0, -1.0)
        for k in sesje:
            if k != "2026-07-05":
                sesje[k]["A_count"] = sesje[k]["A_count"] * 0.05
        o = g.ocen(sesje)
        assert not o["warunki"][6]

    def test_deterministyczna(self):
        a = g.ocen(_sesje_fixture(np.random.default_rng(5)))
        b = g.ocen(_sesje_fixture(np.random.default_rng(5)))
        assert a["werdykt"] == b["werdykt"]
        assert a["wyniki"]["A_count"]["pooled_vif"] == b["wyniki"]["A_count"]["pooled_vif"]


# --------------------------------------------------------------- werdykt ----
WSZYSTKIE = dict.fromkeys(range(1, 7), True)


@pytest.mark.parametrize(("niespelnione", "abc", "oczekiwany"), [
    (set(), True, "D5-B2 GO"),
    (set(), False, "D5-B2 INCONCLUSIVE"),          # §4a Etapu 2
    ({2}, True, "D5-B2 INCONCLUSIVE"),             # identyfikacja miedzy sesjami
    ({3}, True, "D5-B2 INCONCLUSIVE"),
    ({4}, True, "D5-B2 INCONCLUSIVE"),             # z pory dnia
    ({6}, True, "D5-B2 INCONCLUSIVE"),
    ({2, 3, 4, 6}, True, "D5-B2 INCONCLUSIVE"),
    ({5}, True, "D5-B2 NO-GO"),                    # brak obu stron — pomiar
    ({2, 5}, True, "D5-B2 NO-GO"),
    ({1}, True, "D5-B2 NO-GO"),
    ({1, 2}, True, "D5-B2 NO-GO"),
    ({1}, False, "D5-B2 NO-GO"),
])
def test_mapowanie_werdyktu(niespelnione, abc, oczekiwany):
    """Tabela §12.2 — zapisana ex ante, tu jako test, zeby nie dryfowala."""
    war = {k: k not in niespelnione for k in WSZYSTKIE}
    assert g.werdykt(war, abc)[0] == oczekiwany


def test_werdykt_wymaga_kompletu_warunkow():
    with pytest.raises(ValueError):
        g.werdykt({1: True}, True)


# -------------------------------------------- progi zgodne ze spec §5 -------
def test_progi_zgodne_ze_specyfikacja():
    """Progi zyja w DWOCH miejscach: w zamrozonej spec i w kodzie. Ten test
    pilnuje, zeby rozjazd byl czerwony — `progow nie ruszamy` jako mechanizm."""
    spec = (KORZEN / "docs" / "D5_ETAP4_SPEC.md").read_text(encoding="utf-8")
    sek = spec[spec.index("## 5. Progi GO/NO-GO"):spec.index("### Kontrole B i C")]
    assert "1. pooled VIF < 5," in sek and g.PROG_VIF == 5.0
    assert "2. mediana dziennego VIF < 5," in sek
    assert "3. ≥ 75% kompletnych sesji ma VIF < 5," in sek and g.UDZIAL_SESJI == 0.75
    assert re.search(r"4\. .*pora dnia .*> 20% zmienności", sek) and g.MAX_KONC == 0.20
    assert re.search(r"5\. .*≥ 20% okien", sek) and g.MIN_STRONA == 0.20
    assert re.search(r"6\. .*sesja .*> 20% całkowitej zmienności", sek)
    assert "**60 sekund**" in spec and g.MIN_NS == 60 * 10**9
