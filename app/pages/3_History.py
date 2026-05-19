"""
History — browse all past queries from the JSONL log.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import streamlit as st
import pandas as pd
from app.components.styles import inject_css

LOG_FILE = Path("logs") / "query_log.jsonl"

st.set_page_config(page_title="History | Smart DW", layout="wide", initial_sidebar_state="expanded")
inject_css()

st.markdown("""
<div style="animation:fadeInUp .4s ease;margin-bottom:28px;">
    <div style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
                color:#475569;margin-bottom:6px;">Query Log</div>
    <h1 style="font-size:2rem;font-weight:800;color:#f1f5f9;margin:0 0 6px;letter-spacing:-.02em;">
        Query History
    </h1>
    <p style="font-size:14px;color:#64748b;margin:0;">
        Every query is logged with its SQL, outcome, duration, and AI summary.
    </p>
</div>
""", unsafe_allow_html=True)


def _load() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    out = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return list(reversed(out))


records = _load()

if not records:
    st.markdown("""
    <div class="empty-state" style="padding-top:80px;">
        <div class="empty-icon-wrap">&#9632;</div>
        <div class="empty-title">No history yet</div>
        <div class="empty-desc">
            Run a question on the Query page — every pipeline execution is automatically logged here.
        </div>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── Summary KPIs ──────────────────────────────────────────────────────────────
total     = len(records)
successes = sum(1 for r in records if r.get("success"))
failures  = total - successes
avg_dur   = sum(r.get("duration_ms", 0) for r in records) / total

kc1, kc2, kc3, kc4 = st.columns(4)
for col, val, lbl in [
    (kc1, str(total),              "Total Queries"),
    (kc2, str(successes),          "Successful"),
    (kc3, str(failures),           "Failed"),
    (kc4, f"{avg_dur/1000:.1f}s", "Avg Duration"),
]:
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-val">{val}</div>
        <div class="kpi-lbl">{lbl}</div>
    </div>""", unsafe_allow_html=True)

st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

# ── Filters ───────────────────────────────────────────────────────────────────
fc1, fc2, fc3 = st.columns([3, 1, 1])
with fc1:
    search = st.text_input("Search queries", placeholder="Filter by keyword, table name, or error text…",
                           label_visibility="collapsed")
with fc2:
    status_filter = st.selectbox("Status", ["All", "Successful", "Failed"], label_visibility="collapsed")
with fc3:
    max_n = st.number_input("Show", min_value=5, max_value=500, value=50, step=10,
                            label_visibility="collapsed")

filtered = records
if search:
    kw = search.lower()
    filtered = [r for r in filtered if
                kw in r.get("user_query", "").lower() or
                kw in (r.get("sql") or "").lower() or
                kw in (r.get("error") or "").lower()]
if status_filter == "Successful":
    filtered = [r for r in filtered if r.get("success")]
elif status_filter == "Failed":
    filtered = [r for r in filtered if not r.get("success")]

filtered = filtered[:int(max_n)]

st.markdown(
    f'<p style="font-size:12px;color:#475569;margin-bottom:16px;">'
    f'Showing {len(filtered)} of {total} records</p>',
    unsafe_allow_html=True,
)

# ── CSV export ────────────────────────────────────────────────────────────────
if filtered:
    cols = ["timestamp", "user_query", "sql", "success", "row_count",
            "duration_ms", "retry_count", "error", "insight_summary"]
    df_export = pd.DataFrame([{c: r.get(c, "") for c in cols} for r in filtered])
    st.download_button("Export as CSV", df_export.to_csv(index=False),
                       "query_history.csv", "text/csv", type="secondary")

st.markdown('<div class="fancy-divider" style="margin:12px 0 20px;"></div>', unsafe_allow_html=True)

# ── Timeline ──────────────────────────────────────────────────────────────────
for i, rec in enumerate(filtered):
    ts      = rec.get("timestamp", "")[:19].replace("T", " ")
    q       = rec.get("user_query", "—")
    ok      = rec.get("success", False)
    rows    = rec.get("row_count", 0)
    dur     = rec.get("duration_ms", 0)
    retries = rec.get("retry_count", 0)
    err     = rec.get("error", "") or ""
    sql_txt = rec.get("sql") or ""
    summary = rec.get("insight_summary") or ""

    badge_cls = "badge-success" if ok else "badge-error"
    badge_lbl = "Success" if ok else "Failed"

    with st.expander(
        f"{ts}  ·  {q[:90]}{'…' if len(q) > 90 else ''}",
        expanded=False,
    ):
        col_left, col_right = st.columns([3, 1])

        with col_left:
            st.markdown(f"""
            <div class="timeline-entry">
                <div class="timeline-query">{q}</div>
                <div class="timeline-meta">
                    <span class="badge {badge_cls}">{badge_lbl}</span>
                    &nbsp;
                    <span style="color:#475569;">{rows} rows &nbsp;·&nbsp; {dur/1000:.1f}s &nbsp;·&nbsp; {retries} retries</span>
                </div>
            </div>""", unsafe_allow_html=True)

            if summary:
                st.markdown(f"""
                <div class="glass-card" style="padding:12px 16px;margin:8px 0;">
                    <div style="font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
                                color:#475569;margin-bottom:6px;">AI Summary</div>
                    <div style="font-size:13px;color:#cbd5e1;line-height:1.6;">{summary}</div>
                </div>""", unsafe_allow_html=True)

        with col_right:
            st.markdown(f"""
            <div style="text-align:right;font-size:11px;color:#475569;padding-top:4px;">{ts}</div>
            """, unsafe_allow_html=True)
            if ok:
                if st.button("Re-run", key=f"rerun_{i}", type="secondary"):
                    st.session_state["rerun_query"] = q
                    st.switch_page("pages/1_Query.py")

        if sql_txt:
            st.code(sql_txt, language="sql")

        if err:
            st.markdown(f"""
            <div class="glass-card" style="border-color:rgba(239,68,68,.25);padding:12px 16px;">
                <span class="badge badge-error" style="margin-bottom:6px;">Error</span>
                <div style="font-size:12.5px;color:#fca5a5;margin-top:6px;font-family:monospace;">{err}</div>
            </div>""", unsafe_allow_html=True)
