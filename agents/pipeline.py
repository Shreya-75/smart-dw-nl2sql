"""
Pipeline Orchestrator — agentic ReAct loop.

Each iteration of the loop follows the Observe → Reason → Act pattern:

  Agent 1  →  Parse natural-language intent (reruns if incomplete or reflection advises)
  ↓
  [Agentic loop — up to MAX_RETRY_ATTEMPTS]:
    Agent 2  →  Generate SQL (receives structured reflection feedback, not raw error)
    Agent 3  →  Validate SQL (safety + schema checks)
    if fail  →  Reflection Agent classifies error, plans fix → loop
    Agent 4  →  Execute SQL against MySQL
    if empty →  Reflection Agent plans filter relaxation → loop (once)
    if error →  Reflection Agent diagnoses DB error → loop
  ↓
  Agent 5  →  Generate business insights from result DataFrame

Progress events are emitted via an optional callback so the UI can render
a live step-by-step trace of every decision the pipeline makes.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable
import pandas as pd
from loguru import logger

from agents.query_agent      import understand_query
from agents.sql_agent        import generate_sql
from agents.validation_agent import validate_sql, ValidationResult
from agents.execution_agent  import execute_query, QueryExecutionError
from agents.insight_agent    import generate_insights
from agents.reflection_agent import reflect, classify_error
import config

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

ProgressFn = Optional[Callable[[dict], None]]

# Agent display names used in traces and UI
_AGENT_NAMES = {
    1:   "Query Understanding",
    2:   "NL2SQL Generation",
    3:   "SQL Validation",
    4:   "SQL Execution",
    5:   "Insight Generation",
    "R": "Reflection",
}


@dataclass
class PipelineResult:
    user_query:    str
    intent:        Optional[dict]             = None
    sql:           Optional[str]              = None
    validation:    Optional[ValidationResult] = None
    data:          Optional[pd.DataFrame]     = None
    insights:      Optional[dict]             = None
    success:       bool                       = False
    error_message: str                        = ""
    duration_ms:   int                        = 0
    retry_count:   int                        = 0
    agent_trace:   list                       = field(default_factory=list)


def run_pipeline(
    user_query: str,
    on_progress: ProgressFn = None,
    conversation_history: str = "",
) -> PipelineResult:
    result = PipelineResult(user_query=user_query)
    start  = time.time()

    def emit(agent, action, message, **extra):
        event = {"agent": agent, "action": action, "message": message,
                 "name": _AGENT_NAMES.get(agent, str(agent)), **extra}
        result.agent_trace.append(event)
        if on_progress:
            on_progress(event)

    try:
        # ────────────────────────────────────────────────────────────────────
        # Agent 1 — Query Understanding
        # ────────────────────────────────────────────────────────────────────
        emit(1, "start",  "Parsing natural-language intent…")
        logger.info(f"[Agent 1] Understanding: {user_query!r}")
        result.intent = understand_query(user_query, conversation_history=conversation_history)
        emit(1, "done",   "Intent extracted", intent=result.intent)

        # Self-check: if both metric and dimension are absent, re-run Agent 1
        # with an explicit clarification nudge before entering the SQL loop.
        if not result.intent.get("metric") and not result.intent.get("dimension"):
            emit(1, "re_understand",
                 "Intent incomplete — re-running Agent 1 with clarification")
            logger.warning("[Agent 1] Intent incomplete — clarification pass")
            result.intent = understand_query(
                user_query,
                conversation_history=conversation_history,
                context=(
                    "Re-analyse the question and explicitly identify: "
                    "(1) the numeric metric being requested and "
                    "(2) the dimension or grouping field."
                ),
            )
            emit(1, "done", "Intent refined", intent=result.intent)

        # ────────────────────────────────────────────────────────────────────
        # Agentic loop: Generate → Validate → [Reflect] → Execute
        # ────────────────────────────────────────────────────────────────────
        reflection    = None   # last Reflection Agent output
        empty_retried = False  # guard: only attempt empty-result recovery once

        for attempt in range(1, config.MAX_RETRY_ATTEMPTS + 1):

            # Build structured feedback from the reflection (beats passing raw errors)
            if reflection:
                feedback = (
                    f"PREVIOUS FAILURE TYPE : {reflection.get('error_type', 'unknown')}\n"
                    f"ROOT CAUSE DIAGNOSED  : {reflection['root_cause']}\n"
                    f"REQUIRED FIX          : {reflection['fix_instruction']}"
                )
            else:
                feedback = ""

            # ── Agent 2: Generate SQL ────────────────────────────────────────
            emit(2, "start",
                 f"Generating SQL (attempt {attempt}/{config.MAX_RETRY_ATTEMPTS})…",
                 attempt=attempt)
            logger.info(f"[Agent 2] Generating SQL (attempt {attempt})")
            result.sql = generate_sql(result.intent, user_query, feedback)
            emit(2, "done", "SQL generated", sql=result.sql)

            # ── Agent 3: Validate SQL ────────────────────────────────────────
            emit(3, "start", "Validating SQL — safety and schema checks…")
            logger.info("[Agent 3] Validating SQL")
            result.validation = validate_sql(result.sql)

            if not result.validation.is_valid:
                raw_error = " | ".join(result.validation.errors)
                logger.warning(f"[Agent 3] Validation failed (attempt {attempt}): {raw_error}")
                result.retry_count = attempt
                emit(3, "failed",
                     f"Validation failed: {raw_error}",
                     error=raw_error, attempt=attempt)

                if attempt < config.MAX_RETRY_ATTEMPTS:
                    # ── Reflection Agent ─────────────────────────────────────
                    error_type = classify_error(raw_error)
                    emit("R", "start",
                         f"Analysing failure [{error_type}]…",
                         error_type=error_type)
                    reflection = reflect(
                        user_query, result.intent, result.sql, raw_error, attempt
                    )
                    emit("R", "done",
                         reflection["root_cause"],
                         plan=reflection["fix_instruction"],
                         error_type=reflection["error_type"])

                    # If reflection flags intent as the root cause, re-run Agent 1
                    if reflection.get("should_revise_intent"):
                        emit(1, "re_understand",
                             "Reflection recommends revising query understanding…")
                        result.intent = understand_query(
                            user_query,
                            context=reflection.get("fix_instruction", ""),
                            conversation_history=conversation_history,
                        )
                        emit(1, "done", "Query intent revised", intent=result.intent)
                else:
                    result.error_message = (
                        f"SQL validation failed after {attempt} attempts: {raw_error}"
                    )
                    return result
                continue  # next attempt with structured reflection feedback

            emit(3, "done", "SQL passed all validation checks")

            # ── Agent 4: Execute SQL ─────────────────────────────────────────
            try:
                emit(4, "start", "Executing query against MySQL warehouse…")
                logger.info("[Agent 4] Executing SQL")
                result.data = execute_query(result.sql)
                row_count   = len(result.data)
                logger.info(f"[Agent 4] {row_count:,} rows returned")

                # Empty-result recovery: reflect once and retry with looser filters
                if row_count == 0 and not empty_retried and attempt < config.MAX_RETRY_ATTEMPTS:
                    empty_retried = True
                    empty_error   = (
                        "Query executed successfully but returned 0 rows. "
                        "Filters are likely too restrictive."
                    )
                    emit(4, "empty_result",
                         "Zero rows returned — reflecting on filter constraints…")
                    reflection = reflect(
                        user_query, result.intent, result.sql, empty_error, attempt
                    )
                    emit("R", "done",
                         reflection["root_cause"],
                         plan=reflection["fix_instruction"],
                         error_type=reflection["error_type"])
                    continue  # retry with relaxed filters

                emit(4, "done",
                     f"Execution succeeded — {row_count:,} row{'s' if row_count != 1 else ''} returned",
                     rows=row_count)
                break  # success — exit the agentic loop

            except QueryExecutionError as exc:
                raw_error = str(exc)
                logger.warning(f"[Agent 4] Execution error (attempt {attempt}): {raw_error}")
                result.retry_count = attempt
                emit(4, "failed",
                     f"Execution error: {raw_error[:90]}",
                     error=raw_error, attempt=attempt)

                if attempt < config.MAX_RETRY_ATTEMPTS:
                    error_type = classify_error(raw_error)
                    emit("R", "start",
                         f"Diagnosing DB error [{error_type}]…",
                         error_type=error_type)
                    reflection = reflect(
                        user_query, result.intent, result.sql, raw_error, attempt
                    )
                    emit("R", "done",
                         reflection["root_cause"],
                         plan=reflection["fix_instruction"],
                         error_type=reflection["error_type"])
                else:
                    result.error_message = (
                        f"Execution failed after {attempt} attempts: {raw_error}"
                    )
                    return result

        # ────────────────────────────────────────────────────────────────────
        # Agent 5 — Insight Generation
        # ────────────────────────────────────────────────────────────────────
        emit(5, "start", "Generating business insights from result…")
        logger.info("[Agent 5] Generating insights")
        result.insights = generate_insights(user_query, result.sql, result.data)
        emit(5, "done",  "Insights generated")

        result.success = True

    except Exception as exc:
        result.error_message = f"Pipeline error: {exc}"
        logger.error(result.error_message)
        emit("pipeline", "error", str(exc))

    finally:
        result.duration_ms = int((time.time() - start) * 1000)
        _log_event(result, start)

    return result


def _log_event(result: PipelineResult, start: float) -> None:
    event = {
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "user_query":        result.user_query,
        "intent":            result.intent,
        "sql":               result.sql,
        "validation_passed": result.validation.is_valid if result.validation else False,
        "row_count":         len(result.data) if result.data is not None else 0,
        "duration_ms":       result.duration_ms,
        "success":           result.success,
        "error":             result.error_message,
        "retry_count":       result.retry_count,
        "insight_summary":   result.insights.get("summary", "") if result.insights else "",
        "agent_trace":       result.agent_trace,
    }
    with open(LOG_DIR / "query_log.jsonl", "a") as f:
        f.write(json.dumps(event, default=str) + "\n")
