"""
Dashboard page — pre-built KPI charts queried directly from the star-schema warehouse.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.db_connection import get_engine, test_connection

st.set_page_config(page_title="Dashboard | Smart DW", page_icon="📊", layout="wide")

st.markdown("""
<style>
  .stApp { background-color: #0f1117; }
  .section-hdr { color:#90caf9; font-size:1.1rem; font-weight:700;
                 border-bottom:1px solid #2e3456; padding-bottom:6px; margin:20px 0 12px; }
</style>
""", unsafe_allow_html=True)

st.title("📊 KPI Dashboard")
st.caption("Pre-built analytics charts from the Olist star-schema warehouse.")

if not test_connection():
    st.error("Database not connected. Check your `.env` settings.")
    st.stop()

engine = get_engine()


@st.cache_data(ttl=300)
def _q(sql: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(sql, conn)


# ── Row 1 — Monthly Revenue Trend ─────────────────────────────────────────────
st.markdown('<div class="section-hdr">📈 Monthly Revenue Trend</div>', unsafe_allow_html=True)

df_rev = _q("""
    SELECT DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS month,
           ROUND(SUM(payment_value), 0)                  AS revenue,
           COUNT(DISTINCT fs.order_id)                   AS orders
    FROM fact_sales fs
    JOIN dim_time dt ON fs.time_key = dt.time_key
    WHERE order_status = 'delivered'
    GROUP BY month
    ORDER BY month
""")

if not df_rev.empty:
    fig_rev = px.line(
        df_rev, x="month", y="revenue",
        title="Monthly Revenue (delivered orders)",
        markers=True, color_discrete_sequence=["#1a73e8"],
    )
    fig_rev.update_layout(template="plotly_dark", xaxis_title="Month", yaxis_title="Revenue (R$)")
    st.plotly_chart(fig_rev, use_container_width=True)
else:
    st.info("No revenue data found. Run the ETL first.")

# ── Row 2 — Revenue by State + Top Categories ─────────────────────────────────
col_state, col_cat = st.columns(2)

with col_state:
    st.markdown('<div class="section-hdr">🗺️ Revenue by Customer State</div>', unsafe_allow_html=True)
    df_state = _q("""
        SELECT dc.customer_state AS state,
               ROUND(SUM(fs.payment_value), 0) AS revenue
        FROM fact_sales fs
        JOIN dim_customer dc ON fs.customer_key = dc.customer_key
        WHERE fs.order_status = 'delivered'
        GROUP BY dc.customer_state
        ORDER BY revenue DESC
        LIMIT 15
    """)
    if not df_state.empty:
        fig_state = px.bar(
            df_state, x="state", y="revenue",
            color="revenue", color_continuous_scale="Blues",
            title="Top 15 States by Revenue",
        )
        fig_state.update_layout(template="plotly_dark", showlegend=False)
        st.plotly_chart(fig_state, use_container_width=True)
    else:
        st.info("No data.")

with col_cat:
    st.markdown('<div class="section-hdr">🏷️ Top 10 Product Categories</div>', unsafe_allow_html=True)
    df_cat = _q("""
        SELECT dp.product_category_name AS category,
               ROUND(SUM(fs.payment_value), 0) AS revenue
        FROM fact_sales fs
        JOIN dim_product dp ON fs.product_key = dp.product_key
        WHERE fs.order_status = 'delivered'
          AND dp.product_category_name IS NOT NULL
        GROUP BY dp.product_category_name
        ORDER BY revenue DESC
        LIMIT 10
    """)
    if not df_cat.empty:
        fig_cat = px.bar(
            df_cat.sort_values("revenue"), x="revenue", y="category",
            orientation="h", color="revenue", color_continuous_scale="Teal",
            title="Top 10 Categories by Revenue",
        )
        fig_cat.update_layout(template="plotly_dark", showlegend=False)
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("No data.")

# ── Row 3 — Payment Type Donut + Avg Review Gauge ────────────────────────────
col_pay, col_rev = st.columns(2)

with col_pay:
    st.markdown('<div class="section-hdr">💳 Payment Type Distribution</div>', unsafe_allow_html=True)
    df_pay = _q("""
        SELECT payment_type,
               COUNT(*) AS cnt,
               ROUND(SUM(payment_value), 0) AS total_value
        FROM fact_sales
        WHERE order_status = 'delivered'
        GROUP BY payment_type
        ORDER BY cnt DESC
    """)
    if not df_pay.empty:
        fig_pay = px.pie(
            df_pay, names="payment_type", values="total_value",
            title="Payment Share by Value",
            color_discrete_sequence=px.colors.sequential.Blues_r,
            hole=0.4,
        )
        fig_pay.update_layout(template="plotly_dark")
        st.plotly_chart(fig_pay, use_container_width=True)
    else:
        st.info("No data.")

with col_rev:
    st.markdown('<div class="section-hdr">⭐ Average Review Score</div>', unsafe_allow_html=True)
    df_score = _q("""
        SELECT ROUND(AVG(review_score), 2) AS avg_score,
               COUNT(*) AS total_reviews
        FROM fact_sales
        WHERE review_score IS NOT NULL AND order_status = 'delivered'
    """)
    if not df_score.empty:
        avg_score = float(df_score["avg_score"].iloc[0])
        total_rev = int(df_score["total_reviews"].iloc[0])

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=avg_score,
            delta={"reference": 4.0},
            title={"text": f"Avg Review Score<br><span style='font-size:12px'>({total_rev:,} reviews)</span>"},
            gauge={
                "axis": {"range": [1, 5]},
                "bar": {"color": "#1a73e8"},
                "steps": [
                    {"range": [1, 3], "color": "#37474f"},
                    {"range": [3, 4], "color": "#1e3a5f"},
                    {"range": [4, 5], "color": "#0d2137"},
                ],
                "threshold": {
                    "line": {"color": "#00e676", "width": 4},
                    "thickness": 0.75,
                    "value": 4.0,
                },
            },
        ))
        fig_gauge.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig_gauge, use_container_width=True)
    else:
        st.info("No review data.")

# ── Row 4 — Delivery Performance ──────────────────────────────────────────────
st.markdown('<div class="section-hdr">🚚 Delivery Time Distribution</div>', unsafe_allow_html=True)

df_del = _q("""
    SELECT DATEDIFF(order_delivered_customer_date, order_purchase_timestamp) AS delivery_days,
           COUNT(*) AS orders
    FROM fact_sales
    WHERE order_status = 'delivered'
      AND order_delivered_customer_date IS NOT NULL
    GROUP BY delivery_days
    ORDER BY delivery_days
""")

if not df_del.empty:
    fig_del = px.bar(
        df_del[df_del["delivery_days"] <= 60],
        x="delivery_days", y="orders",
        title="Delivery Days Distribution (≤ 60 days)",
        color="orders", color_continuous_scale="Blues",
    )
    fig_del.update_layout(template="plotly_dark", xaxis_title="Days to Deliver", yaxis_title="Orders")
    st.plotly_chart(fig_del, use_container_width=True)
else:
    st.info("No delivery data.")

st.markdown("---")
st.caption("Data cached for 5 minutes. Refresh page to reload.")
