"""
RFM (Recency-Frequency-Monetary) Customer Segmentation.

Pulls customer-level data from the MySQL warehouse and applies:
  R  = days since most recent order (lower = better)
  F  = number of orders placed (higher = better)
  M  = total payment value (higher = better)

KMeans (k=4) clusters customers into named segments:
  Champions    — recent, frequent, high-spend
  Loyal        — moderate recency, decent frequency/spend
  At-Risk      — haven't ordered recently but were previously active
  Lost/Dormant — long dormant, low frequency, low spend

Returns both the per-customer DataFrame and an aggregated segment summary.
"""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
import numpy as np
from loguru import logger


_RFM_SQL = """
SELECT
    fs.customer_id,
    MAX(dt.full_date)                        AS last_order_date,
    COUNT(DISTINCT fs.order_id)              AS frequency,
    SUM(fs.payment_value)                    AS monetary,
    DATEDIFF('2018-12-31', MAX(dt.full_date)) AS recency_days
FROM fact_sales fs
JOIN dim_time dt ON fs.date_key = dt.date_key
WHERE fs.order_status = 'delivered'
GROUP BY fs.customer_id
HAVING frequency >= 1
"""

# Segment labels assigned after sorting clusters by composite RFM score
_SEGMENT_LABELS = {
    0: ("Champions",    "#10b981", "Recent, frequent, high-spend. Your best customers."),
    1: ("Loyal",        "#3b82f6", "Steady buyers. Reward them to elevate to Champions."),
    2: ("At-Risk",      "#f59e0b", "Previously active but lapsing. Time-sensitive win-back."),
    3: ("Lost/Dormant", "#ef4444", "Long inactive. Low-cost re-engagement only."),
}


@dataclass
class RFMResult:
    customers:   pd.DataFrame   # customer_id + R, F, M + rfm_score + segment label
    summary:     pd.DataFrame   # per-segment: count, avg_r, avg_f, avg_m, revenue_share
    total_customers: int
    total_revenue:   float


def compute_rfm() -> RFMResult | None:
    """Run RFM analysis. Returns None if DB unavailable or not enough data."""
    try:
        from sqlalchemy import text
        from utils.db_connection import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            df = pd.read_sql(text(_RFM_SQL), conn)
    except Exception as exc:
        logger.error(f"[RFM] DB query failed: {exc}")
        return None

    if len(df) < 10:
        return None

    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans

    df = df.copy()
    df["recency_days"] = pd.to_numeric(df["recency_days"], errors="coerce").fillna(999)
    df["frequency"]    = pd.to_numeric(df["frequency"],    errors="coerce").fillna(1)
    df["monetary"]     = pd.to_numeric(df["monetary"],     errors="coerce").fillna(0)

    # Note: for recency we invert so higher = better (consistent with F and M)
    features = df[["recency_days", "frequency", "monetary"]].copy()
    features["recency_inv"] = 1 / (features["recency_days"] + 1)

    X = features[["recency_inv", "frequency", "monetary"]].values
    X_scaled = StandardScaler().fit_transform(X)

    km = KMeans(n_clusters=4, random_state=42, n_init=10)
    raw_labels = km.fit_predict(X_scaled)
    df["_cluster"] = raw_labels

    # Rank clusters by composite score so we can assign consistent segment names
    cluster_scores = (
        df.groupby("_cluster")
        .agg(avg_r=("recency_days", "mean"),
             avg_f=("frequency",    "mean"),
             avg_m=("monetary",     "mean"))
        .reset_index()
    )
    # Higher F and M are better; lower R is better
    cluster_scores["score"] = (
        -cluster_scores["avg_r"]        # lower recency = more recent = better
        + cluster_scores["avg_f"] * 10  # weight frequency
        + cluster_scores["avg_m"] / cluster_scores["avg_m"].max() * 50
    )
    cluster_scores = cluster_scores.sort_values("score", ascending=False).reset_index(drop=True)
    rank_map = {row["_cluster"]: i for i, row in cluster_scores.iterrows()}

    df["segment_id"] = df["_cluster"].map(rank_map)
    df["segment"]    = df["segment_id"].map(lambda i: _SEGMENT_LABELS[i][0])
    df["seg_color"]  = df["segment_id"].map(lambda i: _SEGMENT_LABELS[i][1])

    # Composite RFM score (1–100 scale)
    r_score = (df["recency_days"].max() - df["recency_days"]) / (df["recency_days"].max() + 1)
    f_score = (df["frequency"] - df["frequency"].min()) / (df["frequency"].max() + 1)
    m_score = (df["monetary"]  - df["monetary"].min())  / (df["monetary"].max()  + 1)
    df["rfm_score"] = ((r_score + f_score + m_score) / 3 * 100).round(1)

    # Segment summary
    total_rev = float(df["monetary"].sum())
    summary = (
        df.groupby(["segment", "seg_color", "segment_id"])
        .agg(
            customers=("customer_id", "count"),
            avg_recency=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
            total_revenue=("monetary", "sum"),
        )
        .reset_index()
        .sort_values("segment_id")
    )
    summary["revenue_share"] = (summary["total_revenue"] / total_rev * 100).round(1)
    summary["avg_recency"]   = summary["avg_recency"].round(0).astype(int)
    summary["avg_frequency"] = summary["avg_frequency"].round(2)
    summary["avg_monetary"]  = summary["avg_monetary"].round(2)

    return RFMResult(
        customers=df,
        summary=summary,
        total_customers=len(df),
        total_revenue=total_rev,
    )


def get_segment_description(segment_name: str) -> str:
    for _id, (name, _, desc) in _SEGMENT_LABELS.items():
        if name == segment_name:
            return desc
    return ""
