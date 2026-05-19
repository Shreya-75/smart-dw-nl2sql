"""
Admin page — database status, live log viewer, agent diagnostics, schema explorer.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import streamlit as st
import pandas as pd

from utils.db_connection import get_engine, test_connection
from utils.llm_client import get_active_provider
import config

LOG_FILE = Path("logs") / "query_log.jsonl"

st.set_page_config(page_title="Admin | Smart DW", page_icon="⚙️", layout="wide")

st.markdown("""
<style>
  .stApp { background-color: #0f1117; }
  .status-ok  { color:#00e676; font-weight:700; }
  .status-err { color:#ef5350; font-weight:700; }
  .log-line   { font-family:monospace; font-size:12px; color:#b0bec5;
                border-bottom:1px solid #1e2336; padding:4px 0; }
</style>
""", unsafe_allow_html=True)

st.title("⚙️ Admin & Diagnostics")

# ── Section 1: System Status ──────────────────────────────────────────────────
st.markdown("### System Status")

col_db, col_llm, col_log = st.columns(3)

with col_db:
    db_ok = test_connection()
    status_cls = "status-ok" if db_ok else "status-err"
    status_txt = "Connected ✅" if db_ok else "Disconnected ❌"
    st.markdown(f"""
    **Database**
    <span class="{status_cls}">{status_txt}</span>
    """, unsafe_allow_html=True)
    st.caption(f"`{config.DB_USER}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}`")

with col_llm:
    provider, model = get_active_provider()
    st.markdown(f"""
    **LLM Provider**
    <span class="status-ok">{provider.upper()} / {model}</span>
    """, unsafe_allow_html=True)
    ollama_url = config.OLLAMA_BASE_URL if provider == "ollama" else "N/A"
    st.caption(f"Ollama URL: `{ollama_url}`")

with col_log:
    log_exists = LOG_FILE.exists()
    log_lines = 0
    if log_exists:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            log_lines = sum(1 for line in f if line.strip())
    log_status = "status-ok" if log_exists else "status-err"
    log_txt = f"{log_lines} entries" if log_exists else "Not found"
    st.markdown(f"""
    **Query Log**
    <span class="{log_status}">{log_txt}</span>
    """, unsafe_allow_html=True)
    st.caption(f"`{LOG_FILE}`")

st.markdown("---")

# ── Section 2: Database Schema Explorer ───────────────────────────────────────
st.markdown("### Database Schema Explorer")

if db_ok:
    engine = get_engine()

    @st.cache_data(ttl=120)
    def _get_tables() -> list[str]:
        with engine.connect() as conn:
            df = pd.read_sql("SHOW TABLES", conn)
            return df.iloc[:, 0].tolist()

    @st.cache_data(ttl=120)
    def _get_table_info(table: str) -> pd.DataFrame:
        with engine.connect() as conn:
            return pd.read_sql(f"DESCRIBE `{table}`", conn)

    @st.cache_data(ttl=120)
    def _get_row_count(table: str) -> int:
        with engine.connect() as conn:
            result = conn.execute(
                __import__("sqlalchemy").text(f"SELECT COUNT(*) FROM `{table}`")
            )
            return result.scalar()

    tables = _get_tables()
    if tables:
        selected_table = st.selectbox("Select table", tables)
        col_desc, col_cnt = st.columns([3, 1])
        with col_desc:
            st.dataframe(_get_table_info(selected_table), use_container_width=True)
        with col_cnt:
            cnt = _get_row_count(selected_table)
            st.metric("Row Count", f"{cnt:,}")

            if st.button("Preview 5 rows"):
                with engine.connect() as conn:
                    df_preview = pd.read_sql(
                        f"SELECT * FROM `{selected_table}` LIMIT 5", conn
                    )
                st.dataframe(df_preview, use_container_width=True)
    else:
        st.info("No tables found. Run the ETL to populate the warehouse.")
else:
    st.warning("Database not connected — schema explorer unavailable.")

st.markdown("---")

# ── Section 3: Agent Configuration ───────────────────────────────────────────
st.markdown("### Agent Configuration")

agent_info = [
    ("Agent 1 — Query Understanding", "query_agent.py",
     "Extracts intent, entities, and metric type from the user question.",
     "Sends NL → JSON intent dict"),
    ("Agent 2 — NL2SQL Generation", "sql_agent.py",
     "Generates a MySQL SELECT query from the intent JSON and schema context.",
     "Outputs raw SQL string"),
    ("Agent 3 — SQL Validation", "validation_agent.py",
     "Checks for SELECT-only, valid table names, no injection patterns.",
     "Returns ValidationResult(is_valid, errors)"),
    ("Agent 4 — SQL Execution", "execution_agent.py",
     "Runs the validated SQL against MySQL, returns pandas DataFrame.",
     "Raises QueryExecutionError on failure → triggers retry"),
    ("Agent 5 — Insight Generation", "insight_agent.py",
     "Summarises the result set and produces business recommendations.",
     "Returns insights dict: summary, trend, key_finding, recommendation"),
]

for name, fname, desc, io in agent_info:
    with st.expander(name):
        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.markdown(f"**Description:** {desc}")
            st.markdown(f"**I/O:** {io}")
        with col_b:
            st.code(f"agents/{fname}", language="text")

st.markdown(f"**Max retry attempts:** `{config.MAX_RETRY_ATTEMPTS}`")
st.markdown(f"**Query timeout:** `{config.QUERY_TIMEOUT_SECONDS}s`")

st.markdown("---")

# ── Section 4: Live Log Viewer ────────────────────────────────────────────────
st.markdown("### Live Query Log")

n_show = st.slider("Show last N entries", min_value=5, max_value=100, value=20)

if LOG_FILE.exists():
    records = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    records = list(reversed(records))[:n_show]

    if records:
        df_log = pd.DataFrame([{
            "timestamp": r.get("timestamp", "")[:19].replace("T", " "),
            "query": r.get("user_query", "")[:60],
            "success": "✅" if r.get("success") else "❌",
            "rows": r.get("row_count", 0),
            "duration_ms": r.get("duration_ms", 0),
            "retries": r.get("retry_count", 0),
            "error": (r.get("error") or "")[:60],
        } for r in records])
        st.dataframe(df_log, use_container_width=True, hide_index=True)

        if st.button("🗑️ Clear log file"):
            st.warning("This will permanently delete all log entries. Confirm by clicking again.")
            if st.button("⚠️ Yes, clear the log", type="primary"):
                open(LOG_FILE, "w").close()
                st.success("Log cleared.")
                st.rerun()
    else:
        st.info("Log file is empty.")
else:
    st.info("No log file found yet. Run a query to create it.")

st.markdown("---")

# ── Section 5: Config overview ────────────────────────────────────────────────
st.markdown("### Configuration (sanitized)")
st.json({
    "LLM_PROVIDER": config.LLM_PROVIDER,
    "OLLAMA_MODEL": config.OLLAMA_MODEL,
    "GROQ_MODEL": config.GROQ_MODEL,
    "GROQ_API_KEY": "***" if config.GROQ_API_KEY else "(not set)",
    "DB_HOST": config.DB_HOST,
    "DB_PORT": config.DB_PORT,
    "DB_NAME": config.DB_NAME,
    "DB_USER": config.DB_USER,
    "DB_PASSWORD": "***" if config.DB_PASSWORD else "(not set)",
    "MAX_RETRY_ATTEMPTS": config.MAX_RETRY_ATTEMPTS,
    "QUERY_TIMEOUT_SECONDS": config.QUERY_TIMEOUT_SECONDS,
    "LOG_LEVEL": config.LOG_LEVEL,
})
