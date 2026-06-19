"""
Reflection Agent — the reasoning layer between pipeline attempts.

Implements the "Observe → Reason → Plan" step of the ReAct loop:
  Observe  : receives the SQL that failed, the error, and the parsed intent
  Reason   : classifies the error type with fast pattern matching
  Plan     : returns a structured recovery dict consumed by the orchestrator

For known error categories (GROUP BY, column names, syntax, etc.) the fix
instruction is rule-based and requires no extra LLM call — keeping retries fast.
For genuinely unknown errors, falls back to a targeted LLM reasoning call.
"""
import json
import re
from loguru import logger
from utils.llm_client import chat


# ── Fast rule-based error classifier ─────────────────────────────────────────
_ERROR_PATTERNS: dict[str, re.Pattern] = {
    "group_by_violation": re.compile(
        r"1055|ONLY_FULL_GROUP_BY|isn.t in GROUP BY|not in GROUP BY", re.IGNORECASE
    ),
    "unknown_column": re.compile(
        r"1054|Unknown column|'[\w\s.`]+' in '(field list|where clause|order clause)'",
        re.IGNORECASE,
    ),
    "syntax_error": re.compile(
        r"1064|SQL syntax|You have an error in your SQL syntax", re.IGNORECASE
    ),
    "table_not_found": re.compile(
        r"1146|Table .* doesn.t exist", re.IGNORECASE
    ),
    "query_timeout": re.compile(
        r"timeout|MAX_EXECUTION_TIME|2013|Lost connection|2006", re.IGNORECASE
    ),
    "empty_result": re.compile(
        r"returned 0 rows|zero rows|no rows", re.IGNORECASE
    ),
    "validation_no_select": re.compile(
        r"Query must begin with SELECT", re.IGNORECASE
    ),
    "forbidden_keyword": re.compile(
        r"Forbidden keyword", re.IGNORECASE
    ),
}

_FIX_INSTRUCTIONS: dict[str, str] = {
    "group_by_violation": (
        "MySQL 8.0 ONLY_FULL_GROUP_BY violation: every column in SELECT must either "
        "be inside an aggregate (SUM, COUNT, AVG, etc.) or appear literally in GROUP BY. "
        "Fix: use integer columns dt.year and dt.month in GROUP BY — never YEAR(column) or "
        "MONTH(column) unless that same expression is also in SELECT."
    ),
    "unknown_column": (
        "A column name in the SQL does not exist in the schema. "
        "Correct column names: fact_sales uses 'payment_value' (not revenue), "
        "'delivery_time_days' (not delivery_days), 'date_key' (not time_key or date_id). "
        "dim_time uses 'year', 'month', 'quarter', 'day_of_week'. "
        "Regenerate using only schema-verified column names."
    ),
    "syntax_error": (
        "The SQL has a syntax error. Check for: missing commas between SELECT columns, "
        "unmatched parentheses, missing ON clause after JOIN, invalid MySQL 8.0 syntax. "
        "Regenerate the complete query from scratch."
    ),
    "table_not_found": (
        "An invalid table name was used. The only valid tables are: "
        "fact_sales, dim_customers, dim_products, dim_sellers, dim_time. "
        "Fix the table name and regenerate."
    ),
    "query_timeout": (
        "The query exceeded the execution time limit. "
        "Fix: add WHERE order_status = 'delivered' to reduce rows, add LIMIT if appropriate, "
        "ensure all JOINs use the indexed FK columns (customer_id, product_id, seller_id, date_key)."
    ),
    "empty_result": (
        "The query ran successfully but returned 0 rows — filters are likely too restrictive. "
        "Fix: relax year/status filters. Use WHERE order_status = 'delivered' instead of "
        "specific years if the dataset is sparse. Try removing date filters entirely."
    ),
    "validation_no_select": (
        "The output contained prose text instead of raw SQL. "
        "Output ONLY the raw MySQL SELECT statement — no explanation, no markdown fences, "
        "no introductory sentences. Start directly with SELECT."
    ),
    "forbidden_keyword": (
        "The query contains a forbidden DDL/DML keyword. "
        "Generate ONLY a SELECT statement — no INSERT, UPDATE, DELETE, DROP, ALTER, or TRUNCATE."
    ),
}


def classify_error(error: str) -> str:
    """Rule-based classifier — returns the error category name."""
    for name, pattern in _ERROR_PATTERNS.items():
        if pattern.search(error):
            return name
    return "unknown"


def reflect(
    user_query: str,
    intent: dict,
    sql: str,
    error: str,
    attempt: int,
) -> dict:
    """
    Observe → Reason → Plan.

    Returns a structured recovery dict:
      error_type          : classified error category
      root_cause          : one-sentence diagnosis
      fix_instruction     : targeted instruction for Agent 2 on next attempt
      should_revise_intent: True if Agent 1 should re-parse the query
      revised_intent      : optional partial intent override (or None)
    """
    error_type = classify_error(error)
    logger.debug(f"[Reflection] Classified: {error_type} | attempt {attempt}")

    # For known error types, rule-based fix is enough — no LLM call needed
    if error_type not in ("unknown",):
        return {
            "error_type":           error_type,
            "root_cause":           f"{error_type.replace('_', ' ').title()}: {error[:140]}",
            "fix_instruction":      _FIX_INSTRUCTIONS[error_type],
            "should_revise_intent": error_type in ("unknown_column", "empty_result"),
            "revised_intent":       None,
        }

    # Unknown error — invoke LLM for targeted diagnosis
    prompt = f"""You are a MySQL SQL debugging expert for a data warehouse.

User question: "{user_query}"
Parsed intent:
{json.dumps(intent, indent=2)}

SQL that failed:
{sql}

Error message:
{error}

Known schema facts:
- Tables: fact_sales, dim_customers, dim_products, dim_sellers, dim_time
- GROUP BY rule: use dt.year and dt.month (INT columns), never YEAR(col)/MONTH(col)
- fact_sales columns: fact_id, order_id, customer_id, product_id, seller_id, date_key,
  order_status, payment_type, payment_value, price, freight_value, review_score,
  delivery_time_days, delay_days, is_late, approval_time_hours

Respond with ONLY valid JSON matching this schema:
{{
  "error_type": "brief label",
  "root_cause": "one sentence pinpointing exactly what went wrong",
  "fix_instruction": "2-3 precise sentences telling the SQL generator exactly how to fix it",
  "should_revise_intent": false,
  "revised_intent": null
}}"""

    try:
        content = chat(
            messages=[{"role": "user", "content": prompt}],
            json_mode=True,
            temperature=0,
        )
        plan = json.loads(content)
        logger.debug(f"[Reflection] LLM plan: {plan}")
        return plan
    except Exception as exc:
        logger.warning(f"[Reflection] LLM fallback failed: {exc}")
        return {
            "error_type":           "unknown",
            "root_cause":           error[:200],
            "fix_instruction":      (
                f"The previous attempt failed with: {error[:200]}. "
                "Rewrite the SQL query from scratch using only verified schema columns."
            ),
            "should_revise_intent": False,
            "revised_intent":       None,
        }
