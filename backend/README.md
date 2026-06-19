---
title: NovaPlan CALM
emoji: 🌿
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
license: mit
app_port: 8501
startup_duration_timeout: 45m
---

# NovaPlan Backend

NovaPlan backend runs Rasa Pro CALM, FastAPI APIs, Rasa custom actions, Nginx, Supervisor, and the optional Streamlit test UI in one Hugging Face Docker Space.

## Structure

```text
backend/
  api/        FastAPI API package
    services/ routes, schemas, repositories, and business services
  config/     backend settings and nginx.conf
  db/         novaplan.py database helper and final Neon schema.sql
  docs/       API, deployment, environment, and testing documentation
  rasa/       Rasa Pro config, flows, actions, tests
  scripts/    container startup and Rasa train/run scripts
  ui/         Streamlit test console
```

Supplemental delivery documentation is available under `docs/`:

| File | Purpose |
|---|---|
| `docs/API_SUMMARY.md` | Backend API surface |
| `docs/DEPLOYMENT.md` | Hugging Face deployment |
| `docs/ENVIRONMENT_VARIABLES.md` | Runtime environment variables and secrets |
| `docs/TESTING_README.md` | Pytest and runtime evidence |
| `docs/RASA_TESTING_README.md` | Rasa Pro CALM testing |
| `docs/TEST_EVIDENCE_NOTES.md` | Evidence interpretation |

## Database

Run `db/schema.sql` manually in Neon before deployment. It creates all tables and seeds:

```text
admin@novaplan.ai / admin123
```

Change this password after deployment through the admin flow or by updating the database.

## Required Secrets

Set secrets in Hugging Face Space settings:

```text
DATABASE_URL
JWT_SECRET
RASA_LICENSE
TRAVELPAYOUTS_API_TOKEN
CLIMATIQ_API_KEY
GEOAPIFY_API_KEY
OPENROUTER_API_KEY
LLM_MODEL_NAME
CORS_ORIGINS
```

Remove unused secrets from the Space. `OPENAI_API_KEY`, `NOVAPLAN_USER_AGENT`, `USE_MOCK_DATA`, `ENABLE_OSM_HOTEL_LOOKUP`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `HUGGINGFACE_API_KEY`, `TRAVELPAYOUTS_MARKER`, and `RASA_PRO_TOKEN` are not required unless code is reintroduced that consumes them. Use `RASA_LICENSE` as the standard Rasa Pro license secret. `RASA_PRO_LICENSE` is accepted only as a legacy compatibility fallback by startup scripts.

## Endpoints

| Path | Description |
|---|---|
| `GET /` | Nginx/FastAPI health route |
| `GET /ui/` | Streamlit test console |
| `POST /api/rasa/webhook` | Firebase frontend chatbot webhook |
| `POST /api/register` | User registration |
| `POST /api/login` | User/admin/support login |
| `GET /api/users` | Admin user list |
| `PATCH /api/users/{id}/role` | Admin role update |
| `GET /api/sessions` | Support/admin session list |
| `GET /api/sessions/{id}/conversations` | Session conversations |
| `POST /api/conversations` | Save support/user/bot conversation entry |
| `GET /api/itineraries/{user_id}` | User saved itineraries |
| `GET /api/diag` | Runtime diagnostics |

## Validation

```bash
python -m compileall -q hf_proxy.py config db api rasa/actions
rasa data validate --config rasa/config.yml --domain rasa/domain.yml --data rasa/data/flows
```

Rasa tests require a licensed Rasa Pro environment.
