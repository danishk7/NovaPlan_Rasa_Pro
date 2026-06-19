# NovaPlan Backend Deployment

The backend is deployed as a Hugging Face Docker Space. The container runs Nginx, Supervisor, FastAPI, Rasa Pro 3.12.42, the Rasa action server, and the optional Streamlit test UI.

## Required Hugging Face Secrets

Set the required runtime variables in the Space settings. See `ENVIRONMENT_VARIABLES.md` for the full list.

```text
APP_ENV=PROD
DATABASE_URL=postgresql://USER:PASSWORD@HOST/neondb?sslmode=require
JWT_SECRET=replace-with-long-random-secret
RASA_LICENSE=your-rasa-pro-license
OPENROUTER_API_KEY=your-openrouter-key
LLM_MODEL_NAME=openai/gpt-oss-20b:free
CORS_ORIGINS=https://novaplan-496111.web.app
```

Recommended integration secrets:

```text
TRAVELPAYOUTS_API_TOKEN=...
CLIMATIQ_API_KEY=...
GEOAPIFY_API_KEY=...
```

## Production Startup

Production must leave `APP_ENV` unset or set it to `PROD`.

```bash
APP_ENV=PROD
```

In production mode, `/app/scripts/run_tests.sh` exits immediately and does not run tests during service startup.

## Test Evidence Startup

Use a separate test deployment or temporary test run:

```bash
APP_ENV=TEST
```

The test-mode startup generates evidence under `/app/results` and exposes test-result endpoints under `/api/test-results`. These endpoints return `404` when `APP_ENV` is not `TEST`.

## Public Routes

| Path | Purpose |
|---|---|
| `/` | Nginx health JSON |
| `/api/*` | FastAPI APIs and Rasa proxy |
| `/ui/` | Optional Streamlit test console |
| `/docs` | Swagger UI when `ENABLE_API_DOCS=true` |
| `/openapi.json` | OpenAPI schema when `ENABLE_API_DOCS=true` |

## Database Setup

Run `db/schema.sql` manually in Neon before first deployment or after schema reset.
