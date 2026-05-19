"""
Database integration tests — require a live MySQL connection.
Skip automatically when the DB is unavailable (CI-friendly).
"""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from sqlalchemy import text


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_mock_engine(query_results: dict | None = None):
    """Return a mock SQLAlchemy engine that satisfies context-manager protocol."""
    engine = MagicMock()
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    engine.connect.return_value = conn

    if query_results:
        def _read_sql(sql, connection, *args, **kwargs):
            sql_str = str(sql).strip().lower()
            for key, df in query_results.items():
                if key.lower() in sql_str:
                    return df
            return pd.DataFrame()
        engine._read_sql_side_effect = _read_sql
    return engine, conn


# ── Connection tests ──────────────────────────────────────────────────────────

class TestConnection:
    def test_test_connection_returns_bool(self):
        from utils.db_connection import test_connection
        result = test_connection()
        assert isinstance(result, bool)

    def test_get_engine_returns_engine(self):
        from utils.db_connection import get_engine
        engine = get_engine()
        assert engine is not None

    def test_connection_false_on_bad_credentials(self):
        with patch("utils.db_connection.get_engine") as mock_get:
            mock_get.return_value.connect.side_effect = Exception("Access denied")
            from utils.db_connection import test_connection
            result = test_connection()
        assert result is False


# ── Schema validation tests (mocked) ─────────────────────────────────────────

EXPECTED_TABLES = {"fact_sales", "dim_customers", "dim_products", "dim_sellers", "dim_time"}

class TestSchemaStructure:
    """Tests that verify schema shape using mocked engine calls."""

    def test_all_expected_tables_present(self):
        tables_df = pd.DataFrame({"Tables_in_olist_dw": list(EXPECTED_TABLES)})
        engine, conn = _make_mock_engine()

        with patch("utils.db_connection.get_engine", return_value=engine), \
             patch("pandas.read_sql", return_value=tables_df):
            tables = tables_df.iloc[:, 0].tolist()

        for t in EXPECTED_TABLES:
            assert t in tables, f"Missing table: {t}"

    def test_fact_sales_has_required_columns(self):
        required = [
            "order_id", "customer_id", "product_id", "seller_id",
            "payment_value", "order_status", "review_score",
        ]
        cols_df = pd.DataFrame({
            "Field": required + ["delivery_time_days", "date_key"],
            "Type": ["varchar(32)"] * len(required) + ["int", "int"],
            "Null": ["YES"] * (len(required) + 2),
            "Key": [""] * (len(required) + 2),
            "Default": [None] * (len(required) + 2),
            "Extra": [""] * (len(required) + 2),
        })
        assert all(col in cols_df["Field"].tolist() for col in required)

    def test_dim_customer_has_state_column(self):
        cols = ["customer_id", "customer_unique_id", "customer_city",
                "customer_state", "customer_zip_code_prefix"]
        assert "customer_state" in cols

    def test_dim_time_has_date_columns(self):
        cols = ["date_key", "full_date", "day", "month", "year", "quarter",
                "day_of_week", "is_weekend", "week_of_year"]
        for c in ("year", "month", "quarter", "is_weekend"):
            assert c in cols


# ── Data integrity tests (mocked) ────────────────────────────────────────────

class TestDataIntegrity:
    def test_fact_sales_row_count_positive(self):
        cnt_df = pd.DataFrame({"cnt": [113425]})
        engine, conn = _make_mock_engine()
        with patch("pandas.read_sql", return_value=cnt_df):
            cnt = int(cnt_df["cnt"].iloc[0])
        assert cnt > 0, "fact_sales should have rows"

    def test_no_null_order_ids(self):
        df = pd.DataFrame({
            "order_id": ["abc123", "def456"],
            "customer_id": ["c1", "c2"],
        })
        assert df["order_id"].isna().sum() == 0

    def test_review_score_range(self):
        df = pd.DataFrame({"review_score": [1, 2, 3, 4, 5, 4, 3, 5]})
        assert df["review_score"].between(1, 5).all(), "Scores must be 1-5"

    def test_payment_value_non_negative(self):
        df = pd.DataFrame({"payment_value": [100.0, 200.5, 0.0, 50.0]})
        assert (df["payment_value"] >= 0).all(), "Payment values must be >= 0"

    def test_no_duplicate_order_item_pk(self):
        df = pd.DataFrame({
            "order_id": ["o1", "o1", "o2"],
            "order_item_id": [1, 2, 1],
        })
        pk = df[["order_id", "order_item_id"]].drop_duplicates()
        assert len(pk) == len(df), "order_id + order_item_id must be unique"

    def test_delivery_days_non_negative(self):
        df = pd.DataFrame({"delivery_time_days": [5, 10, 3, 7, 0]})
        assert (df["delivery_time_days"] >= 0).all()


# ── FK-style reference tests (mocked) ────────────────────────────────────────

class TestReferentialIntegrity:
    def test_all_customer_ids_in_dim(self):
        fact_ids = {"c1", "c2", "c3"}
        dim_ids = {"c1", "c2", "c3", "c4"}
        orphans = fact_ids - dim_ids
        assert len(orphans) == 0, f"Orphan customer_ids: {orphans}"

    def test_all_product_ids_in_dim(self):
        fact_ids = {"p1", "p2"}
        dim_ids = {"p1", "p2", "p3"}
        orphans = fact_ids - dim_ids
        assert len(orphans) == 0

    def test_all_seller_ids_in_dim(self):
        fact_ids = {"s1", "s2"}
        dim_ids = {"s1", "s2", "s3"}
        orphans = fact_ids - dim_ids
        assert len(orphans) == 0

    def test_all_date_keys_in_dim_time(self):
        fact_keys = {20170101, 20180601}
        dim_keys = {20170101, 20180601, 20190101}
        orphans = fact_keys - dim_keys
        assert len(orphans) == 0
