# NovaPlan Backend Environment Variables

NovaPlan backend variables are runtime secrets/configuration for the Hugging Face Docker Space unless noted otherwise.

| Variable | Required | Purpose | Expected format | Used by | Secret |
|---|---:|---|---|---|---:|
| `APP_ENV` | No | Controls runtime mode. `TEST` runs evidence-generation tests before startup; unset or `PROD` skips tests. | `PROD` or `TEST` | `scripts/run_tests.sh`, `config/settings.py`, test-result routes | No |
| `DATABASE_URL` | Yes | Neon PostgreSQL connection string. | `postgresql://USER:PASSWORD@HOST/neondb?sslmode=require` | `db/novaplan.py`, API repositories | Yes |
| `JWT_SECRET` | Yes | Signs and validates backend auth tokens. | Long random string | `api/services/auth_service.py`, `api/services/auth_dependencies.py` | Yes |
| `RASA_LICENSE` | Yes | Rasa Pro license key. | Rasa Pro license text/key | Rasa train/run scripts and Rasa Pro runtime | Yes |
| `RASA_PRO_LICENSE` | No | Legacy compatibility fallback only. Prefer `RASA_LICENSE`. | Rasa Pro license text/key | Startup/train scripts fallback | Yes |
| `CORS_ORIGINS` | No | Allowed frontend origins for FastAPI. | Comma-separated URLs | `config/settings.py`, `hf_proxy.py` | No |
| `ENABLE_API_DOCS` | No | Enables `/docs`, `/redoc`, and `/openapi.json` when `true`. | `true` or `false` | `hf_proxy.py` | No |
| `PUBLIC_BASE_URL` | No | Public backend URL used by the optional Streamlit test UI. | URL | `config/settings.py`, `ui/streamlit_app.py` | No |
| `RASA_URL` | No | Internal Rasa server URL. Defaults to local container Rasa. | URL | `hf_proxy.py`, health services | No |
| `TARGET_RASA_URL` | No | Compatibility/default source for `RASA_URL`. | URL | `config/settings.py`, startup script | No |
| `ACTION_SERVER_URL` | No | Internal Rasa action server URL. | URL | `hf_proxy.py`, health services | No |
| `TRAVELPAYOUTS_API_TOKEN` | Recommended | Enables Travelpayouts flight/ticket lookups. Without it, curated transport options are used. | API token | Rasa travel service, health checks | Yes |
| `CLIMATIQ_API_KEY` | Recommended | Enables Climatiq carbon estimates. Without it, fallback estimates are used. | API key | Rasa carbon service, health checks | Yes |
| `GEOAPIFY_API_KEY` | Recommended | Enables Geoapify geocoding and hotel/place search. Without it, open-data fallback is used. | API key | Rasa hotel service, health checks | Yes |
| `OPENROUTER_API_KEY` | Required for CALM LLM | OpenRouter key used by Rasa CALM command generation. | API key | `rasa/endpoints.yml` | Yes |
| `LLM_MODEL_NAME` | No | OpenRouter model name. | Example: `openai/gpt-oss-20b:free` | `rasa/endpoints.yml`, `config/settings.py` | No |
| `ENABLE_GUEST_ITINERARY_PERSISTENCE` | No | Allows guest itinerary persistence from Rasa actions when enabled. | `true` or `false` | `rasa/actions/action_config.py` | No |
| `LOG_LEVEL` | No | Backend logging level. | `INFO`, `DEBUG`, `WARNING`, `ERROR` | `config/settings.py` | No |

Obsolete variables not required by the current code path: `RASA_PRO_TOKEN`, `OPENAI_API_KEY`, `NOVAPLAN_USER_AGENT`, `USE_MOCK_DATA`, `ENABLE_OSM_HOTEL_LOOKUP`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `HUGGINGFACE_API_KEY`, and `TRAVELPAYOUTS_MARKER`.
