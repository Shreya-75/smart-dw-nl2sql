"""
Smart Data Warehouse — NL2SQL Agentic System
Main entry point (landing / home page).
Run: streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import utils.logger
from utils.db_connection import get_engine, test_connection

st.set_page_config(
    page_title="Smart DW | NL2SQL",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .stApp { background-color: #0f1117; }
  .hero { background: linear-gradient(135deg,#0d1b3e,#1a237e);
          padding:48px 40px; border-radius:16px; margin-bottom:28px; }
  .hero h1 { color:white; margin:0; font-size:2.6rem; }
  .hero h3 { color:#90caf9; margin:8px 0 16px; }
  .hero p  { color:#b0bec5; max-width:680px; font-size:1rem; line-height:1.6; }
  .kpi-card { background:#1e2336; border:1px solid #2e3456;
              border-radius:12px; padding:20px; text-align:center; }
  .kpi-val  { font-size:2rem; font-weight:800; color:#1a73e8; }
  .kpi-lbl  { font-size:12px; color:#9098b8; margin-top:4px; }
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🧠 Smart Data Warehouse</h1>
  <h3>Agentic NL2SQL System · Olist Brazilian E-Commerce</h3>
  <p>Ask any business question in plain English — a 5-agent AI pipeline
     translates it to SQL, executes against a star-schema MySQL warehouse,
     and returns interactive charts with business insights automatically.</p>
</div>
""", unsafe_allow_html=True)

# ── DB KPIs ───────────────────────────────────────────────────────────────────
db_ok = test_connection()
if db_ok:
    @st.cache_data(ttl=600)
    def _load_kpis():
        engine = get_engine()
        sql = """
        SELECT COUNT(DISTINCT order_id)       AS orders,
               ROUND(SUM(payment_value),0)    AS revenue,
               COUNT(DISTINCT customer_id)    AS customers,
               COUNT(DISTINCT product_id)     AS products,
               ROUND(AVG(review_score),2)      AS avg_review
        FROM fact_sales WHERE order_status='delivered'
        """
        with engine.connect() as conn:
            return pd.read_sql(sql, conn).iloc[0]

    try:
        k = _load_kpis()
        c1, c2, c3, c4, c5 = st.columns(5)
        for col, val, lbl in [
            (c1, f"R${k['revenue']:,.0f}", "Total Revenue"),
            (c2, f"{k['orders']:,.0f}",    "Delivered Orders"),
            (c3, f"{k['customers']:,.0f}", "Unique Customers"),
            (c4, f"{k['products']:,.0f}",  "Products"),
            (c5, f"{k['avg_review']}/5",   "Avg Review Score"),
        ]:
            col.markdown(f"""<div class="kpi-card">
                <div class="kpi-val">{val}</div>
                <div class="kpi-lbl">{lbl}</div>
            </div>""", unsafe_allow_html=True)
    except Exception:
        st.info("Database connected — run the ETL to populate stats.")
else:
    st.warning("Database not connected. Check your `.env` settings.")

st.markdown("---")

# ── Architecture ──────────────────────────────────────────────────────────────
col_arch, col_stack = st.columns([3, 2])
with col_arch:
    st.markdown("### 5-Agent Pipeline")
    st.code("""
User Question (Natural Language)
        ↓
Agent 1 — Query Understanding   → intent JSON
        ↓
Agent 2 — NL2SQL Generation     → MySQL SELECT
        ↓
Agent 3 — SQL Validation        → safety + schema check
        ↓  ↑ retry on error (max 3 attempts)
Agent 4 — SQL Execution         → Pandas DataFrame
        ↓
Agent 5 — Insight Generation    → summary + recommendation
        ↓
Streamlit UI — charts + table + AI insights
    """, language="text")

with col_stack:
    st.markdown("### Tech Stack")
    st.markdown("""
| Layer | Technology |
|---|---|
| **LLM** | Ollama llama3 / mistral · Groq |
| **Warehouse** | MySQL 8.0 · Star Schema |
| **ETL** | Pandas · SQLAlchemy |
| **Agents** | Python · Tenacity retry |
| **UI** | Streamlit · Plotly |
| **Tests** | pytest · pytest-cov |
    """)
    st.markdown("### Dataset")
    st.info("**Olist Brazilian E-Commerce**  \n99,441 orders · 2016–2018  \n5-table star schema  \n113,425 fact rows")

st.markdown("---")
st.markdown("### Navigate using the sidebar →")
st.markdown("""
| Page | Description |
|---|---|
| **🔍 Query** | Ask a business question in plain English |
| **📊 Dashboard** | Pre-built KPI charts and metrics |
| **📜 History** | Browse past queries, re-run, export CSV |
| **⚙️ Admin** | DB status, live logs, agent diagnostics |
""")
