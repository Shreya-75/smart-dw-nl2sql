"""
Data Integration — merges raw Olist CSVs into a single master DataFrame
used by the data_loading module to populate fact_sales.
"""
import pandas as pd
from loguru import logger


def integrate_orders(
    orders_df: pd.DataFrame,
    order_items_df: pd.DataFrame,
    order_payments_df: pd.DataFrame,
    order_reviews_df: pd.DataFrame,
    customers_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Joins orders, payments, reviews, and customers into one flat frame.
    Returns a deduplicated master DataFrame keyed on order_id.
    """
    logger.info("Integrating order data…")

    # ── Aggregate payments per order ──────────────────────────────────────────
    payments_agg = (
        order_payments_df
        .groupby("order_id", as_index=False)
        .agg(
            payment_type=("payment_type", "first"),
            payment_installments=("payment_installments", "sum"),
            payment_value=("payment_value", "sum"),
        )
    )

    # ── Aggregate reviews per order (latest review wins) ─────────────────────
    reviews_agg = (
        order_reviews_df
        .sort_values("review_creation_date")
        .groupby("order_id", as_index=False)
        .agg(review_score=("review_score", "last"))
    )

    # ── Merge chain ───────────────────────────────────────────────────────────
    master = (
        orders_df
        .merge(customers_df[["customer_id", "customer_unique_id",
                              "customer_city", "customer_state"]], on="customer_id", how="left")
        .merge(payments_agg, on="order_id", how="left")
        .merge(reviews_agg, on="order_id", how="left")
    )

    logger.info(f"Master frame shape after integration: {master.shape}")
    return master


def validate_integration(master_df: pd.DataFrame, items_df: pd.DataFrame) -> None:
    """Logs basic integrity checks on the integrated data."""
    n_orders = master_df["order_id"].nunique()
    n_no_payment = master_df["payment_value"].isna().sum()
    n_no_review = master_df["review_score"].isna().sum()
    item_orders = items_df["order_id"].nunique()

    logger.info(f"Integrated orders: {n_orders:,}")
    logger.info(f"Orders in items table: {item_orders:,}")
    logger.info(f"Orders without payment: {n_no_payment}")
    logger.info(f"Orders without review: {n_no_review}")

    if n_no_payment > n_orders * 0.05:
        logger.warning(f"{n_no_payment} orders missing payment data (>{n_orders * 0.05:.0f} threshold)")
