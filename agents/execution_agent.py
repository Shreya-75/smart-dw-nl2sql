"""
Agent 4 — Execution Agent
Runs the validated SQL against MySQL and returns a DataFrame.
"""
import pandas as pd
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loguru import logger
import sys
sys.path.insert(0, ".")
from utils.db_connection import get_engine
import config


class QueryExecutionError(Exception):
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def execute_query(sql: str) -> pd.DataFrame:
    engine = get_engine()
    timeout_ms = config.QUERY_TIMEOUT_SECONDS * 1000

    with engine.connect() as conn:
        try:
            conn.execute(text(f"SET SESSION MAX_EXECUTION_TIME={timeout_ms}"))
        except Exception:
            pass  # Some MySQL versions don't support per-session timeout

        try:
            result = conn.execute(text(sql))
            df = pd.DataFrame(result.fetchall(), columns=list(result.keys()))
            logger.info(f"Agent 4 executed query: {len(df):,} rows returned")
            return df
        except Exception as e:
            logger.warning(f"Agent 4 execution error: {e}")
            raise QueryExecutionError(str(e)) from e
