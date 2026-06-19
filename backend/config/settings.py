import os

DATABASE_URL = os.getenv("DATABASE_URL", "")
JWT_SECRET = os.getenv("JWT_SECRET", "")
TRAVELPAYOUTS_API_TOKEN = os.getenv("TRAVELPAYOUTS_API_TOKEN", "")
CLIMATIQ_API_KEY = os.getenv("CLIMATIQ_API_KEY")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

APP_ENV = os.getenv("APP_ENV", "PROD").strip().upper()
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-20b:free").strip()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
ENABLE_API_DOCS = os.getenv("ENABLE_API_DOCS", "false").strip().lower() == "true"

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8501").rstrip("/")
RASA_URL = os.getenv("RASA_URL", os.getenv("TARGET_RASA_URL", "http://127.0.0.1:5005")).rstrip("/")
ACTION_SERVER_URL = os.getenv("ACTION_SERVER_URL", "http://127.0.0.1:5055").rstrip("/")
DB_POOL_MIN_SIZE = 0
DB_POOL_MAX_SIZE = 10
DB_POOL_TIMEOUT = 10
DB_POOL_MAX_IDLE = 60
DB_POOL_MAX_LIFETIME = 300


def _csv_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name, "")
    values = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
    return values or default


ALLOWED_ORIGINS = _csv_env(
    "CORS_ORIGINS",
    [
        "https://novaplan-496111.web.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
)
NOVAPLAN_USER_AGENT = "NovaPlan.ai/1.0 (sustainable travel assistant; contact: support@novaplan.ai)"

TRAVELPAYOUTS_FLIGHT_URL = "https://api.travelpayouts.com/v1/prices/cheap"
CLIMATIQ_ESTIMATE_URL = "https://api.climatiq.io/data/v1/estimate"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary"
RESTCOUNTRIES_NAME_URL = "https://restcountries.com/v3.1/name"

DIAGNOSTIC_ENV_KEYS = (
    "RASA_LICENSE",
    "RASA_PRO_LICENSE",
    "TRAVELPAYOUTS_API_TOKEN",
    "CLIMATIQ_API_KEY",
    "DATABASE_URL",
    "GEOAPIFY_API_KEY",
    "OPENROUTER_API_KEY",
    "JWT_SECRET",
    "ENABLE_API_DOCS",
    "APP_ENV",
)


def config_value(name: str) -> str:
    return os.getenv(name, "")
