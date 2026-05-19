"""
ETL Entry Point — run this to populate the MySQL data warehouse.
Usage: python run_etl.py
"""
import time
from loguru import logger

import utils.logger  # configure loguru
from etl.data_ingestion import load_all, profile
from etl.data_cleaning import clean_all
from etl.feature_engineering import engineer_features
from etl.data_loading import (
    load_dim_time, load_dim_customers, load_dim_products,
    load_dim_sellers, load_fact_sales, apply_indexes
)
from utils.db_connection import get_engine, test_connection


def main():
    start = time.time()
    logger.info("=" * 60)
    logger.info("OLIST SMART DW — ETL PIPELINE STARTING")
    logger.info("=" * 60)

    # ── 1. Test DB connection ──
    if not test_connection():
        logger.error("Cannot connect to MySQL. Check .env settings. Aborting.")
        return

    # ── 2. Ingest ──
    logger.info("\n[STEP 1] Data Ingestion")
    dfs = load_all()
    profile(dfs)

    # ── 3. Clean ──
    logger.info("\n[STEP 2] Data Cleaning")
    dfs = clean_all(dfs)

    # ── 4. Feature Engineering ──
    logger.info("\n[STEP 3] Feature Engineering")
    master_df = engineer_features(
        dfs["orders"], dfs["order_items"],
        dfs["payments"], dfs["reviews"]
    )

    # ── 5. Load ──
    logger.info("\n[STEP 4] Loading to MySQL (star schema)")
    engine = get_engine()

    load_dim_time(engine, dfs["orders"])
    load_dim_customers(engine, dfs["customers"])
    load_dim_products(engine, dfs["products"])
    load_dim_sellers(engine, dfs["sellers"])
    load_fact_sales(engine, master_df, dfs["order_items"])
    apply_indexes(engine)

    elapsed = round(time.time() - start, 1)
    logger.info("=" * 60)
    logger.info(f"ETL COMPLETE in {elapsed}s")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
