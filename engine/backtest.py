"""Silnik backtestowy — event-driven, bar po barze.

Specyfikacja: PLAN.pdf rozdz. 5.1-5.4.

Zasady konstrukcyjne (gwarancje architektoniczne, nie konwencje):
  1. Strategia widzi wylacznie dane do biezacego bara wlacznie. Nie ma zadnej
     sciezki API, ktora pozwolilaby zajrzec w przyszlosc.
  2. Sygnal na close -> wykonanie na open NASTEPNEGO bara.
  3. Konserwatyzm przy niejednoznacznosci: gdzie bar M1 nie rozstrzyga kolejnosci
     zdarzen, wybieramy wariant gorszy dla strategii. Backtest ma prawo zanizac
     wynik; nie ma prawa go zawyzac.
  4. ZAKAZ wykonania w barze o wolumenie zero — nie bylo gdzie sie wykonac.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from statistics import median
from typing import Literal, Protocol

from engine.costs import (
    POINT_VALUE,
    TICK_SIZE,
    CostModel,
    gap_stop_slippage_ticks,
    slippage_ticks,
)
from engine.guards import HistoryView
from engine.sessions import to_et, trade_date


class AmbiguousBarPolicy(StrEnum):
    """Rozstrzyganie bara dotykajacego jednoczesnie SL i TP (rozdz. 5.4).

    Regula "SL wygrywa" wydaje sie bezpiecznym konserwatyzmem, ale jest
    SKRZYWIENIEM STATYSTYCZNYM: im szerszy cel wzgledem stopa, tym czesciej bar
    obejmuje oba poziomy, wiec regula nieproporcjonalnie karze strategie
    o wysokim R:R.

    Rozwiazanie docelowe: SUBBAR_1S — dociagniecie 60 sub-barow sekundowych
    tylko dla spornej minuty. Bez tych danych obowiazkowo raportujemy PASMO
    WRAZLIWOSCI: wynik przy SL_WINS i TP_WINS jako dwie osobne liczby.
    Strategia dobra tylko przy optymistycznym koncu pasma nie jest dobra.
    """

    SL_WINS = "sl_wins"        # konserwatywny fallback
    TP_WINS = "tp_wins"        # gorna granica pasma wrazliwosci
    SUBBAR_1S = "subbar_1s"    # rozstrzygniecie faktyczne (wymaga danych 1s)


Side = Literal["long", "short"]


@dataclass(frozen=True)
class Bar:
    """Bar M1. `volume == 0` oznacza brak transakcji — nie wolno w nim wykonac zlecenia."""

    ts: object          # datetime (UTC)
    open: float
    high: float
    low: float
    close: float
    volume: int
    segment: str = "midday"
    px_raw_offset: float = 0.0   # roznica px_raw - px_adj (rozdz. 4.3)

    @property
    def tradeable(self) -> bool:
        return self.volume > 0


@dataclass(frozen=True)
class Order:
    side: Side
    qty: int = 1
    kind: Literal["mkt", "stop", "limit"] = "mkt"
    px: float | None = None       # dla stop/limit
    sl: float | None = None
    tp: float | None = None
    tag: str = ""
    # Jak dlugo zlecenie zyje. "next_bar" — wylacznie najblizszy bar (domyslne,
    # zgodne z zasada "sygnal na close -> wykonanie na open nastepnego bara");
    # "day" — pracuje do konca dnia sesyjnego, jak zlecenie oczekujace na gieldzie.
    tif: Literal["next_bar", "day"] = "next_bar"


@dataclass
class Position:
    side: Side
    qty: int
    entry_px: float
    entry_ts: object
    sl: float
    tp: float | None = None
    tag: str = ""


@dataclass
class Trade:
    side: Side
    qty: int
    entry_ts: object
    entry_px: float
    exit_ts: object
    exit_px: float
    pnl_points: float
    pnl_usd: float
    r_multiple: float
    exit_reason: str
    tag: str = ""


@dataclass
class Result:
    trades: list[Trade] = field(default_factory=list)
    equity: list[float] = field(default_factory=list)
    config: dict = field(default_factory=dict)
    ambiguous_bars: int = 0      # ile barow wymagalo rozstrzygniecia SL/TP
    skipped_zero_volume: int = 0 # ile wykonan zablokowano brakiem wolumenu
    # Dzienny P&L w USD — WSZYSTKIE dni sesyjne w danych, takze bez transakcji.
    # Pominiecie dni zerowych zawyzaloby Sharpe strategii rzadko handlujacych
    # (rozdz. 6.3), dlatego klucze zaklada sie przy pierwszym barze dnia.
    daily_pnl: dict = field(default_factory=dict)
    rejected_orders: list = field(default_factory=list)  # (ts, powod) — odrzucenia warstwy ryzyka
    risk_blocked_bars: int = 0   # bary, w ktorych limit dzienny/tygodniowy wylaczyl strategie
    blackout_bars: int = 0       # bary w oknie blackoutu wokol zdarzen rangi 1
    forced_exits: int = 0        # przymusowe zamkniecia (flat-by)

    @property
    def r_multiples(self) -> list[float]:
        return [t.r_multiple for t in self.trades]

    def daily_pnl_series(self) -> list[float]:
        """P&L dzien po dniu, chronologicznie — wejscie do `metrics.summarize`."""
        return [self.daily_pnl[k] for k in sorted(self.daily_pnl)]


class Strategy(Protocol):
    """Czysta funkcja (bar, state) -> (orders, state).

    Identyczny kod dziala w backtescie i w petli live — eliminuje klase bledow
    "w backtescie liczylo sie inaczej niz live".
    """

    def on_bar(self, bar: Bar, history: Sequence[Bar], state: dict) -> list[Order]:
        ...


# --------------------------------------------------------------------------
# Rozstrzyganie wewnatrzbarowe — tabela 5.4
# --------------------------------------------------------------------------

def resolve_exit(
    pos: Position,
    bar: Bar,
    *,
    policy: AmbiguousBarPolicy = AmbiguousBarPolicy.SL_WINS,
    slippage_points: float = 0.125,
    gap_slippage_points: float | None = None,
    subbar_resolver: Callable[[Position, Bar], str | None] | None = None,
) -> tuple[float, str] | None:
    """Zwraca (cena_wyjscia, powod) albo None, jesli pozycja przezyla bar.

    Implementuje kazdy wiersz tabeli 5.4:
      * dotyka tylko SL          -> wyjscie po SL minus poslizg
      * dotyka tylko TP          -> wymagane PRZEBICIE limitu o >= 1 tick
      * dotyka SL i TP           -> wg `policy` (domyslnie SL)
      * open przeskakuje SL luka -> wyjscie po OPEN minus poslizg zwiekszony
    """
    long = pos.side == "long"

    # --- gap: open juz przekroczyl stopa -> wykonanie po open, nie po cenie SL
    gap_hit = (bar.open <= pos.sl) if long else (bar.open >= pos.sl)
    if gap_hit:
        slip = gap_slippage_points if gap_slippage_points is not None else slippage_points
        px = bar.open - slip if long else bar.open + slip
        return px, "stop_gap"

    sl_touched = (bar.low <= pos.sl) if long else (bar.high >= pos.sl)

    # Zlecenie z limitem wymaga PRZEBICIA o co najmniej tick — samo dotkniecie
    # nie gwarantuje wypelnienia przy odleglej pozycji w kolejce.
    tp_touched = False
    if pos.tp is not None:
        tp_touched = (bar.high >= pos.tp + 0.25) if long else (bar.low <= pos.tp - 0.25)

    if sl_touched and tp_touched:
        if policy is AmbiguousBarPolicy.SUBBAR_1S:
            if subbar_resolver is None:
                raise ValueError(
                    "Polityka SUBBAR_1S wymaga danych 1s (subbar_resolver). "
                    "Bez nich uzyj SL_WINS/TP_WINS i raportuj pasmo wrazliwosci."
                )
            first = subbar_resolver(pos, bar)
            if first == "tp":
                return pos.tp, "take_profit"
            if first == "sl":
                return (pos.sl - slippage_points) if long else (pos.sl + slippage_points), "stop_loss"
            # resolver nie rozstrzygnal -> konserwatywnie
            return (pos.sl - slippage_points) if long else (pos.sl + slippage_points), "stop_loss"

        if policy is AmbiguousBarPolicy.TP_WINS:
            return pos.tp, "take_profit"
        return (pos.sl - slippage_points) if long else (pos.sl + slippage_points), "stop_loss"

    if sl_touched:
        return (pos.sl - slippage_points) if long else (pos.sl + slippage_points), "stop_loss"

    if tp_touched:
        return pos.tp, "take_profit"

    return None


def is_ambiguous(pos: Position, bar: Bar) -> bool:
    """Czy bar dotyka jednoczesnie SL i TP (wymaga rozstrzygniecia)."""
    if pos.tp is None:
        return False
    long = pos.side == "long"
    sl_touched = (bar.low <= pos.sl) if long else (bar.high >= pos.sl)
    tp_touched = (bar.high >= pos.tp + 0.25) if long else (bar.low <= pos.tp - 0.25)
    return bool(sl_touched and tp_touched)


# --------------------------------------------------------------------------
# Limity ryzyka — dzialaja PRZED strategia (rozdz. 10.3)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class RiskLimits:
    """Warstwa ryzyka, ktorej strategia nie moze obejsc."""

    daily_stop_r: float = 2.0       # koniec handlu po -2R w dniu sesyjnym
    weekly_stop_r: float = 4.0
    max_positions: int = 1
    allow_averaging_down: bool = False   # ZAKAZ bezwzgledny (rozdz. 10.4)
    require_stop: bool = True            # zlecenie bez stopa jest odrzucane


class RiskGate:
    """Egzekwuje limity. Zlicza R w dniu i tygodniu sesyjnym."""

    def __init__(self, limits: RiskLimits | None = None):
        self.limits = limits or RiskLimits()
        self._day_r: dict[object, float] = {}
        self._week_r: dict[object, float] = {}

    def register(self, trade_date_key: object, week_key: object, r: float) -> None:
        self._day_r[trade_date_key] = self._day_r.get(trade_date_key, 0.0) + r
        self._week_r[week_key] = self._week_r.get(week_key, 0.0) + r

    def blocked(self, trade_date_key: object, week_key: object) -> bool:
        day_hit = self._day_r.get(trade_date_key, 0.0) <= -self.limits.daily_stop_r
        week_hit = self._week_r.get(week_key, 0.0) <= -self.limits.weekly_stop_r
        return day_hit or week_hit

    def validate(self, order: Order, open_positions: int) -> None:
        if self.limits.require_stop and order.sl is None:
            raise ValueError("Zlecenie bez stop-lossa odrzucone przez warstwe ryzyka (rozdz. 10.4)")
        if open_positions >= self.limits.max_positions and not self.limits.allow_averaging_down:
            raise ValueError("Usrednianie w strate jest zablokowane (rozdz. 10.4)")


# --------------------------------------------------------------------------
# Wykonanie zlecen — wejscie na open NASTEPNEGO bara (rozdz. 5.1, 5.4)
# --------------------------------------------------------------------------

def entry_fill(order: Order, bar: Bar, slippage_points: float) -> float | None:
    """Cena wejscia dla zlecenia oczekujacego na tym barze albo None (brak wypelnienia).

    Wiersze tabeli 5.4 dotyczace wejsc:
      * rynkowe            -> open bara + poslizg (dla longa w gore, dla shorta w dol)
      * stop, open przebil -> wykonanie po OPEN, nie po cenie zlecenia
      * stop, dotkniecie   -> wykonanie po cenie stopa + poslizg
      * limit              -> wymagane PRZEBICIE o >= 1 tick; nigdy lepiej niz limit

    Poslizg zawsze dziala przeciwko strategii — kupujemy drozej, sprzedajemy taniej.
    """
    long = order.side == "long"
    kierunek = 1.0 if long else -1.0

    if order.kind == "mkt":
        return bar.open + kierunek * slippage_points

    if order.px is None:
        raise ValueError(f"Zlecenie {order.kind} wymaga ceny (px)")

    if order.kind == "stop":
        # Stop-buy lezy POWYZEJ rynku, stop-sell PONIZEJ.
        przebil_open = (bar.open >= order.px) if long else (bar.open <= order.px)
        if przebil_open:
            return bar.open + kierunek * slippage_points
        dotkniety = (bar.high >= order.px) if long else (bar.low <= order.px)
        if dotkniety:
            return order.px + kierunek * slippage_points
        return None

    # limit: kupujemy PONIZEJ rynku, sprzedajemy POWYZEJ; samo dotkniecie nie
    # gwarantuje wypelnienia (pozycja w kolejce), stad wymog przebicia o tick.
    przebicie = (bar.low <= order.px - TICK_SIZE) if long else (bar.high >= order.px + TICK_SIZE)
    if przebicie:
        return order.px          # bez korzysci z lepszej ceny — nigdy nie zawyzamy
    return None


class _VolatilityTracker:
    """ATR minutowy i jego mediana — mnoznik poslizgu z rozdz. 5.5.

    Statyczna tabela poslizgow zanizalaby koszt dokladnie w tych momentach,
    w ktorych jest on najwiekszy. Mediana liczona jest raz na dzien sesyjny
    (przeliczanie jej co bar kosztowaloby wielokrotnie wiecej niz caly backtest,
    a zmienia sie o ulamek procenta miedzy sasiednimi minutami).
    """

    def __init__(self, atr_window: int = 14, median_days: int = 60, bars_per_day: int = 1380):
        self._tr = deque(maxlen=atr_window)
        self._tr_long = deque(maxlen=median_days * bars_per_day)
        self._prev_close: float | None = None
        self._median: float | None = None
        self._median_day: object = None

    def update(self, bar: Bar, day_key: object) -> None:
        tr = (bar.high - bar.low) if self._prev_close is None else max(
            bar.high - bar.low,
            abs(bar.high - self._prev_close),
            abs(bar.low - self._prev_close),
        )
        self._prev_close = bar.close
        self._tr.append(tr)
        self._tr_long.append(tr)
        if day_key != self._median_day:
            self._median_day = day_key
            self._median = median(self._tr_long) if self._tr_long else None

    @property
    def atr(self) -> float | None:
        return (sum(self._tr) / len(self._tr)) if self._tr else None

    @property
    def atr_median(self) -> float | None:
        return self._median


def _week_key(d: date) -> tuple[int, int]:
    iso = d.isocalendar()
    return (iso.year, iso.week)


def _near_event(ts: datetime, events: Sequence[datetime], minutes: int) -> bool:
    """Czy znacznik lezy w oknie +-`minutes` od zdarzenia rangi 1 (rozdz. 5.5)."""
    if not events:
        return False
    okno = timedelta(minutes=minutes)
    return any(abs(ts - e) <= okno for e in events)


def run(
    bars: Sequence[Bar],
    strategy: Strategy,
    *,
    cost: CostModel | None = None,
    risk: RiskLimits | None = None,
    policy: AmbiguousBarPolicy = AmbiguousBarPolicy.SL_WINS,
    subbar_resolver: Callable[[Position, Bar], str | None] | None = None,
    events: Sequence[datetime] = (),
    blackout_minutes: int = 10,
    blackout: bool = True,
    flat_by: time | None = None,
    state: dict | None = None,
    tag: str = "",
) -> Result:
    """Glowna petla backtestu — PLAN.pdf rozdz. 5.3.

    Kolejnosc w kazdym barze jest kontraktem, nie szczegolem implementacyjnym:

      1. WYKONANIE zlecen zlozonych na poprzednim barze — po OPEN tego bara.
         Sygnal liczony na close nie moze wykonac sie po tym samym close.
      2. AKTUALIZACJA POZYCJI — wewnatrzbarowe SL/TP wg tabeli 5.4. Pozycja
         otwarta na TYM barze nie moze na nim wyjsc: znamy fakt wypelnienia,
         nie trajektorie ceny po nim.
      3. LIMITY RYZYKA — twarde, PRZED strategia. Po -daily_stop_R dzien jest
         zamkniety; strategia nie jest nawet pytana o zdanie.
      4. STRATEGIA — widzi wylacznie `HistoryView` do biezacego bara wlacznie.
         Proba siegniecia dalej konczy sie `LookaheadError`, nie cicha zmyslona
         wartoscia.
      5. KSIEGOWANIE — equity mark-to-market na close bara.

    Silnik jest deterministyczny: nie ma w nim zadnego zrodla losowosci.
    Dwa przebiegi na tych samych danych daja bitowo identyczne wyniki (test
    determinizmu z rozdz. 5.6). Losowosc — jesli strategia jej potrzebuje —
    nalezy do strategii i musi byc przez nia ziarnowana.
    """
    cm = cost or CostModel()
    limits = risk or RiskLimits()
    gate = RiskGate(limits)
    res = Result()
    res.config = {
        "policy": str(policy),
        "commission_rt": cm.commission_rt,
        "stress_multiplier": cm.stress_multiplier,
        "daily_stop_r": limits.daily_stop_r,
        "weekly_stop_r": limits.weekly_stop_r,
        "max_positions": limits.max_positions,
        "require_stop": limits.require_stop,
        "blackout": blackout,
        "blackout_minutes": blackout_minutes,
        "flat_by": flat_by.isoformat() if flat_by else None,
        "n_events": len(events),
        "n_bars": len(bars),
        "tag": tag,
        "strategy": type(strategy).__name__,
    }
    res.config["config_hash"] = hashlib.sha256(
        json.dumps(res.config, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]

    st = state if state is not None else {}
    vol = _VolatilityTracker()
    otwarte: list[Position] = []
    oczekujace: list[Order] = []
    zrealizowane = 0.0       # skumulowany P&L w USD
    ryzyko_pozycji: dict[int, float] = {}   # id(pozycji) -> ryzyko w USD (do R)

    for idx, bar in enumerate(bars):
        dzien = trade_date(bar.ts)
        tydzien = _week_key(dzien)
        res.daily_pnl.setdefault(dzien, 0.0)
        vol.update(bar, dzien)

        przy_zdarzeniu = _near_event(bar.ts, events, blackout_minutes)
        slip_ticks = slippage_ticks(
            bar.segment,
            atr_m1=vol.atr,
            atr_m1_median=vol.atr_median,
            near_event=przy_zdarzeniu,
            stress_multiplier=cm.stress_multiplier,
        )
        slip_pkt = slip_ticks * TICK_SIZE

        # --- 1. WYKONANIE zlecen z poprzedniego bara -------------------------
        nowe_pozycje: list[Position] = []
        if oczekujace:
            if not bar.tradeable:
                # Wolumen zero = nie bylo gdzie sie wykonac (rozdz. 4.2).
                res.skipped_zero_volume += len(oczekujace)
                oczekujace = [o for o in oczekujace if o.tif == "day"]
            else:
                pozostale: list[Order] = []
                for order in oczekujace:
                    px = entry_fill(order, bar, slip_pkt)
                    if px is None:
                        if order.tif == "day":
                            pozostale.append(order)
                        continue
                    if len(otwarte) >= limits.max_positions:
                        res.rejected_orders.append((bar.ts, "limit otwartych pozycji"))
                        continue
                    pos = Position(
                        side=order.side, qty=order.qty, entry_px=px, entry_ts=bar.ts,
                        sl=float(order.sl), tp=order.tp, tag=order.tag or tag,
                    )
                    otwarte.append(pos)
                    nowe_pozycje.append(pos)
                    ryzyko_pozycji[id(pos)] = abs(px - pos.sl) * POINT_VALUE * pos.qty
                oczekujace = pozostale

        # --- 2. AKTUALIZACJA POZYCJI — wewnatrzbarowe SL/TP ------------------
        if bar.tradeable:
            przetrwaly: list[Position] = []
            swieze = {id(p) for p in nowe_pozycje}
            for pos in otwarte:
                if id(pos) in swieze:
                    # Wejscie i potencjalne wyjscie w tym samym barze: wyjscie
                    # dopiero od bara nastepnego (tabela 5.4).
                    przetrwaly.append(pos)
                    continue
                if is_ambiguous(pos, bar):
                    res.ambiguous_bars += 1
                gap_slip = None
                long = pos.side == "long"
                gap = (pos.sl - bar.open) if long else (bar.open - pos.sl)
                if gap > 0 and vol.atr:
                    gap_slip = gap_stop_slippage_ticks(
                        gap, vol.atr, stress_multiplier=cm.stress_multiplier
                    ) * TICK_SIZE
                wyjscie = resolve_exit(
                    pos, bar, policy=policy, slippage_points=slip_pkt,
                    gap_slippage_points=gap_slip, subbar_resolver=subbar_resolver,
                )
                if wyjscie is None and flat_by is not None and to_et(bar.ts).time() >= flat_by:
                    wyjscie = (bar.close - slip_pkt if long else bar.close + slip_pkt, "flat_by")
                    res.forced_exits += 1
                if wyjscie is None:
                    przetrwaly.append(pos)
                    continue
                px, powod = wyjscie
                trade = _close_position(pos, bar.ts, px, powod, cm, ryzyko_pozycji.pop(id(pos), 0.0))
                res.trades.append(trade)
                zrealizowane += trade.pnl_usd
                res.daily_pnl[dzien] += trade.pnl_usd
                gate.register(dzien, tydzien, trade.r_multiple)
            otwarte = przetrwaly
        elif otwarte or oczekujace:
            res.skipped_zero_volume += len(otwarte)

        # --- 3. LIMITY RYZYKA — przed strategia ------------------------------
        wolno_handlowac = True
        if gate.blocked(dzien, tydzien):
            res.risk_blocked_bars += 1
            wolno_handlowac = False
        elif blackout and przy_zdarzeniu:
            res.blackout_bars += 1
            wolno_handlowac = False

        # --- 4. STRATEGIA — widzi wylacznie przeszlosc -----------------------
        if wolno_handlowac:
            widok = HistoryView(bars, cutoff=idx)
            zlecenia = strategy.on_bar(bar, widok, st) or []
            for order in zlecenia:
                try:
                    gate.validate(order, len(otwarte) + len(oczekujace))
                except ValueError as e:
                    # Odrzucenie, nie awaria: zle zlecenie nie moze przewrocic
                    # calego badania, ale musi byc widoczne w wyniku.
                    res.rejected_orders.append((bar.ts, str(e)))
                    continue
                oczekujace.append(order)

        # Zlecenia jednobarowe wygasaja z koncem dnia sesyjnego tak czy inaczej.
        if oczekujace and idx + 1 < len(bars) and trade_date(bars[idx + 1].ts) != dzien:
            wygasle = [o for o in oczekujace if o.tif != "day"]
            oczekujace = [o for o in oczekujace if o.tif == "day"]
            if wygasle:
                res.rejected_orders.append((bar.ts, f"wygasniecie {len(wygasle)} zlecen na granicy dnia"))

        # --- 5. KSIEGOWANIE — mark-to-market na close ------------------------
        niezrealizowane = sum(
            (bar.close - p.entry_px if p.side == "long" else p.entry_px - bar.close)
            * POINT_VALUE * p.qty
            for p in otwarte
        )
        res.equity.append(zrealizowane + niezrealizowane)

    # Pozycje otwarte na koncu danych zamykamy po ostatnim close — inaczej ich
    # wynik zniknalby z metryk, a otwarta pozycja to nie jest wynik zerowy.
    if otwarte and bars:
        ostatni = bars[-1]
        dzien = trade_date(ostatni.ts)
        for pos in otwarte:
            long = pos.side == "long"
            px = ostatni.close - TICK_SIZE if long else ostatni.close + TICK_SIZE
            trade = _close_position(pos, ostatni.ts, px, "end_of_data", cm,
                                    ryzyko_pozycji.pop(id(pos), 0.0))
            res.trades.append(trade)
            zrealizowane += trade.pnl_usd
            res.daily_pnl[dzien] = res.daily_pnl.get(dzien, 0.0) + trade.pnl_usd
        res.forced_exits += len(otwarte)
        if res.equity:
            res.equity[-1] = zrealizowane

    return res


def _close_position(pos: Position, ts, px: float, powod: str,
                    cm: CostModel, ryzyko_usd: float) -> Trade:
    """Domkniecie pozycji z pelnym rachunkiem kosztow.

    Poslizg siedzi juz w cenach wejscia i wyjscia; tutaj dochodzi prowizja
    round-turn. R liczymy PO KOSZTACH — strategia, ktora wychodzi na zero
    dopiero po prowizji, nie jest strategia zyskowna.
    """
    punkty = (px - pos.entry_px) if pos.side == "long" else (pos.entry_px - px)
    brutto = punkty * POINT_VALUE * pos.qty
    prowizja = cm.commission_rt * pos.qty
    netto = brutto - prowizja
    r = (netto / ryzyko_usd) if ryzyko_usd > 0 else 0.0
    return Trade(
        side=pos.side, qty=pos.qty, entry_ts=pos.entry_ts, entry_px=pos.entry_px,
        exit_ts=ts, exit_px=px, pnl_points=punkty, pnl_usd=netto,
        r_multiple=r, exit_reason=powod, tag=pos.tag,
    )
