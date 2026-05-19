"""
Pipeline Orchestrator — chains all 5 agents with retry logic and logging.
"""
import time
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
from loguru import logger

from agents.query_agent import understand_query
from agents.sql_agent import generate_sql
from agents.validation_agent import validate_sql, ValidationResult
from agents.execution_agent import execute_query, QueryExecutionError
from agents.insight_agent import generate_insights
import config

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


@dataclass
class PipelineResult:
    user_query: str
    intent: Optional[dict] = None
    sql: Optional[str] = None
    validation: Optional[ValidationResult] = None
    data: Optional[pd.DataFrame] = None
    insights: Optional[dict] = None
    success: bool = False
    error_message: str = ""
    duration_ms: int = 0
    retry_count: int = 0


def run_pipeline(user_query: str) -> PipelineResult:
    result = PipelineResult(user_query=user_query)
    start = time.time()

    try:
        # ── Agent 1: Query Understanding ──
        logger.info(f"[Agent 1] Understanding: {user_query!r}")
        result.intent = understand_query(user_query)

        # ── Agent 2 + 3 + 4: NL2SQL → Validate → Execute (with retry) ──
        error_feedback = ""
        for attempt in range(1, config.MAX_RETRY_ATTEMPTS + 1):
            logger.info(f"[Agent 2] Generating SQL (attempt {attempt})")
            result.sql = generate_sql(result.intent, user_query, error_feedback)

            logger.info("[Agent 3] Validating SQL")
            result.validation = validate_sql(result.sql)

            if not result.validation.is_valid:
                error_feedback = " | ".join(result.validation.errors)
                logger.warning(f"Validation failed (attempt {attempt}): {error_feedback}")
                result.retry_count = attempt
                if attempt == config.MAX_RETRY_ATTEMPTS:
                    result.error_message = f"SQL validation failed after {attempt} attempts: {error_feedback}"
                    return result
                continue

            try:
                logger.info("[Agent 4] Executing SQL")
                result.data = execute_query(result.sql)
                break
            except QueryExecutionError as e:
                error_feedback = str(e)
                logger.warning(f"Execution error (attempt {attempt}): {error_feedback}")
                result.retry_count = attempt
                if attempt == config.MAX_RETRY_ATTEMPTS:
                    result.error_message = f"Execution failed after {attempt} attempts: {error_feedback}"
                    return result

        # ── Agent 5: Insight Generation ──
        logger.info("[Agent 5] Generating insights")
        result.insights = generate_insights(user_query, result.sql, result.data)

        result.success = True

    except Exception as e:
        result.error_message = f"Pipeline error: {e}"
        logger.error(result.error_message)

    finally:
        result.duration_ms = int((time.time() - start) * 1000)
        _log_event(result, start)

    return result


def _log_event(result: PipelineResult, start: float) -> None:
    event = {
        "user_query": result.user_query,
        "intent": result.intent,
        "sql": result.sql,
        "validation_passed": result.validation.is_valid if result.validation else False,
        "row_count": len(result.data) if result.data is not None else 0,
        "duration_ms": result.duration_ms,
        "success": result.success,
        "error": result.error_message,
        "retry_count": result.retry_count,
        "insight_summary": result.insights.get("summary", "") if result.insights else "",
    }
    with open(LOG_DIR / "query_log.jsonl", "a") as f:
        f.write(json.dumps(event) + "\n")
