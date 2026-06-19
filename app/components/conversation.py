"""
Conversation history manager for multi-turn queries.

Stores the last N completed turns in st.session_state so the user can ask
follow-up questions that reference previous results:

  Turn 1: "Show revenue by state"
  Turn 2: "Now filter to just 2018"          ← references turn 1 context
  Turn 3: "Which of those are above average?" ← chains on turn 2

Each turn stores the minimum needed to give Agent 1 context without
ballooning the prompt: query text, intent summary, row shape, key finding.
"""
from __future__ import annotations
import streamlit as st
import pandas as pd

MAX_HISTORY = 4  # last N turns injected as context


def _init() -> None:
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []


def add_turn(query: str, intent: dict, data: pd.DataFrame | None, key_finding: str) -> None:
    """Append a completed pipeline turn to history."""
    _init()
    shape = f"{len(data)} rows × {len(data.columns)} cols" if data is not None and not data.empty else "no rows"
    cols  = list(data.columns)[:6] if data is not None and not data.empty else []
    st.session_state.conversation_history.append({
        "query":       query,
        "metric":      intent.get("metric",    "unknown"),
        "dimension":   intent.get("dimension", "unknown"),
        "filters":     intent.get("filters",   {}),
        "shape":       shape,
        "columns":     cols,
        "key_finding": key_finding[:180] if key_finding else "",
    })
    # Keep only last MAX_HISTORY turns
    st.session_state.conversation_history = st.session_state.conversation_history[-MAX_HISTORY:]


def clear_history() -> None:
    st.session_state.conversation_history = []


def get_history() -> list[dict]:
    _init()
    return st.session_state.conversation_history


def build_context_string() -> str:
    """Render history as a compact context block for Agent 1's prompt."""
    history = get_history()
    if not history:
        return ""
    lines = ["Previous conversation turns (for context — user may reference these):"]
    for i, turn in enumerate(history, 1):
        filters_str = ", ".join(f"{k}={v}" for k, v in turn["filters"].items()) if turn["filters"] else "none"
        lines.append(
            f"  Turn {i}: \"{turn['query']}\"\n"
            f"    → metric={turn['metric']}, dimension={turn['dimension']}, "
            f"filters={filters_str}, result={turn['shape']}\n"
            f"    → key finding: {turn['key_finding']}"
        )
    return "\n".join(lines)


def render_history_thread() -> None:
    """Render the conversation thread above the query box (compact chips)."""
    _init()
    history = st.session_state.conversation_history
    if not history:
        return

    chips_html = ""
    for i, turn in enumerate(history):
        q_short = (turn["query"][:52] + "…") if len(turn["query"]) > 55 else turn["query"]
        chips_html += f"""
        <div style="display:flex;align-items:flex-start;gap:10px;padding:7px 0;
                    border-bottom:1px solid rgba(255,255,255,0.05);">
            <div style="min-width:22px;height:22px;border-radius:50%;
                        background:rgba(59,130,246,0.18);border:1px solid rgba(59,130,246,0.4);
                        display:flex;align-items:center;justify-content:center;
                        font-size:10px;font-weight:700;color:#60a5fa;flex-shrink:0;">{i+1}</div>
            <div style="flex:1;">
                <div style="font-size:12.5px;color:#cbd5e1;line-height:1.4;">{q_short}</div>
                <div style="font-size:10.5px;color:#475569;margin-top:2px;">
                    {turn['shape']} &nbsp;·&nbsp; {turn['metric'] or '?'} by {turn['dimension'] or '?'}
                </div>
            </div>
        </div>"""

    st.markdown(f"""
    <div class="glass-card" style="padding:12px 16px;margin-bottom:14px;">
        <div style="font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;
                    color:#475569;margin-bottom:8px;">Conversation thread</div>
        {chips_html}
    </div>""", unsafe_allow_html=True)
