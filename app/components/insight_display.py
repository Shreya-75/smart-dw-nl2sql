"""Renders the AI insights panel in the Streamlit UI."""
import streamlit as st


_INSIGHT_CSS = """
<style>
.insight-box {
  background: #1b2838; border-left: 4px solid #1a73e8;
  border-radius: 8px; padding: 16px; margin: 8px 0; color: #e8eaf6;
}
.insight-box.green { border-left-color: #00e676; }
</style>
"""


def render_insights(insights: dict) -> None:
    st.markdown(_INSIGHT_CSS, unsafe_allow_html=True)
    st.markdown("### AI Insights")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""<div class="insight-box">
            <b>📋 Summary</b><br>{insights.get('summary', '')}
        </div>""", unsafe_allow_html=True)
        st.markdown(f"""<div class="insight-box">
            <b>📈 Trend</b><br>{insights.get('trend', '')}
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""<div class="insight-box">
            <b>💡 Key Finding</b><br>{insights.get('key_finding', '')}
        </div>""", unsafe_allow_html=True)
        st.markdown(f"""<div class="insight-box green">
            <b>✅ Recommendation</b><br>{insights.get('recommendation', '')}
        </div>""", unsafe_allow_html=True)
