"""
Query — natural language to SQL, chart, and AI insights.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
import streamlit as st

from agents.pipeline import run_pipeline
from utils.llm_client import set_provider, get_active_provider
from app.components.chart_builder import render_auto_chart
from app.components.insight_display import render_insights
from app.components.styles import inject_css

st.set_page_config(page_title="Query | Smart DW", layout="wide", initial_sidebar_state="expanded")
inject_css()

# ── Sidebar: LLM selector ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
                color:#475569;padding:4px 0 12px;">LLM Configuration</div>
    """, unsafe_allow_html=True)

    provider = st.selectbox("Provider", ["ollama", "groq"],
                            help="Ollama runs locally (private, no cost). Groq is a free cloud API (~2s vs ~35s).")
    if provider == "ollama":
        model = st.selectbox("Model", ["llama3", "mistral", "llama3:8b"])
    else:
        model = st.selectbox("Model", ["llama3-70b-8192", "mixtral-8x7b-32768", "llama3-8b-8192"])

    set_provider(provider, model)

    active_p, active_m = get_active_provider()
    st.markdown(f"""
    <div class="glass-card" style="padding:10px 14px;margin-top:4px;">
        <div style="font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#475569;">Active</div>
        <div style="font-size:13px;font-weight:600;color:#60a5fa;margin-top:3px;">{active_p} / {active_m}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="fancy-divider" style="margin:16px 0;"></div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
                color:#475569;padding:4px 0 10px;">Sample Questions</div>
    """, unsafe_allow_html=True)

    examples = [
        "What are the top 5 product categories by revenue?",
        "Show monthly revenue trend for 2018",
        "Which states have the highest number of orders?",
        "What is the average delivery time by seller state?",
        "Show payment method distribution",
        "Which sellers have the best average review scores?",
        "What is the late delivery rate by product category?",
        "Compare revenue across different payment types",
    ]
    chosen = st.selectbox("Load a sample", ["— select —"] + examples, label_visibility="collapsed")

# ── Rate limit (10 queries / min) ─────────────────────────────────────────────
if "query_ts" not in st.session_state:
    st.session_state.query_ts = []

def _within_rate_limit() -> bool:
    now = time.time()
    st.session_state.query_ts = [t for t in st.session_state.query_ts if now - t < 60]
    return len(st.session_state.query_ts) < 10

# ── Re-run injection from History page ────────────────────────────────────────
injected = st.session_state.pop("rerun_query", None)
default_q = injected or (chosen if chosen != "— select —" else "")

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="animation:fadeInUp .4s ease;">
    <div style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
                color:#475569;margin-bottom:6px;">Natural Language Query</div>
    <h1 style="font-size:2rem;font-weight:800;color:#f1f5f9;margin:0 0 6px;letter-spacing:-.02em;">
        Ask the warehouse anything
    </h1>
    <p style="font-size:14px;color:#64748b;margin:0 0 24px;">
        The 5-agent pipeline converts your question to SQL, runs it, and returns insights automatically.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Input area ────────────────────────────────────────────────────────────────
user_query = st.text_area(
    "Your question",
    value=default_q,
    max_chars=500,
    height=96,
    placeholder="e.g. What are the top 10 product categories by total revenue in 2018?",
    label_visibility="collapsed",
)

char_count = len(user_query)
col_btn, col_info = st.columns([1, 4])
with col_btn:
    run_btn = st.button("Run Query", type="primary", use_container_width=True)
with col_info:
    st.markdown(
        f'<span style="font-size:11.5px;color:#475569;">{char_count}/500 characters</span>',
        unsafe_allow_html=True,
    )

# ── Pipeline ─────────────────────────────────────────────────────────────────
if run_btn:
    q = user_query.strip()
    if not q:
        st.warning("Enter a question before running.")
    elif char_count > 500:
        st.error("Question exceeds the 500-character limit.")
    elif not _within_rate_limit():
        st.error("Rate limit reached (10 queries/min). Please wait a moment.")
    else:
        st.session_state.query_ts.append(time.time())

        progress_ph = st.empty()
        progress_ph.markdown("""
        <div class="glass-card" style="padding:18px 20px;">
            <div style="font-size:12px;font-weight:600;color:#60a5fa;margin-bottom:10px;
                        letter-spacing:.05em;">Running pipeline…</div>
            <div style="display:flex;gap:8px;align-items:center;">
                <span class="pulse-dot dot-amber"></span>
                <span style="font-size:13px;color:#94a3b8;">Agent 1 → understanding query intent</span>
            </div>
        </div>""", unsafe_allow_html=True)

        with st.spinner(""):
            result = run_pipeline(q)

        progress_ph.empty()

        if not result.success:
            st.markdown(f"""
            <div class="glass-card" style="border-color:rgba(239,68,68,.3);padding:18px 20px;">
                <span class="badge badge-error">Pipeline Failed</span>
                <p style="color:#fca5a5;margin:10px 0 0;font-size:13.5px;">{result.error_message}</p>
            </div>""", unsafe_allow_html=True)
            if result.sql:
                st.markdown('<div class="section-title" style="margin-top:20px;">Last Generated SQL</div>',
                            unsafe_allow_html=True)
                st.code(result.sql, language="sql")
        else:
            # ── Result metadata strip ─────────────────────────────────────────
            row_cnt  = len(result.data) if result.data is not None else 0
            dur_s    = result.duration_ms / 1000
            retry    = result.retry_count

            st.markdown(f"""
            <div class="result-meta">
                <div class="result-meta-item">
                    <span class="result-meta-val">{dur_s:.1f}s</span>
                    <span class="result-meta-lbl">Duration</span>
                </div>
                <div class="result-meta-item">
                    <span class="result-meta-val">{row_cnt}</span>
                    <span class="result-meta-lbl">Rows</span>
                </div>
                <div class="result-meta-item">
                    <span class="result-meta-val">{retry}</span>
                    <span class="result-meta-lbl">Retries</span>
                </div>
                <div class="result-meta-item">
                    <span class="result-meta-val">{active_p}</span>
                    <span class="result-meta-lbl">Provider</span>
                </div>
                <div style="margin-left:auto;">
                    <span class="badge badge-success">Success</span>
                </div>
            </div>""", unsafe_allow_html=True)

            # ── Tabs ──────────────────────────────────────────────────────────
            tab_chart, tab_data, tab_sql, tab_intent = st.tabs(
                ["Chart", "Data Table", "SQL", "Intent JSON"]
            )

            with tab_chart:
                render_auto_chart(result.data, q)

            with tab_data:
                if result.data is not None and not result.data.empty:
                    st.dataframe(result.data, use_container_width=True, hide_index=True)
                    st.download_button(
                        "Download CSV",
                        result.data.to_csv(index=False),
                        "query_result.csv",
                        "text/csv",
                        type="secondary",
                    )
                else:
                    st.markdown("""
                    <div class="empty-state">
                        <div class="empty-icon-wrap">&#8709;</div>
                        <div class="empty-title">No rows returned</div>
                        <div class="empty-desc">The query executed successfully but matched no records.</div>
                    </div>""", unsafe_allow_html=True)

            with tab_sql:
                if result.sql:
                    st.code(result.sql, language="sql")
                    valid = result.validation
                    if valid:
                        badge = "badge-success" if valid.is_valid else "badge-error"
                        label = "Validation passed" if valid.is_valid else "Validation failed"
                        st.markdown(f'<span class="badge {badge}">{label}</span>', unsafe_allow_html=True)
                        if valid.warnings:
                            for w in valid.warnings:
                                st.markdown(f'<span class="badge badge-warn">{w}</span>', unsafe_allow_html=True)

            with tab_intent:
                if result.intent:
                    st.json(result.intent)

            # ── Insights ──────────────────────────────────────────────────────
            if result.insights:
                st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
                render_insights(result.insights)
