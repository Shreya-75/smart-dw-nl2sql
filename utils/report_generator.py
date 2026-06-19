"""
PDF report generator for NL2SQL query results.

Produces a single-page branded PDF containing:
  - Query asked (natural language)
  - Generated SQL
  - Chart image (Plotly → PNG via kaleido)
  - All 4 AI insight cards
  - Metadata: timestamp, row count, duration, provider

Uses fpdf2 (no LaTeX, no Java, pure Python).
Kaleido is used only if available; if not, the chart section is skipped gracefully.
"""
from __future__ import annotations
import io
import textwrap
from datetime import datetime

from fpdf import FPDF, XPos, YPos


_DARK  = (8,  13, 26)      # #080d1a
_BLUE  = (59, 130, 246)    # #3b82f6
_CYAN  = (6,  182, 212)    # #06b6d4
_SLATE = (100,116, 139)    # #64748b
_WHITE = (241,245, 249)    # #f1f5f9
_AMBER = (245,158, 11)     # #f59e0b
_GREEN = (16, 185, 129)    # #10b981


class _PDF(FPDF):
    def header(self):
        # Solid dark background band
        self.set_fill_color(*_DARK)
        self.rect(0, 0, 210, 22, "F")
        # Accent bar
        self.set_fill_color(*_BLUE)
        self.rect(0, 20, 210, 2, "F")
        # Title
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*_WHITE)
        self.set_xy(12, 6)
        self.cell(0, 10, "Smart DW — NL2SQL Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def footer(self):
        self.set_y(-14)
        self.set_fill_color(*_DARK)
        self.rect(0, self.get_y() - 2, 210, 20, "F")
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_SLATE)
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        self.cell(0, 8, f"Generated {ts}  |  Smart Data Warehouse NL2SQL  |  Olist Dataset 2016–2018",
                  align="C")


def _section_title(pdf: _PDF, title: str) -> None:
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*_CYAN)
    pdf.set_fill_color(12, 18, 36)
    pdf.cell(0, 7, f"  {title.upper()}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    pdf.ln(1)


def _body_text(pdf: _PDF, text: str, color=_WHITE) -> None:
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*color)
    pdf.multi_cell(0, 5, text)
    pdf.ln(2)


def _insight_block(pdf: _PDF, label: str, text: str, accent: tuple) -> None:
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*accent)
    pdf.cell(0, 5, label.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_WHITE)
    pdf.multi_cell(0, 5, text or "—")
    pdf.ln(2)


def generate_report(
    query: str,
    sql: str,
    insights: dict,
    row_count: int,
    duration_ms: int,
    provider: str,
    chart_fig=None,     # Plotly figure or None
    retry_count: int = 0,
    confidence: int | None = None,
) -> bytes:
    """
    Build the PDF and return raw bytes suitable for st.download_button.
    """
    pdf = _PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(12, 28, 12)
    pdf.add_page()

    # ── Meta strip ────────────────────────────────────────────────────────────
    pdf.set_fill_color(12, 18, 36)
    pdf.rect(12, 26, 186, 12, "F")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*_SLATE)
    pdf.set_xy(14, 27)
    conf_str = f"  ·  Confidence {confidence}%" if confidence is not None else ""
    pdf.cell(0, 8,
             f"Rows: {row_count}   ·   Duration: {duration_ms/1000:.1f}s"
             f"   ·   Retries: {retry_count}   ·   Provider: {provider}{conf_str}")
    pdf.ln(14)

    # ── Natural language query ────────────────────────────────────────────────
    _section_title(pdf, "Query")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*_WHITE)
    wrapped = "\n".join(textwrap.wrap(query, width=95))
    pdf.multi_cell(0, 6, wrapped)
    pdf.ln(4)

    # ── Chart image ───────────────────────────────────────────────────────────
    if chart_fig is not None:
        try:
            import kaleido  # noqa: F401 — just check it's installed
            img_bytes = chart_fig.to_image(format="png", width=900, height=380, scale=1.5)
            img_buf = io.BytesIO(img_bytes)
            _section_title(pdf, "Chart")
            pdf.image(img_buf, x=12, w=186)
            pdf.ln(4)
        except Exception:
            pass  # kaleido not available — skip chart gracefully

    # ── SQL ───────────────────────────────────────────────────────────────────
    _section_title(pdf, "Generated SQL")
    pdf.set_font("Courier", "", 8)
    pdf.set_text_color(148, 163, 184)  # slate-400
    pdf.set_fill_color(10, 16, 30)
    for line in (sql or "").splitlines():
        if line.strip():
            pdf.cell(0, 5, f"  {line}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    pdf.ln(4)

    # ── AI Insights ───────────────────────────────────────────────────────────
    _section_title(pdf, "AI Insights")
    if insights:
        _insight_block(pdf, "Summary",       insights.get("summary",        ""), _BLUE)
        _insight_block(pdf, "Trend",         insights.get("trend",          ""), _CYAN)
        _insight_block(pdf, "Key Finding",   insights.get("key_finding",    ""), _AMBER)
        _insight_block(pdf, "Recommendation",insights.get("recommendation", ""), _GREEN)

    return bytes(pdf.output())
