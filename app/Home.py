"""
Smart Data Warehouse — NL2SQL Agentic System
Landing page.  Run: streamlit run app/Home.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from sqlalchemy import text
from app.components.styles import inject_css
from utils.db_connection import get_engine, test_connection

st.set_page_config(
    page_title="Smart DW | Home",
    page_icon="assets/favicon.png" if Path("assets/favicon.png").exists() else None,
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
  <div class="hero-eyebrow">Agentic NL2SQL &nbsp;·&nbsp; Olist Brazilian E-Commerce &nbsp;·&nbsp; MySQL Star Schema</div>
  <div class="hero-title">Smart Data<br><span>Warehouse</span></div>
  <p class="hero-desc">
    Ask any business question in plain English. A five-agent AI pipeline translates it
    to SQL, executes it against a star-schema warehouse, and returns interactive charts
    with business insights — automatically.
  </p>
</div>
""", unsafe_allow_html=True)

# ── Live KPIs ─────────────────────────────────────────────────────────────────
db_ok = test_connection()
if db_ok:
    @st.cache_data(ttl=600)
    def _load_kpis() -> pd.Series:
        engine = get_engine()
        sql = text("""
            SELECT COUNT(DISTINCT order_id)    AS orders,
                   ROUND(SUM(payment_value),0) AS revenue,
                   COUNT(DISTINCT customer_id) AS customers,
                   COUNT(DISTINCT product_id)  AS products,
                   ROUND(AVG(review_score),2)  AS avg_review
            FROM fact_sales
            WHERE order_status = 'delivered'
        """)
        with engine.connect() as conn:
            return pd.read_sql(sql, conn).iloc[0]

    try:
        k = _load_kpis()
        c1, c2, c3, c4, c5 = st.columns(5)
        for col, val, lbl in [
            (c1, f"R$ {k['revenue']:,.0f}", "Total Revenue"),
            (c2, f"{k['orders']:,.0f}",     "Delivered Orders"),
            (c3, f"{k['customers']:,.0f}",  "Unique Customers"),
            (c4, f"{k['products']:,.0f}",   "Products"),
            (c5, f"{k['avg_review']}/5",    "Avg Review Score"),
        ]:
            col.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-val">{val}</div>
                <div class="kpi-lbl">{lbl}</div>
            </div>""", unsafe_allow_html=True)
    except Exception:
        st.info("Database connected — run the ETL pipeline to populate warehouse stats.")
else:
    st.markdown("""
    <div class="glass-card" style="border-color:rgba(245,158,11,0.3)">
        <span class="badge badge-warn">Database Offline</span>
        <p style="color:#94a3b8;margin:10px 0 0;font-size:13.5px;">
            Could not connect to MySQL. Verify your <code>.env</code> credentials and ensure the server is running.
        </p>
    </div>""", unsafe_allow_html=True)

st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

# ── Architecture + Stack ──────────────────────────────────────────────────────
col_pipe, col_stack = st.columns([3, 2], gap="large")

with col_pipe:
    st.markdown('<div class="section-title">5-Agent Pipeline</div>', unsafe_allow_html=True)

    steps = [
        ("1", "Query Understanding",  "query_agent.py",
         "Parses the natural-language question into a structured JSON intent containing metric, dimension, filters, and time-grain. Uses a zero-shot prompt with output schema enforcement."),
        ("2", "NL2SQL Generation",    "sql_agent.py",
         "Receives the intent JSON and the full database schema, then generates a syntactically valid MySQL SELECT query. Enforces ONLY_FULL_GROUP_BY rules and star-schema join patterns."),
        ("3", "SQL Validation",       "validation_agent.py",
         "Enforces a strict allowlist: SELECT-only, known table names, no DDL/DML keywords, no comment-based injection. Blocks any query that fails these checks before it reaches the database."),
        ("4", "SQL Execution",        "execution_agent.py",
         "Executes the validated query against MySQL with a configurable timeout. On failure, the error message is fed back to Agent 2 for automatic correction — up to 3 retry attempts."),
        ("5", "Insight Generation",   "insight_agent.py",
         "Receives the result DataFrame, summarises the key finding in plain English, and produces an actionable business recommendation tailored to the data."),
    ]
    for num, name, fname, detail in steps:
        st.markdown(f"""
        <details class="pipeline-detail">
          <summary>
            <div class="step-num">{num}</div>
            <div class="step-content">
              <div class="step-name">{name}
                <span style="font-family:monospace;font-size:11px;color:#475569;margin-left:10px;">agents/{fname}</span>
              </div>
              <div class="step-desc">Click to expand</div>
            </div>
            <span class="step-chevron">&#9660;</span>
          </summary>
          <div style="padding:12px 18px 16px 60px;font-size:13.5px;color:#94a3b8;line-height:1.7;border-top:1px solid rgba(255,255,255,0.05);">
            {detail}
          </div>
        </details>""", unsafe_allow_html=True)

with col_stack:
    st.markdown('<div class="section-title">Technology Stack</div>', unsafe_allow_html=True)
    stack = [
        ("LLM",       "Ollama llama3 / mistral &nbsp;·&nbsp; Groq cloud (free tier)"),
        ("Warehouse", "MySQL 8.0 &nbsp;·&nbsp; Star schema &nbsp;·&nbsp; 5 tables"),
        ("ETL",       "Pandas &nbsp;·&nbsp; SQLAlchemy &nbsp;·&nbsp; tenacity retry"),
        ("Agents",    "Python &nbsp;·&nbsp; JSON structured output"),
        ("UI",        "Streamlit 1.35 &nbsp;·&nbsp; Plotly 5"),
        ("Tests",     "pytest &nbsp;·&nbsp; 54 passing"),
    ]
    for layer, tech in stack:
        st.markdown(f"""
        <div class="glass-card" style="padding:12px 16px;margin-bottom:8px;">
            <span style="font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:#475569;">{layer}</span>
            <div style="font-size:13px;color:#cbd5e1;margin-top:3px;">{tech}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div class="glass-card" style="padding:14px 16px;margin-top:16px;border-color:rgba(59,130,246,0.2);">
        <span style="font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:#475569;">Dataset</span>
        <div style="font-size:13px;color:#cbd5e1;margin-top:3px;line-height:1.6;">
            Olist Brazilian E-Commerce<br>
            <span style="color:#3b82f6;font-weight:600;">99,441</span> orders &nbsp;·&nbsp;
            <span style="color:#06b6d4;font-weight:600;">2016 – 2018</span>
        </div>
    </div>""", unsafe_allow_html=True)

st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

# ── Navigation Cards ──────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Navigate</div>', unsafe_allow_html=True)

nc1, nc2, nc3, nc4 = st.columns(4)
nav = [
    (nc1, "Query",     "Type any business question and get SQL, charts, and AI insights in seconds."),
    (nc2, "Dashboard", "Pre-built KPI charts: revenue trends, top categories, delivery performance."),
    (nc3, "History",   "Browse all past queries with timestamps, SQL, outcomes, and re-run support."),
    (nc4, "Admin",     "Live DB status, schema explorer, agent diagnostics, and log viewer."),
]
icons = ["&#9906;", "&#9642;", "&#9632;", "&#9654;"]  # minimal geometric shapes
for col, title, desc in nav:
    col.markdown(f"""
    <div class="nav-card">
        <div class="nav-card-title">{title}</div>
        <div class="nav-card-desc">{desc}</div>
    </div>""", unsafe_allow_html=True)
