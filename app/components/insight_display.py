"""Renders the AI insights panel with color-coded cards."""
import streamlit as st


def render_insights(insights: dict) -> None:
    st.markdown('<div class="section-title">AI Insights</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
        <div class="insight-box insight-box-blue">
            <div class="insight-lbl">Summary</div>
            <div class="insight-text">{insights.get('summary', '—')}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div class="insight-box insight-box-cyan" style="margin-top:14px;">
            <div class="insight-lbl">Trend</div>
            <div class="insight-text">{insights.get('trend', '—')}</div>
        </div>""", unsafe_allow_html=True)

    with col_b:
        st.markdown(f"""
        <div class="insight-box insight-box-amber">
            <div class="insight-lbl">Key Finding</div>
            <div class="insight-text">{insights.get('key_finding', '—')}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div class="insight-box insight-box-green" style="margin-top:14px;">
            <div class="insight-lbl">Recommendation</div>
            <div class="insight-text">{insights.get('recommendation', '—')}</div>
        </div>""", unsafe_allow_html=True)
