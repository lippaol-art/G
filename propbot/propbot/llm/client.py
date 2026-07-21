"""Claude API client for the daily ORB analysis.

Called 1-3x per trading day (pre-session analysis + optional final check), so
cost is a few dollars a month — the LLM is OFF the execution hot path.

Uses structured outputs (output_config.format json_schema) so the response is
guaranteed to match the DayAnalysis schema; parse_llm_response still validates
as defense-in-depth. Import of the `anthropic` SDK is guarded so the core test
suite runs without it.
"""
from __future__ import annotations

import os
from pathlib import Path

from .pack import pack_to_json
from .plan_parser import DayAnalysis, PlanParseError, parse_llm_response

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:  # sandbox / tests without the SDK
    anthropic = None  # type: ignore[assignment]
    HAS_ANTHROPIC = False

MODEL = os.environ.get("PROPBOT_LLM_MODEL", "claude-opus-4-8")

_PROMPT_PATH = Path(__file__).with_name("prompt_template.md")

# Mirrors llm/prompt_template.md and plan_parser.py — keep the three in sync.
DAY_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "trade_today": {"type": "boolean"},
        "grade": {"type": "string", "enum": ["A+", "A", "B", "skip"]},
        "bias": {"type": "string", "enum": ["LONG", "SHORT", "BOTH"]},
        "confidence": {"type": "number"},
        "rationale": {"type": "string"},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["trade_today", "grade", "bias", "confidence", "rationale",
                 "warnings"],
    "additionalProperties": False,
}


def load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


class AnalystClient:
    """Thin wrapper: analysis pack in, validated DayAnalysis out."""

    def __init__(self, model: str = MODEL):
        if not HAS_ANTHROPIC:
            raise RuntimeError(
                "The 'anthropic' package is not installed. "
                "pip install -r requirements.txt on the VPS deployment."
            )
        # Reads ANTHROPIC_API_KEY (or an ant auth profile) from the environment.
        self.client = anthropic.Anthropic()
        self.model = model
        self.system_prompt = load_system_prompt()

    def analyze_day(self, pack: dict) -> DayAnalysis:
        """One API call: grade the trading day from the analysis pack.

        Raises PlanParseError on a malformed response — callers treat that as
        grade="skip" (fail closed, no trade).
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            # Stable system prompt first, volatile pack in the user turn —
            # keeps the prompt-caching prefix intact across daily calls.
            system=[{
                "type": "text",
                "text": self.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            output_config={
                "format": {"type": "json_schema", "schema": DAY_ANALYSIS_SCHEMA},
            },
            messages=[{
                "role": "user",
                "content": "Analysis pack:\n" + pack_to_json(pack),
            }],
        )
        if response.stop_reason == "refusal":
            raise PlanParseError("model refused the request")
        text = next((b.text for b in response.content if b.type == "text"), "")
        if not text:
            raise PlanParseError("empty response from model")
        return parse_llm_response(text)
