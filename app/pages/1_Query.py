"""
Query page — user types a natural-language question, selects an LLM provider,
and gets SQL + chart + AI insights back.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
import streamlit as st

from agents.pipeline import run_pipeline
from utils.llm_client import set_provider
from app.components.chart_builder import render_auto_chart
from app.components.insight_display import render_insights

st.set_page_config(page_title="Query | Smart DW", page_icon="🔍", layout="wide")

st.markdown("""
<style>
  .stApp { background-color: #0f1117; }
  .sql-box { background:#1e2336; border:1px solid #2e3456; border-radius:8px;
             padding:14px; font-family:monospace; color:#90caf9; font-size:13px;
             white-space:pre-wrap; word-break:break-all; }
  .metric-chip { display:inline-block; background:#1e2336; border:1px solid #2e3456;
                 border-radius:20px; padding:4px 12px; margin:4px;
                 color:#b0bec5; font-size:12px; }
</style>
""", unsafe_allow_html=True)

st.title("🔍 Natural Language Query")
st.caption("Ask any business question — the AI pipeline converts it to SQL and charts automatically.")

# ── LLM Selector ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### LLM Settings")
    provider = st.selectbox(
        "Provider",
        ["ollama", "groq"],
        index=0,
        help="Ollama = local (private, slower). Groq = cloud (faster, free tier).",
    )
    if provider == "ollama":
        model = st.selectbox("Model", ["llama3", "mistral", "llama3:8b"])
    else:
        model = st.selectbox("Model", ["llama3-70b-8192", "mixtral-8x7b-32768", "llama3-8b-8192"])

    set_provider(provider, model)
    st.markdown(f"**Active:** `{provider}` / `{model}`")
    st.markdown("---")

    st.markdown("### Example Questions")
    examples = [
        "What are the top 5 product categories by revenue?",
        "Show monthly revenue trend for 2018",
        "Which states have the highest number of orders?",
        "What is the average delivery time by seller state?",
        "Show payment method distribution as percentages",
        "Which sellers have the best average review scores?",
        "What is the cancellation rate by product category?",
    ]
    chosen_example = st.selectbox("Load an example", ["— pick one —"] + examples)

# ── Rate limiting via session state ───────────────────────────────────────────
if "query_timestamps" not in st.session_state:
    st.session_state.query_timestamps = []

RATE_LIMIT = 10   # max queries per minute
WINDOW_SEC = 60


def _within_rate_limit() -> bool:
    now = time.time()
    st.session_state.query_timestamps = [
        t for t in st.session_state.query_timestamps if now - t < WINDOW_SEC
    ]
    return len(st.session_state.query_timestamps) < RATE_LIMIT


# ── Input ──────────────────────────────────────────────────────────────────────
default_q = chosen_example if chosen_example != "— pick one —" else ""
user_query = st.text_area(
    "Your question",
    value=default_q,
    max_chars=500,
    height=100,
    placeholder="e.g. What are the top 10 selling products by revenue?",
)

col_run, col_clear = st.columns([1, 5])
with col_run:
    run_btn = st.button("▶ Run", type="primary", use_container_width=True)
with col_clear:
    if st.button("✕ Clear", use_container_width=False):
        st.rerun()

# ── Pipeline execution ────────────────────────────────────────────────────────
if run_btn:
    q = user_query.strip()
    if not q:
        st.warning("Please enter a question.")
    elif len(q) > 500:
        st.error("Question exceeds 500 character limit.")
    elif not _within_rate_limit():
        st.error(f"Rate limit: max {RATE_LIMIT} queries per minute. Please wait.")
    else:
        st.session_state.query_timestamps.append(time.time())

        with st.spinner(f"Running 5-agent pipeline via {provider}/{model}…"):
            result = run_pipeline(q)

        if not result.success:
            st.error(f"Pipeline failed: {result.error_message}")
            if result.sql:
                st.markdown("**Last generated SQL:**")
                st.code(result.sql, language="sql")
        else:
            # ── Metrics row ────────────────────────────────────────────────────
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Duration", f"{result.duration_ms / 1000:.1f}s")
            m2.metric("Rows returned", len(result.data) if result.data is not None else 0)
            m3.metric("Retries", result.retry_count)
            m4.metric("Provider", f"{provider}/{model}")

            st.markdown("---")

            # ── Tabs: Chart | Data | SQL | Intent ──────────────────────────────
            tab_chart, tab_data, tab_sql, tab_intent = st.tabs(
                ["📊 Chart", "📋 Data Table", "🗄️ SQL", "🧠 Intent"]
            )

            with tab_chart:
                if result.data is not None and not result.data.empty:
                    render_auto_chart(result.data, q)
                else:
                    st.info("No rows returned.")

            with tab_data:
                if result.data is not None and not result.data.empty:
                    st.dataframe(result.data, use_container_width=True)
                    csv = result.data.to_csv(index=False)
                    st.download_button("⬇ Download CSV", csv, "results.csv", "text/csv")
                else:
                    st.info("No data.")

            with tab_sql:
                if result.sql:
                    st.code(result.sql, language="sql")
                    st.caption(
                        f"Validation passed: {result.validation.is_valid if result.validation else 'N/A'}"
                    )

            with tab_intent:
                if result.intent:
                    st.json(result.intent)

            # ── Insights ────────────────────────────────────────────────────────
            if result.insights:
                st.markdown("---")
                render_insights(result.insights)
