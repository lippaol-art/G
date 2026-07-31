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

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Callable, Literal, Protocol, Sequence


class AmbiguousBarPolicy(str, Enum):
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
        if self._day_r.get(trade_date_key, 0.0) <= -self.limits.daily_stop_r:
            return True
        if self._week_r.get(week_key, 0.0) <= -self.limits.weekly_stop_r:
            return True
        return False

    def validate(self, order: Order, open_positions: int) -> None:
        if self.limits.require_stop and order.sl is None:
            raise ValueError("Zlecenie bez stop-lossa odrzucone przez warstwe ryzyka (rozdz. 10.4)")
        if open_positions >= self.limits.max_positions and not self.limits.allow_averaging_down:
            raise ValueError("Usrednianie w strate jest zablokowane (rozdz. 10.4)")
