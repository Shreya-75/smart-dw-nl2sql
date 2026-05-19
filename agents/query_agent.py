"""
Agent 1 — Query Understanding Agent
Converts natural language → structured JSON intent.
"""
import json
import sys
sys.path.insert(0, ".")
from loguru import logger
from utils.llm_client import chat

SYSTEM_PROMPT = """You are a query understanding agent for a data warehouse about Brazilian e-commerce (Olist dataset, 2016–2018).

Extract structured intent from the user's natural language question and return ONLY valid JSON.

JSON fields:
- intent: one of [aggregation, trend, comparison, lookup, ranking]
- metric: the measure (revenue, orders, review_score, delivery_time_days, delay_days, freight_value, item_count)
- dimension: grouping field (customer_city, customer_state, product_category_name_english, seller_id, payment_type, order_status)
- filters: dict of conditions (year, month, quarter, order_status, payment_type, is_late, customer_state)
- limit: integer or null
- sort_order: "ASC" or "DESC" or null
- time_grain: one of [daily, monthly, quarterly, annual, null]

Available tables: fact_sales, dim_customers, dim_products, dim_sellers, dim_time
"""


def understand_query(user_query: str) -> dict:
    logger.debug(f"Agent 1 input: {user_query}")

    content = chat(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ],
        json_mode=True,
        temperature=0,
    )

    intent = json.loads(content)
    logger.debug(f"Agent 1 output: {intent}")
    return intent
