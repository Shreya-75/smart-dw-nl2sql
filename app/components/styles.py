"""Shared CSS and Plotly theme for every page."""
import streamlit as st


GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; }

.stApp {
    background: #080d1a;
    font-family: 'Inter', -apple-system, 'Segoe UI', system-ui, sans-serif;
}

/* ── Sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a1020 0%, #080d1a 100%);
    border-right: 1px solid rgba(99,102,241,0.12);
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label {
    color: #94a3b8 !important;
    font-size: 13px !important;
}
[data-testid="stSidebarNav"] a {
    color: #94a3b8;
    font-weight: 500;
    letter-spacing: 0.01em;
    border-radius: 8px;
    transition: all 0.2s;
}
[data-testid="stSidebarNav"] a:hover,
[data-testid="stSidebarNav"] [aria-selected="true"] {
    background: rgba(59,130,246,0.12) !important;
    color: #60a5fa !important;
}

/* ── Animations ──────────────────────────────────────────── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(22px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}
@keyframes slideInLeft {
    from { opacity: 0; transform: translateX(-18px); }
    to   { opacity: 1; transform: translateX(0); }
}
@keyframes gradientFlow {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.55; transform: scale(0.9); }
}
@keyframes borderGlow {
    0%, 100% { border-color: rgba(99,102,241,0.2); box-shadow: 0 0 0 0 rgba(59,130,246,0); }
    50%       { border-color: rgba(59,130,246,0.5); box-shadow: 0 0 16px rgba(59,130,246,0.15); }
}

/* ── Hero Banner ─────────────────────────────────────────── */
.hero-banner {
    background: linear-gradient(135deg, #0d1b3e 0%, #1a2f6e 40%, #1e3a8a 70%, #1d4ed8 100%);
    background-size: 300% 300%;
    animation: gradientFlow 10s ease infinite;
    border-radius: 20px;
    padding: 52px 48px 48px;
    margin-bottom: 32px;
    border: 1px solid rgba(99,102,241,0.22);
    position: relative;
    overflow: hidden;
}
.hero-banner::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse at 75% 30%, rgba(6,182,212,0.1) 0%, transparent 55%);
    pointer-events: none;
}
.hero-banner::after {
    content: '';
    position: absolute;
    bottom: -1px; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(6,182,212,0.6) 50%, transparent 100%);
}
.hero-eyebrow {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #60a5fa;
    margin: 0 0 14px;
    animation: fadeIn 0.5s ease;
}
.hero-title {
    font-size: 2.75rem;
    font-weight: 800;
    color: #f1f5f9;
    letter-spacing: -0.025em;
    line-height: 1.12;
    margin: 0 0 16px;
    animation: fadeInUp 0.5s ease;
}
.hero-title span {
    background: linear-gradient(135deg, #60a5fa, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-desc {
    font-size: 1rem;
    color: #94a3b8;
    max-width: 600px;
    line-height: 1.75;
    margin: 0;
    animation: fadeInUp 0.6s ease 0.1s both;
}

/* ── KPI Cards ───────────────────────────────────────────── */
.kpi-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(99,102,241,0.18);
    border-radius: 16px;
    padding: 22px 18px 18px;
    text-align: center;
    position: relative;
    overflow: hidden;
    animation: fadeInUp 0.55s ease forwards;
    transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
    cursor: default;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 10%; right: 10%;
    height: 2px;
    background: linear-gradient(90deg, #3b82f6, #06b6d4, #3b82f6);
    border-radius: 0 0 4px 4px;
}
.kpi-card:hover {
    transform: translateY(-5px);
    border-color: rgba(59,130,246,0.38);
    box-shadow: 0 16px 40px rgba(0,0,0,0.45), 0 0 24px rgba(59,130,246,0.1);
}
.kpi-val {
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #60a5fa, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.15;
    letter-spacing: -0.02em;
}
.kpi-lbl {
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #475569;
    margin-top: 7px;
}

/* ── Section Title ───────────────────────────────────────── */
.section-title {
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #475569;
    padding-bottom: 12px;
    margin: 32px 0 18px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    display: flex;
    align-items: center;
    gap: 8px;
    animation: slideInLeft 0.4s ease;
}
.section-title::before {
    content: '';
    width: 3px; height: 14px;
    background: linear-gradient(180deg, #3b82f6, #06b6d4);
    border-radius: 2px;
    flex-shrink: 0;
}

/* ── Glass Card ──────────────────────────────────────────── */
.glass-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 24px;
    animation: fadeInUp 0.5s ease;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.glass-card:hover {
    border-color: rgba(99,102,241,0.28);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}

/* ── Pipeline Step ───────────────────────────────────────── */
.pipeline-step {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 14px 16px;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    margin: 8px 0;
    transition: background 0.2s, border-color 0.2s;
    animation: fadeInUp 0.5s ease;
}
.pipeline-step:hover {
    background: rgba(59,130,246,0.06);
    border-color: rgba(59,130,246,0.2);
}
.step-num {
    width: 30px; height: 30px; flex-shrink: 0;
    border-radius: 50%;
    background: linear-gradient(135deg, #1e3a8a, #3b82f6);
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700; color: #fff;
    box-shadow: 0 4px 10px rgba(59,130,246,0.35);
}
.step-content { flex: 1; }
.step-name { font-size: 13.5px; font-weight: 600; color: #e2e8f0; }
.step-desc { font-size: 12px; color: #64748b; margin-top: 2px; }

/* ── Badges ──────────────────────────────────────────────── */
.badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase;
}
.badge-success { background: rgba(16,185,129,0.1); color: #10b981; border: 1px solid rgba(16,185,129,0.22); }
.badge-error   { background: rgba(239,68,68,0.1);  color: #ef4444; border: 1px solid rgba(239,68,68,0.22); }
.badge-info    { background: rgba(59,130,246,0.1); color: #60a5fa; border: 1px solid rgba(59,130,246,0.22); }
.badge-warn    { background: rgba(245,158,11,0.1); color: #f59e0b; border: 1px solid rgba(245,158,11,0.22); }

/* ── Pulse dot ───────────────────────────────────────────── */
.pulse-dot {
    width: 8px; height: 8px; border-radius: 50%;
    display: inline-block; animation: pulse 2s ease-in-out infinite;
}
.dot-green { background: #10b981; box-shadow: 0 0 7px rgba(16,185,129,0.7); }
.dot-red   { background: #ef4444; box-shadow: 0 0 7px rgba(239,68,68,0.7); }
.dot-amber { background: #f59e0b; box-shadow: 0 0 7px rgba(245,158,11,0.7); }

/* ── Empty State ─────────────────────────────────────────── */
.empty-state {
    text-align: center;
    padding: 56px 24px;
    animation: fadeIn 0.5s ease;
}
.empty-icon-wrap {
    width: 64px; height: 64px;
    border-radius: 16px;
    background: rgba(99,102,241,0.08);
    border: 1px solid rgba(99,102,241,0.15);
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 16px;
    font-size: 28px;
}
.empty-title {
    font-size: 1.05rem; font-weight: 600; color: #64748b; margin-bottom: 6px;
}
.empty-desc {
    font-size: 0.875rem; color: #475569; max-width: 360px; margin: 0 auto; line-height: 1.65;
}

/* ── Divider ─────────────────────────────────────────────── */
.fancy-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(99,102,241,0.35) 50%, transparent 100%);
    margin: 28px 0;
    border: none;
}

/* ── Nav Cards ───────────────────────────────────────────── */
.nav-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(99,102,241,0.14);
    border-radius: 14px;
    padding: 20px;
    transition: all 0.25s ease;
    animation: fadeInUp 0.5s ease;
    height: 100%;
}
.nav-card:hover {
    background: rgba(59,130,246,0.06);
    border-color: rgba(59,130,246,0.3);
    transform: translateY(-3px);
    box-shadow: 0 12px 30px rgba(0,0,0,0.4);
}
.nav-card-icon {
    width: 40px; height: 40px; border-radius: 10px;
    background: linear-gradient(135deg, rgba(59,130,246,0.2), rgba(6,182,212,0.2));
    border: 1px solid rgba(99,102,241,0.2);
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 12px; font-size: 18px;
}
.nav-card-title { font-size: 15px; font-weight: 700; color: #e2e8f0; margin-bottom: 4px; }
.nav-card-desc  { font-size: 12.5px; color: #64748b; line-height: 1.55; }

/* ── Results meta strip ──────────────────────────────────── */
.result-meta {
    display: flex; gap: 24px; align-items: center;
    padding: 12px 16px;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    margin-bottom: 20px;
    animation: fadeIn 0.4s ease;
}
.result-meta-item { display: flex; flex-direction: column; }
.result-meta-val  { font-size: 16px; font-weight: 700; color: #e2e8f0; }
.result-meta-lbl  { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: #475569; }

/* ── Timeline entry ──────────────────────────────────────── */
.timeline-entry {
    border-left: 2px solid rgba(99,102,241,0.2);
    padding-left: 16px;
    margin-bottom: 16px;
    position: relative;
    animation: fadeInUp 0.4s ease;
}
.timeline-entry::before {
    content: '';
    position: absolute;
    left: -5px; top: 16px;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #3b82f6;
    border: 2px solid #080d1a;
}
.timeline-query { font-size: 14px; font-weight: 600; color: #e2e8f0; margin-bottom: 4px; }
.timeline-meta  { font-size: 11.5px; color: #64748b; }

/* ── Insight Box ─────────────────────────────────────────── */
.insight-box {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(99,102,241,0.15);
    border-radius: 14px;
    padding: 18px;
    height: 100%;
    transition: border-color 0.2s;
    animation: fadeInUp 0.5s ease;
}
.insight-box:hover { border-color: rgba(99,102,241,0.3); }
.insight-box.accent { border-left: 3px solid #10b981; }
.insight-lbl {
    font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    color: #475569; margin-bottom: 8px;
}
.insight-text { font-size: 13.5px; color: #cbd5e1; line-height: 1.65; }

/* ── Streamlit component overrides ──────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    letter-spacing: 0.03em !important;
    transition: all 0.22s ease !important;
    box-shadow: 0 4px 14px rgba(37,99,235,0.35) !important;
    padding: 8px 20px !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(37,99,235,0.45) !important;
    background: linear-gradient(135deg, #2563eb, #3b82f6) !important;
}
.stButton > button[kind="secondary"] {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    box-shadow: none !important;
    color: #94a3b8 !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.08) !important;
    border-color: rgba(255,255,255,0.18) !important;
    box-shadow: none !important;
    transform: none !important;
    color: #f1f5f9 !important;
}
.stTextArea > label, .stTextInput > label, .stSelectbox > label,
.stNumberInput > label, .stSlider > label { color: #94a3b8 !important; font-size: 13px !important; font-weight: 500 !important; }
.stTextArea textarea {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(99,102,241,0.22) !important;
    border-radius: 12px !important;
    color: #f1f5f9 !important;
    font-size: 14.5px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextArea textarea:focus {
    border-color: rgba(59,130,246,0.5) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
}
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(99,102,241,0.22) !important;
    border-radius: 10px !important;
    color: #f1f5f9 !important;
}
.stSelectbox > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(99,102,241,0.22) !important;
    border-radius: 10px !important;
    color: #f1f5f9 !important;
}
[data-testid="metric-container"] {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(99,102,241,0.14);
    border-radius: 12px;
    padding: 14px;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #e2e8f0;
    font-weight: 700;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 3px;
    background: rgba(255,255,255,0.025);
    border-radius: 10px;
    padding: 4px;
    border: 1px solid rgba(255,255,255,0.06);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    color: #64748b;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    background: rgba(37,99,235,0.2) !important;
    color: #60a5fa !important;
}
.streamlit-expanderHeader {
    background: rgba(255,255,255,0.02) !important;
    border-radius: 10px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    color: #94a3b8 !important;
    font-size: 13px !important;
}
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.stDeployButton { display: none; }
header[data-testid="stHeader"] { background: transparent; }

/* ── Page transition on navigation ──────────────────────── */
@keyframes pageEnter {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
[data-testid="stMain"] > div:first-child {
    animation: pageEnter 0.38s cubic-bezier(0.16, 1, 0.3, 1);
}

/* ── Larger base font sizes ──────────────────────────────── */
.stApp, .stApp p, .stApp div { font-size: 15px; }
.stMarkdown p { font-size: 15px; color: #94a3b8; line-height: 1.7; }
[data-testid="stSidebar"] .stMarkdown p { font-size: 14px !important; }
[data-baseweb="select"] div { font-size: 14px !important; }
.stTabs [data-baseweb="tab"] { font-size: 14px; font-weight: 500; }
.streamlit-expanderHeader { font-size: 15px !important; }

/* ── Expandable pipeline steps (HTML details/summary) ────── */
details.pipeline-detail {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    margin: 8px 0;
    overflow: hidden;
    transition: border-color 0.2s;
}
details.pipeline-detail[open] {
    border-color: rgba(59,130,246,0.3);
    background: rgba(59,130,246,0.04);
}
details.pipeline-detail summary {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px 18px;
    cursor: pointer;
    list-style: none;
    user-select: none;
}
details.pipeline-detail summary::-webkit-details-marker { display: none; }
details.pipeline-detail summary:hover { background: rgba(59,130,246,0.05); }
details.pipeline-detail .detail-body {
    padding: 0 18px 16px 62px;
    animation: fadeIn 0.25s ease;
}
.step-chevron {
    margin-left: auto;
    color: #475569;
    font-size: 12px;
    transition: transform 0.2s ease;
}
details.pipeline-detail[open] .step-chevron {
    transform: rotate(180deg);
}

/* ── Sidebar collapse button more visible ────────────────── */
[data-testid="collapsedControl"] {
    background: rgba(59,130,246,0.1) !important;
    border-radius: 0 8px 8px 0 !important;
}
</style>
"""


# Custom Plotly layout shared across all charts
CHART_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color="#94a3b8", size=12),
    title_font=dict(size=15, color="#e2e8f0", family="Inter, system-ui, sans-serif"),
    title_x=0.0,
    margin=dict(l=0, r=0, t=48, b=0),
    xaxis=dict(
        gridcolor="rgba(255,255,255,0.05)",
        linecolor="rgba(255,255,255,0.08)",
        tickcolor="rgba(255,255,255,0.08)",
        tickfont=dict(size=11),
        title_font=dict(size=12, color="#64748b"),
    ),
    yaxis=dict(
        gridcolor="rgba(255,255,255,0.05)",
        linecolor="rgba(255,255,255,0.08)",
        tickcolor="rgba(255,255,255,0.08)",
        tickfont=dict(size=11),
        title_font=dict(size=12, color="#64748b"),
    ),
    colorway=["#3b82f6", "#06b6d4", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#ec4899"],
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor="rgba(255,255,255,0.08)",
        font=dict(color="#94a3b8", size=11),
    ),
    hoverlabel=dict(
        bgcolor="rgba(15,23,42,0.95)",
        bordercolor="rgba(99,102,241,0.4)",
        font=dict(color="#f1f5f9", size=12),
    ),
)

COLOR_SEQ   = ["#3b82f6", "#06b6d4", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444"]
COLOR_BLUE  = "#3b82f6"
COLOR_CYAN  = "#06b6d4"
COLOR_GREEN = "#10b981"
GRADIENT_BLUE_CYAN = [[0, "#1d4ed8"], [0.5, "#2563eb"], [1.0, "#06b6d4"]]


def inject_css() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def chart_layout(**overrides) -> dict:
    """Merge CHART_LAYOUT base with chart-specific overrides. Later values win, preventing
    'multiple values for keyword argument' errors when passing e.g. yaxis= or legend=."""
    return {**CHART_LAYOUT, **overrides}
