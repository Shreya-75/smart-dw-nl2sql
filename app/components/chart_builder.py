"""Auto chart selection — picks bar / line / pie based on query text and data shape."""
import streamlit as st
import pandas as pd
import plotly.express as px


def render_auto_chart(df: pd.DataFrame, query: str) -> None:
    if df.empty or len(df.columns) < 2:
        return

    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()
    if not num_cols:
        return

    y_col = num_cols[0]
    x_col = cat_cols[0] if cat_cols else df.columns[0]
    q = query.lower()

    if any(w in q for w in ["trend", "monthly", "over time", "by month", "by year", "per month"]):
        fig = px.line(df, x=x_col, y=y_col, title="Trend Over Time",
                      markers=True, color_discrete_sequence=["#1a73e8"])
    elif any(w in q for w in ["percentage", "split", "share", "proportion", "pie", "distribution"]):
        fig = px.pie(df, names=x_col, values=y_col, title="Distribution",
                     color_discrete_sequence=px.colors.sequential.Blues_r)
    elif len(df) <= 5 and cat_cols:
        fig = px.pie(df, names=x_col, values=y_col, title="Distribution",
                     color_discrete_sequence=px.colors.sequential.Blues_r)
    else:
        fig = px.bar(df, x=x_col, y=y_col, title="Results",
                     color=y_col, color_continuous_scale="Blues",
                     text_auto=".2s")

    fig.update_layout(template="plotly_dark", margin=dict(t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)
