# propbot

A **hybrid AI/human** trading assistant for a prop-firm account.

An LLM does the slow, thorough analysis and proposes a *conditional* setup; fast
deterministic code watches for the entry trigger and enforces risk; **you** get a
Telegram card and approve or cancel with one tap; the executor then sends the
order and verifies the whole lifecycle at the broker.

> **Status:** framework + backtest, running on a mock adapter. Not connected to a
> real account. This is an **experiment** ("can AI pass and manage a prop-firm
> account?"), not financial advice. See *Reality check* below.

---

## Why this shape

The feasibility research was blunt: **do not put an LLM on the execution hot
path** — 1–4 s latency means slippage, missed fills, and JSON-parse failures.
So the LLM stays off it:

| Layer | Owner | On the hot path? | Role |
|---|---|---|---|
| Day analysis → conditional plan | **LLM** (Claude, async) | ❌ | grade the day (A+/A/B/skip), bias, rationale |
| Confirmation on candle close | **deterministic code** | ✅ | cheap check every closed candle — can wait for hours |
| Position sizing + hard veto | **deterministic RMS** | ✅ | independent of the model; final say |
| Approve / cancel | **human** (Telegram) | — | one tap |
| Order lifecycle + reconciliation | **deterministic code** | ✅ | verify retcode → position → SL/TP → slippage |

The LLM is called **1–3× per trading day** (pre-session grade + optional final
check), so API cost is a few dollars a month — the "$100–500/mo" figure in the
research is for continuous M1/M5 polling, which this does not do.

## Strategy

**Opening Range Breakout (ORB)** on index CFDs (US30 / NAS100), the market and
setup chosen for the test:

- Range = first 30 min of the NY session (09:30 ET, DST-aware via `zoneinfo`).
- Long plan above the range high, short below the low.
- **Confirmation = an M15 candle *closes* beyond the edge** (checked by the
  watcher, not the LLM).
- SL capped by ATR, TP a multiple of risk, flat by session cutoff — no overnight
  risk from this strategy.

ORB is deterministic (so it codes cleanly and maps onto the zone→confirm
watcher) and evidence-backed (Zarattini/Barbon/Aziz, SSRN 4729284; ~56% WR, R:R
1.8 on 15-min S&P). The LLM only *grades* the day; the grade feeds the risk
manager's yellow-zone "A/A+ only" gate.

## Prop-firm rules baked in

Target: **The5ers High Stakes 2-Step, $10k** (self-authored EA allowed, 1:100,
penalises HFT — fits this design). Rules live in `config/prop_firms.yaml` and are
just parameters; other firms (E8, FTMO, FundedNext, FundingPips) are included.

- **Daily loss** 5% and **max loss** 10% (static) → floors in the risk manager,
  with a safety buffer (α=0.80) so we stop before the hard limit to survive
  slippage.
- **Graduated Recovery Protocol**: 🟢 0–2% dd → 1% risk · 🟡 2–3.5% → 0.5%, A/A+
  only · 🔴 >3.5% → flat & block for the day.
- **News blackout** ±2 min around high-impact events (fail-closed if the
  calendar is missing/stale).
- Stochastic entry jitter + per-instance magic number to avoid group-trading
  detection.

## Architecture

```
propbot/
  config/
    prop_firms.yaml          # rule sets per firm (limits, automation, news)
    settings.example.yaml    # account + market + execution settings
  propbot/
    schema.py                # TradePlan / AccountState / order contracts
    risk/                    # deterministic RMS: zones, floors, sizing, veto
    state/                   # setup state machine + durable JSON store
    market/                  # indicators (EMA/SMA/RSI/ATR) + news blackout
    strategy/orb.py          # opening-range detection + conditional plans
    watcher/                 # candle-close watcher (arms/confirms/expires)
    llm/                     # analysis pack, prompt, Claude client, parser
    execution/               # base interface, mock, MT5, lifecycle+reconcile
    telegram/                # card formatting (pure) + bot runtime
    backtest/                # runner using the SAME risk + watcher as live
  tests/                     # 57 stdlib unittest cases
  demo.py                    # end-to-end flow on the mock adapter
```

### Setup lifecycle

```
WAITING_FOR_PRICE → ARMED → CONFIRMED → EXECUTING → OPEN → CLOSED
        └── EXPIRED / INVALIDATED / CANCELLED (terminal)
```

State is persisted (atomic JSON write), so a setup can sit `ARMED` for hours and
survive a VPS/process restart.

## Run it

Core + tests need **only the Python standard library** (3.11+):

```bash
python3 -m unittest discover -s tests   # 57 tests
python3 demo.py                          # end-to-end flow, mock adapter
```

Backtest (bring your own M15 CSV: `time,open,high,low,close[,volume]`):

```python
from propbot.backtest import BacktestRunner, load_candles_csv
from propbot.risk import RiskLimits, SymbolSpec
runner = BacktestRunner(
    RiskLimits(daily_loss_limit=0.05, max_drawdown=0.10, drawdown_type="static",
               profit_target=0.10, min_trading_days=0),
    SymbolSpec(pip_size=1.0, pip_value_per_lot=1.0))   # VERIFY broker specs
print(runner.run(load_candles_csv("US30_M15.csv")).summary())
```

## Live deployment (Windows VPS)

Live trading needs MetaTrader5 + Telegram + Claude, none of which run in the dev
sandbox. On a low-latency **Windows VPS (London)** with the MT5 terminal logged
into the prop account:

1. `pip install -r requirements.txt`
2. Copy `config/settings.example.yaml` → `settings.yaml`, `.env.example` → `.env`
   (both gitignored). **Verify the index CFD contract specs** (min lot, point
   value) against the broker — on a $10k account the sizing must fit the ~$100
   per-trade budget.
3. Register the VPS static IP with the prop firm.
4. Run against a **demo/micro account for ≥30 days** (forward test) before any
   real challenge.

## Reality check

- $10k is a great **testbed**, not an income stream — absolute numbers are small.
- Prop-firm rules change often; re-verify before risking the entry fee.
- Confirm The5ers' automation policy for this exact program, and whether Max Loss
  is static or trailing, before trading.
- Numbers in `prop_firms.yaml` are representative and marked `VERIFY`.

## Not yet built

- Orchestrator (`app.py`) wiring the daily LLM call → watcher loop → Telegram.
- Economic-calendar fetcher (currently a hand-maintained JSON).
- Fully-autonomous mode (LLM via API on candle close) — deliberately deferred
  until the human-approval flow proves out.
