import pandas as pd
from sqlalchemy import text
from loguru import logger
import sys
sys.path.insert(0, ".")
from utils.db_connection import get_engine


def load_dim_time(engine, orders_df: pd.DataFrame) -> None:
    min_date = orders_df["order_purchase_timestamp"].min().date()
    max_date = orders_df["order_purchase_timestamp"].max().date()
    dates = pd.date_range(min_date, max_date, freq="D")

    dim_time = pd.DataFrame({
        "date_key":     dates.strftime("%Y%m%d").astype(int),
        "full_date":    dates.date,
        "day":          dates.day,
        "month":        dates.month,
        "year":         dates.year,
        "quarter":      dates.quarter,
        "day_of_week":  dates.day_name(),
        "is_weekend":   (dates.dayofweek >= 5).astype(int),
        "week_of_year": dates.isocalendar().week.values,
    })
    dim_time.to_sql("dim_time", engine, if_exists="replace", index=False, chunksize=500)
    logger.info(f"dim_time loaded: {len(dim_time):,} rows")


def load_dim_customers(engine, customers_df: pd.DataFrame) -> None:
    cols = ["customer_id", "customer_unique_id", "customer_city",
            "customer_state", "customer_zip_code_prefix"]
    df = customers_df[cols].copy()
    df.to_sql("dim_customers", engine, if_exists="replace", index=False, chunksize=5000)
    logger.info(f"dim_customers loaded: {len(df):,} rows")


def load_dim_products(engine, products_df: pd.DataFrame) -> None:
    cols = ["product_id", "product_category_name", "product_category_name_english",
            "product_name_length", "product_description_length",
            "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]
    available = [c for c in cols if c in products_df.columns]
    df = products_df[available].copy()
    df.to_sql("dim_products", engine, if_exists="replace", index=False, chunksize=5000)
    logger.info(f"dim_products loaded: {len(df):,} rows")


def load_dim_sellers(engine, sellers_df: pd.DataFrame) -> None:
    cols = ["seller_id", "seller_city", "seller_state", "seller_zip_code_prefix"]
    df = sellers_df[cols].copy()
    df.to_sql("dim_sellers", engine, if_exists="replace", index=False, chunksize=2000)
    logger.info(f"dim_sellers loaded: {len(df):,} rows")


def load_fact_sales(engine, master_df: pd.DataFrame, items_df: pd.DataFrame) -> None:
    # Explode to item level (one row per order_item)
    fact = master_df.merge(
        items_df[["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"]],
        on="order_id", how="left"
    )

    # Add date_key
    fact["date_key"] = pd.to_datetime(fact["order_purchase_timestamp"]).dt.strftime("%Y%m%d").astype(int)

    # Select and rename to final schema
    final_cols = {
        "order_id": "order_id",
        "order_item_id": "order_item_id",
        "customer_id": "customer_id",
        "product_id": "product_id",
        "seller_id": "seller_id",
        "date_key": "date_key",
        "order_status": "order_status",
        "payment_type": "payment_type",
        "payment_installments": "payment_installments",
        "payment_value": "payment_value",
        "price": "price",
        "freight_value": "freight_value",
        "total_order_value": "total_order_value",
        "review_score": "review_score",
        "delivery_time_days": "delivery_time_days",
        "delay_days": "delay_days",
        "is_late": "is_late",
        "approval_time_hours": "approval_time_hours",
    }
    available = {k: v for k, v in final_cols.items() if k in fact.columns}
    fact_final = fact[list(available.keys())].rename(columns=available)

    fact_final.to_sql("fact_sales", engine, if_exists="replace",
                      index=False, chunksize=5000, method="multi")
    logger.info(f"fact_sales loaded: {len(fact_final):,} rows")


def apply_indexes(engine) -> None:
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_fact_date ON fact_sales(date_key)",
        "CREATE INDEX IF NOT EXISTS idx_fact_customer ON fact_sales(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_fact_product ON fact_sales(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_fact_seller ON fact_sales(seller_id)",
        "CREATE INDEX IF NOT EXISTS idx_fact_status ON fact_sales(order_status)",
        "CREATE INDEX IF NOT EXISTS idx_cust_state ON dim_customers(customer_state)",
        "CREATE INDEX IF NOT EXISTS idx_prod_cat ON dim_products(product_category_name_english(50))",
        "CREATE INDEX IF NOT EXISTS idx_time_year ON dim_time(year, month)",
    ]
    with engine.connect() as conn:
        for sql in indexes:
            try:
                conn.execute(text(sql))
            except Exception as e:
                logger.warning(f"Index warning: {e}")
        conn.commit()
    logger.info("Indexes applied")
