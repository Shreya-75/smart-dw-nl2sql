"""
Agent 2 — NL2SQL Generation Agent
Generates a MySQL SELECT query from structured intent + schema context.
"""
import json
import re
from openai import OpenAI
from loguru import logger
import config

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

dim_customers(
  customer_id VARCHAR(36) PRIMARY KEY,
  customer_unique_id VARCHAR(36),
  customer_city VARCHAR(100),
  customer_state CHAR(2),
  customer_zip_code_prefix VARCHAR(10)
)

dim_products(
  product_id VARCHAR(36) PRIMARY KEY,
  product_category_name VARCHAR(100),
  product_category_name_english VARCHAR(100),
  product_name_length INT,
  product_description_length INT,
  product_weight_g DECIMAL(8,2),
  product_length_cm DECIMAL(6,2),
  product_height_cm DECIMAL(6,2),
  product_width_cm DECIMAL(6,2)
)

dim_sellers(
  seller_id VARCHAR(36) PRIMARY KEY,
  seller_city VARCHAR(100),
  seller_state CHAR(2),
  seller_zip_code_prefix VARCHAR(10)
)

dim_time(
  date_key INT PRIMARY KEY,
  full_date DATE,
  day TINYINT,
  month TINYINT,
  year SMALLINT,
  quarter TINYINT,
  day_of_week VARCHAR(10),
  is_weekend TINYINT(1),
  week_of_year TINYINT
)

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
3. Always alias aggregations: SUM(fs.payment_value) AS total_revenue
4. Use dim_time columns for time filtering: WHERE dt.year = 2018
5. Use dim_products.product_category_name_english for product categories (English names)
6. Apply LIMIT only when the user asks for "top N" or "bottom N"
7. For trend queries include ORDER BY time dimension ASC
8. Return ONLY the raw SQL — no markdown, no explanation, no triple backticks
"""

client = OpenAI(api_key=config.OPENAI_API_KEY)


def generate_sql(intent: dict, user_query: str, error_feedback: str = "") -> str:
    user_msg = f"User question: {user_query}\nParsed intent: {json.dumps(intent, indent=2)}"
    if error_feedback:
        user_msg += f"\n\nPrevious SQL had this error — fix it:\n{error_feedback}"
    user_msg += "\n\nGenerate the MySQL SELECT query:"

    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SQL_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0,
    )

    sql = response.choices[0].message.content.strip()
    # Strip markdown fences if model ignores rule
    sql = re.sub(r"```(?:sql)?", "", sql).strip().rstrip("```").strip()
    logger.debug(f"Agent 2 generated SQL:\n{sql}")
    return sql
