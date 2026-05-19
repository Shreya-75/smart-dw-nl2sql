import pandas as pd
from pathlib import Path
from loguru import logger

RAW_DIR = Path("data/raw")

FILES = {
    "customers":   "olist_customers_dataset.csv",
    "orders":      "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments":    "olist_order_payments_dataset.csv",
    "reviews":     "olist_order_reviews_dataset.csv",
    "products":    "olist_products_dataset.csv",
    "sellers":     "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "translation": "product_category_name_translation.csv",
}

def load_all() -> dict[str, pd.DataFrame]:
    dfs = {}
    for name, filename in FILES.items():
        path = RAW_DIR / filename
        if not path.exists():
            logger.warning(f"File not found: {path} — skipping")
            continue
        df = pd.read_csv(path, low_memory=False)
        logger.info(f"Loaded '{name}': {df.shape[0]:,} rows × {df.shape[1]} cols")
        dfs[name] = df
    return dfs

def profile(dfs: dict[str, pd.DataFrame]) -> None:
    logger.info("=" * 50)
    logger.info("DATA PROFILE")
    logger.info("=" * 50)
    for name, df in dfs.items():
        null_pct = (df.isnull().sum() / len(df) * 100).round(2)
        nulls_with_data = null_pct[null_pct > 0]
        logger.info(f"\n── {name} ({len(df):,} rows) ──")
        if nulls_with_data.empty:
            logger.info("  No nulls found")
        else:
            for col, pct in nulls_with_data.items():
                logger.info(f"  {col}: {pct:.1f}% null")
        dupes = df.duplicated().sum()
        if dupes:
            logger.warning(f"  Duplicate rows: {dupes:,}")
