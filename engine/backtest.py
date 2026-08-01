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

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal, Protocol

from engine.costs import BASE_SLIPPAGE_TICKS, TICK_SIZE, CostModel, points_to_usd
from engine.guards import HistoryView


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
    trade_date: object = None    # dzien sesyjny (od 18:00 ET) — klucz limitow ryzyka

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


@dataclass
class Position:
    side: Side
    qty: int
    entry_px: float
    entry_ts: object
    sl: float | None
    tp: float | None = None
    tag: str = ""
    entry_bar_index: int = -1    # bar wejscia — wyjscie dopuszczalne od nastepnego (5.4)


@dataclass
class Trade:
    side: Side
    qty: int
    entry_ts: object
    entry_px: float
    exit_ts: object
    exit_px: float
    pnl_points: float
    pnl_usd: float               # NETTO — po prowizji; poslizg juz w cenach
    r_multiple: float
    exit_reason: str
    tag: str = ""
    commission_usd: float = 0.0

    @property
    def pnl_usd_gross(self) -> float:
        """Wynik przed prowizja. Poslizg pozostaje w cenach wejscia/wyjscia —
        jest czescia wykonania, nie oplata. Test symetrii (5.6) porownuje
        wlasnie te wielkosc przy zerowym poslizgu."""
        return self.pnl_usd + self.commission_usd


@dataclass
class Result:
    trades: list[Trade] = field(default_factory=list)
    equity: list[float] = field(default_factory=list)
    config: dict = field(default_factory=dict)
    ambiguous_bars: int = 0      # ile barow wymagalo rozstrzygniecia SL/TP
    skipped_zero_volume: int = 0 # ile wykonan zablokowano brakiem wolumenu
    rejected_orders: int = 0     # odrzucone przez warstwe ryzyka lub zajeta pozycje
    blocked_bars: int = 0        # bary, w ktorych limit dzienny/tygodniowy wylaczyl strategie

    @property
    def net_usd(self) -> float:
        return sum(t.pnl_usd for t in self.trades)

    @property
    def gross_usd(self) -> float:
        return sum(t.pnl_usd_gross for t in self.trades)

    @property
    def commission_usd(self) -> float:
        return sum(t.commission_usd for t in self.trades)


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

    # Pozycja bez stopa istnieje wylacznie w testach silnika (5.6, test symetrii)
    # i w strategiach z wyjsciem czasowym. Warstwa ryzyka domyslnie jej zabrania.
    if pos.sl is None:
        if pos.tp is not None:
            tp_hit = (bar.high >= pos.tp + TICK_SIZE) if long else (bar.low <= pos.tp - TICK_SIZE)
            if tp_hit:
                return pos.tp, "take_profit"
        return None

    # --- gap: open juz przekroczyl stopa -> wykonanie po open, nie po cenie SL
    gap_hit = (bar.open <= pos.sl) if long else (bar.open >= pos.sl)
    if gap_hit:
        slip = gap_slippage_points if gap_slippage_points is not None else slippage_points
        px = bar.open - slip if long else bar.open + slip
        return px, "stop_gap"

    sl_touched = (bar.low <= pos.sl) if long else (bar.high >= pos.sl)

    # Zlecenie z limitem wymaga PRZEBICIA o co najmniej tick — samo dotkniecie
    # nie gwarantuje wypelnienia przy odleglej pozycji w kolejce.
    tp = pos.tp
    tp_touched = False
    if tp is not None:
        tp_touched = (bar.high >= tp + TICK_SIZE) if long else (bar.low <= tp - TICK_SIZE)

    if sl_touched and tp_touched:
        assert tp is not None   # tp_touched implikuje istnienie limitu
        if policy is AmbiguousBarPolicy.SUBBAR_1S:
            if subbar_resolver is None:
                raise ValueError(
                    "Polityka SUBBAR_1S wymaga danych 1s (subbar_resolver). "
                    "Bez nich uzyj SL_WINS/TP_WINS i raportuj pasmo wrazliwosci."
                )
            first = subbar_resolver(pos, bar)
            if first == "tp":
                return tp, "take_profit"
            if first == "sl":
                return (pos.sl - slippage_points) if long else (pos.sl + slippage_points), "stop_loss"
            # resolver nie rozstrzygnal -> konserwatywnie
            return (pos.sl - slippage_points) if long else (pos.sl + slippage_points), "stop_loss"

        if policy is AmbiguousBarPolicy.TP_WINS:
            return tp, "take_profit"
        return (pos.sl - slippage_points) if long else (pos.sl + slippage_points), "stop_loss"

    if sl_touched:
        return (pos.sl - slippage_points) if long else (pos.sl + slippage_points), "stop_loss"

    if tp_touched and tp is not None:
        return tp, "take_profit"

    return None


def is_ambiguous(pos: Position, bar: Bar) -> bool:
    """Czy bar dotyka jednoczesnie SL i TP (wymaga rozstrzygniecia)."""
    if pos.tp is None or pos.sl is None:
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
# Glowna petla — pseudokod 5.3 przelozony 1:1
# --------------------------------------------------------------------------

def default_slippage_points(bar: Bar) -> float:
    """Poslizg bazowy w PUNKTACH wg segmentu doby (tabela 5.5).

    Mnoznik zmiennosci wymaga ATR minutowego, ktorego surowy Bar nie niesie —
    strategie liczace ATR podaja wlasny `slippage_model`. Ta funkcja jest baza
    i celowo NIE zaniza kosztu: brak mnoznika oznacza mnoznik 1.0, czyli dolna
    granice przedzialu [1.0, 3.0] z rozdz. 5.5.
    """
    return BASE_SLIPPAGE_TICKS.get(bar.segment, 2) * TICK_SIZE


def _week_key(td: object) -> object:
    """Klucz tygodnia sesyjnego dla limitu tygodniowego."""
    iso = getattr(td, "isocalendar", None)
    if iso is None:
        return td
    c = iso()
    return (c[0], c[1])


def run_backtest(
    bars: Sequence[Bar],
    strategy: Strategy,
    *,
    cost_model: CostModel | None = None,
    policy: AmbiguousBarPolicy = AmbiguousBarPolicy.SL_WINS,
    risk: RiskLimits | None = None,
    slippage_model: Callable[[Bar], float] | None = None,
    force_flat: Callable[[Bar, Position], bool] | None = None,
    subbar_resolver: Callable[[Position, Bar], str | None] | None = None,
    config: dict | None = None,
) -> Result:
    """Przebieg backtestu bar po barze — realizacja pseudokodu z rozdz. 5.3.

    Kolejnosc w barze jest CZESCIA SPECYFIKACJI, nie detalem implementacji:

      1. wyjscia pozycji otwartych we WCZESNIEJSZYCH barach (tabela 5.4),
      2. przymusowe splaszczenie (flat-by), jesli strategia je definiuje,
      3. wypelnienie zlecen zlozonych w barze poprzednim — po OPEN tego bara,
      4. twarde limity ryzyka — PRZED strategia, zeby zadna regula ich nie obeszla,
      5. strategia widzi wylacznie `HistoryView` do biezacego bara wlacznie,
      6. ksiegowanie equity po mark-to-market.

    Punkt 1 przed 3 gwarantuje niezmiennik z tabeli 5.4: pozycja otwarta w barze
    i moze sie zamknac najwczesniej w barze i+1. W barze wejscia znamy fakt
    wypelnienia, ale nie trajektorie ceny po nim — rozstrzyganie SL/TP w tym
    samym barze byloby zgadywaniem kolejnosci, ktorej dane M1 nie zawieraja.

    KOSZTY SA DOMYSLNE. `cost_model=None` oznacza `CostModel()` — pelna prowizja
    z rozdz. 3.2 — a nie "bez kosztow". Backtest bez kosztow musi byc zazadany
    jawnie (`CostModel(commission_rt=0.0)` + `slippage_model=lambda b: 0.0`)
    i sluzy WYLACZNIE testom silnika z rozdz. 5.6, gdzie symetrie mierzy sie
    "przed kosztami". Zaden wynik badawczy nie moze pochodzic z tego trybu.
    """
    slip_fn = slippage_model if slippage_model is not None else default_slippage_points
    koszty = cost_model if cost_model is not None else CostModel()
    gate = RiskGate(risk if risk is not None else RiskLimits())
    res = Result(config=dict(config or {}))

    state: dict = {}
    pos: Position | None = None
    pending: list[Order] = []
    realized_usd = 0.0

    def _close(bar: Bar, px: float, reason: str, idx: int) -> None:
        nonlocal pos, realized_usd
        assert pos is not None
        pts = (px - pos.entry_px) if pos.side == "long" else (pos.entry_px - px)
        gross = points_to_usd(pts, pos.qty)
        prowizja = koszty.commission_rt * pos.qty
        netto = gross - prowizja
        ryzyko = abs(pos.entry_px - pos.sl) if pos.sl is not None else 0.0
        r = (pts / ryzyko) if ryzyko > 0 else 0.0
        res.trades.append(Trade(
            side=pos.side, qty=pos.qty,
            entry_ts=pos.entry_ts, entry_px=pos.entry_px,
            exit_ts=bar.ts, exit_px=px,
            pnl_points=pts, pnl_usd=netto, r_multiple=r,
            exit_reason=reason, tag=pos.tag, commission_usd=prowizja,
        ))
        realized_usd += netto
        gate.register(bar.trade_date, _week_key(bar.trade_date), r)
        pos = None

    for i, bar in enumerate(bars):
        # --- 1. WYJSCIA (tylko pozycje z wczesniejszych barow)
        if pos is not None and pos.entry_bar_index < i:
            if is_ambiguous(pos, bar):
                res.ambiguous_bars += 1
            wyjscie = resolve_exit(
                pos, bar, policy=policy,
                slippage_points=slip_fn(bar),
                subbar_resolver=subbar_resolver,
            )
            if wyjscie is not None:
                _close(bar, wyjscie[0], wyjscie[1], i)

        # --- 2. PRZYMUSOWE SPLASZCZENIE (koniec okna strategii intraday)
        if pos is not None and pos.entry_bar_index < i and force_flat is not None \
                and force_flat(bar, pos) and bar.tradeable:
            slip = slip_fn(bar)
            px = bar.close - slip if pos.side == "long" else bar.close + slip
            _close(bar, px, "flat_by", i)

        # --- 3. WYPELNIENIE ZLECEN Z POPRZEDNIEGO BARA — po OPEN
        if pending:
            if not bar.tradeable:
                # Bar bez transakcji: nie bylo gdzie sie wykonac (rozdz. 4.2).
                res.skipped_zero_volume += len(pending)
            elif pos is not None:
                res.rejected_orders += len(pending)
            else:
                o = pending[0]
                res.rejected_orders += len(pending) - 1
                slip = slip_fn(bar)
                fill = bar.open + slip if o.side == "long" else bar.open - slip
                pos = Position(
                    side=o.side, qty=o.qty, entry_px=fill, entry_ts=bar.ts,
                    sl=o.sl, tp=o.tp, tag=o.tag, entry_bar_index=i,
                )
            pending = []

        # --- 4. LIMITY RYZYKA — twarde, przed strategia
        if gate.blocked(bar.trade_date, _week_key(bar.trade_date)):
            res.blocked_bars += 1
        else:
            # --- 5. STRATEGIA — widzi wylacznie przeszlosc do bara i wlacznie
            # Silnik dokleja do stanu wlasny obraz pozycji. Strategia musi wiedziec,
            # czy jest plaska, a nie moze tego wnioskowac z historii barow — bez tego
            # kazda regula w rodzaju "wchodz tylko gdy brak pozycji" bylaby
            # nieodtwarzalna miedzy backtestem a petla live.
            state["position_side"] = pos.side if pos is not None else None
            state["position_entry_px"] = pos.entry_px if pos is not None else None
            state["realized_usd"] = realized_usd
            for o in strategy.on_bar(bar, HistoryView(bars, cutoff=i), state):
                try:
                    gate.validate(o, 1 if pos is not None else 0)
                except ValueError:
                    res.rejected_orders += 1
                    continue
                pending.append(o)

        # --- 6. KSIEGOWANIE
        if pos is None:
            res.equity.append(realized_usd)
        else:
            otw = (bar.close - pos.entry_px) if pos.side == "long" else (pos.entry_px - bar.close)
            res.equity.append(realized_usd + points_to_usd(otw, pos.qty))

    return res
