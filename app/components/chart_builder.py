"""Auto chart selection — picks bar / line / scatter / pie based on query intent and data shape."""
import streamlit as st
import pandas as pd
import plotly.express as px
from app.components.styles import CHART_LAYOUT, COLOR_SEQ, GRADIENT_BLUE_CYAN


def render_auto_chart(df: pd.DataFrame, query: str) -> None:
    if df is None or df.empty:
        _render_no_results("Query returned no rows.",
                           "Try broadening your filters or checking that the data exists in the warehouse.")
        return

    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()

    if not num_cols:
        _render_no_chart("No numeric columns to plot.",
                         "The result set contains only text columns. View the data in the table tab.")
        return

    y_col = num_cols[0]
    x_col = cat_cols[0] if cat_cols else df.columns[0]
    q = query.lower()

    try:
        if any(w in q for w in ("trend", "monthly", "over time", "by month", "by year",
                                 "per month", "time series", "historical", "month")):
            fig = _line_chart(df, x_col, y_col)

        elif any(w in q for w in ("percentage", "split", "share", "proportion",
                                   "distribution", "breakdown", "composition")):
            fig = _pie_chart(df, x_col, y_col)

        elif len(df) <= 6 and cat_cols:
            fig = _pie_chart(df, x_col, y_col)

        elif len(num_cols) >= 2:
            fig = _scatter_chart(df, num_cols[0], num_cols[1], cat_cols[0] if cat_cols else None, y_col)

        else:
            fig = _bar_chart(df, x_col, y_col)

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True,
                                                                "displaylogo": False,
                                                                "modeBarButtonsToRemove": ["lasso2d", "select2d"]})

    except Exception as e:
        _render_no_chart(
            "Chart could not be generated.",
            f"The data shape is unusual for automatic charting. Use the Data Table tab to view results.",
        )


# ── Chart factories ────────────────────────────────────────────────────────────

def _bar_chart(df, x, y):
    # Truncate long labels
    df = df.copy()
    if df[x].dtype == object:
        df[x] = df[x].astype(str).str[:32]
    top = df.nlargest(20, y) if len(df) > 20 else df

    fig = px.bar(
        top.sort_values(y, ascending=True),
        x=y, y=x, orientation="h",
        title=f"{y.replace('_', ' ').title()} by {x.replace('_', ' ').title()}",
        color=y,
        color_continuous_scale=GRADIENT_BLUE_CYAN,
        text=y,
    )
    fig.update_traces(
        texttemplate="%{x:,.0f}",
        textposition="outside",
        textfont=dict(color="#94a3b8", size=11),
        marker_line_width=0,
    )
    fig.update_coloraxes(showscale=False)
    fig.update_layout(
        **CHART_LAYOUT,
        height=max(320, min(len(top) * 38 + 80, 580)),
        yaxis_title=None,
        xaxis_title=y.replace("_", " ").title(),
        bargap=0.2,
    )
    return fig


def _line_chart(df, x, y):
    df = df.copy()
    if df[x].dtype == object:
        df[x] = df[x].astype(str)

    fig = px.line(
        df, x=x, y=y,
        title=f"{y.replace('_', ' ').title()} Over Time",
        markers=True,
        color_discrete_sequence=["#3b82f6"],
    )
    fig.update_traces(
        line=dict(width=2.5),
        marker=dict(size=7, color="#3b82f6",
                    line=dict(width=2, color="#080d1a")),
    )
    # Subtle area fill
    fig.add_scatter(
        x=df[x], y=df[y],
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.08)",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
    )
    fig.update_layout(
        **CHART_LAYOUT,
        height=360,
        xaxis_title=None,
        yaxis_title=y.replace("_", " ").title(),
    )
    return fig


def _pie_chart(df, names, values):
    df = df.copy()
    if df[names].dtype == object:
        df[names] = df[names].astype(str).str[:28]

    fig = px.pie(
        df, names=names, values=values,
        title=f"{values.replace('_', ' ').title()} Distribution",
        color_discrete_sequence=COLOR_SEQ,
        hole=0.38,
    )
    fig.update_traces(
        textfont=dict(size=12, color="#f1f5f9"),
        marker=dict(line=dict(color="#080d1a", width=2)),
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} (%{percent})<extra></extra>",
    )
    fig.update_layout(
        **CHART_LAYOUT,
        height=380,
        legend=dict(orientation="v", x=1, y=0.5),
    )
    return fig


def _scatter_chart(df, x, y, color_col, size_col):
    kwargs = dict(x=x, y=y,
                  title=f"{y.replace('_', ' ').title()} vs {x.replace('_', ' ').title()}",
                  color_discrete_sequence=["#3b82f6"],
                  opacity=0.75)
    if color_col and color_col in df.columns:
        kwargs["color"] = color_col
        kwargs["color_discrete_sequence"] = COLOR_SEQ

    fig = px.scatter(df, **kwargs)
    fig.update_traces(marker=dict(size=9, line=dict(width=1, color="rgba(0,0,0,0.3)")))
    fig.update_layout(
        **CHART_LAYOUT,
        height=380,
        xaxis_title=x.replace("_", " ").title(),
        yaxis_title=y.replace("_", " ").title(),
    )
    return fig


# ── Empty state helpers ────────────────────────────────────────────────────────

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
