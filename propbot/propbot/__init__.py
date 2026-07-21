"""propbot - hybrid AI/human prop-firm trading assistant.

Architecture (see README.md):
  LLM (async)          -> builds conditional TradePlans, off the execution hot path
  Watcher (fast code)  -> checks confirmation conditions on each closed candle
  RiskManager (code)   -> position sizing + hard veto (independent of the LLM)
  Human (Telegram)     -> approves/cancels each confirmed setup
  Executor (code)      -> sends orders and verifies the full order lifecycle
"""

__version__ = "0.1.0"
