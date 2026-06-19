"""
Smart DW NL2SQL — FastAPI REST Endpoint
========================================
Start with:
    uvicorn api.main:app --reload --port 8000

Swagger docs auto-generated at:  http://localhost:8000/docs
Redoc at:                         http://localhost:8000/redoc

Endpoints
---------
GET  /health          Liveness check + DB connectivity
GET  /schema          Returns the warehouse star-schema summary
POST /query           Run the full 5-agent NL2SQL pipeline
POST /query/sql-only  Generate SQL without executing (dry-run)
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.pipeline import run_pipeline
from agents.query_agent import understand_query
from agents.sql_agent import generate_sql
from agents.validation_agent import validate_sql


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Smart DW NL2SQL API",
    description=(
        "Agentic NL2SQL pipeline for the Olist Brazilian E-Commerce data warehouse.\n\n"
        "Converts natural language business questions to SQL, executes them against a "
        "MySQL 8.0 star schema, and returns AI-generated insights alongside the result set."
    ),
    version="1.0.0",
    contact={"name": "Smart DW", "email": "22f3000165@ds.study.iitm.ac.in"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response schemas ────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question:    str  = Field(..., min_length=3, max_length=500,
                              example="What are the top 5 product categories by revenue?")
    provider:    str  = Field("groq",  pattern="^(groq|ollama)$",
                              description="LLM provider: 'groq' (cloud) or 'ollama' (local)")
    model:       str  = Field("llama3-70b-8192",
                              description="Model name for the chosen provider")
    max_rows:    int  = Field(200, ge=1, le=5000,
                              description="Maximum rows returned in the response")


class InsightResponse(BaseModel):
    summary:        str
    trend:          str
    key_finding:    str
    recommendation: str


class QueryResponse(BaseModel):
    question:    str
    sql:         str
    rows:        list[dict]
    row_count:   int
    duration_ms: int
    retry_count: int
    insights:    InsightResponse | None
    success:     bool
    error:       str


class SQLOnlyRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500,
                          example="Monthly revenue trend for 2018")
    provider: str = Field("groq", pattern="^(groq|ollama)$")
    model:    str = Field("llama3-70b-8192")


class SQLOnlyResponse(BaseModel):
    question:   str
    intent:     dict
    sql:        str
    is_valid:   bool
    errors:     list[str]
    warnings:   list[str]


class SchemaResponse(BaseModel):
    tables:     list[dict]
    note:       str


class HealthResponse(BaseModel):
    status:   str
    db_ok:    bool
    message:  str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
def health():
    """Liveness check. Returns DB connectivity status."""
    try:
        from utils.db_connection import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return HealthResponse(status="ok", db_ok=True, message="All systems operational")
    except Exception as exc:
        return HealthResponse(status="degraded", db_ok=False, message=str(exc))


@app.get("/schema", response_model=SchemaResponse, tags=["Metadata"])
def schema():
    """Returns the warehouse star-schema table and column list."""
    tables = [
        {"name": "fact_sales",     "type": "fact",
         "columns": ["fact_id","order_id","customer_id","product_id","seller_id","date_key",
                     "order_status","payment_type","payment_value","price","freight_value",
                     "review_score","delivery_time_days","delay_days","is_late","approval_time_hours"]},
        {"name": "dim_customers",  "type": "dimension",
         "columns": ["customer_id","customer_city","customer_state","customer_zip_code_prefix"]},
        {"name": "dim_products",   "type": "dimension",
         "columns": ["product_id","product_category_name_english","product_weight_g",
                     "product_length_cm","product_height_cm","product_width_cm"]},
        {"name": "dim_sellers",    "type": "dimension",
         "columns": ["seller_id","seller_city","seller_state","seller_zip_code_prefix"]},
        {"name": "dim_time",       "type": "dimension",
         "columns": ["date_key","full_date","day","month","year","quarter",
                     "day_of_week","is_weekend","week_of_year"]},
    ]
    return SchemaResponse(
        tables=tables,
        note="Star schema: fact_sales joins to all dimension tables via FK columns.",
    )


@app.post("/query", response_model=QueryResponse, tags=["NL2SQL"])
def query(req: QueryRequest):
    """
    Run the full agentic NL2SQL pipeline:
    Query Understanding → SQL Generation → Validation → Execution → Insights.
    Returns the SQL, result rows (up to max_rows), and AI insights.
    """
    from utils.llm_client import set_provider as _set
    _set(req.provider, req.model)

    result = run_pipeline(req.question)

    rows = []
    if result.data is not None and not result.data.empty:
        rows = result.data.head(req.max_rows).to_dict(orient="records")

    insights_out = None
    if result.insights:
        insights_out = InsightResponse(
            summary        = result.insights.get("summary",        ""),
            trend          = result.insights.get("trend",          ""),
            key_finding    = result.insights.get("key_finding",    ""),
            recommendation = result.insights.get("recommendation", ""),
        )

    if not result.success and not result.sql:
        raise HTTPException(status_code=422, detail=result.error_message)

    return QueryResponse(
        question    = req.question,
        sql         = result.sql or "",
        rows        = rows,
        row_count   = len(rows),
        duration_ms = result.duration_ms,
        retry_count = result.retry_count,
        insights    = insights_out,
        success     = result.success,
        error       = result.error_message,
    )


@app.post("/query/sql-only", response_model=SQLOnlyResponse, tags=["NL2SQL"])
def sql_only(req: SQLOnlyRequest):
    """
    Dry-run mode: parse intent and generate SQL without executing against the DB.
    Useful for previewing queries or integrating with external execution engines.
    """
    from utils.llm_client import set_provider as _set
    _set(req.provider, req.model)

    intent     = understand_query(req.question)
    sql        = generate_sql(intent, req.question, "")
    validation = validate_sql(sql)

    return SQLOnlyResponse(
        question = req.question,
        intent   = intent,
        sql      = sql,
        is_valid = validation.is_valid,
        errors   = validation.errors,
        warnings = validation.warnings,
    )
