"""
Dashboard — pre-built KPI charts from the star-schema warehouse.

Root-cause fix: pd.read_sql(raw_string, conn) lets pymysql treat %Y/%m as Python
format specifiers. All SQL is now wrapped with sqlalchemy.text() to prevent this.
Column/table names corrected to match actual schema (date_key, customer_id, etc.).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text

from utils.db_connection import get_engine, test_connection
from app.components.styles import inject_css, COLOR_SEQ, GRADIENT_BLUE_CYAN, chart_layout

st.set_page_config(page_title="Dashboard | Smart DW", layout="wide", initial_sidebar_state="collapsed")
inject_css()

st.markdown("""
<div style="animation:fadeInUp .4s ease;margin-bottom:28px;">
    <div style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
                color:#475569;margin-bottom:6px;">KPI Dashboard</div>
    <h1 style="font-size:2rem;font-weight:800;color:#f1f5f9;margin:0 0 6px;letter-spacing:-.02em;">
        Warehouse Analytics
    </h1>
    <p style="font-size:14px;color:#64748b;margin:0;">
        Pre-built charts powered by direct warehouse queries. Cached for 5 minutes.
    </p>
</div>
""", unsafe_allow_html=True)

if not test_connection():
    st.markdown("""
    <div class="glass-card" style="border-color:rgba(239,68,68,.3);">
        <span class="badge badge-error">Database Offline</span>
        <p style="color:#fca5a5;margin:10px 0 0;font-size:13.5px;">
            Cannot connect to MySQL. Check your .env settings and ensure the server is running.
        </p>
    </div>""", unsafe_allow_html=True)
    st.stop()


@st.cache_data(ttl=300)
def _q(sql: str) -> pd.DataFrame:
    """Execute SQL safely — wrap with text() to prevent %Y/%m format-string errors."""
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


# ── Live KPI strip ────────────────────────────────────────────────────────────
try:
    kpi = _q("""
        SELECT COUNT(DISTINCT order_id)    AS total_orders,
               ROUND(SUM(payment_value),0) AS total_revenue,
               ROUND(AVG(review_score),2)  AS avg_review,
               ROUND(AVG(delivery_time_days),1) AS avg_delivery_days,
               SUM(CASE WHEN is_late=1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS late_pct
        FROM fact_sales
        WHERE order_status = 'delivered'
    """).iloc[0]

    k1, k2, k3, k4, k5 = st.columns(5)
    for col, val, lbl in [
        (k1, f"R$ {kpi['total_revenue']:,.0f}", "Total Revenue"),
        (k2, f"{kpi['total_orders']:,.0f}",     "Delivered Orders"),
        (k3, f"{kpi['avg_review']:.2f} / 5",   "Avg Review Score"),
        (k4, f"{kpi['avg_delivery_days']:.1f}d", "Avg Delivery Time"),
        (k5, f"{kpi['late_pct']:.1f}%",          "Late Delivery Rate"),
    ]:
        col.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-val">{val}</div>
            <div class="kpi-lbl">{lbl}</div>
        </div>""", unsafe_allow_html=True)
except Exception:
    st.info("Run the ETL pipeline to populate the warehouse before viewing charts.")
    st.stop()

st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)


def _chart_error(msg: str) -> None:
    st.markdown(f"""
    <div class="empty-state">
        <div class="empty-icon-wrap">&#9638;</div>
        <div class="empty-title">Chart unavailable</div>
        <div class="empty-desc">{msg}</div>
    </div>""", unsafe_allow_html=True)


# ── Section 1: Monthly Revenue Trend ─────────────────────────────────────────
st.markdown('<div class="section-title">Monthly Revenue Trend</div>', unsafe_allow_html=True)
try:
    df_rev = _q("""
        SELECT CONCAT(dt.year, '-', LPAD(dt.month, 2, '0')) AS month,
               ROUND(SUM(fs.payment_value), 0)              AS revenue,
               COUNT(DISTINCT fs.order_id)                  AS orders
        FROM   fact_sales fs
        JOIN   dim_time dt ON fs.date_key = dt.date_key
        WHERE  fs.order_status = 'delivered'
        GROUP  BY dt.year, dt.month
        ORDER  BY dt.year, dt.month
    """)
    if not df_rev.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_rev["month"], y=df_rev["revenue"],
            mode="lines+markers",
            name="Revenue",
            line=dict(color="#3b82f6", width=2.5),
            marker=dict(size=7, color="#3b82f6", line=dict(width=2, color="#080d1a")),
            fill="tozeroy",
            fillcolor="rgba(59,130,246,0.08)",
            hovertemplate="<b>%{x}</b><br>Revenue: R$ %{y:,.0f}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=df_rev["month"], y=df_rev["orders"],
            name="Orders",
            marker_color="rgba(6,182,212,0.25)",
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Orders: %{y:,.0f}<extra></extra>",
        ))
        fig.update_layout(**chart_layout(
            height=340,
            title="Monthly Revenue (R$) and Order Volume",
            yaxis=dict(title="Revenue (R$)", gridcolor="rgba(255,255,255,0.05)", tickformat=",.0f"),
            yaxis2=dict(title="Orders", overlaying="y", side="right",
                        showgrid=False, tickfont=dict(color="#06b6d4")),
            legend=dict(orientation="h", x=0, y=1.08),
            xaxis_tickangle=-30,
        ))
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    else:
        _chart_error("No delivered orders found. Run the ETL first.")
except Exception as e:
    _chart_error(str(e))

st.markdown('<div class="fancy-divider" style="margin:20px 0;"></div>', unsafe_allow_html=True)

# ── Section 2: Revenue by State + Top Categories ──────────────────────────────
col_state, col_cat = st.columns(2, gap="large")

with col_state:
    st.markdown('<div class="section-title">Revenue by Customer State</div>', unsafe_allow_html=True)
    try:
        df_state = _q("""
            SELECT dc.customer_state                   AS state,
                   ROUND(SUM(fs.payment_value), 0)     AS revenue,
                   COUNT(DISTINCT fs.order_id)         AS orders
            FROM   fact_sales fs
            JOIN   dim_customers dc ON fs.customer_id = dc.customer_id
            WHERE  fs.order_status = 'delivered'
            GROUP  BY dc.customer_state
            ORDER  BY revenue DESC
            LIMIT  15
        """)
        if not df_state.empty:
            fig = px.bar(
                df_state, x="state", y="revenue",
                title="Top 15 States — Total Revenue",
                color="revenue",
                color_continuous_scale=GRADIENT_BLUE_CYAN,
                text="revenue",
            )
            fig.update_traces(
                texttemplate="R$%{text:,.0f}",
                textposition="outside",
                textfont=dict(size=10, color="#94a3b8"),
                marker_line_width=0,
            )
            fig.update_coloraxes(showscale=False)
            fig.update_layout(**chart_layout(
                height=340,
                xaxis_title="State", yaxis_title="Revenue (R$)",
                yaxis_tickformat=",.0f",
            ))
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
        else:
            _chart_error("No data.")
    except Exception as e:
        _chart_error(str(e))

with col_cat:
    st.markdown('<div class="section-title">Top Product Categories</div>', unsafe_allow_html=True)
    try:
        df_cat = _q("""
            SELECT COALESCE(dp.product_category_name_english,
                            dp.product_category_name, 'Unknown') AS category,
                   ROUND(SUM(fs.payment_value), 0)               AS revenue
            FROM   fact_sales fs
            JOIN   dim_products dp ON fs.product_id = dp.product_id
            WHERE  fs.order_status = 'delivered'
            GROUP  BY category
            ORDER  BY revenue DESC
            LIMIT  12
        """)
        if not df_cat.empty:
            df_cat["category"] = df_cat["category"].str.replace("_", " ").str.title().str[:28]
            fig = px.bar(
                df_cat.sort_values("revenue"), x="revenue", y="category",
                orientation="h",
                title="Top 12 Categories by Revenue",
                color="revenue",
                color_continuous_scale=[[0, "#1e3a8a"], [1, "#06b6d4"]],
                text="revenue",
            )
            fig.update_traces(
                texttemplate="%{text:,.0f}",
                textposition="outside",
                textfont=dict(size=10, color="#94a3b8"),
                marker_line_width=0,
            )
            fig.update_coloraxes(showscale=False)
            fig.update_layout(**chart_layout(
                height=360,
                xaxis_title="Revenue (R$)", yaxis_title=None,
                yaxis_tickfont=dict(size=11),
                xaxis_tickformat=",.0f",
            ))
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
        else:
            _chart_error("No data.")
    except Exception as e:
        _chart_error(str(e))

st.markdown('<div class="fancy-divider" style="margin:20px 0;"></div>', unsafe_allow_html=True)

# ── Section 3: Payment Distribution + Review Score Gauge ──────────────────────
col_pay, col_gauge = st.columns(2, gap="large")

with col_pay:
    st.markdown('<div class="section-title">Payment Type Distribution</div>', unsafe_allow_html=True)
    try:
        df_pay = _q("""
            SELECT payment_type,
                   COUNT(*)                           AS transactions,
                   ROUND(SUM(payment_value), 0)       AS total_value
            FROM   fact_sales
            WHERE  order_status = 'delivered'
            GROUP  BY payment_type
            ORDER  BY total_value DESC
        """)
        if not df_pay.empty:
            df_pay["payment_type"] = df_pay["payment_type"].str.replace("_", " ").str.title()
            fig = px.pie(
                df_pay, names="payment_type", values="total_value",
                title="Share of Revenue by Payment Method",
                color_discrete_sequence=COLOR_SEQ,
                hole=0.42,
            )
            fig.update_traces(
                textfont=dict(size=12, color="#f1f5f9"),
                marker=dict(line=dict(color="#080d1a", width=2.5)),
                hovertemplate="<b>%{label}</b><br>R$ %{value:,.0f}<br>%{percent}<extra></extra>",
            )
            fig.update_layout(**chart_layout(height=340,
                                           legend=dict(orientation="h", x=0.1, y=-0.15)))
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
        else:
            _chart_error("No data.")
    except Exception as e:
        _chart_error(str(e))

with col_gauge:
    st.markdown('<div class="section-title">Review Score Gauge</div>', unsafe_allow_html=True)
    try:
        df_score = _q("""
            SELECT ROUND(AVG(review_score), 2)      AS avg_score,
                   COUNT(*)                         AS total_reviews,
                   SUM(CASE WHEN review_score = 5 THEN 1 ELSE 0 END) * 100.0
                       / COUNT(*)                   AS five_star_pct
            FROM   fact_sales
            WHERE  review_score IS NOT NULL
              AND  order_status = 'delivered'
        """).iloc[0]

        avg   = float(df_score["avg_score"])
        total = int(df_score["total_reviews"])
        five  = float(df_score["five_star_pct"])

        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=avg,
            delta={"reference": 4.0, "valueformat": ".2f"},
            number={"suffix": " / 5", "font": {"size": 36, "color": "#f1f5f9"}},
            title={"text": f"Avg Review Score<br><span style='font-size:12px;color:#64748b'>"
                           f"{total:,} reviews · {five:.1f}% five-star</span>",
                   "font": {"size": 14, "color": "#94a3b8"}},
            gauge={
                "axis":       {"range": [1, 5], "tickcolor": "#475569", "tickwidth": 1},
                "bar":        {"color": "#3b82f6", "thickness": 0.22},
                "bgcolor":    "rgba(0,0,0,0)",
                "bordercolor": "rgba(0,0,0,0)",
                "steps": [
                    {"range": [1, 2.5], "color": "rgba(239,68,68,0.15)"},
                    {"range": [2.5, 3.5], "color": "rgba(245,158,11,0.15)"},
                    {"range": [3.5, 5],   "color": "rgba(16,185,129,0.1)"},
                ],
                "threshold": {
                    "line":      {"color": "#10b981", "width": 3},
                    "thickness": 0.75,
                    "value":     4.0,
                },
            },
        ))
        fig.update_layout(**chart_layout(height=320, margin=dict(l=20, r=20, t=60, b=20)))
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    except Exception as e:
        _chart_error(str(e))

st.markdown('<div class="fancy-divider" style="margin:20px 0;"></div>', unsafe_allow_html=True)

# ── Section 4: Delivery Time Distribution ─────────────────────────────────────
st.markdown('<div class="section-title">Delivery Time Distribution</div>', unsafe_allow_html=True)
try:
    df_del = _q("""
        SELECT CAST(delivery_time_days AS UNSIGNED) AS delivery_days,
               COUNT(*)                             AS orders
        FROM   fact_sales
        WHERE  order_status = 'delivered'
          AND  delivery_time_days IS NOT NULL
          AND  delivery_time_days BETWEEN 0 AND 60
        GROUP  BY CAST(delivery_time_days AS UNSIGNED)
        ORDER  BY delivery_days
    """)
    if not df_del.empty:
        fig = go.Figure(go.Bar(
            x=df_del["delivery_days"],
            y=df_del["orders"],
            marker=dict(
                color=df_del["delivery_days"],
                colorscale=GRADIENT_BLUE_CYAN,
                line=dict(width=0),
            ),
            hovertemplate="<b>%{x} days</b><br>Orders: %{y:,}<extra></extra>",
        ))
        fig.update_layout(**chart_layout(
            height=300,
            title="Orders by Delivery Days (delivered, ≤ 60 days)",
            xaxis_title="Days to Deliver",
            yaxis_title="Orders",
            bargap=0.05,
        ))
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    else:
        _chart_error("No delivery data.")
except Exception as e:
    _chart_error(str(e))

st.markdown('<div class="fancy-divider" style="margin:20px 0;"></div>', unsafe_allow_html=True)

# ── Section 5: Seller Performance ─────────────────────────────────────────────
st.markdown('<div class="section-title">Top Seller States by Average Review Score</div>', unsafe_allow_html=True)
try:
    df_sel = _q("""
        SELECT ds.seller_state                        AS state,
               COUNT(DISTINCT fs.seller_id)           AS sellers,
               ROUND(AVG(fs.review_score), 2)         AS avg_review,
               ROUND(SUM(fs.payment_value), 0)        AS revenue
        FROM   fact_sales fs
        JOIN   dim_sellers ds ON fs.seller_id = ds.seller_id
        WHERE  fs.order_status = 'delivered'
          AND  fs.review_score IS NOT NULL
        GROUP  BY ds.seller_state
        HAVING COUNT(*) > 50
        ORDER  BY avg_review DESC
        LIMIT  20
    """)
    if not df_sel.empty:
        fig = px.scatter(
            df_sel, x="avg_review", y="revenue",
            size="sellers", color="avg_review",
            text="state",
            title="Seller States: Review Score vs Revenue (bubble = # sellers)",
            color_continuous_scale=[[0, "#1d4ed8"], [0.5, "#3b82f6"], [1, "#06b6d4"]],
            size_max=50,
        )
        fig.update_traces(
            textposition="top center",
            textfont=dict(size=11, color="#94a3b8"),
            marker=dict(line=dict(width=1, color="rgba(0,0,0,0.3)")),
            hovertemplate="<b>%{text}</b><br>Avg Review: %{x:.2f}<br>Revenue: R$ %{y:,.0f}<extra></extra>",
        )
        fig.update_coloraxes(showscale=False)
        fig.update_layout(**chart_layout(
            height=360,
            xaxis_title="Average Review Score",
            yaxis_title="Total Revenue (R$)",
            yaxis_tickformat=",.0f",
        ))
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    else:
        _chart_error("Insufficient seller data.")
except Exception as e:
    _chart_error(str(e))

st.markdown('<div class="fancy-divider" style="margin:20px 0;"></div>', unsafe_allow_html=True)

# ── Section 6: Review Score Analysis ─────────────────────────────────────────
col_rev_dist, col_rev_cat = st.columns(2, gap="large")

with col_rev_dist:
    st.markdown('<div class="section-title">Review Score Distribution</div>', unsafe_allow_html=True)
    try:
        df_rscore = _q("""
            SELECT review_score,
                   COUNT(*) AS reviews
            FROM   fact_sales
            WHERE  order_status = 'delivered'
              AND  review_score IS NOT NULL
            GROUP  BY review_score
            ORDER  BY review_score
        """)
        if not df_rscore.empty:
            colors = ["#ef4444", "#f97316", "#f59e0b", "#10b981", "#3b82f6"]
            fig = go.Figure(go.Bar(
                x=df_rscore["review_score"].astype(str),
                y=df_rscore["reviews"],
                marker_color=colors,
                text=df_rscore["reviews"],
                texttemplate="%{text:,}",
                textposition="outside",
                textfont=dict(size=11, color="#94a3b8"),
                hovertemplate="<b>Score %{x}</b><br>Reviews: %{y:,}<extra></extra>",
            ))
            fig.update_layout(**chart_layout(
                height=300,
                title="Customer Review Scores (1 = Worst, 5 = Best)",
                xaxis_title="Review Score",
                yaxis_title="Count",
                bargap=0.25,
            ))
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
        else:
            _chart_error("No review data.")
    except Exception as e:
        _chart_error(str(e))

with col_rev_cat:
    st.markdown('<div class="section-title">Best-Rated Product Categories</div>', unsafe_allow_html=True)
    try:
        df_rcat = _q("""
            SELECT COALESCE(dp.product_category_name_english,
                            dp.product_category_name) AS category,
                   ROUND(AVG(fs.review_score), 2)     AS avg_review,
                   COUNT(*)                           AS reviews
            FROM   fact_sales fs
            JOIN   dim_products dp ON fs.product_id = dp.product_id
            WHERE  fs.order_status = 'delivered'
              AND  fs.review_score IS NOT NULL
            GROUP  BY category
            HAVING COUNT(*) > 100
            ORDER  BY avg_review DESC
            LIMIT  12
        """)
        if not df_rcat.empty:
            df_rcat["category"] = df_rcat["category"].str.replace("_", " ").str.title().str[:28]
            fig = px.bar(
                df_rcat.sort_values("avg_review"), x="avg_review", y="category",
                orientation="h",
                title="Top 12 Categories — Average Review Score",
                color="avg_review",
                color_continuous_scale=[[0, "#1e3a8a"], [0.5, "#3b82f6"], [1, "#10b981"]],
                text="avg_review",
            )
            fig.update_traces(
                texttemplate="%{text:.2f}",
                textposition="outside",
                textfont=dict(size=10, color="#94a3b8"),
                marker_line_width=0,
            )
            fig.update_coloraxes(showscale=False)
            fig.update_layout(**chart_layout(
                height=360,
                xaxis_title="Average Score", yaxis_title=None,
                xaxis_range=[0, 5.5],
                yaxis_tickfont=dict(size=11),
            ))
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
        else:
            _chart_error("No data.")
    except Exception as e:
        _chart_error(str(e))

st.markdown('<div class="fancy-divider" style="margin:20px 0;"></div>', unsafe_allow_html=True)

# ── Section 7: Late Delivery Intelligence ────────────────────────────────────
col_late, col_delay = st.columns(2, gap="large")

with col_late:
    st.markdown('<div class="section-title">Late Delivery Rate by State</div>', unsafe_allow_html=True)
    try:
        df_late = _q("""
            SELECT dc.customer_state AS state,
                   COUNT(*)          AS total_orders,
                   ROUND(SUM(CASE WHEN fs.is_late = 1 THEN 1 ELSE 0 END) * 100.0
                         / COUNT(*), 1) AS late_pct,
                   ROUND(AVG(CASE WHEN fs.is_late = 1 THEN fs.delay_days END), 1) AS avg_delay
            FROM   fact_sales fs
            JOIN   dim_customers dc ON fs.customer_id = dc.customer_id
            WHERE  fs.order_status = 'delivered'
            GROUP  BY dc.customer_state
            HAVING COUNT(*) > 30
            ORDER  BY late_pct DESC
            LIMIT  15
        """)
        if not df_late.empty:
            fig = px.bar(
                df_late, x="state", y="late_pct",
                title="Top 15 States — % Late Deliveries",
                color="late_pct",
                color_continuous_scale=[[0, "#10b981"], [0.4, "#f59e0b"], [1, "#ef4444"]],
                text="late_pct",
            )
            fig.update_traces(
                texttemplate="%{text:.1f}%",
                textposition="outside",
                textfont=dict(size=10, color="#94a3b8"),
                marker_line_width=0,
            )
            fig.update_coloraxes(showscale=False)
            fig.update_layout(**chart_layout(
                height=340,
                xaxis_title="State",
                yaxis_title="Late Delivery Rate (%)",
                yaxis_ticksuffix="%",
            ))
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
        else:
            _chart_error("No late delivery data.")
    except Exception as e:
        _chart_error(str(e))

with col_delay:
    st.markdown('<div class="section-title">Freight Cost as % of Order Value</div>', unsafe_allow_html=True)
    try:
        df_freight = _q("""
            SELECT COALESCE(dp.product_category_name_english,
                            dp.product_category_name) AS category,
                   ROUND(AVG(fs.freight_value), 2)   AS avg_freight,
                   ROUND(AVG(fs.price), 2)            AS avg_price,
                   ROUND(AVG(fs.freight_value) * 100
                         / NULLIF(AVG(fs.price), 0), 1) AS freight_pct
            FROM   fact_sales fs
            JOIN   dim_products dp ON fs.product_id = dp.product_id
            WHERE  fs.order_status = 'delivered'
              AND  fs.price > 0
            GROUP  BY category
            HAVING COUNT(*) > 100
            ORDER  BY freight_pct DESC
            LIMIT  12
        """)
        if not df_freight.empty:
            df_freight["category"] = df_freight["category"].str.replace("_", " ").str.title().str[:28]
            fig = px.bar(
                df_freight.sort_values("freight_pct"), x="freight_pct", y="category",
                orientation="h",
                title="Top 12 Categories — Freight as % of Price",
                color="freight_pct",
                color_continuous_scale=[[0, "#10b981"], [0.5, "#f59e0b"], [1, "#ef4444"]],
                text="freight_pct",
            )
            fig.update_traces(
                texttemplate="%{text:.1f}%",
                textposition="outside",
                textfont=dict(size=10, color="#94a3b8"),
                marker_line_width=0,
            )
            fig.update_coloraxes(showscale=False)
            fig.update_layout(**chart_layout(
                height=360,
                xaxis_title="Freight / Price (%)", yaxis_title=None,
                yaxis_tickfont=dict(size=11),
            ))
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
        else:
            _chart_error("No freight data.")
    except Exception as e:
        _chart_error(str(e))

st.markdown('<div class="fancy-divider" style="margin:20px 0;"></div>', unsafe_allow_html=True)

# ── Section 8: YoY Growth & Payment Behaviour ────────────────────────────────
col_qyoy, col_inst = st.columns(2, gap="large")

with col_qyoy:
    st.markdown('<div class="section-title">Year-over-Year Quarterly Revenue</div>', unsafe_allow_html=True)
    try:
        df_qyoy = _q("""
            SELECT dt.year,
                   dt.quarter,
                   ROUND(SUM(fs.payment_value), 0) AS revenue,
                   COUNT(DISTINCT fs.order_id)     AS orders
            FROM   fact_sales fs
            JOIN   dim_time dt ON fs.date_key = dt.date_key
            WHERE  fs.order_status = 'delivered'
              AND  dt.year IN (2017, 2018)
            GROUP  BY dt.year, dt.quarter
            ORDER  BY dt.year, dt.quarter
        """)
        if not df_qyoy.empty:
            df_qyoy["year"]          = df_qyoy["year"].astype(str)
            df_qyoy["quarter_label"] = "Q" + df_qyoy["quarter"].astype(str)
            fig = px.bar(
                df_qyoy, x="quarter_label", y="revenue",
                color="year", barmode="group",
                title="Revenue by Quarter — 2017 vs 2018",
                color_discrete_map={"2017": "#3b82f6", "2018": "#06b6d4"},
                text="revenue",
            )
            fig.update_traces(
                texttemplate="R$%{text:,.0f}",
                textposition="outside",
                textfont=dict(size=10, color="#94a3b8"),
                marker_line_width=0,
            )
            fig.update_layout(**chart_layout(
                height=300,
                xaxis_title="Quarter",
                yaxis_title="Revenue (R$)",
                yaxis_tickformat=",.0f",
                legend=dict(orientation="h", x=0, y=1.12),
                bargap=0.2,
                bargroupgap=0.06,
            ))
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
        else:
            _chart_error("Insufficient data for YoY comparison.")
    except Exception as e:
        _chart_error(str(e))

with col_inst:
    st.markdown('<div class="section-title">Credit Card Instalment Breakdown</div>', unsafe_allow_html=True)
    try:
        df_inst = _q("""
            SELECT payment_installments          AS installments,
                   COUNT(*)                      AS transactions,
                   ROUND(AVG(payment_value), 0)  AS avg_value
            FROM   fact_sales
            WHERE  order_status = 'delivered'
              AND  payment_type  = 'credit_card'
              AND  payment_installments BETWEEN 1 AND 12
            GROUP  BY payment_installments
            ORDER  BY payment_installments
        """)
        if not df_inst.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_inst["installments"].astype(str),
                y=df_inst["transactions"],
                name="Transactions",
                marker_color="rgba(59,130,246,0.7)",
                hovertemplate="<b>%{x}x</b><br>Transactions: %{y:,}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=df_inst["installments"].astype(str),
                y=df_inst["avg_value"],
                name="Avg Value (R$)",
                mode="lines+markers",
                line=dict(color="#f59e0b", width=2),
                marker=dict(size=7),
                yaxis="y2",
                hovertemplate="<b>%{x}x</b><br>Avg R$ %{y:,.0f}<extra></extra>",
            ))
            fig.update_layout(**chart_layout(
                height=300,
                title="Credit Card Instalments (1–12×)",
                yaxis=dict(title="Transactions", gridcolor="rgba(255,255,255,0.05)"),
                yaxis2=dict(title="Avg Value (R$)", overlaying="y", side="right",
                            showgrid=False, tickfont=dict(color="#f59e0b")),
                legend=dict(orientation="h", x=0, y=1.08),
                xaxis_title="Instalments",
                bargap=0.2,
            ))
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
        else:
            _chart_error("No instalment data.")
    except Exception as e:
        _chart_error(str(e))

st.markdown('<div class="fancy-divider" style="margin:20px 0;"></div>', unsafe_allow_html=True)

# ── Dataset Context Visual Strip ──────────────────────────────────────────────
st.markdown('<div class="section-title">Dataset Context</div>', unsafe_allow_html=True)
img1, img2, img3 = st.columns(3, gap="large")
for col, url, title, caption in [
    (img1,
     "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=600&auto=format&fit=crop&q=70",
     "E-Commerce Platform",
     "99,441 orders placed on Olist marketplace across 27 Brazilian states (2016–2018)"),
    (img2,
     "https://images.unsplash.com/photo-1553413077-190dd305871c?w=600&auto=format&fit=crop&q=70",
     "Logistics & Delivery",
     "Over 70% of orders delivered on time. Average delivery window: 12 days."),
    (img3,
     "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600&auto=format&fit=crop&q=70",
     "Agentic Analytics",
     "Natural language → SQL → insights. Five-agent pipeline with automatic retry."),
]:
    col.markdown(f"""
    <div style="border-radius:14px;overflow:hidden;border:1px solid rgba(255,255,255,0.07);
                animation:fadeInUp .6s ease;">
        <div style="height:160px;background:url('{url}') center/cover no-repeat;
                    position:relative;">
            <div style="position:absolute;inset:0;background:linear-gradient(
                        0deg,rgba(8,13,26,0.85) 0%,rgba(8,13,26,0.2) 100%);"></div>
            <div style="position:absolute;bottom:12px;left:14px;font-size:13px;
                        font-weight:700;color:#f1f5f9;letter-spacing:.01em;">{title}</div>
        </div>
        <div style="padding:12px 14px;background:rgba(255,255,255,0.02);">
            <p style="font-size:12px;color:#64748b;margin:0;line-height:1.55;">{caption}</p>
        </div>
    </div>""", unsafe_allow_html=True)

st.markdown("""
<p style="font-size:11.5px;color:#334155;text-align:center;margin-top:32px;">
    Data cached 5 min &nbsp;·&nbsp; Delivered orders only &nbsp;·&nbsp;
    Olist Brazilian E-Commerce 2016–2018 &nbsp;·&nbsp;
    Images: Unsplash (free licence)
</p>""", unsafe_allow_html=True)
