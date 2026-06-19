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

st.set_page_config(page_title="Query | Smart DW", layout="wide", initial_sidebar_state="collapsed")
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
        <div class="glass-card" style="padding:16px 20px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;
                        color:#475569;margin-bottom:10px;">Agentic Pipeline</div>
            <div style="display:flex;gap:8px;align-items:center;">
                <span class="pulse-dot dot-amber"></span>
                <span style="font-size:13px;color:#94a3b8;">Initialising agents…</span>
            </div>
        </div>""", unsafe_allow_html=True)

        with st.spinner(""):
            result = run_pipeline(q)

        progress_ph.empty()

        # ── Agent trace: show every decision made by the pipeline ─────────────
        if result.agent_trace:
            _AGENT_COLORS = {
                1: ("#3b82f6", "#1e3a8a"),
                2: ("#06b6d4", "#0e4f5e"),
                3: ("#8b5cf6", "#2e1065"),
                4: ("#10b981", "#064e3b"),
                5: ("#f59e0b", "#451a03"),
                "R": ("#ef4444", "#450a0a"),
            }
            _ACTION_ICONS = {
                "done": "&#10003;", "failed": "&#10007;", "empty_result": "&#9650;",
                "re_understand": "&#8635;", "reflect": "&#9651;", "start": "&#9656;",
                "error": "&#10007;",
            }
            rows_html = ""
            for ev in result.agent_trace:
                ag  = ev.get("agent", "?")
                act = ev.get("action", "")
                msg = ev.get("message", "")
                clr, bg = _AGENT_COLORS.get(ag, ("#64748b", "#1e293b"))
                icon = _ACTION_ICONS.get(act, "&#9656;")
                is_fail = act in ("failed", "error")
                is_reflect = ag == "R"
                label = f"Agent {ag}" if isinstance(ag, int) else ("Reflection" if ag == "R" else str(ag))
                rows_html += f"""
                <div style="display:flex;align-items:flex-start;gap:10px;padding:6px 0;
                             border-bottom:1px solid rgba(255,255,255,0.04);">
                    <div style="min-width:20px;font-size:11px;color:{'#ef4444' if is_fail else clr};
                                margin-top:1px;">{icon}</div>
                    <div style="display:inline-flex;align-items:center;gap:6px;min-width:130px;">
                        <span style="font-size:10px;font-weight:700;letter-spacing:.06em;
                                     text-transform:uppercase;color:{clr};
                                     background:{bg}33;border:1px solid {clr}33;
                                     border-radius:5px;padding:2px 7px;">{label}</span>
                    </div>
                    <div style="font-size:12.5px;color:{'#fca5a5' if is_fail else ('#fcd34d' if is_reflect else '#94a3b8')};
                                line-height:1.5;">{msg}</div>
                </div>"""

            with st.expander("Agent execution trace", expanded=(result.retry_count > 0)):
                st.markdown(f"""
                <div style="font-family:monospace;padding:4px 0;">{rows_html}</div>
                """, unsafe_allow_html=True)

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
            tab_chart, tab_data, tab_sql, tab_intent, tab_trace = st.tabs(
                ["Chart", "Data Table", "SQL", "Intent JSON", "Agent Trace"]
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

            with tab_trace:
                if result.agent_trace:
                    _STEP_COLORS = {
                        1: "#3b82f6", 2: "#06b6d4", 3: "#8b5cf6",
                        4: "#10b981", 5: "#f59e0b", "R": "#ef4444",
                    }
                    for step in result.agent_trace:
                        ag  = step.get("agent", "?")
                        act = step.get("action", "")
                        msg = step.get("message", "")
                        clr = _STEP_COLORS.get(ag, "#64748b")
                        lbl = (f"Agent {ag} — {step.get('name', '')}"
                               if isinstance(ag, int) else step.get("name", str(ag)))
                        is_fail = act in ("failed", "error")
                        # Extra detail fields (sql, plan, intent, etc.)
                        extras = {k: v for k, v in step.items()
                                  if k not in ("agent","action","message","name")
                                  and v is not None and v != ""}
                        st.markdown(f"""
                        <div style="display:flex;gap:12px;padding:10px 0;
                                    border-bottom:1px solid rgba(255,255,255,0.05);">
                            <div style="width:3px;border-radius:2px;flex-shrink:0;
                                        background:{'#ef4444' if is_fail else clr};"></div>
                            <div style="flex:1;">
                                <div style="font-size:10.5px;font-weight:700;letter-spacing:.08em;
                                            text-transform:uppercase;color:{clr};margin-bottom:3px;">
                                    {lbl}
                                </div>
                                <div style="font-size:13px;color:{'#fca5a5' if is_fail else '#cbd5e1'};">
                                    {msg}
                                </div>
                            </div>
                        </div>""", unsafe_allow_html=True)
                        if "sql" in extras:
                            st.code(extras.pop("sql"), language="sql")
                        if "plan" in extras:
                            st.markdown(f"""
                            <div style="margin:4px 0 0 15px;font-size:12px;color:#f59e0b;
                                        font-style:italic;line-height:1.5;">
                                Fix plan: {extras.pop('plan')}
                            </div>""", unsafe_allow_html=True)
                        if "intent" in extras:
                            st.json(extras.pop("intent"))
                else:
                    st.info("No trace available for this run.")

            # ── Insights ──────────────────────────────────────────────────────
            if result.insights:
                st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
                render_insights(result.insights)
