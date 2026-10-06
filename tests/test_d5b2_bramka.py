"""Bramka D5-B2 — test END-TO-END skryptu na sztucznych plikach DBN.

Fixture'y testowe, nie dane rynkowe: 22 sesje po kilkadziesiat minut
z losowymi akcjami, zapisane prawdziwym koderem DBN i skompresowane zstd —
czyli dokladnie ta sciezka, ktora przejdzie bieg na danych wlasciciela.

PO CO: pelny bieg trwa ~100 minut na komputerze wlasciciela, a tu nie ma
danych. Blad w I/O (parsowanie, cache, kontrole §6, zapis raportu) wyszedlby
dopiero tam — po godzinie. Ten test przechodzi te sama sciezke w sekundy.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

db = pytest.importorskip("databento", reason="sciezka I/O bramki wymaga databento")
dbn = pytest.importorskip("databento_dbn", reason="koder DBN z pakietu databento")
zstd = pytest.importorskip("zstandard", reason="pliki MBO sa kompresowane zstd")

KORZEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORZEN))

from engine.d5b2 import MIN_NS  # noqa: E402
from engine.mbo_events import F_LAST  # noqa: E402
from scripts import d5b2_bramka as b  # noqa: E402
from scripts import fetch_d5b2_month as f  # noqa: E402

OKIEN = 60          # minut na sesje — wystarczy na dzienny VIF (>= 50)
TICK = 250_000_000  # 0,25 pkt w jednostkach DBN


def _sesja_rekordy(sesja: str, rng) -> list:
    lo, _ = b.granice_ns(sesja)
    cena = 20_000 * 10**9
    seq = 1
    out = []
    for k in range(OKIEN):
        for j in range(int(rng.integers(3, 9))):
            ts = lo + k * MIN_NS + (j + 1) * 1_000_000_000
            strona = dbn.Side.BID if rng.random() < 0.5 else dbn.Side.ASK
            cena += int(rng.integers(-2, 3)) * TICK
            rozmiar = int(rng.integers(1, 5))
            oid = 1_000_000 + seq
            out.append(dbn.MBOMsg(1, 42, ts, oid, cena, rozmiar, dbn.Action.TRADE,
                                  strona, ts, flags=0, sequence=seq))
            out.append(dbn.MBOMsg(1, 42, ts, oid + 500_000, cena, rozmiar,
                                  dbn.Action.FILL,
                                  dbn.Side.ASK if strona == dbn.Side.BID else dbn.Side.BID,
                                  ts, flags=F_LAST, sequence=seq))
            seq += 1
    return out


def _bary(msgs) -> dict:
    """Bary 'dostawcy' zbudowane z tych samych Trade — kontrola 5 ma przejsc."""
    bary: dict[int, list] = {}
    for m in msgs:
        if m.action != dbn.Action.TRADE:
            continue
        mi = m.ts_recv // MIN_NS
        if mi not in bary:
            bary[mi] = [m.price, m.price, m.price, m.price, 0]
        x = bary[mi]
        x[1], x[2], x[3], x[4] = max(x[1], m.price), min(x[2], m.price), m.price, x[4] + m.size
    return {k: tuple(v) for k, v in bary.items()}


@pytest.fixture
def swiat(tmp_path, monkeypatch):
    """Katalog danych z 22 sesjami, manifestem i barami — jak u wlasciciela."""
    monkeypatch.setenv("PROJECT_G_DATA_ROOT", str(tmp_path))
    rng = np.random.default_rng(20261006)
    meta = dbn.Metadata(dataset="GLBX.MDP3", start=0, stype_in=dbn.SType.RAW_SYMBOL,
                        stype_out=dbn.SType.INSTRUMENT_ID, schema=dbn.Schema.MBO,
                        symbols=["MNQU6"], end=10**19 - 1)
    plan, wyniki, bary = [], [], {}
    for s in f.SESJE:
        msgs = _sesja_rekordy(s, rng)
        p = f.sciezka_docelowa(s)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(zstd.ZstdCompressor().compress(
            meta.encode() + b"".join(bytes(m) for m in msgs)))
        a, e = f.okno(s)
        plan.append({"sesja": s, "start_utc": a, "end_utc": e, "koszt_usd": 1.0,
                     "rekordow": len(msgs)})
        wyniki.append({"sesja": s, "rekordow": len(msgs), "kompletny": True,
                       "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
        bary[s] = _bary(msgs)
    man = f.sciezka_manifestu()
    man.parent.mkdir(parents=True, exist_ok=True)
    man.write_text(json.dumps({"plan": plan, "wyniki": wyniki}), encoding="utf-8")
    # kanoniczny D5-C wskazuje na NASZ plik 07-30, nie na prawdziwy z repo
    d5c = tmp_path / "manifest_d5c.json"
    d5c.write_text(json.dumps({"rekordow_wg_metadata": plan[-1]["rekordow"],
                               "sha256": wyniki[-1]["sha256"]}), encoding="utf-8")
    monkeypatch.setattr(b, "KANONICZNY_D5C", d5c)
    monkeypatch.setattr(b, "bary_dostawcy", lambda: bary)
    monkeypatch.setattr(b, "RAPORT", tmp_path / "raport.json")
    return tmp_path


def _uruchom(argv) -> int:
    stare = sys.argv
    try:
        sys.argv = ["d5b2_bramka.py", *argv]
        return b.main()
    finally:
        sys.argv = stare


def test_pelny_bieg_wydaje_werdykt_i_zapisuje_raport(swiat):
    assert _uruchom([]) == 0
    rap = json.loads((swiat / "raport.json").read_text(encoding="utf-8"))
    assert rap["werdykt"].startswith("D5-B2 ")
    assert set(rap["warunki"]) == {"1", "2", "3", "4", "5", "6"}
    assert len(rap["sesje"]) == 22
    assert all(not s["stop"] for s in rap["sesje"].values())
    assert all(s["bary"]["niezgodnych"] == 0 for s in rap["sesje"].values())
    # normalizacja oznaczona per sesja, liczona ze stalej, nie zgadywana
    stare = {s for s, v in rap["sesje"].items() if v["normalizacja"] == "stara"}
    assert stare == set(f.SESJE_STARA_NORMALIZACJA)


def test_drugi_bieg_z_cache_daje_ten_sam_wynik(swiat):
    assert _uruchom([]) == 0
    pierwszy = json.loads((swiat / "raport.json").read_text(encoding="utf-8"))
    assert _uruchom([]) == 0
    drugi = json.loads((swiat / "raport.json").read_text(encoding="utf-8"))
    assert all(v["z_cache"] for v in drugi["sesje"].values())
    for k in ("werdykt", "warunki", "wyniki", "koncentracja_pory_dnia"):
        assert pierwszy[k] == drugi[k], k


def test_rozjazd_liczby_rekordow_zatrzymuje_bez_werdyktu(swiat):
    """Kontrola 2 §6: plik inny niz zapisany w manifescie -> STOP, nie werdykt."""
    man = f.sciezka_manifestu()
    d = json.loads(man.read_text(encoding="utf-8"))
    d["wyniki"][5]["rekordow"] += 1
    man.write_text(json.dumps(d), encoding="utf-8")
    assert _uruchom([]) == 2
    rap = json.loads((swiat / "raport.json").read_text(encoding="utf-8"))
    assert rap["werdykt"] is None
    assert f.SESJE[5] in rap["stop"]


def test_brak_sha_w_manifescie_jest_zapisany_teraz(swiat):
    """§12.3: cztery stare sesje nie maja SHA z dnia pobrania — liczony teraz."""
    man = f.sciezka_manifestu()
    d = json.loads(man.read_text(encoding="utf-8"))
    del d["wyniki"][0]["sha256"]
    man.write_text(json.dumps(d), encoding="utf-8")
    assert _uruchom([]) == 0
    rap = json.loads((swiat / "raport.json").read_text(encoding="utf-8"))
    assert rap["sesje"][f.SESJE[0]]["sha_zrodlo"] == "zapisany_teraz"
    assert len(rap["sesje"][f.SESJE[0]]["sha256"]) == 64


def test_tryb_jednej_sesji_nie_wydaje_werdyktu(swiat):
    assert _uruchom(["--sesja", "2026-07-03"]) == 0
    assert not (swiat / "raport.json").exists(), "proba generalna nie pisze raportu"
