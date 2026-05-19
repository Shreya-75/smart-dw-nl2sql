import pandas as pd
import numpy as np
from loguru import logger

DATETIME_COLS_ORDERS = [
    "order_purchase_timestamp", "order_approved_at",
    "order_delivered_carrier_date", "order_delivered_customer_date",
    "order_estimated_delivery_date",
]
DATETIME_COLS_REVIEWS = ["review_creation_date", "review_answer_timestamp"]


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    orig = len(df)
    df = df.drop_duplicates(subset=["order_id"]).copy()
    for col in DATETIME_COLS_ORDERS:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["order_status"] = df["order_status"].str.strip().str.lower()
    logger.info(f"orders: {orig:,} → {len(df):,} rows after dedup")
    return df


def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["customer_id"]).copy()
    df["customer_city"]  = df["customer_city"].str.strip().str.lower()
    df["customer_state"] = df["customer_state"].str.strip().str.upper()
    return df


def clean_products(df: pd.DataFrame, translation: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["product_id"]).copy()
    df = df.merge(translation, on="product_category_name", how="left")
    df["product_category_name_english"] = df["product_category_name_english"].fillna("unknown")
    df["product_category_name"] = df["product_category_name"].fillna("unknown")
    num_cols = ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(df[col].median())
    if "product_name_lenght" in df.columns:
        df = df.rename(columns={"product_name_lenght": "product_name_length"})
    if "product_description_lenght" in df.columns:
        df = df.rename(columns={"product_description_lenght": "product_description_length"})
    return df


def clean_reviews(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["review_id"]).copy()
    df["review_comment_message"] = df["review_comment_message"].fillna("")
    df["review_comment_title"]   = df["review_comment_title"].fillna("")
    for col in DATETIME_COLS_REVIEWS:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["review_score"] = pd.to_numeric(df["review_score"], errors="coerce")
    return df


def clean_sellers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["seller_id"]).copy()
    df["seller_city"]  = df["seller_city"].str.strip().str.lower()
    df["seller_state"] = df["seller_state"].str.strip().str.upper()
    return df


def clean_order_items(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["order_id", "order_item_id"]).copy()
    df["shipping_limit_date"] = pd.to_datetime(df["shipping_limit_date"], errors="coerce")
    df["price"]         = pd.to_numeric(df["price"], errors="coerce").fillna(0)
    df["freight_value"] = pd.to_numeric(df["freight_value"], errors="coerce").fillna(0)
    return df


def clean_payments(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["order_id", "payment_sequential"]).copy()
    df["payment_value"] = pd.to_numeric(df["payment_value"], errors="coerce").fillna(0)
    df["payment_type"]  = df["payment_type"].str.strip().str.lower()
    return df


def clean_all(dfs: dict) -> dict:
    logger.info("Starting data cleaning...")
    dfs["orders"]      = clean_orders(dfs["orders"])
    dfs["customers"]   = clean_customers(dfs["customers"])
    dfs["products"]    = clean_products(dfs["products"], dfs["translation"])
    dfs["reviews"]     = clean_reviews(dfs["reviews"])
    dfs["sellers"]     = clean_sellers(dfs["sellers"])
    dfs["order_items"] = clean_order_items(dfs["order_items"])
    dfs["payments"]    = clean_payments(dfs["payments"])
    logger.info("Data cleaning complete")
    return dfs
