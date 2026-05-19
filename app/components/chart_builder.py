"""
Smart auto chart builder.

Decision tree (priority order):
  1. Time column present (year/month/label/date/week/quarter)  →  line + area + optional dual bar
  2. Distribution query signal + ≤ 10 rows, NOT a ranking query  →  donut
  3. ≤ 4 rows with no ranking signal  →  donut
  4. Category labels long (avg > 11 chars) OR many rows (> 12)  →  horizontal bar
  5. Short codes / ordinal x (states, scores, 1-digit)  →  vertical bar
  6. Two numeric columns, no category  →  scatter
  7. Fallback  →  horizontal bar
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from app.components.styles import COLOR_SEQ, GRADIENT_BLUE_CYAN, chart_layout

# ── Semantic hint groups ──────────────────────────────────────────────────────
_TIME_COLS   = {"year", "month", "date", "week", "quarter", "period", "label", "time"}
_MONEY_PREF  = ("revenue", "value", "payment", "price", "amount", "total", "sales", "profit")
_VOLUME_PREF = ("count", "orders", "transactions", "quantity", "qty", "num")
_RATE_PREF   = ("rate", "pct", "percent", "ratio", "score", "avg", "average", "mean", "days", "hours")

_DIST_QUERY  = {"distribution", "share", "breakdown", "proportion", "split", "composition"}
_RANK_QUERY  = {"top", "best", "highest", "lowest", "worst", "most", "least", "ranking", "rank"}
_TIME_QUERY  = {"trend", "monthly", "over time", "by month", "by year", "per month", "quarterly",
                "historical", "growth", "time series", "weekly", "annual", "overtime"}


def _is_time_col(col: str) -> bool:
    cl = col.lower()
    return any(h in cl for h in _TIME_COLS)


def _pick_y(num_cols: list) -> str:
    """Return the most business-relevant numeric column."""
    for hint_group in (_MONEY_PREF, _VOLUME_PREF, _RATE_PREF):
        for c in num_cols:
            if any(h in c.lower() for h in hint_group):
                return c
    return num_cols[0]


def _fmt(col: str) -> str:
    return col.replace("_", " ").title()


# ── Chart renderers ───────────────────────────────────────────────────────────

def _render_line(df: pd.DataFrame, x: str, num_cols: list) -> None:
    """Time-series: line + area fill, dual y-axis for second metric."""
    y1 = _pick_y(num_cols)
    other = [c for c in num_cols if c != y1]
    y2 = other[0] if other else None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x].astype(str), y=df[y1],
        mode="lines+markers", name=_fmt(y1),
        line=dict(color="#3b82f6", width=2.5),
        marker=dict(size=6, color="#3b82f6", line=dict(width=2, color="#080d1a")),
        fill="tozeroy", fillcolor="rgba(59,130,246,0.08)",
        hovertemplate=f"<b>%{{x}}</b><br>{_fmt(y1)}: %{{y:,.2f}}<extra></extra>",
    ))

    extra = dict(
        height=400,
        title=f"{_fmt(y1)} Over Time",
        xaxis_tickangle=-30 if df[x].nunique() > 6 else 0,
        yaxis=dict(title=_fmt(y1), gridcolor="rgba(255,255,255,0.05)", tickformat=",.0f"),
    )
    if y2:
        fig.add_trace(go.Bar(
            x=df[x].astype(str), y=df[y2], name=_fmt(y2),
            marker_color="rgba(6,182,212,0.22)", yaxis="y2",
            hovertemplate=f"<b>%{{x}}</b><br>{_fmt(y2)}: %{{y:,.0f}}<extra></extra>",
        ))
        extra["yaxis2"] = dict(title=_fmt(y2), overlaying="y", side="right",
                                showgrid=False, tickfont=dict(color="#06b6d4"))
        extra["legend"] = dict(orientation="h", x=0, y=1.1)

    fig.update_layout(**chart_layout(**extra))
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


def _render_hbar(df: pd.DataFrame, cat: str, val: str, n_max: int = 20) -> None:
    """Horizontal bar — best for long category labels or large row counts."""
    top = df.nlargest(n_max, val) if len(df) > n_max else df.copy()
    top = top.copy().sort_values(val, ascending=True)
    top[cat] = top[cat].astype(str).str[:34]

    fig = px.bar(
        top, x=val, y=cat, orientation="h",
        title=f"{_fmt(val)} by {_fmt(cat)}",
        color=val, color_continuous_scale=GRADIENT_BLUE_CYAN, text=val,
    )
    fig.update_traces(
        texttemplate="%{text:,.1f}", textposition="outside",
        textfont=dict(size=10, color="#94a3b8"), marker_line_width=0,
    )
    fig.update_coloraxes(showscale=False)
    fig.update_layout(**chart_layout(
        height=max(280, min(len(top) * 36 + 80, 560)),
        xaxis_title=_fmt(val), yaxis_title=None,
        yaxis_tickfont=dict(size=11),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


def _render_vbar(df: pd.DataFrame, cat: str, val: str) -> None:
    """Vertical bar — best for short codes or ordinal categories (states, scores)."""
    df = df.copy()
    df[cat] = df[cat].astype(str)

    fig = px.bar(
        df, x=cat, y=val,
        title=f"{_fmt(val)} by {_fmt(cat)}",
        color=val, color_continuous_scale=GRADIENT_BLUE_CYAN, text=val,
    )
    fig.update_traces(
        texttemplate="%{text:,.1f}", textposition="outside",
        textfont=dict(size=10, color="#94a3b8"), marker_line_width=0,
    )
    fig.update_coloraxes(showscale=False)
    fig.update_layout(**chart_layout(
        height=360, xaxis_title=_fmt(cat), yaxis_title=_fmt(val),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


def _render_donut(df: pd.DataFrame, names: str, values: str) -> None:
    """Donut chart — for proportional breakdowns (≤ 10 categories)."""
    df = df.copy()
    df[names] = df[names].astype(str).str.replace("_", " ").str.title().str[:30]
    fig = px.pie(
        df, names=names, values=values,
        title=f"{_fmt(values)} Breakdown",
        color_discrete_sequence=COLOR_SEQ, hole=0.42,
    )
    fig.update_traces(
        textfont=dict(size=12, color="#f1f5f9"),
        marker=dict(line=dict(color="#080d1a", width=2.5)),
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} (%{percent})<extra></extra>",
    )
    fig.update_layout(**chart_layout(
        height=400, legend=dict(orientation="h", x=0.1, y=-0.12),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


def _render_scatter(df: pd.DataFrame, x: str, y: str, color_col) -> None:
    """Scatter — for two-metric correlation (e.g. review score vs revenue)."""
    fig = px.scatter(
        df, x=x, y=y,
        title=f"{_fmt(y)} vs {_fmt(x)}",
        color=color_col, color_discrete_sequence=COLOR_SEQ, opacity=0.75,
    )
    fig.update_traces(marker=dict(size=9, line=dict(width=1, color="rgba(0,0,0,0.3)")))
    fig.update_layout(**chart_layout(
        height=400, xaxis_title=_fmt(x), yaxis_title=_fmt(y),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


# ── Empty states ──────────────────────────────────────────────────────────────

def _render_no_results(title: str, desc: str) -> None:
    st.markdown(f"""
    <div class="empty-state">
        <div class="empty-icon-wrap">&#8709;</div>
        <div class="empty-title">{title}</div>
        <div class="empty-desc">{desc}</div>
    </div>""", unsafe_allow_html=True)


def _render_no_chart(title: str, desc: str) -> None:
    st.markdown(f"""
    <div class="empty-state">
        <div class="empty-icon-wrap">&#9638;</div>
        <div class="empty-title">{title}</div>
        <div class="empty-desc">{desc}</div>
    </div>""", unsafe_allow_html=True)


# ── Main entry point ──────────────────────────────────────────────────────────

def render_auto_chart(df: pd.DataFrame, query: str) -> None:
    if df is None or df.empty:
        _render_no_results(
            "Query returned no rows.",
            "Try broadening your filters or checking that the data exists in the warehouse.",
        )
        return

    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()
    q = query.lower()
    n = len(df)

    if not num_cols:
        _render_no_chart(
            "No numeric columns to chart.",
            "The result contains only text columns — see the Data Table tab.",
        )
        return

    is_ranking = any(kw in q for kw in _RANK_QUERY)
    is_dist    = any(kw in q for kw in _DIST_QUERY) and not is_ranking

    # ── 1. Time-series ────────────────────────────────────────────────────────
    time_col = next((c for c in df.columns if _is_time_col(c)), None)
    if time_col:
        _render_line(df, time_col, num_cols)
        return

    # ── 2. Donut: distribution query + small result, OR tiny non-ranking result
    if cat_cols and num_cols:
        if (is_dist and n <= 10) or (n <= 4 and not is_ranking):
            _render_donut(df, cat_cols[0], _pick_y(num_cols))
            return

    # ── 3. Category + metric: orientation by label length / row count ─────────
    if cat_cols and num_cols:
        y = _pick_y(num_cols)
        avg_label_len = df[cat_cols[0]].astype(str).str.len().mean()
        if avg_label_len > 11 or n > 12:
            _render_hbar(df, cat_cols[0], y)
        else:
            _render_vbar(df, cat_cols[0], y)
        return

    # ── 4. Pure numeric → scatter ─────────────────────────────────────────────
    if len(num_cols) >= 2:
        _render_scatter(df, num_cols[0], num_cols[1],
                        cat_cols[0] if cat_cols else None)
        return

    # ── 5. Single aggregate (one row, one number) ─────────────────────────────
    _render_no_chart(
        "No chart available for this result.",
        "Switch to the Data Table tab to view the data.",
    )
