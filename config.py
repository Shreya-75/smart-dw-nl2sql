from dotenv import load_dotenv
import os

load_dotenv()

# ── LLM Provider ──
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # "ollama" | "groq" | "openai"

# ── OpenAI (unused when LLM_PROVIDER=ollama/groq) ──
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL     = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ── Groq (free cloud LLM — faster + larger than local Ollama) ──
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama3-70b-8192")

# ── MySQL ──
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = int(os.getenv("DB_PORT", 3306))
DB_NAME     = os.getenv("DB_NAME", "olist_dw")
DB_USER     = os.getenv("DB_USER", "olist_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# ── Ollama ──
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3")

# ── App ──
LOG_LEVEL              = os.getenv("LOG_LEVEL", "INFO")
MAX_RETRY_ATTEMPTS     = int(os.getenv("MAX_RETRY_ATTEMPTS", 3))
QUERY_TIMEOUT_SECONDS  = int(os.getenv("QUERY_TIMEOUT_SECONDS", 30))

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)
