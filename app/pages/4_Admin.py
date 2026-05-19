"""
Admin — database diagnostics, schema explorer, agent config, and live log viewer.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import streamlit as st
import pandas as pd
from sqlalchemy import text

from utils.db_connection import get_engine, test_connection
from utils.llm_client import get_active_provider
from app.components.styles import inject_css
import config

st.set_page_config(page_title="Admin | Smart DW", layout="wide", initial_sidebar_state="collapsed")
inject_css()

LOG_FILE = Path("logs") / "query_log.jsonl"

st.markdown("""
<div style="animation:fadeInUp .4s ease;margin-bottom:28px;">
    <div style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
                color:#475569;margin-bottom:6px;">Administration</div>
    <h1 style="font-size:2rem;font-weight:800;color:#f1f5f9;margin:0 0 6px;letter-spacing:-.02em;">
        System Diagnostics
    </h1>
    <p style="font-size:14px;color:#64748b;margin:0;">
        Database health, schema explorer, agent configuration, and query log.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Status strip ──────────────────────────────────────────────────────────────
db_ok = test_connection()
active_p, active_m = get_active_provider()
log_lines = 0
if LOG_FILE.exists():
    with open(LOG_FILE, encoding="utf-8") as f:
        log_lines = sum(1 for ln in f if ln.strip())

sc1, sc2, sc3 = st.columns(3)
sc1.markdown(f"""
<div class="kpi-card" style="text-align:left;padding:18px 20px;">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        <span class="pulse-dot {'dot-green' if db_ok else 'dot-red'}"></span>
        <span class="badge {'badge-success' if db_ok else 'badge-error'}">{'Connected' if db_ok else 'Offline'}</span>
    </div>
    <div style="font-size:15px;font-weight:700;color:#e2e8f0;">MySQL Database</div>
    <div style="font-size:11.5px;color:#475569;margin-top:4px;">
        {config.DB_USER}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}
    </div>
</div>""", unsafe_allow_html=True)

sc2.markdown(f"""
<div class="kpi-card" style="text-align:left;padding:18px 20px;">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        <span class="pulse-dot dot-green"></span>
        <span class="badge badge-info">Active</span>
    </div>
    <div style="font-size:15px;font-weight:700;color:#e2e8f0;">LLM Provider</div>
    <div style="font-size:11.5px;color:#475569;margin-top:4px;">{active_p} / {active_m}</div>
</div>""", unsafe_allow_html=True)

sc3.markdown(f"""
<div class="kpi-card" style="text-align:left;padding:18px 20px;">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        <span class="pulse-dot {'dot-green' if log_lines > 0 else 'dot-amber'}"></span>
        <span class="badge badge-info">Log</span>
    </div>
    <div style="font-size:15px;font-weight:700;color:#e2e8f0;">Query Log</div>
    <div style="font-size:11.5px;color:#475569;margin-top:4px;">
        {f"{log_lines:,} entries" if LOG_FILE.exists() else "File not found"}
    </div>
</div>""", unsafe_allow_html=True)

st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

# ── Schema explorer ───────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Schema Explorer</div>', unsafe_allow_html=True)

if db_ok:
    engine = get_engine()

    @st.cache_data(ttl=120)
    def _tables() -> list[str]:
        with engine.connect() as conn:
            return pd.read_sql(text("SHOW TABLES"), conn).iloc[:, 0].tolist()

    @st.cache_data(ttl=120)
    def _describe(tbl: str) -> pd.DataFrame:
        with engine.connect() as conn:
            return pd.read_sql(text(f"DESCRIBE `{tbl}`"), conn)

    @st.cache_data(ttl=120)
    def _count(tbl: str) -> int:
        with engine.connect() as conn:
            return conn.execute(text(f"SELECT COUNT(*) FROM `{tbl}`")).scalar()

    tables = _tables()
    if tables:
        col_sel, col_cnt = st.columns([3, 1])
        with col_sel:
            sel = st.selectbox("Table", tables, label_visibility="collapsed")
        with col_cnt:
            cnt = _count(sel)
            st.markdown(f"""
            <div class="glass-card" style="padding:10px 16px;">
                <div style="font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#475569;">Rows</div>
                <div style="font-size:1.5rem;font-weight:800;color:#60a5fa;">{cnt:,}</div>
            </div>""", unsafe_allow_html=True)

        st.dataframe(_describe(sel), use_container_width=True, hide_index=True)

        with st.expander("Preview first 5 rows"):
            with engine.connect() as conn:
                preview = pd.read_sql(text(f"SELECT * FROM `{sel}` LIMIT 5"), conn)
            st.dataframe(preview, use_container_width=True, hide_index=True)
    else:
        st.info("No tables found. Run the ETL pipeline to populate the warehouse.")
else:
    st.markdown("""
    <div class="glass-card" style="border-color:rgba(239,68,68,.25);">
        <span class="badge badge-error">Database Offline</span>
        <p style="color:#94a3b8;margin:10px 0 0;font-size:13px;">Schema explorer requires a live database connection.</p>
    </div>""", unsafe_allow_html=True)

st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

# ── Agent config ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Agent Pipeline</div>', unsafe_allow_html=True)

agents = [
    ("1", "Query Understanding",  "query_agent.py",
     "Parses plain English into a structured JSON intent: metric, dimension, filters, time-grain."),
    ("2", "NL2SQL Generation",     "sql_agent.py",
     "Converts intent JSON to a valid MySQL SELECT using schema context and the active LLM."),
    ("3", "SQL Validation",        "validation_agent.py",
     "Enforces SELECT-only, verifies table names against the known schema, blocks injection patterns."),
    ("4", "SQL Execution",         "execution_agent.py",
     "Runs the SQL on MySQL with tenacity retry (up to 3×). Returns a pandas DataFrame on success."),
    ("5", "Insight Generation",    "insight_agent.py",
     "Summarises the result set, identifies a key finding, and produces a business recommendation."),
]
for num, name, fname, desc in agents:
    st.markdown(f"""
    <div class="pipeline-step">
        <div class="step-num">{num}</div>
        <div class="step-content">
            <div class="step-name">{name}
                <span style="font-family:monospace;font-size:11px;color:#475569;margin-left:10px;">agents/{fname}</span>
            </div>
            <div class="step-desc">{desc}</div>
        </div>
    </div>""", unsafe_allow_html=True)

st.markdown(f"""
<div class="glass-card" style="padding:14px 20px;margin-top:14px;display:flex;gap:36px;flex-wrap:wrap;">
    <div>
        <div style="font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#475569;">Max Retries</div>
        <div style="font-size:1.4rem;font-weight:800;color:#60a5fa;">{config.MAX_RETRY_ATTEMPTS}</div>
    </div>
    <div>
        <div style="font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#475569;">Query Timeout</div>
        <div style="font-size:1.4rem;font-weight:800;color:#60a5fa;">{config.QUERY_TIMEOUT_SECONDS}s</div>
    </div>
    <div>
        <div style="font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#475569;">Log Level</div>
        <div style="font-size:1.4rem;font-weight:800;color:#60a5fa;">{config.LOG_LEVEL}</div>
    </div>
</div>""", unsafe_allow_html=True)

st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

# ── Live log ──────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Live Query Log</div>', unsafe_allow_html=True)

n_show = st.slider("Last N entries", 5, 100, 25, label_visibility="collapsed")

if LOG_FILE.exists() and log_lines > 0:
    raw = []
    with open(LOG_FILE, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    raw.append(json.loads(ln))
                except json.JSONDecodeError:
                    pass
    shown = list(reversed(raw))[:n_show]
    df_log = pd.DataFrame([{
        "timestamp":   r.get("timestamp", "")[:19].replace("T", " "),
        "query":       (r.get("user_query") or "")[:55],
        "status":      "OK" if r.get("success") else "FAIL",
        "rows":        r.get("row_count", 0),
        "ms":          r.get("duration_ms", 0),
        "retries":     r.get("retry_count", 0),
        "error":       (r.get("error") or "")[:50],
    } for r in shown])
    st.dataframe(df_log, use_container_width=True, hide_index=True,
                 column_config={
                     "status":  st.column_config.TextColumn("Status", width="small"),
                     "rows":    st.column_config.NumberColumn("Rows",    width="small"),
                     "ms":      st.column_config.NumberColumn("ms",      width="small"),
                     "retries": st.column_config.NumberColumn("Retries", width="small"),
                 })
else:
    st.markdown("""
    <div class="empty-state" style="padding:32px;">
        <div class="empty-title">No log entries</div>
        <div class="empty-desc">Run a query on the Query page to start logging pipeline executions.</div>
    </div>""", unsafe_allow_html=True)

st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

# ── Config dump ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Runtime Configuration (sanitised)</div>', unsafe_allow_html=True)
st.json({
    "LLM_PROVIDER":          config.LLM_PROVIDER,
    "OLLAMA_MODEL":          config.OLLAMA_MODEL,
    "GROQ_MODEL":            config.GROQ_MODEL,
    "GROQ_API_KEY":          "***" if config.GROQ_API_KEY else "(not set)",
    "DB_HOST":               config.DB_HOST,
    "DB_PORT":               config.DB_PORT,
    "DB_NAME":               config.DB_NAME,
    "DB_USER":               config.DB_USER,
    "DB_PASSWORD":           "***" if config.DB_PASSWORD else "(not set)",
    "MAX_RETRY_ATTEMPTS":    config.MAX_RETRY_ATTEMPTS,
    "QUERY_TIMEOUT_SECONDS": config.QUERY_TIMEOUT_SECONDS,
    "LOG_LEVEL":             config.LOG_LEVEL,
})
