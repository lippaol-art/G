"""Model kosztow transakcyjnych MNQ.

Specyfikacja: PLAN.pdf rozdz. 3.2 (rachunek kosztow), 5.5 (model poslizgu).

Baza przyjeta swiadomie (decyzja z 31.07.2026):
    prowizja 1.20 USD RT + 1 tick poslizgu na strone = 2.20 USD round-turn

Konserwatyzm NIE jest wbudowany w baze — baza ma odzwierciedlac rzeczywistosc
(1 tick to realny spread MNQ w RTH przy 1-5 kontraktach). Margines bezpieczenstwa
mieszka w obowiazkowym stress-tescie x2, ktory jest warunkiem bramki walidacyjnej.
Wbudowanie bufora w baze powodowaloby odrzucanie strategii, ktore realnie dzialaja.
"""

from __future__ import annotations

from dataclasses import dataclass

# Specyfikacja kontraktu (PLAN.pdf aneks B)
POINT_VALUE = 2.0        # USD za punkt indeksowy
TICK_SIZE = 0.25         # punktu
TICK_VALUE = 0.50        # USD (= TICK_SIZE * POINT_VALUE)

# Poslizg bazowy w tickach, per segment doby (PLAN.pdf tabela 5.5).
# Weryfikacja zewnetrzna potwierdzila, ze 1 tick w RTH odpowiada realnej
# glebokosci pierwszego poziomu ksiegi przy 1-5 kontraktach.
BASE_SLIPPAGE_TICKS: dict[str, int] = {
    "globex_open": 2,
    "asia": 2,          # cienka ksiega
    "europe": 1,
    "premarket": 2,
    "rth_open": 2,      # ruchliwa ksiega
    "midday": 1,        # baza
    "afternoon": 1,
    "close": 1,
    "after_hours": 3,   # plynnosc ucieka
    "maintenance": 99,  # nie handlujemy
}

EVENT_SLIPPAGE_TICKS = 4     # +-10 min od zdarzenia rangi 1
VOL_MULT_MIN, VOL_MULT_MAX = 1.0, 3.0
GAP_SLIPPAGE_K = 1.5         # wspolczynnik skalowania poslizgu stop-gap
GAP_SLIPPAGE_CAP = 4.0       # maks. krotnosc ATR uwzgledniana


@dataclass(frozen=True)
class CostModel:
    """Konfiguracja kosztow. Kazdy backtest zapisuje ja do raportu."""

    commission_rt: float = 1.20      # USD round-turn (prowizja + oplaty gieldowe + regulacyjne)
    stress_multiplier: float = 1.0   # 2.0 w stress-tescie (bramka 7.6)

    def commission_per_side(self) -> float:
        return self.commission_rt / 2.0

    def round_turn_cost(self, slippage_ticks_total: int) -> float:
        """Pelny koszt round-turn w USD przy zadanym lacznym poslizgu (obie strony)."""
        return self.commission_rt + slippage_ticks_total * TICK_VALUE * self.stress_multiplier


def slippage_ticks(
    segment: str,
    *,
    atr_m1: float | None = None,
    atr_m1_median: float | None = None,
    near_event: bool = False,
    stress_multiplier: float = 1.0,
) -> float:
    """Poslizg w tickach, skalowany zmiennoscia.

    Statyczna tabela zanizalaby koszt dokladnie w tych momentach, w ktorych
    jest najwiekszy — stad mnoznik zmiennosci (rozdz. 5.5):

        slippage = base(segment) * clamp(ATR_M1 / median(ATR_M1, 60d), 1.0, 3.0)

    Model nie korzysta z rzeczywistej szerokosci spreadu, bo schemat OHLCV jej
    nie zawiera; ATR minutowy jest proxy. Przy danych bbo-1s nalezy zastapic
    mnoznik zmierzonym spreadem — to jedyna zmiana wymagana w tym module.
    """
    base = float(EVENT_SLIPPAGE_TICKS if near_event else BASE_SLIPPAGE_TICKS.get(segment, 2))

    mult = 1.0
    if atr_m1 is not None and atr_m1_median is not None and atr_m1_median > 0:
        mult = min(max(atr_m1 / atr_m1_median, VOL_MULT_MIN), VOL_MULT_MAX)

    return base * mult * stress_multiplier


def gap_stop_slippage_ticks(
    gap_points: float,
    atr_m1: float,
    *,
    base_ticks: float = 1.0,
    stress_multiplier: float = 1.0,
) -> float:
    """Poslizg stopa przeskoczonego luka (rozdz. 5.4).

    W pierwszych sekundach po otwarciu luka plynnosc w ksiedze spada niemal do
    zera, wiec realna kara siega 2-8 tickow ponad cene open. Zwykly narzut
    segmentowy zanizalby tu ryzyko.

        slip_gap = base + k * min(gap / ATR_M1, 4)
    """
    if atr_m1 <= 0:
        ratio = 0.0
    else:
        ratio = min(abs(gap_points) / atr_m1, GAP_SLIPPAGE_CAP)
    return (base_ticks + GAP_SLIPPAGE_K * ratio) * stress_multiplier


def ticks_to_usd(ticks: float) -> float:
    return ticks * TICK_VALUE


def points_to_usd(points: float, contracts: int = 1) -> float:
    return points * POINT_VALUE * contracts


def annual_cost(trades_per_day: float, cost_model: CostModel | None = None,
                slippage_ticks_total: int = 2, sessions_per_year: int = 251) -> float:
    """Roczny koszt na kontrakt — rachunek z rozdz. 3.2.

    Przy bazie 2.20 USD RT: 2 transakcje dziennie -> ~1104 USD rocznie.
    """
    cm = cost_model or CostModel()
    return trades_per_day * sessions_per_year * cm.round_turn_cost(slippage_ticks_total)
