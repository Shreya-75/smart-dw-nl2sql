import pandas as pd
from loguru import logger


def engineer_features(orders: pd.DataFrame, items: pd.DataFrame,
                       payments: pd.DataFrame, reviews: pd.DataFrame) -> pd.DataFrame:
    df = orders.copy()

    # ── Delivery time (purchase → customer received) ──
    df["delivery_time_days"] = (
        (df["order_delivered_customer_date"] - df["order_purchase_timestamp"])
        .dt.total_seconds() / 86400
    ).round(2)

    # ── Delay (positive = late, negative = early) ──
    df["delay_days"] = (
        (df["order_delivered_customer_date"] - df["order_estimated_delivery_date"])
        .dt.total_seconds() / 86400
    ).round(2)

    # ── Binary late flag ──
    df["is_late"] = (df["delay_days"] > 0).astype(int)

    # ── Payment approval time ──
    df["approval_time_hours"] = (
        (df["order_approved_at"] - df["order_purchase_timestamp"])
        .dt.total_seconds() / 3600
    ).round(2)

    # ── Aggregate order items → order level ──
    order_totals = items.groupby("order_id").agg(
        total_price=("price", "sum"),
        total_freight=("freight_value", "sum"),
        item_count=("order_item_id", "count"),
    ).reset_index()
    order_totals["total_order_value"] = (
        order_totals["total_price"] + order_totals["total_freight"]
    ).round(2)
    df = df.merge(order_totals, on="order_id", how="left")

    # ── Aggregate payments → order level (primary payment type & total) ──
    pay_agg = (
        payments.sort_values("payment_sequential")
        .groupby("order_id")
        .agg(payment_type=("payment_type", "first"),
             payment_installments=("payment_installments", "first"),
             payment_value=("payment_value", "sum"))
        .reset_index()
    )
    df = df.merge(pay_agg, on="order_id", how="left")

    # ── Aggregate reviews → order level (latest score) ──
    rev_agg = (
        reviews.sort_values("review_creation_date", ascending=False)
        .groupby("order_id")
        .agg(review_score=("review_score", "first"))
        .reset_index()
    )
    df = df.merge(rev_agg, on="order_id", how="left")

    logger.info(f"Feature engineering complete: {len(df):,} rows, {len(df.columns)} columns")
    return df
