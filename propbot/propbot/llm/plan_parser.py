"""Parse & validate the LLM's day-analysis response.

The model returns a *grade*, not a trade. Deterministic code (strategy/orb.py)
builds the actual TradePlans and stamps the grade onto them. Strict validation:
anything malformed is rejected — the system then behaves as if the day were
graded "skip" (fail closed).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass


class PlanParseError(Exception):
    pass


VALID_GRADES = {"A+", "A", "B", "skip"}
VALID_BIAS = {"LONG", "SHORT", "BOTH"}


@dataclass
class DayAnalysis:
    trade_today: bool
    grade: str
    bias: str
    confidence: float
    rationale: str
    warnings: list[str]


def _extract_json(text: str) -> dict:
    """Tolerate accidental markdown fences, but nothing beyond that."""
    cleaned = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    try:
        obj = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise PlanParseError(f"response is not valid JSON: {e}") from e
    if not isinstance(obj, dict):
        raise PlanParseError("response JSON is not an object")
    return obj


def parse_llm_response(text: str) -> DayAnalysis:
    obj = _extract_json(text)

    missing = [k for k in ("trade_today", "grade", "bias", "confidence",
                           "rationale") if k not in obj]
    if missing:
        raise PlanParseError(f"missing fields: {', '.join(missing)}")

    grade = str(obj["grade"])
    if grade not in VALID_GRADES:
        raise PlanParseError(f"invalid grade {grade!r}, expected one of {sorted(VALID_GRADES)}")

    bias = str(obj["bias"]).upper()
    if bias not in VALID_BIAS:
        raise PlanParseError(f"invalid bias {bias!r}, expected one of {sorted(VALID_BIAS)}")

    try:
        confidence = float(obj["confidence"])
    except (TypeError, ValueError) as e:
        raise PlanParseError("confidence is not a number") from e
    if not 0.0 <= confidence <= 1.0:
        raise PlanParseError(f"confidence {confidence} outside [0,1]")

    trade_today = bool(obj["trade_today"])
    if grade == "skip" and trade_today:
        raise PlanParseError("grade 'skip' contradicts trade_today=true")

    warnings = obj.get("warnings", [])
    if not isinstance(warnings, list):
        raise PlanParseError("warnings must be a list")

    return DayAnalysis(
        trade_today=trade_today,
        grade=grade,
        bias=bias,
        confidence=confidence,
        rationale=str(obj["rationale"]),
        warnings=[str(w) for w in warnings],
    )
