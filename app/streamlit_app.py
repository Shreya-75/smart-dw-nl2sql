"""
Smart Data Warehouse — NL2SQL Streamlit App
Entry point: streamlit run app/streamlit_app.py
"""
import sys
sys.path.insert(0, ".")

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text

import utils.logger
from agents.pipeline import run_pipeline
from utils.db_connection import get_engine, test_connection

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smart DW | NL2SQL",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .stApp { background-color: #0f1117; }
  .metric-card {
    background: #1e2336; border: 1px solid #2e3456;
    border-radius: 12px; padding: 20px; text-align: center;
  }
  .metric-value { font-size: 32px; font-weight: 800; color: #1a73e8; }
  .metric-label { font-size: 13px; color: #9098b8; margin-top: 4px; }
  .insight-box {
    background: #1b2838; border-left: 4px solid #1a73e8;
    border-radius: 8px; padding: 16px; margin: 8px 0;
  }
  .tag { display: inline-block; padding: 3px 10px; border-radius: 12px;
         font-size: 11px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ── Helper: auto chart selection (must be defined before page routing) ────────
def _render_auto_chart(df: pd.DataFrame, query: str):
    if df.empty or len(df.columns) < 2:
        return

    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()

    if not num_cols:
        return

    y_col = num_cols[0]
    x_col = cat_cols[0] if cat_cols else df.columns[0]

    q_lower = query.lower()
    if any(w in q_lower for w in ["trend", "monthly", "over time", "by month", "by year"]):
        fig = px.line(df, x=x_col, y=y_col, title="Trend", markers=True,
                      color_discrete_sequence=["#1a73e8"])
    elif any(w in q_lower for w in ["percentage", "split", "share", "proportion", "pie"]):
        fig = px.pie(df, names=x_col, values=y_col, title="Distribution")
    else:
        fig = px.bar(df, x=x_col, y=y_col, title="Result",
                     color=y_col, color_continuous_scale="Blues")

    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.shields.io/badge/Smart%20DW-NL2SQL-blue?style=for-the-badge", width=200)
    st.markdown("---")
    page = st.radio("Navigate", ["🏠 Home", "🔍 Query", "📊 Dashboard", "📜 History"])
    st.markdown("---")
    db_ok = test_connection()
    st.markdown(f"**DB Status:** {'🟢 Connected' if db_ok else '🔴 Disconnected'}")
    st.caption("Olist Brazilian E-Commerce DW")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Home":
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0d1b3e,#1a237e);
                padding:40px;border-radius:16px;margin-bottom:24px;">
      <h1 style="color:white;margin:0;">🧠 Smart Data Warehouse</h1>
      <h3 style="color:#90caf9;margin:8px 0 16px;">Agentic NL2SQL System</h3>
      <p style="color:#b0bec5;max-width:700px;">
        Ask business questions in plain English — a 5-agent AI pipeline
        translates them to SQL, executes on a star-schema MySQL warehouse,
        and returns charts + business insights automatically.
      </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**Dataset**\n\nOlist Brazilian E-Commerce\n112,000+ orders · 2016–2018")
    with col2:
        st.success("**AI Layer**\n\n5-Agent LLM Pipeline\nGPT-4o + Llama 3 fallback")
    with col3:
        st.warning("**Warehouse**\n\nStar Schema MySQL\nfact_sales + 4 dimensions")

    st.markdown("### Architecture")
    st.code("""
User Question (NL)
      ↓
Agent 1: Query Understanding  → extracts intent, filters, metrics
      ↓
Agent 2: NL2SQL Generation    → produces MySQL SELECT query
      ↓
Agent 3: SQL Validation       → safety + schema correctness check
      ↓
Agent 4: Execution            → runs on MySQL, returns DataFrame
      ↓
Agent 5: Insight Generation   → summary + recommendation
      ↓
Streamlit UI                  → charts + table + insights
    """, language="text")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: QUERY
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Query":
    st.title("🔍 Ask Your Business Question")
    st.caption("Type a question in plain English. The AI will generate and run the SQL for you.")

    # Example prompts
    examples = [
        "Show top 10 cities by total revenue",
        "What is the monthly sales trend in 2018?",
        "Which product categories have the highest average review score?",
        "What percentage of orders were delivered late?",
        "Compare revenue by payment type",
        "Show top 5 sellers by number of orders",
        "What is the average delivery time by state?",
    ]
    st.markdown("**Quick examples:**")
    cols = st.columns(4)
    chosen_example = ""
    for i, ex in enumerate(examples):
        if cols[i % 4].button(ex[:35] + "…" if len(ex) > 35 else ex, key=f"ex_{i}"):
            chosen_example = ex

    user_query = st.text_area(
        "Your question:",
        value=chosen_example,
        height=80,
        placeholder="e.g. What are the top 5 product categories by revenue in 2018?",
    )

    col_run, col_clear = st.columns([1, 5])
    run_btn   = col_run.button("▶ Run Query", type="primary", use_container_width=True)
    clear_btn = col_clear.button("✕ Clear", use_container_width=False)

    if clear_btn:
        st.rerun()

    if run_btn and user_query.strip():
        with st.spinner("Running 5-agent pipeline…"):
            result = run_pipeline(user_query.strip())

        if not result.success:
            st.error(f"❌ {result.error_message}")
            st.info("💡 Try rephrasing your question or using one of the example prompts above.")
        else:
            # ── SQL Transparency ──
            with st.expander("🔍 Generated SQL (click to expand)", expanded=False):
                st.code(result.sql, language="sql")
                if result.validation and result.validation.warnings:
                    for w in result.validation.warnings:
                        st.warning(w)
                if result.retry_count > 0:
                    st.caption(f"ℹ️ Required {result.retry_count} retry attempt(s)")

            # ── Intent Details ──
            with st.expander("🧠 Query Intent (Agent 1 output)"):
                st.json(result.intent)

            # ── Results ──
            df = result.data
            st.markdown(f"### Results — {len(df):,} rows ({result.duration_ms}ms)")

            if df.empty:
                st.warning("Query returned no rows. Try different filters.")
            else:
                # ── Auto chart ──
                _render_auto_chart(df, user_query)

                # ── Data table ──
                with st.expander("📋 Raw Data Table", expanded=True):
                    st.dataframe(df, use_container_width=True)
                    csv = df.to_csv(index=False)
                    st.download_button("⬇ Download CSV", csv, "results.csv", "text/csv")

            # ── Insights ──
            if result.insights:
                st.markdown("### 🤖 AI Insights")
                ins = result.insights
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"""<div class="insight-box">
                        <b>📋 Summary</b><br>{ins.get('summary','')}
                    </div>""", unsafe_allow_html=True)
                    st.markdown(f"""<div class="insight-box">
                        <b>📈 Trend</b><br>{ins.get('trend','')}
                    </div>""", unsafe_allow_html=True)
                with col_b:
                    st.markdown(f"""<div class="insight-box">
                        <b>💡 Key Finding</b><br>{ins.get('key_finding','')}
                    </div>""", unsafe_allow_html=True)
                    st.markdown(f"""<div class="insight-box" style="border-color:#00e676;">
                        <b>✅ Recommendation</b><br>{ins.get('recommendation','')}
                    </div>""", unsafe_allow_html=True)

            # Save to history
            if "history" not in st.session_state:
                st.session_state.history = []
            st.session_state.history.append({
                "query": user_query,
                "sql": result.sql,
                "rows": len(result.data) if result.data is not None else 0,
                "duration_ms": result.duration_ms,
            })

    elif run_btn:
        st.warning("Please enter a question first.")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Dashboard":
    st.title("📊 KPI Dashboard")
    engine = get_engine()

    @st.cache_data(ttl=300)
    def get_kpis():
        sql = """
        SELECT
          SUM(payment_value)             AS total_revenue,
          COUNT(DISTINCT order_id)       AS total_orders,
          AVG(delivery_time_days)        AS avg_delivery_days,
          AVG(review_score)              AS avg_review_score,
          SUM(is_late) / COUNT(*) * 100  AS late_pct
        FROM fact_sales
        WHERE order_status = 'delivered'
        """
        with engine.connect() as conn:
            return pd.read_sql(sql, conn)

    @st.cache_data(ttl=300)
    def get_monthly_revenue():
        sql = """
        SELECT dt.year, dt.month,
               SUM(fs.payment_value) AS revenue
        FROM fact_sales fs
        JOIN dim_time dt ON fs.date_key = dt.date_key
        WHERE fs.order_status = 'delivered'
        GROUP BY dt.year, dt.month
        ORDER BY dt.year, dt.month
        """
        with engine.connect() as conn:
            return pd.read_sql(sql, conn)

    @st.cache_data(ttl=300)
    def get_revenue_by_state():
        sql = """
        SELECT dc.customer_state AS state,
               SUM(fs.payment_value) AS revenue,
               COUNT(DISTINCT fs.order_id) AS orders
        FROM fact_sales fs
        JOIN dim_customers dc ON fs.customer_id = dc.customer_id
        GROUP BY dc.customer_state
        ORDER BY revenue DESC
        """
        with engine.connect() as conn:
            return pd.read_sql(sql, conn)

    @st.cache_data(ttl=300)
    def get_top_categories():
        sql = """
        SELECT dp.product_category_name_english AS category,
               SUM(fs.payment_value) AS revenue
        FROM fact_sales fs
        JOIN dim_products dp ON fs.product_id = dp.product_id
        GROUP BY dp.product_category_name_english
        ORDER BY revenue DESC
        LIMIT 10
        """
        with engine.connect() as conn:
            return pd.read_sql(sql, conn)

    if db_ok:
        kpi = get_kpis()
        k = kpi.iloc[0]

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("💰 Total Revenue", f"R${k['total_revenue']:,.0f}")
        c2.metric("📦 Total Orders", f"{k['total_orders']:,}")
        c3.metric("🚚 Avg Delivery", f"{k['avg_delivery_days']:.1f} days")
        c4.metric("⭐ Avg Review", f"{k['avg_review_score']:.2f}/5")
        c5.metric("⏱ Late Orders", f"{k['late_pct']:.1f}%")

        st.markdown("---")
        col_l, col_r = st.columns(2)

        with col_l:
            monthly = get_monthly_revenue()
            monthly["period"] = monthly["year"].astype(str) + "-" + monthly["month"].astype(str).str.zfill(2)
            fig = px.line(monthly, x="period", y="revenue", title="Monthly Revenue Trend",
                          markers=True, color_discrete_sequence=["#1a73e8"])
            fig.update_layout(template="plotly_dark", xaxis_tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            cats = get_top_categories()
            fig2 = px.bar(cats, x="revenue", y="category", orientation="h",
                          title="Top 10 Product Categories by Revenue",
                          color="revenue", color_continuous_scale="Blues")
            fig2.update_layout(template="plotly_dark", yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig2, use_container_width=True)

        states = get_revenue_by_state()
        fig3 = px.bar(states.head(15), x="state", y="revenue",
                      title="Revenue by State (Top 15)",
                      color="revenue", color_continuous_scale="Viridis")
        fig3.update_layout(template="plotly_dark")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.error("Database not connected. Please check your .env configuration.")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: HISTORY
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📜 History":
    st.title("📜 Query History")
    history = st.session_state.get("history", [])
    if not history:
        st.info("No queries run in this session yet. Go to the Query page to get started.")
    else:
        for i, h in enumerate(reversed(history[-50:])):
            with st.expander(f"#{len(history)-i}  {h['query'][:80]}"):
                st.code(h["sql"], language="sql")
                st.caption(f"Rows: {h['rows']} | Duration: {h['duration_ms']}ms")


