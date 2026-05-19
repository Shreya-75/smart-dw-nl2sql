"""
Agent 3 — SQL Validation Agent
Checks generated SQL for safety, schema correctness, and syntax.
"""
import re
import sqlparse
from dataclasses import dataclass, field
from loguru import logger

FORBIDDEN_PATTERN = re.compile(
    r"\b(DELETE|DROP|UPDATE|INSERT|TRUNCATE|ALTER|EXEC|EXECUTE|GRANT|REVOKE|CREATE|REPLACE|CALL|LOAD)\b",
    re.IGNORECASE,
)

KNOWN_TABLES = {"fact_sales", "dim_customers", "dim_products", "dim_sellers", "dim_time"}

KNOWN_COLUMNS = {
    "fact_sales": {
        "fact_id","order_id","order_item_id","customer_id","product_id","seller_id",
        "date_key","order_status","payment_type","payment_installments","payment_value",
        "price","freight_value","total_order_value","review_score",
        "delivery_time_days","delay_days","is_late","approval_time_hours",
    },
    "dim_customers": {
        "customer_id","customer_unique_id","customer_city","customer_state","customer_zip_code_prefix",
    },
    "dim_products": {
        "product_id","product_category_name","product_category_name_english",
        "product_name_length","product_description_length",
        "product_weight_g","product_length_cm","product_height_cm","product_width_cm",
    },
    "dim_sellers": {
        "seller_id","seller_city","seller_state","seller_zip_code_prefix",
    },
    "dim_time": {
        "date_key","full_date","day","month","year","quarter",
        "day_of_week","is_weekend","week_of_year",
    },
}


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __str__(self):
        lines = [f"Valid: {self.is_valid}"]
        if self.errors:
            lines += [f"  ERROR: {e}" for e in self.errors]
        if self.warnings:
            lines += [f"  WARN: {w}" for w in self.warnings]
        return "\n".join(lines)


def validate_sql(sql: str) -> ValidationResult:
    errors, warnings = [], []
    sql = sql.strip()

    # ── Safety: forbidden keywords ──
    match = FORBIDDEN_PATTERN.search(sql)
    if match:
        errors.append(f"Forbidden keyword: '{match.group()}' — only SELECT is allowed")
        return ValidationResult(is_valid=False, errors=errors)

    # ── Must start with SELECT ──
    if not sql.upper().lstrip().startswith("SELECT"):
        errors.append("Query must begin with SELECT")

    # ── Sqlparse syntax check ──
    parsed = sqlparse.parse(sql)
    if not parsed:
        errors.append("Failed to parse SQL — may be malformed")

    # ── Known table references ──
    table_refs = re.findall(r'\b(fact_sales|dim_\w+)\b', sql, re.IGNORECASE)
    for t in set(t.lower() for t in table_refs):
        if t not in KNOWN_TABLES:
            errors.append(f"Unknown table referenced: '{t}'")

    # ── Complexity warnings ──
    join_count = len(re.findall(r'\bJOIN\b', sql, re.IGNORECASE))
    if join_count > 5:
        warnings.append(f"High JOIN count ({join_count}) — verify query correctness")

    subquery_count = sql.upper().count("SELECT") - 1
    if subquery_count > 2:
        warnings.append(f"{subquery_count} subqueries detected — may be overcomplicated")

    result = ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    logger.debug(f"Agent 3 validation:\n{result}")
    return result
