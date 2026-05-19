"""
Agent 5 — Insight Generation Agent
Converts query results into business-readable summaries and recommendations.
"""
import json
import sys
sys.path.insert(0, ".")
import pandas as pd
from loguru import logger
from utils.llm_client import chat


def generate_insights(user_query: str, sql: str, df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "summary": "The query returned no results.",
            "key_finding": "No data found for the given filters.",
            "trend": "N/A",
            "recommendation": "Try broadening the filters or checking the date range.",
        }

    data_preview = df.head(20).to_markdown(index=False, floatfmt=".2f")
    try:
        stats = df.describe(include="all").to_markdown()
    except Exception:
        stats = ""

    prompt = f"""You are a senior e-commerce business analyst.

The user asked: "{user_query}"

SQL executed:
{sql}

Query result ({len(df)} rows, showing first 20):
{data_preview}

{f"Statistical summary:{chr(10)}{stats}" if stats else ""}

Provide a structured JSON analysis with exactly these keys:
- summary: 2–3 sentences describing what the data shows
- key_finding: The single most important insight in one sentence
- trend: Any notable pattern, growth, decline, or anomaly observed
- recommendation: One specific, actionable business recommendation

Return ONLY valid JSON."""

    content = chat(
        messages=[{"role": "user", "content": prompt}],
        json_mode=True,
        temperature=0.3,
    )

    insights = json.loads(content)
    logger.debug(f"Agent 5 insights: {insights}")
    return insights
