"""
History page — browse past queries from logs/query_log.jsonl,
re-run them, and export as CSV.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import streamlit as st
import pandas as pd

LOG_FILE = Path("logs") / "query_log.jsonl"

st.set_page_config(page_title="History | Smart DW", page_icon="📜", layout="wide")

st.markdown("""
<style>
  .stApp { background-color: #0f1117; }
  .log-row { background:#1e2336; border:1px solid #2e3456; border-radius:8px;
             padding:12px 16px; margin-bottom:8px; }
  .log-q { color:#e8eaf6; font-weight:600; font-size:15px; }
  .log-meta { color:#9098b8; font-size:12px; margin-top:4px; }
  .success-badge { color:#00e676; font-weight:700; }
  .fail-badge { color:#ef5350; font-weight:700; }
</style>
""", unsafe_allow_html=True)

st.title("📜 Query History")
st.caption("All past queries logged with timestamps, SQL, and outcome.")


def _load_log() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    records = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return list(reversed(records))  # newest first


records = _load_log()

if not records:
    st.info(
        "No query history yet. Go to the **🔍 Query** page and run a question first."
    )
    st.stop()

# ── Summary stats ─────────────────────────────────────────────────────────────
total = len(records)
successes = sum(1 for r in records if r.get("success"))
avg_dur = sum(r.get("duration_ms", 0) for r in records) / total if total else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Queries", total)
c2.metric("Successful", successes)
c3.metric("Failed", total - successes)
c4.metric("Avg Duration", f"{avg_dur / 1000:.1f}s")

st.markdown("---")

# ── Filters ───────────────────────────────────────────────────────────────────
col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
with col_f1:
    search_term = st.text_input("🔍 Filter by keyword", placeholder="e.g. revenue, trend…")
with col_f2:
    show_only = st.selectbox("Status", ["All", "Success only", "Failed only"])
with col_f3:
    max_show = st.number_input("Show latest N", min_value=5, max_value=500, value=50, step=5)

# Apply filters
filtered = records
if search_term:
    kw = search_term.lower()
    filtered = [
        r for r in filtered
        if kw in r.get("user_query", "").lower()
        or kw in (r.get("sql") or "").lower()
    ]
if show_only == "Success only":
    filtered = [r for r in filtered if r.get("success")]
elif show_only == "Failed only":
    filtered = [r for r in filtered if not r.get("success")]

filtered = filtered[:max_show]
st.caption(f"Showing {len(filtered)} of {total} records")

# ── CSV export of filtered results ────────────────────────────────────────────
if filtered:
    export_cols = ["timestamp", "user_query", "sql", "success", "row_count", "duration_ms", "error", "insight_summary"]
    df_export = pd.DataFrame([{c: r.get(c, "") for c in export_cols} for r in filtered])
    st.download_button(
        "⬇ Export filtered results as CSV",
        df_export.to_csv(index=False),
        "query_history.csv",
        "text/csv",
    )

st.markdown("---")

# ── Log entries ───────────────────────────────────────────────────────────────
for i, rec in enumerate(filtered):
    ts = rec.get("timestamp", "")[:19].replace("T", " ")
    q = rec.get("user_query", "")
    ok = rec.get("success", False)
    rows = rec.get("row_count", 0)
    dur = rec.get("duration_ms", 0)
    retries = rec.get("retry_count", 0)
    err = rec.get("error", "")
    sql_text = rec.get("sql") or ""
    summary = rec.get("insight_summary", "")

    badge = '<span class="success-badge">✅ SUCCESS</span>' if ok else '<span class="fail-badge">❌ FAILED</span>'

    with st.expander(f"{ts}  ·  {q[:80]}{'…' if len(q) > 80 else ''}", expanded=False):
        st.markdown(f"""<div class="log-row">
            <div class="log-q">{q}</div>
            <div class="log-meta">
                {badge} &nbsp;|&nbsp; {rows} rows &nbsp;|&nbsp;
                {dur / 1000:.1f}s &nbsp;|&nbsp; {retries} retries
            </div>
        </div>""", unsafe_allow_html=True)

        if summary:
            st.markdown(f"**AI Summary:** {summary}")

        if sql_text:
            st.code(sql_text, language="sql")

        if err:
            st.error(f"Error: {err}")

        if ok:
            if st.button(f"▶ Re-run this query", key=f"rerun_{i}"):
                st.session_state["rerun_query"] = q
                st.switch_page("pages/1_Query.py")
