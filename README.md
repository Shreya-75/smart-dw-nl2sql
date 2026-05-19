# Smart Data Warehouse + Agentic NL2SQL System

Ask business questions in plain English — a 5-agent AI pipeline translates them to SQL, executes on a star-schema MySQL warehouse, and returns charts + insights.

## Quick Start

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/smart-dw-nl2sql.git
cd smart-dw-nl2sql

# 2. Environment
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # Fill in API keys + DB credentials

# 3. MySQL: create DB + user (see docs/project_documentation.html)

# 4. Place Olist CSVs in data/raw/

# 5. Run ETL
python run_etl.py

# 6. Launch App
streamlit run app/streamlit_app.py
```

## Full Documentation

Open `docs/project_documentation.html` in your browser for the complete guide.

## Architecture

```
User Interface (Streamlit)
        ↓
5-Agent AI Layer (GPT-4o / Llama 3)
        ↓
Execution & Validation Layer
        ↓
Star Schema MySQL Data Warehouse
        ↓
ETL Pipeline (Pandas + SQLAlchemy)
```

## Tech Stack

- **Python 3.11** · Pandas · SQLAlchemy
- **MySQL 8.0** — star schema data warehouse
- **OpenAI GPT-4o** — primary LLM
- **Ollama Llama 3** — offline fallback
- **Streamlit** — web UI
- **Power BI** — executive dashboard
- **Plotly** — interactive charts

## Dataset

Olist Brazilian E-Commerce — 9 CSV files, 100,000+ orders (2016–2018).
