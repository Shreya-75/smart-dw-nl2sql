"""
Unit tests for all 5 agents with mocked LLM calls.
Agents must not need a live DB or LLM — all external calls are patched.
"""
import json
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────────────────────────────────────
# Agent 1 — Query Understanding
# ─────────────────────────────────────────────────────────────────────────────

class TestQueryAgent:
    MOCK_INTENT = {
        "intent": "ranking",
        "metric": "revenue",
        "dimension": "product_category_name_english",
        "filters": {"order_status": "delivered"},
        "limit": 5,
        "sort_order": "DESC",
        "time_grain": None,
    }

    def test_understand_query_returns_dict(self):
        with patch("agents.query_agent.chat", return_value=json.dumps(self.MOCK_INTENT)):
            from agents.query_agent import understand_query
            result = understand_query("Top 5 product categories by revenue")
        assert isinstance(result, dict)
        assert result["intent"] == "ranking"
        assert result["metric"] == "revenue"

    def test_understand_query_missing_keys_still_returns(self):
        minimal = {"intent": "lookup", "metric": "orders"}
        with patch("agents.query_agent.chat", return_value=json.dumps(minimal)):
            from agents.query_agent import understand_query
            result = understand_query("How many orders?")
        assert "intent" in result

    def test_understand_query_invalid_json_raises(self):
        with patch("agents.query_agent.chat", return_value="not json at all"):
            from agents.query_agent import understand_query
            with pytest.raises(json.JSONDecodeError):
                understand_query("bad response test")


# ─────────────────────────────────────────────────────────────────────────────
# Agent 2 — SQL Generation
# ─────────────────────────────────────────────────────────────────────────────

class TestSQLAgent:
    INTENT = {
        "intent": "ranking",
        "metric": "revenue",
        "dimension": "product_category_name_english",
        "filters": {},
        "limit": 5,
        "sort_order": "DESC",
        "time_grain": None,
    }
    MOCK_SQL = (
        "SELECT dp.product_category_name_english, SUM(fs.payment_value) AS revenue "
        "FROM fact_sales fs JOIN dim_products dp ON fs.product_id = dp.product_id "
        "WHERE fs.order_status='delivered' "
        "GROUP BY dp.product_category_name_english ORDER BY revenue DESC LIMIT 5"
    )

    def test_generate_sql_returns_string(self):
        with patch("agents.sql_agent.chat", return_value=self.MOCK_SQL):
            from agents.sql_agent import generate_sql
            sql = generate_sql(self.INTENT, "Top 5 product categories by revenue", "")
        assert isinstance(sql, str)
        assert sql.upper().startswith("SELECT")

    def test_generate_sql_strips_markdown(self):
        wrapped = f"```sql\n{self.MOCK_SQL}\n```"
        with patch("agents.sql_agent.chat", return_value=wrapped):
            from agents.sql_agent import generate_sql
            sql = generate_sql(self.INTENT, "Top 5 categories", "")
        assert "```" not in sql

    def test_generate_sql_with_error_feedback(self):
        with patch("agents.sql_agent.chat", return_value=self.MOCK_SQL) as mock_chat:
            from agents.sql_agent import generate_sql
            generate_sql(self.INTENT, "Top 5 categories", "previous error: invalid column")
        call_args = mock_chat.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
        full_text = " ".join(m["content"] for m in messages)
        assert "previous error" in full_text.lower() or "error" in full_text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Agent 3 — SQL Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestValidationAgent:
    def test_valid_simple_select(self):
        from agents.validation_agent import validate_sql
        sql = "SELECT * FROM fact_sales WHERE order_status='delivered' LIMIT 10"
        r = validate_sql(sql)
        assert r.is_valid
        assert r.errors == []

    def test_valid_join_query(self):
        from agents.validation_agent import validate_sql
        sql = (
            "SELECT dc.customer_state, SUM(fs.payment_value) AS rev "
            "FROM fact_sales fs JOIN dim_customers dc ON fs.customer_id = dc.customer_id "
            "GROUP BY dc.customer_state ORDER BY rev DESC"
        )
        r = validate_sql(sql)
        assert r.is_valid

    def test_rejects_delete(self):
        from agents.validation_agent import validate_sql
        r = validate_sql("DELETE FROM fact_sales WHERE 1=1")
        assert not r.is_valid
        assert any("DELETE" in e or "Forbidden" in e for e in r.errors)

    def test_rejects_drop(self):
        from agents.validation_agent import validate_sql
        r = validate_sql("DROP TABLE fact_sales")
        assert not r.is_valid

    def test_rejects_insert(self):
        from agents.validation_agent import validate_sql
        r = validate_sql("INSERT INTO fact_sales VALUES (1,2,3)")
        assert not r.is_valid

    def test_rejects_unknown_table(self):
        from agents.validation_agent import validate_sql
        r = validate_sql("SELECT * FROM nonexistent_table")
        assert not r.is_valid
        assert any("nonexistent_table" in e for e in r.errors)

    def test_rejects_non_select(self):
        from agents.validation_agent import validate_sql
        r = validate_sql("SHOW TABLES")
        assert not r.is_valid

    def test_warns_high_join_count(self):
        from agents.validation_agent import validate_sql
        sql = (
            "SELECT * FROM fact_sales fs "
            "JOIN dim_customers dc ON fs.customer_id=dc.customer_id "
            "JOIN dim_products dp ON fs.product_id=dp.product_id "
            "JOIN dim_sellers ds ON fs.seller_id=ds.seller_id "
            "JOIN dim_time dt ON fs.date_key=dt.date_key "
            "JOIN dim_time dt2 ON dt2.date_key=dt.date_key "
            "JOIN dim_customers dc2 ON dc2.customer_id=fs.customer_id"
        )
        r = validate_sql(sql)
        assert any("JOIN" in w for w in r.warnings)


# ─────────────────────────────────────────────────────────────────────────────
# Agent 4 — SQL Execution
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionAgent:
    def _make_conn(self, rows, cols):
        """Build a mock connection whose execute() returns a proper result object."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = rows
        mock_result.keys.return_value = cols

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        # First execute call is SET SESSION (ignored); second is the real SQL.
        mock_conn.execute.side_effect = [None, mock_result]
        return mock_conn

    def test_execute_returns_dataframe(self):
        mock_conn = self._make_conn(
            rows=[("A", 1000.0), ("B", 800.0)],
            cols=["category", "revenue"],
        )
        with patch("agents.execution_agent.get_engine") as mock_eng:
            mock_eng.return_value.connect.return_value = mock_conn
            from agents.execution_agent import execute_query
            result = execute_query("SELECT category, revenue FROM fact_sales")
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["category", "revenue"]
        assert len(result) == 2

    def test_execute_raises_on_db_error(self):
        # Make the second conn.execute() (the real SQL) fail so QueryExecutionError is raised.
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.side_effect = [None, Exception("Unknown column")]

        with patch("agents.execution_agent.get_engine") as mock_eng, \
             patch("time.sleep"):   # suppress tenacity wait delays
            mock_eng.return_value.connect.return_value = mock_conn
            from agents.execution_agent import execute_query, QueryExecutionError
            with pytest.raises((QueryExecutionError, Exception)):
                execute_query("SELECT bad_col FROM fact_sales")


# ─────────────────────────────────────────────────────────────────────────────
# Agent 5 — Insight Generation
# ─────────────────────────────────────────────────────────────────────────────

class TestInsightAgent:
    MOCK_INSIGHTS = {
        "summary": "Top category is health_beauty with R$1.2M revenue.",
        "key_finding": "health_beauty accounts for 15% of total revenue.",
        "trend": "Revenue peaked in Q4 2017.",
        "recommendation": "Increase inventory for health_beauty ahead of Q4.",
    }

    def test_insights_returns_dict(self):
        df = pd.DataFrame({"category": ["health_beauty"], "revenue": [1200000.0]})
        with patch("agents.insight_agent.chat", return_value=json.dumps(self.MOCK_INSIGHTS)):
            from agents.insight_agent import generate_insights
            result = generate_insights("Top categories by revenue", "SELECT ...", df)
        assert isinstance(result, dict)
        assert "summary" in result
        assert "recommendation" in result

    def test_insights_empty_df_returns_no_data_message(self):
        from agents.insight_agent import generate_insights
        result = generate_insights("Some query", "SELECT ...", pd.DataFrame())
        assert "no results" in result["summary"].lower() or "no data" in result["summary"].lower()

    def test_insights_contains_all_keys(self):
        df = pd.DataFrame({"state": ["SP", "RJ"], "orders": [50000, 20000]})
        with patch("agents.insight_agent.chat", return_value=json.dumps(self.MOCK_INSIGHTS)):
            from agents.insight_agent import generate_insights
            result = generate_insights("Orders by state", "SELECT ...", df)
        for key in ("summary", "key_finding", "trend", "recommendation"):
            assert key in result, f"Missing key: {key}"


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline integration (mocked end-to-end)
# ─────────────────────────────────────────────────────────────────────────────

class TestPipeline:
    INTENT = {"intent": "ranking", "metric": "revenue", "dimension": "product_category_name_english",
               "filters": {}, "limit": 5, "sort_order": "DESC", "time_grain": None}
    SQL = "SELECT dp.product_category_name_english, SUM(fs.payment_value) AS revenue FROM fact_sales fs JOIN dim_products dp ON fs.product_id=dp.product_id GROUP BY dp.product_category_name_english ORDER BY revenue DESC LIMIT 5"
    DF = pd.DataFrame({"product_category_name_english": ["health_beauty", "watches_gifts"], "revenue": [1200000.0, 950000.0]})
    INSIGHTS = {"summary": "Top: health_beauty.", "key_finding": "15%.", "trend": "Up.", "recommendation": "Stock up."}

    def test_pipeline_success(self):
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("health_beauty", 1200000.0),
            ("watches_gifts", 950000.0),
        ]
        mock_result.keys.return_value = ["product_category_name_english", "revenue"]

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        # execute() is called twice inside execute_query: SET SESSION + real SQL
        mock_conn.execute.side_effect = [None, mock_result]

        with patch("agents.query_agent.chat", return_value=json.dumps(self.INTENT)), \
             patch("agents.sql_agent.chat", return_value=self.SQL), \
             patch("agents.execution_agent.get_engine") as mock_eng, \
             patch("agents.insight_agent.chat", return_value=json.dumps(self.INSIGHTS)), \
             patch("agents.pipeline._log_event"):
            mock_eng.return_value.connect.return_value = mock_conn

            from agents.pipeline import run_pipeline
            result = run_pipeline("Top 5 product categories by revenue")

        assert result.success
        assert result.data is not None
        assert len(result.data) == 2

    def test_pipeline_validation_failure_retries(self):
        bad_sql = "DROP TABLE fact_sales"
        with patch("agents.query_agent.chat", return_value=json.dumps(self.INTENT)), \
             patch("agents.sql_agent.chat", return_value=bad_sql), \
             patch("agents.pipeline._log_event"):
            from agents.pipeline import run_pipeline
            result = run_pipeline("Drop all data")
        assert not result.success
        assert result.retry_count > 0
