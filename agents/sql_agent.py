"""
Agent 2 — NL2SQL Generation Agent
Generates a MySQL SELECT query from structured intent + schema context.
"""
import json
import re
import sys
sys.path.insert(0, ".")
from loguru import logger
from utils.llm_client import chat

SCHEMA_CONTEXT = """
DATABASE SCHEMA (MySQL 8.0, database: olist_dw):

fact_sales(
  fact_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  order_id VARCHAR(36),
  order_item_id INT,
  customer_id VARCHAR(36),   -- FK → dim_customers
  product_id VARCHAR(36),    -- FK → dim_products
  seller_id VARCHAR(36),     -- FK → dim_sellers
  date_key INT,              -- FK → dim_time (YYYYMMDD)
  order_status VARCHAR(20),
  payment_type VARCHAR(20),
  payment_installments INT,
  payment_value DECIMAL(10,2),
  price DECIMAL(10,2),
  freight_value DECIMAL(10,2),
  total_order_value DECIMAL(10,2),
  review_score TINYINT,
  delivery_time_days DECIMAL(6,2),
  delay_days DECIMAL(6,2),
  is_late TINYINT(1),
  approval_time_hours DECIMAL(8,2)
)

dim_customers(customer_id PK, customer_unique_id, customer_city, customer_state, customer_zip_code_prefix)
dim_products(product_id PK, product_category_name, product_category_name_english, product_weight_g, product_length_cm, product_height_cm, product_width_cm)
dim_sellers(seller_id PK, seller_city, seller_state, seller_zip_code_prefix)
dim_time(date_key PK, full_date, day, month, year, quarter, day_of_week, is_weekend, week_of_year)

JOIN CONDITIONS:
  fact_sales.customer_id = dim_customers.customer_id
  fact_sales.product_id  = dim_products.product_id
  fact_sales.seller_id   = dim_sellers.seller_id
  fact_sales.date_key    = dim_time.date_key
"""

SQL_SYSTEM = f"""You are an expert MySQL query generator for a star-schema data warehouse.

{SCHEMA_CONTEXT}

RULES:
1. Generate ONLY SELECT statements. Never use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, EXEC, GRANT.
2. Always use explicit JOIN ... ON ... syntax. Never use implicit comma joins.
3. Always alias aggregations: SUM(fs.payment_value) AS revenue
4. Use dim_time columns for time filtering: WHERE dt.year = 2018
5. Use dim_products.product_category_name_english for product categories (English names)
6. Apply LIMIT only when the user asks for "top N" or "bottom N"
7. Return ONLY the raw SQL — no markdown, no explanation, no triple backticks

CRITICAL — MySQL 8.0 ONLY_FULL_GROUP_BY IS ENABLED. THIS IS ENFORCED AND CANNOT BE DISABLED.
- Every column that appears in SELECT must EITHER be inside an aggregate function OR appear literally in GROUP BY.
- WRONG (will always fail): SELECT dt.full_date, SUM(x) ... GROUP BY YEAR(dt.full_date), MONTH(dt.full_date)
  Reason: dt.full_date is not in GROUP BY → MySQL error 1055.
- WRONG (will always fail): SELECT dt.date_key, SUM(x) ... GROUP BY YEAR(dt.date_key), MONTH(dt.date_key)
  Reason: same — dt.date_key is not in GROUP BY.
- CORRECT pattern for monthly time-series using dim_time integer columns:
    SELECT dt.year,
           dt.month,
           CONCAT(dt.year, '-', LPAD(dt.month, 2, '0')) AS month_label,
           ROUND(SUM(fs.payment_value), 0) AS revenue,
           COUNT(DISTINCT fs.order_id)     AS orders
    FROM   fact_sales fs
    JOIN   dim_time dt ON fs.date_key = dt.date_key
    WHERE  fs.order_status = 'delivered'
    GROUP  BY dt.year, dt.month
    ORDER  BY dt.year, dt.month ASC
  (dt.year and dt.month are INT columns in dim_time. GROUP BY on them is valid.
   CONCAT/LPAD expressions built only from grouped columns are also valid in SELECT.)
- For quarterly grouping: GROUP BY dt.year, dt.quarter  — SELECT dt.year, dt.quarter, SUM(...)
- For yearly grouping:    GROUP BY dt.year              — SELECT dt.year, SUM(...)
- NEVER group by YEAR(some_column) or MONTH(some_column) unless that expression is also in SELECT.
- When showing both year and month in SELECT, always put BOTH in GROUP BY: GROUP BY dt.year, dt.month
"""


def generate_sql(intent: dict, user_query: str, error_feedback: str = "") -> str:
    user_msg = f"User question: {user_query}\nParsed intent: {json.dumps(intent, indent=2)}"
    if error_feedback:
        user_msg += f"\n\nPrevious SQL had this error — fix it:\n{error_feedback}"
    user_msg += "\n\nGenerate the MySQL SELECT query:"

    sql = chat(
        messages=[
            {"role": "system", "content": SQL_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        json_mode=False,
        temperature=0,
    )

    sql = sql.strip()
    sql = re.sub(r"```(?:sql)?", "", sql).strip().rstrip("```").strip()
    logger.debug(f"Agent 2 generated SQL:\n{sql}")
    return sql
