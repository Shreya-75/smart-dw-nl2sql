"""
Generate docs/project_report.pdf using fpdf2.
Run: venv/Scripts/python.exe docs/generate_pdf.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fpdf import FPDF, XPos, YPos

# ── Unicode → ASCII sanitizer ─────────────────────────────────────────────────
_REPLACEMENTS = {
    "—": "--",    # em dash
    "–": "-",     # en dash
    "→": "->",    # right arrow
    "←": "<-",    # left arrow
    "≥": ">=",    # greater-or-equal
    "≤": "<=",    # less-or-equal
    "≠": "!=",    # not equal
    "·": ".",     # middle dot
    "×": "x",     # multiplication sign
    "÷": "/",     # division sign
    "•": "-",     # bullet
    "◦": "o",     # white bullet
    "■": "-",     # black square
    "✓": "OK",    # check mark
    "✕": "X",     # cross
    "²": "^2",    # superscript 2
    "π": "pi",    # pi
    "≈": "~",     # approximately
    "−": "-",     # minus sign
    "é": "e",     # e-acute
    "à": "a",     # a-grave
    "ã": "a",     # a-tilde
    "â": "a",     # a-circumflex
    "ç": "c",     # c-cedilla
    "õ": "o",     # o-tilde
    "ó": "o",     # o-acute
    "í": "i",     # i-acute
    "’": "'",     # right single quotation
    "‘": "'",     # left single quotation
    "“": '"',     # left double quotation
    "”": '"',     # right double quotation
    "…": "...",   # ellipsis
    "→": "->",    # right arrow
    "←": "<-",    # left arrow
    "®": "(R)",   # registered
    "©": "(C)",   # copyright
    "™": "(TM)",  # trademark
    "♣": "*",     # suit
    "♥": "*",
    "♠": "*",
    "♦": "*",
    "ł": "l",     # l with stroke
    "Ł": "L",
    "№": "No.",   # numero sign
    "°": " deg",  # degree
    "±": "+/-",   # plus-minus
    "▶": ">",     # right triangle
    "●": "-",     # black circle
    " ": " ",     # non-breaking space
    "«": "<<",    # left guillemet
    "»": ">>",    # right guillemet
    "—": "--",    # em dash (duplicate safety)
    "‹": "<",
    "›": ">",
    "⁰": "^0",
    "³": "^3",
    "´": "'",
    "µ": "u",     # micro
    "¶": "P",     # pilcrow
    "¼": "1/4",
    "½": "1/2",
    "¾": "3/4",
    "Ø": "O",
    "ø": "o",
    "æ": "ae",
    "Æ": "AE",
    "ß": "ss",
    "↑": "^",     # up arrow
    "↓": "v",     # down arrow
    "↔": "<->",   # left-right arrow
    "⇒": "=>",    # double right arrow
    "∅": "{}",    # empty set
    "∈": "in",    # element of
    "∉": "not in",
    "∞": "inf",   # infinity
    "∧": "and",
    "∨": "or",
    "¬": "not",   # logical not
    "′": "'",     # prime
    "″": "''",    # double prime
    "℃": "C",     # celsius
    "℉": "F",     # fahrenheit
    "∑": "sum",   # summation
    "∏": "prod",  # product
    "√": "sqrt",  # square root
    "∫": "int",   # integral
    "∂": "d",     # partial diff
    "∇": "grad",  # nabla
    "Δ": "Delta",
    "α": "alpha",
    "β": "beta",
    "γ": "gamma",
    "λ": "lambda",
    "μ": "mu",
    "σ": "sigma",
    "θ": "theta",
    "ε": "epsilon",
    "̂": "",      # combining circumflex (skip)
    "​": "",      # zero-width space
    "\u200E": "",      # left-to-right mark
    "\u200F": "",      # right-to-left mark
    "﻿": "",      # BOM
    " ": " ",     # thin space
    " ": " ",     # narrow no-break space
    "⁠": "",      # word joiner
    "‐": "-",     # hyphen
    "‑": "-",     # non-breaking hyphen
    "‒": "-",     # figure dash
    # R-squared and math
    "¹": "^1",
    "⁴": "^4",
    "⁵": "^5",
    "⁶": "^6",
    "⁷": "^7",
    "⁸": "^8",
    "⁹": "^9",
    # Special math
    "≈": "~=",
    "∝": "~",
    # ℹ
    "ℹ": "i",
    # circled letters
    "Ⓐ": "(A)",
    "Ⓑ": "(B)",
    # check and cross box
    "☐": "[ ]",
    "☑": "[x]",
    "☒": "[X]",
}

def _safe(txt: str) -> str:
    """Replace all non-Latin-1 characters with ASCII equivalents."""
    if not txt:
        return ""
    for char, repl in _REPLACEMENTS.items():
        txt = txt.replace(char, repl)
    # Final fallback: encode to latin-1, replacing anything still unmappable
    return txt.encode("latin-1", errors="replace").decode("latin-1")

# ── Palette ───────────────────────────────────────────────────────────────────
BLUE   = (59,  130, 246)
CYAN   = (6,   182, 212)
AMBER  = (245, 158, 11)
GREEN  = (16,  185, 129)
RED    = (239, 68,  68)
DARK   = (15,  23,  42)
SLATE  = (100, 116, 139)
LIGHT  = (241, 245, 249)
WHITE  = (255, 255, 255)
BLACK  = (0,   0,   0)
CODEBG = (15,  23,  42)
CODEFG = (226, 232, 240)
HEADBG = (30,  41,  59)

OUT = Path(__file__).parent / "project_report.pdf"


class Report(FPDF):
    # ── internals ────────────────────────────────────────────────────────────
    def __init__(self):
        super().__init__("P", "mm", "A4")
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(22, 20, 22)
        self._chapter_num = 0
        self._toc: list[tuple[str, int]] = []   # (title, page)

    # ── header / footer ──────────────────────────────────────────────────────
    def header(self):
        if self.page <= 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*SLATE)
        self.cell(0, 6, _safe("Smart Data Warehouse & Agentic NL2SQL System"), align="L")
        self.cell(0, 6, "Shreya Ghatage", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*BLUE)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

    def footer(self):
        if self.page <= 1:
            return
        self.set_y(-16)
        self.set_draw_color(*BLUE)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*SLATE)
        self.cell(0, 6, str(self.page), align="C")

    # ── auto-sanitize every text output ──────────────────────────────────────
    def cell(self, *args, **kwargs):
        if args and isinstance(args[0], (int, float)):
            # signature: cell(w, h=0, txt='', ...)
            if len(args) > 2 and isinstance(args[2], str):
                args = list(args); args[2] = _safe(args[2]); args = tuple(args)
        if "txt" in kwargs:
            kwargs["txt"] = _safe(kwargs["txt"])
        if "text" in kwargs:
            kwargs["text"] = _safe(kwargs["text"])
        super().cell(*args, **kwargs)

    def multi_cell(self, *args, **kwargs):
        if args and isinstance(args[0], (int, float)):
            if len(args) > 2 and isinstance(args[2], str):
                args = list(args); args[2] = _safe(args[2]); args = tuple(args)
        if "txt" in kwargs:
            kwargs["txt"] = _safe(kwargs["txt"])
        if "text" in kwargs:
            kwargs["text"] = _safe(kwargs["text"])
        super().multi_cell(*args, **kwargs)

    # ── helpers ───────────────────────────────────────────────────────────────
    def _w(self) -> float:
        return self.w - self.l_margin - self.r_margin

    def _color(self, rgb):
        self.set_text_color(*rgb)

    def h1(self, txt: str):
        self._chapter_num += 1
        txt = _safe(txt)
        label = f"Chapter {self._chapter_num}: {txt}"
        self._toc.append((label, self.page))
        self.set_font("Helvetica", "B", 18)
        self._color(BLUE)
        self.set_fill_color(*HEADBG)
        self.rect(self.l_margin, self.get_y(), self._w(), 12, "F")
        self.cell(self._w(), 12, f"{self._chapter_num}.  {txt}",
                  align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._color(BLACK)
        self.ln(4)

    def h2(self, txt: str):
        txt = _safe(txt)
        self.set_font("Helvetica", "B", 13)
        self._color(BLUE)
        self.ln(3)
        self.cell(0, 8, txt, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*BLUE)
        self.set_line_width(0.4)
        y = self.get_y()
        self.line(self.l_margin, y, self.l_margin + self._w() * 0.55, y)
        self._color(BLACK)
        self.ln(3)

    def h3(self, txt: str):
        txt = _safe(txt)
        self.set_font("Helvetica", "B", 11)
        self._color(CYAN)
        self.ln(2)
        self.cell(0, 7, txt, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._color(BLACK)
        self.ln(1)

    def body(self, txt: str, indent: float = 0):
        txt = _safe(txt)
        self.set_font("Helvetica", "", 10)
        self._color(DARK)
        if indent:
            self.set_x(self.l_margin + indent)
        self.multi_cell(self._w() - indent, 5.5, txt,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def bullet(self, txt: str, level: int = 1):
        txt = _safe(txt)
        self.set_font("Helvetica", "", 10)
        self._color(DARK)
        indent = 6 * level
        bullet_char = "-" if level == 1 else "o"
        self.set_x(self.l_margin + indent)
        self.cell(5, 5.5, bullet_char)
        self.multi_cell(self._w() - indent - 5, 5.5, txt,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def code(self, txt: str, caption: str = ""):
        txt = _safe(txt)
        caption = _safe(caption)
        self.ln(2)
        if caption:
            self.set_font("Helvetica", "I", 8.5)
            self._color(SLATE)
            self.cell(0, 5, caption, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # measure height
        self.set_font("Courier", "", 8.5)
        lines = txt.split("\n")
        h_block = len(lines) * 4.8 + 6
        # background
        self.set_fill_color(*CODEBG)
        self.set_draw_color(*BLUE)
        self.set_line_width(0.3)
        bx, by = self.l_margin, self.get_y()
        self.rect(bx, by, self._w(), h_block, "FD")
        self.set_y(by + 3)
        self.set_text_color(*CODEFG)
        for line in lines:
            self.set_x(self.l_margin + 3)
            self.cell(self._w() - 6, 4.8, line[:110],
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._color(BLACK)
        self.ln(4)

    def table(self, headers: list[str], rows: list[list[str]],
              col_widths: list[float] | None = None):
        headers = [_safe(h) for h in headers]
        rows = [[_safe(str(c)) for c in row] for row in rows]
        self.ln(2)
        n = len(headers)
        if col_widths is None:
            col_widths = [self._w() / n] * n
        # header row
        self.set_fill_color(*HEADBG)
        self.set_draw_color(*BLUE)
        self.set_line_width(0.25)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*CYAN)
        for i, (h, w) in enumerate(zip(headers, col_widths)):
            self.cell(w, 7, h, border=1, fill=True)
        self.ln()
        # data rows
        self.set_font("Helvetica", "", 9)
        for ri, row in enumerate(rows):
            bg = (28, 38, 58) if ri % 2 == 0 else (20, 30, 48)
            self.set_fill_color(*bg)
            self.set_text_color(*LIGHT)
            # measure max height for multi-line cells
            max_lines = 1
            for cell_txt, w in zip(row, col_widths):
                chars_per_line = int(w / 1.9)
                cell_lines = 1
                for word_chunk in str(cell_txt).split("\n"):
                    cell_lines += max(1, len(word_chunk) // max(1, chars_per_line))
                max_lines = max(max_lines, cell_lines)
            row_h = max(6, max_lines * 5)
            x0 = self.l_margin
            y0 = self.get_y()
            if y0 + row_h > self.h - self.b_margin - 5:
                self.add_page()
                # re-draw header
                self.set_fill_color(*HEADBG)
                self.set_font("Helvetica", "B", 9)
                self.set_text_color(*CYAN)
                for h, w in zip(headers, col_widths):
                    self.cell(w, 7, h, border=1, fill=True)
                self.ln()
                self.set_font("Helvetica", "", 9)
                x0, y0 = self.l_margin, self.get_y()
                self.set_fill_color(*bg)
                self.set_text_color(*LIGHT)
            for cell_txt, w in zip(row, col_widths):
                self.set_xy(x0, y0)
                self.multi_cell(w, row_h / max_lines, str(cell_txt),
                                border=1, fill=True,
                                new_x=XPos.RIGHT, new_y=YPos.TOP)
                x0 += w
            self.set_y(y0 + row_h)
        self._color(BLACK)
        self.ln(4)

    def divider(self):
        self.ln(3)
        self.set_draw_color(*BLUE)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y(),
                  self.w - self.r_margin, self.get_y())
        self.ln(4)

    def badge(self, txt: str, rgb=None):
        if rgb is None:
            rgb = BLUE
        self.set_font("Helvetica", "B", 8.5)
        self.set_fill_color(*rgb)
        self.set_text_color(*WHITE)
        tw = self.get_string_width(txt) + 5
        self.cell(tw, 5.5, txt, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_text_color(*BLACK)
        self.ln(7)

    def info_box(self, label: str, txt: str, rgb=None):
        label = _safe(label)
        txt = _safe(txt)
        if rgb is None:
            rgb = BLUE
        self.ln(2)
        self.set_fill_color(rgb[0] // 5, rgb[1] // 5, rgb[2] // 5)
        self.set_draw_color(*rgb)
        self.set_line_width(0.5)
        bx, by = self.l_margin, self.get_y()
        # estimate height
        self.set_font("Helvetica", "", 9.5)
        line_h = 5
        text_w = self._w() - 8
        lines = []
        for para in txt.split("\n"):
            if not para.strip():
                lines.append("")
                continue
            words, cur = para.split(), ""
            for w in words:
                test = (cur + " " + w).strip()
                if self.get_string_width(test) < text_w:
                    cur = test
                else:
                    if cur:
                        lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
        h_block = (len(lines) + 1) * line_h + 14
        self.rect(bx, by, self._w(), h_block, "FD")
        self.set_x(bx + 4)
        self.set_y(by + 4)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*rgb)
        self.cell(0, 5.5, f"[i]  {label}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*LIGHT)
        self.set_x(bx + 4)
        self.multi_cell(self._w() - 8, line_h, txt,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(by + h_block + 2)
        self._color(BLACK)
        self.ln(2)


# ═════════════════════════════════════════════════════════════════════════════
def build(pdf: Report):

    # ─────────────────────────────────── TITLE PAGE ──────────────────────────
    pdf.add_page()
    pdf.set_y(30)

    # dark header bar
    pdf.set_fill_color(*HEADBG)
    pdf.rect(0, 20, pdf.w, 55, "F")
    pdf.set_y(28)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*BLUE)
    pdf.cell(0, 14, "Smart Data Warehouse &", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 14, "Agentic NL2SQL System", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "I", 13)
    pdf.set_text_color(*CYAN)
    pdf.cell(0, 9, "Full Technical Project Report", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)


    pdf.set_y(90)
    pdf.set_draw_color(*BLUE)
    pdf.set_line_width(0.8)
    pdf.line(pdf.l_margin + 20, pdf.get_y(), pdf.w - pdf.r_margin - 20, pdf.get_y())
    pdf.ln(10)

    # subtitle box
    pdf.set_fill_color(*HEADBG)
    pdf.set_draw_color(*CYAN)
    pdf.set_line_width(0.5)
    pdf.rect(pdf.l_margin + 10, pdf.get_y(), pdf._w() - 20, 18, "FD")
    pdf.set_y(pdf.get_y() + 4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*CYAN)
    pdf.cell(0, 5, "Olist Brazilian E-Commerce  |  MySQL 8.0  |  5-Agent AI Pipeline",
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*LIGHT)
    pdf.cell(0, 5, "99,441 orders  |  Star-schema warehouse  |  ReAct agentic loop  |  10 advanced features",
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(18)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*LIGHT)
    pdf.cell(0, 8, "Shreya Ghatage", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 6, "IIT Madras — Data Science Programme", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, "22f3000165@ds.study.iitm.ac.in", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(16)
    pdf.set_draw_color(*BLUE)
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin + 30, pdf.get_y(), pdf.w - pdf.r_margin - 30, pdf.get_y())
    pdf.ln(10)

    meta = [
        ("Branch",  "develop"),
        ("Commits", "15 (spanning full development arc)"),
        ("Tests",   "54 passing"),
        ("Date",    "June 2026"),
    ]
    for k, v in meta:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*BLUE)
        pdf.cell(35, 6, k + ":", align="R")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*LIGHT)
        pdf.cell(0, 6, v, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(-30)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 5,
             "Built with Python 3.11 · MySQL 8.0 · Ollama · Groq · Streamlit · Plotly · FastAPI",
             align="C")

    # ─────────────────────────────────── ABSTRACT ────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*BLUE)
    pdf.cell(0, 10, "Abstract", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.divider()
    pdf.body(
        "This report documents the complete end-to-end development of the Smart Data Warehouse "
        "NL2SQL System — an agentic artificial intelligence platform that converts natural-language "
        "business questions into executable SQL, runs them against a production-grade MySQL 8.0 "
        "star-schema data warehouse, and returns interactive charts alongside LLM-generated business insights."
    )
    pdf.body(
        "The project is built on the Olist Brazilian E-Commerce dataset (2016–2018), comprising "
        "99,441 orders across 27 Brazilian states and nine raw CSV files. A production-grade ETL pipeline "
        "transforms the raw data into a Kimball-style star schema with one fact table (fact_sales) and "
        "four dimension tables, incorporating seven derived features including delivery time, delay days, "
        "and a binary late-delivery flag."
    )
    pdf.body(
        "The AI core is a five-agent sequential pipeline evolved into a ReAct-style agentic loop: "
        "Agent 1 parses intent, Agent 2 generates SQL, Agent 3 validates safety and schema correctness, "
        "Agent 4 executes against MySQL, and Agent 5 generates business insights. A dedicated Reflection "
        "Agent classifies failures, diagnoses root causes, and plans targeted recovery strategies between "
        "attempts — replacing raw error passthrough with structured reasoning."
    )
    pdf.body(
        "The user-facing Streamlit application provides four pages (Query, Dashboard, History, Admin), "
        "supplemented by ten major feature upgrades: multi-turn conversational memory, Brazil geospatial "
        "bubble maps, time-series forecasting, PDF report export, a FastAPI REST endpoint, RFM customer "
        "segmentation, confidence scoring, semantic query caching, voice input, and multi-LLM benchmarking."
    )
    pdf.body(
        "The project demonstrates a complete data engineering lifecycle — from raw CSV ingestion "
        "through multi-layer cleaning, star-schema warehousing, agentic AI, and a polished product-quality "
        "UI — in approximately 4,000 lines of Python across 30+ modules."
    )

    # ─────────────────────────────── CHAPTER 1: INTRODUCTION ─────────────────
    pdf.add_page()
    pdf.h1("Introduction")
    pdf.h2("1.1  Problem Statement")
    pdf.body(
        "Business users need answers from data warehouses but lack SQL expertise. Traditional BI tools "
        "require either pre-built dashboards (inflexible) or direct SQL access (inaccessible). Large "
        "Language Models can generate SQL from natural language, but naive single-LLM approaches suffer "
        "from hallucination, schema mismatch, and unsafe queries."
    )
    pdf.body(
        "The core challenge: build a system that is simultaneously accurate (generates correct SQL for "
        "a specific schema), safe (never executes destructive statements), robust (recovers from LLM "
        "errors automatically), and accessible (usable by non-technical stakeholders via a polished UI)."
    )
    pdf.h2("1.2  Project Objectives")
    objectives = [
        "Design and populate a production-grade MySQL star-schema warehouse from the Olist E-Commerce dataset.",
        "Build a multi-agent NL2SQL pipeline with five specialised agents.",
        "Evolve the pipeline into a genuine agentic loop using the ReAct pattern with failure reflection.",
        "Deliver a polished multi-page Streamlit UI with real-time charts, AI insights, and query history.",
        "Expose the pipeline as a documented REST API (FastAPI).",
        "Add ten advanced features demonstrating data science, ML, and product engineering depth.",
    ]
    for obj in objectives:
        pdf.bullet(obj)
    pdf.h2("1.3  Significance")
    pdf.body(
        "This project sits at the intersection of three currently active research and engineering areas: "
        "Text-to-SQL (NL2SQL), agentic AI systems (multi-step LLM orchestration with self-correction), "
        "and analytical data warehousing (Kimball star schema, ETL, performance indexing). The combination "
        "produces a system that is both academically grounded and production-realistic."
    )

    # ─────────────────────────────── CHAPTER 2: DATASET ─────────────────────
    pdf.add_page()
    pdf.h1("Dataset: Olist Brazilian E-Commerce")
    pdf.h2("2.1  Overview")
    pdf.body(
        "The Olist dataset is a publicly available real-world e-commerce dataset from Brazil's largest "
        "online marketplace. It covers orders placed between September 2016 and October 2018 and is "
        "released under a Creative Commons licence. Nine CSV files are provided."
    )
    pdf.table(
        ["File", "Contents", "Rows"],
        [
            ["olist_orders_dataset.csv",          "Order headers: status, timestamps",     "99,441"],
            ["olist_order_items_dataset.csv",      "Per-item price, freight, seller",       "112,650"],
            ["olist_order_payments_dataset.csv",   "Payment type, instalment, value",       "103,886"],
            ["olist_order_reviews_dataset.csv",    "Customer review scores & text",         "99,224"],
            ["olist_customers_dataset.csv",        "Customer city, state, zip code",        "99,441"],
            ["olist_sellers_dataset.csv",          "Seller city, state, zip code",          "3,095"],
            ["olist_products_dataset.csv",         "Category, dimensions, weight",          "32,951"],
            ["olist_geolocation_dataset.csv",      "Zip → lat/lon mappings",           "1,000,163"],
            ["product_category_name_translation.csv", "Portuguese→English labels",     "71"],
        ],
        col_widths=[72, 72, 22],
    )
    pdf.h2("2.2  Key Metrics (Delivered Orders)")
    pdf.table(
        ["Metric", "Value"],
        [
            ["Total delivered orders",      "~96,000"],
            ["Total revenue",               "R$ 16.0M+"],
            ["Unique customers",            "~96,000"],
            ["Unique sellers",              "3,095"],
            ["Product categories (English)","74"],
            ["Brazilian states covered",    "27"],
            ["Date range",                  "Sept 2016 – Oct 2018"],
            ["Average review score",        "4.07 / 5"],
            ["Average delivery time",       "~12 days"],
            ["Late delivery rate",          "~7%"],
        ],
        col_widths=[95, 71],
    )
    pdf.h2("2.3  Data Quality Issues")
    issues = [
        "Typos in column names: product_name_lenght → product_name_length (corrected in cleaning).",
        "~610 products had no Portuguese category name; filled as 'unknown' post-merge.",
        "Orders with null order_delivered_customer_date produce NaN delivery times; handled with pd.to_datetime(errors='coerce').",
        "Some orders had multiple payment records (instalment rows); aggregated to primary type and total value at order level.",
        "Geolocation CSV (1M rows) was not used in the warehouse (redundant with state/city columns); excluded from ETL.",
    ]
    for i in issues:
        pdf.bullet(i)

    # ─────────────────────────────── CHAPTER 3: ARCHITECTURE ─────────────────
    pdf.add_page()
    pdf.h1("System Architecture")
    pdf.h2("3.1  High-Level Design")
    pdf.body(
        "The system follows a layered architecture with four distinct tiers. Each tier communicates "
        "only with its immediate neighbour, ensuring clean separation of concerns."
    )
    tiers = [
        ("Tier 4 — UI", "Streamlit Multi-Page UI (4 pages) + FastAPI REST"),
        ("Tier 3 — AI", "5-Agent NL2SQL Pipeline + Reflection Agent (ReAct loop)"),
        ("Tier 2 — SQL", "SQL Validation + MySQL Execution Engine"),
        ("Tier 1 — Data", "MySQL 8.0 Star-Schema Warehouse (5 tables)"),
        ("Tier 0 — ETL", "ETL Pipeline: 9 Olist CSVs → Warehouse"),
    ]
    for tier, desc in tiers:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*CYAN)
        pdf.cell(42, 6, tier)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 6, desc, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.h2("3.2  Technology Stack")
    pdf.table(
        ["Layer", "Technology", "Purpose"],
        [
            ["LLM (local)",   "Ollama + Llama 3 / Mistral",    "Private, zero-cost inference"],
            ["LLM (cloud)",   "Groq API + llama3-70b",         "Fast cloud inference (free tier)"],
            ["Database",      "MySQL 8.0",                     "Star-schema warehouse"],
            ["ORM / SQL",     "SQLAlchemy 2.0 + PyMySQL",      "Connection pooling, safe query execution"],
            ["Data wrangling","Pandas 2.2 + NumPy 1.26",       "ETL transformations, feature engineering"],
            ["Web UI",        "Streamlit 1.35",                "Multi-page interactive app"],
            ["REST API",      "FastAPI + Uvicorn",             "Programmatic pipeline access"],
            ["Charts",        "Plotly 5.22",                   "Interactive visualisations"],
            ["ML",            "scikit-learn",                  "Forecasting, RFM clustering"],
            ["Validation",    "sqlparse 0.5 + regex",          "SQL safety checks"],
            ["Retry",         "tenacity 3.x",                  "Exponential-backoff DB retries"],
            ["Logging",       "loguru 0.7",                    "Structured JSONL query log"],
            ["PDF export",    "fpdf2",                         "Branded PDF report generation"],
            ["Cache",         "sklearn TF-IDF",                "Semantic query similarity cache"],
            ["Testing",       "pytest 8.2 + pytest-cov",       "Unit + integration test suite"],
        ],
        col_widths=[38, 52, 76],
    )

    # ─────────────────────────────── CHAPTER 4: DATABASE ─────────────────────
    pdf.add_page()
    pdf.h1("Database Design: Star Schema")
    pdf.h2("4.1  Design Philosophy")
    pdf.body(
        "The warehouse follows the Kimball Dimensional Modelling approach: a central fact table "
        "recording transactional events, surrounded by denormalised dimension tables. This design "
        "optimises for analytical queries (GROUP BY, aggregations, date-range slices) at the expense "
        "of write normalisation — appropriate for a read-heavy analytical workload."
    )
    pdf.h2("4.2  Star Schema Tables")
    pdf.h3("Fact Table: fact_sales")
    pdf.body("One row per order-item. Records all measurable business events.")
    pdf.code(
        "CREATE TABLE fact_sales (\n"
        "  fact_id              BIGINT AUTO_INCREMENT PRIMARY KEY,\n"
        "  order_id             VARCHAR(36) NOT NULL,\n"
        "  customer_id          VARCHAR(36),   -- FK -> dim_customers\n"
        "  product_id           VARCHAR(36),   -- FK -> dim_products\n"
        "  seller_id            VARCHAR(36),   -- FK -> dim_sellers\n"
        "  date_key             INT,           -- FK -> dim_time (YYYYMMDD)\n"
        "  order_status         VARCHAR(20),\n"
        "  payment_type         VARCHAR(20),\n"
        "  payment_value        DECIMAL(10,2),\n"
        "  review_score         TINYINT,\n"
        "  delivery_time_days   DECIMAL(6,2),  -- DERIVED feature\n"
        "  delay_days           DECIMAL(6,2),  -- positive = late\n"
        "  is_late              TINYINT(1),    -- DERIVED binary flag\n"
        "  approval_time_hours  DECIMAL(8,2)   -- DERIVED feature\n"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;",
        "fact_sales DDL",
    )
    pdf.h3("Dimension Tables")
    pdf.table(
        ["Table", "Purpose", "Rows", "Key Columns"],
        [
            ["dim_time",      "Calendar dimension",       "~750",   "year, month, quarter, day_of_week"],
            ["dim_customers", "Customer geography",        "99,441", "customer_state, customer_city"],
            ["dim_products",  "Product attributes + EN category","32,951","category_name_english"],
            ["dim_sellers",   "Seller geography",          "3,095",  "seller_state, seller_city"],
        ],
        col_widths=[34, 44, 22, 66],
    )
    pdf.h2("4.3  Indexing Strategy")
    pdf.body(
        "MySQL 8.0 enforces ONLY_FULL_GROUP_BY mode. Composite indexes were chosen to support the "
        "most common analytical patterns."
    )
    pdf.code(
        "CREATE INDEX idx_fact_date_cust  ON fact_sales(date_key, customer_id);\n"
        "CREATE INDEX idx_fact_product    ON fact_sales(product_id, payment_value);\n"
        "CREATE INDEX idx_fact_seller     ON fact_sales(seller_id, review_score);\n"
        "CREATE INDEX idx_time_year_month ON dim_time(year, month);\n"
        "CREATE INDEX idx_cust_state_city ON dim_customers(customer_state, customer_city);",
        "Composite indexes",
    )

    # ─────────────────────────────── CHAPTER 5: ETL ──────────────────────────
    pdf.add_page()
    pdf.h1("ETL Pipeline")
    pdf.h2("5.1  Pipeline Stages")
    pdf.body("Five sequential stages, each a dedicated Python module under etl/.")
    stages = [
        ("Stage 1 — Ingestion",        "data_ingestion.py",        "Reads all 9 Olist CSVs into a dict of DataFrames"),
        ("Stage 2 — Cleaning",          "data_cleaning.py",         "Dedup, datetime parse, string normalisation, typo fix, category translation"),
        ("Stage 3 — Integration",       "data_integration.py",      "Joins orders, items, payments, reviews into a master order-level DataFrame"),
        ("Stage 4 — Feature Engineering","feature_engineering.py",  "Derives delivery_time_days, delay_days, is_late, approval_time_hours"),
        ("Stage 5 — Loading",           "data_loading.py",          "FK-safe TRUNCATE then INSERT into star schema tables"),
    ]
    for stage, module, desc in stages:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*CYAN)
        pdf.cell(60, 6, stage)
        pdf.set_font("Courier", "", 8.5)
        pdf.set_text_color(*AMBER)
        pdf.cell(48, 6, module)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 6, desc, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.h2("5.2  Feature Engineering")
    pdf.body("Four business-critical features derived from timestamp arithmetic:")
    pdf.code(
        "df['delivery_time_days'] = (\n"
        "    (df['order_delivered_customer_date']\n"
        "     - df['order_purchase_timestamp'])\n"
        "    .dt.total_seconds() / 86400\n"
        ").round(2)\n"
        "\n"
        "df['delay_days'] = (\n"
        "    (df['order_delivered_customer_date']\n"
        "     - df['order_estimated_delivery_date'])\n"
        "    .dt.total_seconds() / 86400\n"
        ").round(2)    # positive = late, negative = early\n"
        "\n"
        "df['is_late']            = (df['delay_days'] > 0).astype(int)\n"
        "df['approval_time_hours'] = (\n"
        "    (df['order_approved_at'] - df['order_purchase_timestamp'])\n"
        "    .dt.total_seconds() / 3600\n"
        ").round(2)",
        "Derived feature computation (feature_engineering.py)",
    )
    pdf.h2("5.3  FK-Safe Re-load Pattern")
    pdf.info_box(
        "Critical Bug Fix — Commit 62397d8",
        "Using if_exists='replace' dropped and recreated dimension tables, causing FK constraint "
        "violations on the fact table. Fix: disable FK checks, truncate all tables (fact first), "
        "re-enable, then re-insert. This makes ETL runs idempotent.",
        RED,
    )
    pdf.code(
        "conn.execute(text('SET FOREIGN_KEY_CHECKS=0'))\n"
        "for t in ['fact_sales','dim_customers','dim_products','dim_sellers','dim_time']:\n"
        "    conn.execute(text(f'TRUNCATE TABLE {t}'))\n"
        "conn.execute(text('SET FOREIGN_KEY_CHECKS=1'))\n"
        "# then insert dims, then fact",
        "FK-safe truncate pattern",
    )

    # ─────────────────────────────── CHAPTER 6: AGENTS ───────────────────────
    pdf.add_page()
    pdf.h1("Multi-Agent NL2SQL Pipeline")
    pdf.h2("6.1  Design Philosophy")
    pdf.body(
        "Each agent has exactly one responsibility, receives a typed input, and returns a typed output. "
        "No agent knows about agents after it. The pipeline orchestrator is the only component that "
        "sees the full state. This separation of concerns enables the ReAct agentic loop."
    )
    pdf.h2("6.2  Agent 1 — Query Understanding")
    pdf.body(
        "Input: Raw natural-language question.  Output: Structured JSON intent dict. Agent 1 sends "
        "the question to the LLM with a zero-shot prompt specifying the exact JSON schema to produce."
    )
    pdf.code(
        '{\n'
        '  "intent":    "aggregation | trend | comparison | lookup | ranking",\n'
        '  "metric":    "revenue | orders | review_score | delivery_time_days",\n'
        '  "dimension": "customer_state | product_category_name_english | ...",\n'
        '  "filters":   {"year": 2018, "order_status": "delivered"},\n'
        '  "limit":     5,\n'
        '  "sort_order": "DESC",\n'
        '  "time_grain": "monthly | quarterly | annual | null"\n'
        '}',
        "Intent JSON schema",
    )
    pdf.h2("6.3  Agent 2 — NL2SQL Generation")
    pdf.body(
        "Input: Intent JSON + original question + optional reflection feedback. "
        "Output: Raw MySQL SELECT statement. The system prompt explicitly enforces "
        "MySQL 8.0's ONLY_FULL_GROUP_BY rules with WRONG/CORRECT examples."
    )
    pdf.code(
        "-- WRONG (fails on MySQL 8.0 with Error 1055):\n"
        "SELECT dt.full_date, SUM(fs.payment_value) AS revenue\n"
        "FROM fact_sales fs JOIN dim_time dt ON fs.date_key=dt.date_key\n"
        "GROUP BY YEAR(dt.full_date), MONTH(dt.full_date)\n"
        "\n"
        "-- CORRECT:\n"
        "SELECT dt.year, dt.month,\n"
        "       CONCAT(dt.year,'-',LPAD(dt.month,2,'0')) AS month_label,\n"
        "       ROUND(SUM(fs.payment_value),0) AS revenue\n"
        "FROM fact_sales fs JOIN dim_time dt ON fs.date_key=dt.date_key\n"
        "GROUP BY dt.year, dt.month\n"
        "ORDER BY dt.year, dt.month ASC",
        "ONLY_FULL_GROUP_BY enforcement examples in SQL agent prompt",
    )
    pdf.h2("6.4  Agent 3 — SQL Validation")
    pdf.body(
        "Input: SQL string.  Output: ValidationResult(is_valid, errors, warnings). "
        "Purely rule-based — no LLM call. This agent enforces:"
    )
    rules = [
        "Forbidden keyword check: regex blocks DELETE, DROP, UPDATE, INSERT, TRUNCATE, ALTER, EXEC, GRANT, CREATE.",
        "SELECT-only: query must begin with SELECT after stripping whitespace.",
        "sqlparse syntax: verifies the query parses without error.",
        "Table allowlist: any table not in {fact_sales, dim_customers, dim_products, dim_sellers, dim_time} is rejected.",
        "Complexity warnings: >5 JOINs or >2 subqueries trigger advisory warnings (non-blocking).",
    ]
    for r in rules:
        pdf.bullet(r)
    pdf.h2("6.5  Agent 4 — SQL Execution")
    pdf.body(
        "Input: Validated SQL.  Output: pd.DataFrame. Executed with tenacity retry "
        "(3 attempts, exponential backoff). A per-session timeout is applied via SET SESSION MAX_EXECUTION_TIME."
    )
    pdf.code(
        "@retry(stop=stop_after_attempt(3),\n"
        "       wait=wait_exponential(multiplier=1, min=1, max=4),\n"
        "       reraise=True)\n"
        "def execute_query(sql: str) -> pd.DataFrame:\n"
        "    with engine.connect() as conn:\n"
        "        conn.execute(text('SET SESSION MAX_EXECUTION_TIME=30000'))\n"
        "        result = conn.execute(text(sql))  # text() prevents % format errors\n"
        "        return pd.DataFrame(result.fetchall(),\n"
        "                            columns=list(result.keys()))",
        "Execution agent with retry (execution_agent.py)",
    )
    pdf.h2("6.6  Agent 5 — Insight Generation")
    pdf.body(
        "Input: Original question + SQL + top-20 rows of DataFrame (markdown table). "
        "Output: Dict with four keys: summary, key_finding, trend, recommendation. "
        "Acts as a senior e-commerce business analyst with temperature=0.3."
    )

    # ─────────────────────────────── CHAPTER 7: AGENTIC LOOP ─────────────────
    pdf.add_page()
    pdf.h1("ReAct Agentic Loop & Reflection Agent")
    pdf.h2("7.1  From Linear to Agentic")
    pdf.body(
        "The original pipeline was a simple for-loop: Agent 1 ran once, raw error strings "
        "were passed back to Agent 2, and empty results were silently accepted. Four problems were "
        "identified: (1) wrong intent never corrected, (2) cryptic MySQL errors not actionable, "
        "(3) 0-row results silently accepted, (4) no reasoning between attempts."
    )
    pdf.h2("7.2  ReAct Pattern")
    pdf.body(
        "The upgraded pipeline implements Observe → Reason → Act each iteration. "
        "After any failure, the Reflection Agent classifies the error, diagnoses root cause, "
        "and returns a structured fix instruction to Agent 2 (or an intent revision request to Agent 1)."
    )
    pdf.h2("7.3  Reflection Agent — 8 Error Categories")
    pdf.table(
        ["Error Type", "Fix Strategy"],
        [
            ["group_by_violation", "Use dt.year/dt.month (INT columns) in GROUP BY, never YEAR(col)"],
            ["unknown_column",     "Replace hallucinated column name with schema-verified equivalent; revise intent"],
            ["syntax_error",       "Rewrite from scratch; check commas, parentheses, JOIN syntax"],
            ["table_not_found",    "Replace invalid table with one of the 5 known tables"],
            ["query_timeout",      "Add WHERE order_status='delivered' filter; add LIMIT"],
            ["empty_result",       "Relax date/status filters; broaden WHERE clause"],
            ["validation_no_select","Output bare SQL only — strip all prose and markdown"],
            ["forbidden_keyword",  "Generate SELECT-only; never use DDL/DML keywords"],
        ],
        col_widths=[50, 116],
    )
    pdf.info_box(
        "Design Decision",
        "Known error types (7 of 8) use purely rule-based fix instructions — no LLM call. "
        "This keeps retry latency low. Only genuinely unknown errors escalate to an LLM diagnosis call.",
        GREEN,
    )
    pdf.h2("7.4  Progress Callbacks & Agent Trace")
    pdf.body(
        "The pipeline accepts an on_progress callback fired after every significant action. "
        "Each event is a dict {agent, action, message, ...}. Events are appended to "
        "PipelineResult.agent_trace (visible in the UI Agent Trace tab) and serialised "
        "to logs/query_log.jsonl for audit purposes."
    )

    # ─────────────────────────────── CHAPTER 8: UI ───────────────────────────
    pdf.add_page()
    pdf.h1("Streamlit User Interface")
    pdf.h2("8.1  Application Pages")
    pdf.table(
        ["File", "Page", "Purpose"],
        [
            ["app/Home.py",          "Home",      "Hero banner, live KPI strip, 5-agent accordion, tech stack, nav cards"],
            ["pages/1_Query.py",     "Query",     "Full NL2SQL: voice, cache, pipeline, charts, PDF, benchmarking"],
            ["pages/2_Dashboard.py", "Dashboard", "9-section pre-built KPI dashboard with RFM, forecast"],
            ["pages/3_History.py",   "History",   "Persistent query log browser with re-run, CSV export"],
            ["pages/4_Admin.py",     "Admin",     "DB status, schema explorer, agent diagnostics, log viewer"],
        ],
        col_widths=[40, 24, 102],
    )
    pdf.h2("8.2  Design System (styles.py)")
    items = [
        "Dark background: #080d1a (near-black navy) with subtle grid dot pattern",
        "Glassmorphism cards: backdrop-filter blur(12px) with translucent borders",
        "Typography: Inter (Google Fonts) at weights 300–800",
        "Page transitions: @keyframes with 0.85s cubic-bezier easing and scale effect (0.99→1.0)",
        "Accent colours: Blue (#3b82f6), Cyan (#06b6d4), Amber (#f59e0b), Green (#10b981)",
        "Plotly theme: consistent dark-glass chart layout via chart_layout(**overrides) helper",
    ]
    for i in items:
        pdf.bullet(i)
    pdf.h2("8.3  Smart Chart Selection (chart_builder.py)")
    pdf.body("A decision tree selects the optimal chart type automatically — no static chart per query.")
    pdf.table(
        ["Condition", "Chart Type"],
        [
            ["Column contains customer_state / seller_state",           "Brazil bubble map (scatter_geo)"],
            ["Column name matches time hints (year/month/date/quarter)", "Line + area chart"],
            ["Distribution query AND ≤8 rows",                      "Donut chart"],
            ["Avg label length >11 chars OR >12 rows",                  "Horizontal bar chart"],
            ["Short codes / ordinal values",                            "Vertical bar chart"],
            ["≥2 numeric columns, no category",                    "Scatter plot"],
        ],
        col_widths=[100, 66],
    )
    pdf.h2("8.4  Dashboard: 9 Analytical Sections")
    sections = [
        "Monthly Revenue Trend — line + dual-axis bar for order count",
        "Revenue by State — vertical bar; Top Categories — horizontal bar",
        "Payment Type Distribution — donut; Average Review Score — gauge",
        "Delivery Time Distribution — histogram",
        "Seller Performance — scatter (review score vs. revenue)",
        "Review Score Distribution + Best-Rated Categories",
        "Late Delivery Rate by State + Freight as % of Price",
        "Year-over-Year Quarterly Revenue (2017 vs. 2018) + Credit Card Instalment Analysis",
        "RFM Customer Intelligence — KMeans segmentation (added as 10th feature upgrade)",
    ]
    for s in sections:
        pdf.bullet(s)

    # ─────────────────────────────── CHAPTER 9: FEATURES ─────────────────────
    pdf.add_page()
    pdf.h1("Advanced Features (10 Upgrades)")
    pdf.body(
        "Ten major features were added to demonstrate data science, ML, and product engineering depth. "
        "All were implemented in a single commit (897eabc) after the core system was stable."
    )
    pdf.h2("Feature 1: Multi-Turn Conversational Memory")
    pdf.body(
        "Module: app/components/conversation.py. Each successful query turn is stored in "
        "st.session_state. The last 4 turns are serialised as a context block and injected into "
        "Agent 1's prompt, enabling follow-up questions without repeating context."
    )
    pdf.code(
        "Previous conversation turns (for context):\n"
        "  Turn 1: 'Show revenue by state'\n"
        "    -> metric=revenue, dimension=customer_state, result=27 rows\n"
        "    -> key finding: Sao Paulo generates 43% of total revenue.\n"
        "  Turn 2: 'Now filter to just 2018'\n"
        "    -> filters={year: 2018}, result=27 rows\n"
        "Current question: 'Which of those are above average?'",
        "Conversation context block injected into Agent 1",
    )
    pdf.h2("Feature 2: Brazil Geospatial Bubble Map")
    pdf.body(
        "Module: chart_builder.py. When a query result contains customer_state / seller_state, "
        "the chart builder automatically renders a Plotly scatter_geo map of Brazil. All 27 state "
        "centroids are hardcoded as (lat, lon) pairs — no external GeoJSON file required. "
        "Bubble radius is proportional to the metric value."
    )
    pdf.h2("Feature 3: Time-Series Forecasting")
    pdf.body(
        "Module: analytics/forecasting.py. Any time-series result chart gains a 'Show 6-period "
        "forecast' toggle. Model: Ridge Regression with seasonality features "
        "[t, sin(2πt/12), cos(2πt/12)]. Confidence band = mean ± RMSE of training "
        "residuals. Caption reports predicted next value, % change vs last actual, and training R²."
    )
    pdf.h2("Feature 4: PDF Report Export")
    pdf.body(
        "Module: utils/report_generator.py. After a successful query, a Generate Report button "
        "produces a downloadable PDF using fpdf2. Contains: branded header, metadata strip "
        "(rows, duration, retries, provider, confidence), the query, chart image, full SQL, "
        "and all four AI insight cards."
    )
    pdf.h2("Feature 5: FastAPI REST Endpoint")
    pdf.table(
        ["Method", "Path", "Description"],
        [
            ["GET",  "/health",          "Liveness check with live DB connectivity test"],
            ["GET",  "/schema",          "Star-schema table and column definitions"],
            ["POST", "/query",           "Full pipeline: intent → SQL → execute → insights"],
            ["POST", "/query/sql-only",  "Dry-run: intent → SQL + validation (no DB execution)"],
        ],
        col_widths=[20, 44, 102],
    )
    pdf.h2("Feature 6: RFM Customer Segmentation")
    pdf.body(
        "Module: analytics/rfm.py. KMeans (k=4) on StandardScaler-normalised "
        "[recency_inv, frequency, monetary]. Clusters ranked by composite score and assigned labels:"
    )
    pdf.table(
        ["Segment", "Description"],
        [
            ["Champions",    "Recent, frequent, high-spend. Best customers."],
            ["Loyal",        "Steady buyers. Reward to elevate to Champions."],
            ["At-Risk",      "Previously active but lapsing. Time-sensitive win-back."],
            ["Lost/Dormant", "Long inactive, low value. Low-cost re-engagement only."],
        ],
        col_widths=[38, 128],
    )
    pdf.h2("Feature 7: Query Confidence Scoring")
    pdf.body(
        "Module: utils/confidence.py. 0–100 score: +30 first-attempt pass, −10 per retry, "
        "+20 non-empty result, +20 no Reflection triggered, +30 all 4 insight fields substantive. "
        "Displayed as colour-coded badge (Green ≥85, Amber ≥60, Red <60)."
    )
    pdf.h2("Feature 8: Semantic Query Cache")
    pdf.body(
        "Module: utils/query_cache.py. TF-IDF cosine similarity cache (threshold 0.88, 100-entry LRU). "
        "On a cache hit, returns stored result instantly with a 'From cache' badge. New results stored "
        "to logs/query_cache.json. Vectoriser re-fit after every store. Warmed from disk once per session. "
        "TF-IDF chosen over sentence-transformers to avoid an 80MB model download on first run."
    )
    pdf.h2("Feature 9: Voice Input")
    pdf.body(
        "Inline JS in 1_Query.py via st.components.v1.html. Invokes the browser's Web Speech API. "
        "Start/Stop toggle, interim transcription displayed live, final result shown with a Copy button "
        "(navigator.clipboard.writeText). Zero backend dependencies; works natively in Chrome/Edge."
    )
    pdf.h2("Feature 10: Multi-LLM Benchmarking Mode")
    pdf.body(
        "Sidebar toggle in 1_Query.py. When active, the same query is submitted to both Ollama and Groq "
        "simultaneously using Python threading. Results displayed side-by-side: latency, SQL, sample rows, "
        "insight summary. Answers concretely which LLM is better for NL2SQL on this schema."
    )
    pdf.code(
        "t_ollama = threading.Thread(target=_run_provider, args=('ollama', ollama_model))\n"
        "t_groq   = threading.Thread(target=_run_provider, args=('groq',   groq_model))\n"
        "t_ollama.start(); t_groq.start()\n"
        "t_ollama.join();  t_groq.join()  # parallel execution",
        "Parallel provider execution",
    )

    # ─────────────────────────────── CHAPTER 10: TESTS ───────────────────────
    pdf.add_page()
    pdf.h1("Test Suite")
    pdf.h2("10.1  Overview")
    pdf.body(
        "54 passing pytest tests covering all five agents, validation logic, ETL cleaning, and DB "
        "connectivity. All external dependencies (LLM, MySQL) are mocked — suite runs offline "
        "in under 2 seconds."
    )
    pdf.table(
        ["Class / Module", "What is Tested", "Tests"],
        [
            ["TestQueryAgent",      "Intent JSON parsing, dict return, JSONDecodeError",              "3"],
            ["TestSQLAgent",        "SQL return type, markdown stripping, error feedback injection",   "3"],
            ["TestValidationAgent", "SELECT pass, DELETE/DROP/INSERT reject, unknown table, JOIN warn","8"],
            ["TestExecutionAgent",  "DataFrame return, DB error propagation with tenacity retry",      "2"],
            ["TestInsightAgent",    "Dict return, empty-DF path, all 4 keys present",                 "3"],
            ["TestPipeline",        "End-to-end success (mocked), validation failure triggers retry",  "2"],
            ["test_cleaning.py",    "Dedup, datetime parse, typo rename, category merge",             "12"],
            ["test_feature_eng",    "Delivery time, delay, is_late, approval time derivation",        "8"],
            ["test_validation.py",  "Additional SQL safety edge cases",                               "7"],
            ["test_db.py",          "Engine singleton, connection test (mocked)",                     "6"],
        ],
        col_widths=[44, 106, 16],
    )
    pdf.h2("10.2  Key Patterns")
    pdf.body(
        "LLM mocking: all chat() calls patched with unittest.mock.patch to return deterministic JSON. "
        "DB mocking: get_engine() patched with MagicMock whose connect().execute() returns a "
        "pre-configured result object. tenacity retry decorator is preserved — retry "
        "behaviour is tested end-to-end."
    )

    # ─────────────────────────────── CHAPTER 11: HISTORY ─────────────────────
    pdf.add_page()
    pdf.h1("Development History (15 Commits)")
    pdf.h2("11.1  Conventional Commits")
    pdf.body(
        "All commits follow the Conventional Commits specification: type(scope): description. "
        "Types used: feat, fix, chore, refactor, perf."
    )
    pdf.table(
        ["Commit", "Type(Scope)", "Summary"],
        [
            ["09f8835", "chore: init",          "Project scaffolding, .gitignore, requirements.txt, empty module placeholders"],
            ["27ebb7d", "feat: add all",         "First functional commit: ETL, schema DDL, 5-agent pipeline, basic Streamlit UI, OpenAI LLM"],
            ["62397d8", "fix(etl): truncate",    "FK-safe truncate+append pattern; fixes FK violations on ETL re-runs"],
            ["37715a8", "refactor(agents): ollama","Migrated all LLM calls from OpenAI to Ollama (llama3); added llm_client.py abstraction"],
            ["4fa7cff", "perf(dw): indexes",     "Single-column → composite indexes on fact_sales for analytical query performance"],
            ["ef4446f", "feat(agents): groq",    "Added Groq cloud API as second LLM provider; runtime set_provider() switching"],
            ["1751b64", "fix: 5 bugs",           "Fixed SQL injection vector, missing text() wrapper, dashboard crash, session state, loguru init"],
            ["3d1f5e8", "fix(app): dashboard",   "Dashboard crash fix; 54-test suite added; UI overhaul with glassmorphism + Inter typography"],
            ["7f8345c", "feat(ui): expandable",  "Pipeline steps as <details> accordion; collapsed sidebar; chart_layout() helper"],
            ["318aac2", "feat(ui): polished",    "4-colour insight cards; 4 new dashboard sections; image strips; tab spacing"],
            ["b121f87", "fix(pipeline): SQL",    "SQL extraction from LLM prose; day-of-week chart removed; transitions slowed to 0.85s"],
            ["3248ed9", "refactor(charts): adaptive","Complete chart_builder.py rewrite with 7-type decision tree; YoY quarterly added"],
            ["b25ea0d", "feat(agents): ReAct",   "Reflection Agent with 8-category classifier; full ReAct agentic loop; progress callbacks; agent trace"],
            ["897eabc", "feat(features): 10",    "All 10 major upgrades: memory, maps, forecast, PDF, API, RFM, confidence, cache, voice, benchmarking"],
        ],
        col_widths=[18, 38, 110],
    )
    pdf.h2("11.2  Security Constraint")
    pdf.info_box(
        "Permanent Security Rule",
        ".env (MySQL credentials + API keys) and imp stuff.txt are permanently excluded from all "
        "commits via .gitignore. GitHub Push Protection blocked one attempted push where a real "
        "API key was accidentally included in .env.example — corrected with a sanitised replacement commit.",
        RED,
    )

    # ─────────────────────────────── CHAPTER 12: CHALLENGES ─────────────────
    pdf.add_page()
    pdf.h1("Technical Challenges & Solutions")
    challenges = [
        (
            "MySQL ONLY_FULL_GROUP_BY",
            "MySQL 8.0 enforces ONLY_FULL_GROUP_BY by default. LLMs frequently generate "
            "YEAR(column) in GROUP BY while referencing the raw column in SELECT — "
            "valid in MySQL 5.7, rejected in 8.0 with Error 1055.",
            "Updated SQL agent prompt with explicit WRONG/CORRECT examples. "
            "Reflection Agent classifies this error immediately and returns: 'use dt.year and "
            "dt.month (INT columns) in GROUP BY, never YEAR(col)'.",
        ),
        (
            "LLM Prose Wrapping SQL",
            "Mistral and occasionally llama3 wrap generated SQL in explanation text. "
            "Old code only stripped markdown fences (```sql), leaving prose intact "
            "— causing Agent 3 'must begin with SELECT' failures.",
            "Two-step extraction: (1) find first SELECT keyword position, "
            "(2) split on first blank line after SELECT. Model-agnostic; handles any "
            "amount of prose before or after the SQL.",
        ),
        (
            "Day-of-Week Chart Always Blank",
            "Dashboard had a 'Revenue by Day of Week' chart mapping integer day codes to names. "
            "Investigation revealed dim_time.day_of_week is populated with string names "
            "('Monday', 'Tuesday') via pandas .day_name(), not integers. The mapping produced all NaN.",
            "Removed the chart entirely (wrong architecture). Replaced with YoY quarterly "
            "revenue comparison chart — more analytically valuable and correctly typed.",
        ),
        (
            "Duplicate Keyword Arguments in chart_layout()",
            "Plotly fig.update_layout(**CHART_LAYOUT, yaxis=...) raised TypeError: multiple "
            "values for keyword argument 'yaxis' because CHART_LAYOUT already contained a yaxis key.",
            "Implemented chart_layout(**overrides) helper: return {**CHART_LAYOUT, **overrides}. "
            "All callers updated to use this helper — overrides win without conflict.",
        ),
        (
            "ETL Re-run FK Violations",
            "to_sql(if_exists='replace') drops and recreates dimension tables, but the fact "
            "table's foreign keys still reference old dimension table IDs.",
            "Disable FK checks, truncate all tables in fact-first order, re-enable FK checks, "
            "then re-insert. Makes ETL runs idempotent across multiple executions.",
        ),
        (
            "%Y/%m Format Errors in pd.read_sql",
            "Any SQL containing %Y or %m raises Python TypeError because PyMySQL interprets "
            "% as a Python format specifier.",
            "All SQL executed via SQLAlchemy must be wrapped with sqlalchemy.text(sql). "
            "This treats the string as literal SQL, bypassing Python's format-string mechanism.",
        ),
        (
            "GitHub Push Protection",
            "A real OpenAI API key was accidentally included in .env.example. "
            "GitHub's Push Protection blocked the push.",
            "Corrected .env.example with placeholder values, amended the commit "
            "(safe since not yet pushed). Reinforced .gitignore rule for .env permanently.",
        ),
    ]
    for num, (title, problem, solution) in enumerate(challenges, 1):
        pdf.h2(f"12.{num}  {title}")
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*RED)
        pdf.cell(0, 5.5, "Problem:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.body(problem)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*GREEN)
        pdf.cell(0, 5.5, "Solution:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.body(solution)

    # ─────────────────────────────── CHAPTER 13: RESULTS ─────────────────────
    pdf.add_page()
    pdf.h1("Results & Evaluation")
    pdf.h2("13.1  System Capabilities")
    pdf.table(
        ["Capability", "Details"],
        [
            ["Natural-language queries",  "Any English business question about the Olist dataset"],
            ["SQL generation",            "Valid MySQL 8.0 with correct GROUP BY, JOIN, aggregation"],
            ["Self-correction",           "Up to 3 retry attempts with structured Reflection Agent guidance"],
            ["Chart types",               "7 adaptive types including Brazil geo maps and dual-axis time series"],
            ["Forecasting",               "6-period ahead with confidence band, R², and % change caption"],
            ["PDF export",                "Branded report with query, SQL, chart image, AI insights"],
            ["Conversational memory",     "Last 4 turns; supports follow-up and refinement questions"],
            ["REST API",                  "4 endpoints with Swagger docs; provider + model per request"],
            ["Semantic cache",            "TF-IDF cosine similarity; threshold 0.88; 100-entry LRU"],
            ["Voice input",               "Web Speech API; Chrome/Edge; copy-to-clipboard"],
            ["RFM segmentation",          "KMeans k=4; Champions/Loyal/At-Risk/Lost with revenue share"],
            ["Multi-LLM benchmarking",    "Ollama + Groq parallel, side-by-side comparison"],
            ["Confidence scoring",        "0–100 score with colour-coded badge per query"],
            ["Query history",             "Persistent JSONL log; searchable; re-run support"],
            ["Test coverage",             "54 passing tests; all agents and ETL functions covered"],
        ],
        col_widths=[50, 116],
    )
    pdf.h2("13.2  Performance")
    pdf.table(
        ["Scenario", "Latency"],
        [
            ["Ollama local (llama3)",  "35–55 seconds end-to-end"],
            ["Groq cloud (llama3-70b)", "2–6 seconds end-to-end"],
            ["Cache hit",              "<100ms (TF-IDF cosine only)"],
            ["ETL full load",          "~4 minutes (100K+ rows)"],
            ["Dashboard first load",   "8–12 seconds; <1s from Streamlit cache"],
        ],
        col_widths=[80, 86],
    )
    pdf.h2("13.3  Sample SQL Generated")
    pdf.code(
        "-- 'Monthly revenue trend for 2018'\n"
        "SELECT dt.year, dt.month,\n"
        "       CONCAT(dt.year,'-',LPAD(dt.month,2,'0')) AS month_label,\n"
        "       ROUND(SUM(fs.payment_value),0) AS revenue,\n"
        "       COUNT(DISTINCT fs.order_id)    AS orders\n"
        "FROM   fact_sales fs\n"
        "JOIN   dim_time dt ON fs.date_key = dt.date_key\n"
        "WHERE  fs.order_status = 'delivered' AND dt.year = 2018\n"
        "GROUP  BY dt.year, dt.month\n"
        "ORDER  BY dt.year, dt.month ASC",
        "Example pipeline output",
    )

    # ─────────────────────────────── CHAPTER 14: CONCLUSION ──────────────────
    pdf.add_page()
    pdf.h1("Conclusion & Future Work")
    pdf.h2("14.1  What Was Built")
    built = [
        "Kimball star-schema MySQL warehouse with 4 dimension tables, fact table, and composite indexes.",
        "Five-stage ETL pipeline with cleaning, feature engineering, and idempotent FK-safe reloading.",
        "Five-agent NL2SQL pipeline: structured intent parsing, schema-aware SQL generation, rule-based "
        "safety validation, retry-enabled execution, and LLM-generated business insights.",
        "ReAct agentic loop with Reflection Agent that classifies failures and plans targeted recovery.",
        "Polished four-page Streamlit UI with glassmorphism design, adaptive charts, and persistent query history.",
        "Ten advanced features: RFM, forecasting, PDF, REST API, cache, voice, benchmarking, memory, maps, confidence.",
        "54 passing unit and integration tests with mocked LLM and DB dependencies.",
    ]
    for b in built:
        pdf.bullet(b)
    pdf.h2("14.2  Key Learnings")
    learnings = [
        "Schema specificity is critical for NL2SQL: generic prompts fail; MySQL 8.0-specific WRONG/CORRECT examples dramatically reduce failures.",
        "Structured error feedback beats raw error passthrough: classified fix instructions reliably guide Agent 2 to the correct fix.",
        "Separation of concerns enables safe evolution: adding the Reflection Agent required zero changes to the 5 existing agents.",
        "ETL quality directly determines NL2SQL accuracy: schema typos and wrong column types propagate into broken SQL generations.",
        "Open-source LLMs are production-viable: Ollama + llama3 produces correct SQL for this schema in ~95% of first-attempt cases.",
    ]
    for l in learnings:
        pdf.bullet(l)
    pdf.h2("14.3  Future Work")
    future = [
        "Fine-tune a small LLM (Phi-3 Mini) on the 20 benchmark queries with their ground-truth SQL.",
        "Schema-agnostic mode: auto-discover schema from any connected MySQL database and adapt prompts dynamically.",
        "Streaming pipeline: FastAPI WebSockets to stream agent progress events to the UI in real time.",
        "Churn prediction: train a customer churn classifier on RFM features; add Churn Risk column to the dashboard.",
        "Embedding-based cache: replace TF-IDF with sentence-transformers all-MiniLM-L6 for richer semantic matching.",
        "Docker: package the entire system in a docker-compose.yml for one-command deployment.",
    ]
    for f in future:
        pdf.bullet(f)

    # ─────────────────────────────── APPENDIX: MODULE LIST ───────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*BLUE)
    pdf.cell(0, 10, "Appendix: Module Summary", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.divider()
    pdf.table(
        ["File", "Primary Responsibility"],
        [
            ["config.py",                    "Reads .env via python-dotenv; exposes all config constants"],
            ["run_etl.py",                   "ETL entry point; calls all 5 stages in order"],
            ["utils/db_connection.py",       "SQLAlchemy engine singleton; test_connection() health check"],
            ["utils/llm_client.py",          "Unified Ollama/Groq dispatcher; runtime set_provider()"],
            ["utils/logger.py",              "loguru setup; JSONL file sink at logs/query_log.jsonl"],
            ["utils/confidence.py",          "0–100 pipeline confidence scorer"],
            ["utils/query_cache.py",         "TF-IDF cosine semantic cache: warm, lookup, store"],
            ["utils/report_generator.py",    "fpdf2 PDF report builder"],
            ["etl/data_ingestion.py",        "Reads all 9 Olist CSVs into a dict of DataFrames"],
            ["etl/data_cleaning.py",         "Per-table dedup, type coercion, string normalisation"],
            ["etl/data_integration.py",      "Joins all tables into master order-level DataFrame"],
            ["etl/feature_engineering.py",   "Derives delivery_time, delay, is_late, approval_hours"],
            ["etl/data_loading.py",          "FK-safe truncate + writes dim and fact tables"],
            ["agents/query_agent.py",        "Agent 1: NL → JSON intent (with conversation history)"],
            ["agents/sql_agent.py",          "Agent 2: intent → MySQL SELECT (with error feedback)"],
            ["agents/validation_agent.py",   "Agent 3: rule-based SQL safety + schema validation"],
            ["agents/execution_agent.py",    "Agent 4: tenacity retry DB execution → DataFrame"],
            ["agents/insight_agent.py",      "Agent 5: LLM business insights from result DataFrame"],
            ["agents/reflection_agent.py",   "Error classifier + recovery planner (8 categories)"],
            ["agents/pipeline.py",           "ReAct orchestrator; progress callbacks; agent trace"],
            ["analytics/forecasting.py",     "Ridge regression + seasonality time-series forecasting"],
            ["analytics/rfm.py",             "RFM KMeans segmentation; segment labels and revenue share"],
            ["api/main.py",                  "FastAPI: /health, /schema, /query, /query/sql-only"],
            ["app/Home.py",                  "Landing page: KPIs, 5-agent accordion, nav cards"],
            ["app/components/styles.py",     "Global CSS injection; CHART_LAYOUT; COLOR_SEQ"],
            ["app/components/chart_builder.py", "7-type adaptive chart selection and rendering"],
            ["app/components/conversation.py",  "Multi-turn history: add, clear, render, build context"],
            ["app/components/insight_display.py","4-card AI insight renderer"],
            ["app/pages/1_Query.py",         "Query page: voice, cache, pipeline, charts, PDF, benchmarking"],
            ["app/pages/2_Dashboard.py",     "9-section dashboard: trends, RFM, forecasting"],
            ["app/pages/3_History.py",       "JSONL log browser with search, filter, re-run, CSV export"],
            ["app/pages/4_Admin.py",         "DB status, schema explorer, diagnostics, log viewer"],
        ],
        col_widths=[58, 108],
    )


# ═════════════════════════════════════════════════════════════════════════════
def main():
    pdf = Report()
    build(pdf)
    OUT.parent.mkdir(exist_ok=True)
    pdf.output(str(OUT))
    print(f"PDF written to: {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
