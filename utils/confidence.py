"""
Query confidence scorer.

Produces a 0–100 score that reflects how reliably the pipeline answered
the query. Agents that self-report their own reliability are a hallmark
of production AI systems — this score is displayed alongside every result.

Scoring rubric
--------------
+30  Passed SQL validation on the first attempt
-10  Each retry that was needed (validation OR execution)
+20  Result set is non-empty (> 0 rows)
+20  Reflection Agent was never triggered
+30  All 4 insight fields are non-empty (not just placeholders)
─────────────────────────────────────
Max: 100  |  Min: 0 (clamped)
"""
from __future__ import annotations
from agents.pipeline import PipelineResult


def compute_confidence(result: PipelineResult) -> int:
    """Return a 0–100 confidence score for a completed pipeline result."""
    if not result.success:
        return 0

    score = 0

    # +30 for first-attempt validation pass
    if result.retry_count == 0:
        score += 30

    # -10 per retry needed
    score -= result.retry_count * 10

    # +20 for non-empty result
    if result.data is not None and not result.data.empty:
        score += 20

    # +20 if no Reflection Agent was triggered (look at trace)
    reflection_triggered = any(
        ev.get("agent") == "R" for ev in (result.agent_trace or [])
    )
    if not reflection_triggered:
        score += 20

    # +30 if all 4 insight fields are substantive (> 10 chars each)
    if result.insights:
        fields = ["summary", "trend", "key_finding", "recommendation"]
        if all(len(result.insights.get(f, "")) > 10 for f in fields):
            score += 30

    return max(0, min(100, score))


def confidence_badge(score: int) -> tuple[str, str]:
    """Return (css_class, label) for the confidence badge."""
    if score >= 85:
        return "badge-success", f"Confidence {score}%"
    if score >= 60:
        return "badge-warn",    f"Confidence {score}%"
    return "badge-error",       f"Confidence {score}%"
