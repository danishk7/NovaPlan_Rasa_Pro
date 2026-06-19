# NovaPlan.ai - Sustainable Travel Chatbot Platform

NovaPlan.ai is a sustainable travel planning platform built with a Firebase-hosted React/Vite frontend and a Hugging Face Docker backend running FastAPI, Rasa Pro CALM, custom Rasa actions, Nginx, Supervisor, and Neon PostgreSQL.

## Live Access

| Resource | Link |
|---|---|
| Frontend application | https://novaplan-496111.web.app |
| Planner/chatbot | https://novaplan-496111.web.app/planner |
| User bookings | https://novaplan-496111.web.app/bookings |
| Admin login | https://novaplan-496111.web.app/admin/login |
| Support login | https://novaplan-496111.web.app/support/login |
| Hugging Face backend | https://danishk84-nprasa.hf.space |
| Backend health | https://danishk84-nprasa.hf.space/api/health |
| Runtime diagnostics | https://danishk84-nprasa.hf.space/api/diag |
| Swagger API docs | https://danishk84-nprasa.hf.space/docs |
| Optional backend UI | https://danishk84-nprasa.hf.space/ui/ |
| GitHub repository | https://github.com/danishk7/NovaPlan_Rasa_Pro |

Swagger is available only when `ENABLE_API_DOCS=true` is set in the Hugging Face Space environment.

## Project Summary

NovaPlan.ai supports:

- Sustainable trip planning through a Rasa Pro 3.12.42 CALM assistant.
- User, admin, and support roles.
- JWT authentication through the FastAPI backend.
- Chat persistence and human support handover.
- Confirmed itinerary persistence in Neon PostgreSQL.
- Booking summary, carbon estimate, transport options, eco hotel options, destination/cultural information, and post-booking survey prompt.
- External integrations for travel, carbon, hotels/geocoding, Wikipedia destination data, country facts, and CALM LLM command generation.

## Architecture

```mermaid
flowchart LR
    A["Firebase Hosting<br/>React + Vite frontend"] --> B["Hugging Face Docker Space"]
    B --> C["Nginx reverse proxy"]
    C --> D["FastAPI API + Rasa proxy"]
    C --> E["Rasa Pro 3.12.42 CALM server"]
    E --> F["Rasa custom action server"]
    D --> G["Neon PostgreSQL"]
    F --> G
    F --> H["Travelpayouts"]
    F --> I["Climatiq"]
    F --> J["Geoapify"]
    F --> K["Wikipedia REST API"]
    F --> L["RestCountries"]
    E --> M["OpenRouter LLM endpoint"]
```

## Repository Structure

```text
NovaPlan/
  backend/
    api/                 FastAPI routes, schemas, services, repositories
    config/              Backend settings and Nginx configuration
    db/                  Neon PostgreSQL helper and schema.sql
    docs/                Backend deployment, API, environment, testing docs
    rasa/                Rasa Pro config, domain, CALM flows, actions, tests
    scripts/             Docker startup, Rasa train/run, test scripts
    tests/               Pytest unit tests for API and Rasa actions/services
    ui/                  Optional Streamlit backend test console
    Dockerfile           Hugging Face Docker image
    hf_proxy.py          FastAPI entrypoint and Rasa proxy
    supervisord.conf     Runtime process manager config

  frontend/
    src/                 React application source
    src/components/      Chatbot, layout, and reusable UI components
    src/pages/           User, admin, support, booking, and content pages
    src/lib/             API client, Rasa parser, booking render helpers
    src/config/          Frontend runtime/build config
    docs/                Frontend deployment and environment docs
    firebase.json        Firebase Hosting configuration
    package.json         Vite/React scripts and dependencies
```

The submission focuses on the `backend/` and `frontend/` code folders. Generated folders such as `node_modules/`, local build artifacts, and temporary workspace folders are not required for review.

## Main Features

| Area | Implementation |
|---|---|
| Authentication | FastAPI JWT login/register with Neon PostgreSQL users |
| Roles | `user`, `admin`, and `support` |
| Chatbot | Rasa Pro CALM assistant behind `/api/rasa/webhook` |
| Trip planning | Origin, destination, dates, budget, travellers, eco level, transport mode |
| Booking | Confirmed itinerary saved once through Rasa action using the displayed booking reference |
| Bookings page | Reads saved itineraries from `/api/itineraries/{user_id}` |
| Carbon | Climatiq API with fallback estimates |
| Transport | Travelpayouts flight data with curated fallback options |
| Hotels | Geoapify place search with curated fallback options |
| Destination info | Wikipedia summary and RestCountries facts |
| Human support | Session handover and support console replies |
| Survey | Google Form prompt after successful booking confirmation |
| Test evidence | Pytest and Rasa evidence endpoints in `APP_ENV=TEST` mode |

## Backend API Overview

All backend APIs are served by the Hugging Face backend under `/api`.

| Method | Path | Purpose | Auth |
|---|---|---|---|
| `GET` | `/api/health` | Aggregate backend health | Public |
| `GET` | `/api/health/database` | Neon health check | Public |
| `GET` | `/api/health/rasa` | Rasa server health | Public |
| `GET` | `/api/health/actions` | Rasa action server health | Public |
| `GET` | `/api/health/integrations` | External integration reachability | Public |
| `POST` | `/api/register` | Register user | Public |
| `POST` | `/api/login` | Login user/admin/support | Public |
| `GET` | `/api/users` | List users | Admin |
| `PATCH` | `/api/users/{user_id}/role` | Update role | Admin |
| `DELETE` | `/api/users/{user_id}` | Delete user | Admin |
| `GET` | `/api/profile/{user_id}` | Read profile | Self/admin/support |
| `PATCH` | `/api/profile/{user_id}` | Update profile | Self/admin |
| `POST` | `/api/contact` | Contact form submission | Public |
| `GET` | `/api/contacts` | View contact messages | Admin/support |
| `GET` | `/api/sessions/user/{user_id}` | Get or create user chat session | Self/admin/support |
| `GET` | `/api/sessions` | List support sessions | Admin/support |
| `GET` | `/api/sessions/{ses_id}/conversations` | List conversation messages | Session owner/admin/support |
| `POST` | `/api/sessions/{ses_id}/request-human` | Request human support | Session owner/admin/support |
| `POST` | `/api/conversations` | Persist conversation message | Authenticated |
| `GET` | `/api/itineraries/{user_id}` | List saved bookings | Self/admin/support |
| `POST` | `/api/itineraries` | Save itinerary | Self/admin/support |
| `POST` | `/api/rasa/webhook` | Frontend chatbot proxy to Rasa | Public |
| `GET` | `/api/diag` | Masked runtime diagnostics | Public |

More detail is available in `backend/docs/API_SUMMARY.md`.

## External API Integrations

| Integration | Purpose | Main config |
|---|---|---|
| Travelpayouts | Flight and ticket price lookup | `TRAVELPAYOUTS_API_TOKEN` |
| Climatiq | Carbon calculation | `CLIMATIQ_API_KEY` |
| Geoapify | Geocoding and hotel/place lookup | `GEOAPIFY_API_KEY` |
| Wikipedia REST API | Destination summaries | Public API |
| RestCountries | Country facts such as capital, region, languages, currencies | Public API |
| OpenRouter | Rasa Pro CALM LLM command generation | `OPENROUTER_API_KEY`, `LLM_MODEL_NAME` |
| Neon PostgreSQL | Application database | `DATABASE_URL` |

The application includes fallback behavior for unavailable or empty travel, hotel, and carbon responses so the planning flow can continue.

## Environment Variables

### Backend

Set these in the Hugging Face Space secrets/settings.

```env
APP_ENV=PROD
DATABASE_URL=postgresql://USER:PASSWORD@HOST/neondb?sslmode=require
JWT_SECRET=replace-with-long-random-secret
RASA_LICENSE=your-rasa-pro-license
OPENROUTER_API_KEY=your-openrouter-key
LLM_MODEL_NAME=openai/gpt-oss-20b:free
CORS_ORIGINS=https://novaplan-496111.web.app
ENABLE_API_DOCS=true
TRAVELPAYOUTS_API_TOKEN=...
CLIMATIQ_API_KEY=...
GEOAPIFY_API_KEY=...
```

Use `RASA_LICENSE` as the standard Rasa Pro license variable. `RASA_PRO_LICENSE` is treated only as a legacy compatibility fallback. `RASA_PRO_TOKEN` is not required by the current code path.

### Frontend

Set these before running the Vite production build.

```env
VITE_API_BASE_URL=https://danishk84-nprasa.hf.space
VITE_AUTH_API_BASE_URL=https://danishk84-nprasa.hf.space
VITE_RASA_WEBHOOK=/api/rasa/webhook
```

The post-booking survey URL is configured in `frontend/src/config/config.ts`:

```text
https://forms.gle/Mj1LLfasTfAnhq6s7
```

## Local Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-test.txt
```

Rasa Pro requires a valid `RASA_LICENSE`. The production deployment uses Docker on Hugging Face; local Rasa execution also requires the same licensed Rasa Pro environment.

Useful validation commands:

```bash
python -m compileall -q hf_proxy.py config db api rasa/actions
pytest -v
pytest --cov=rasa.actions --cov=api --cov-report=term-missing
```

### Frontend

```bash
cd frontend
npm install
npm run lint
npm run build
```

For local development:

```bash
npm run dev
```

## Database Setup

NovaPlan uses Neon PostgreSQL. The schema is maintained in:

```text
backend/db/schema.sql
```

Run the schema manually in the Neon SQL editor before first deployment or after resetting the database.

Primary tables:

| Table | Purpose |
|---|---|
| `users` | User/admin/support accounts |
| `sessions` | Chat/support sessions |
| `conversations` | Persisted user, bot, and support messages |
| `itineraries` | Confirmed bookings |
| `contacts` | Public contact form submissions |

## Deployment

### Backend: Hugging Face Docker Space

The backend is deployed as a Docker Space. The container starts Nginx, FastAPI, Rasa Pro, the Rasa action server, Supervisor, and the optional Streamlit UI.

Deployment steps:

1. Create or update the Hugging Face Space as Docker SDK.
2. Set required secrets/environment variables.
3. Ensure `APP_ENV=PROD` for production.
4. Push the `backend/` code to the Space repository.
5. Confirm health at:
   - https://danishk84-nprasa.hf.space/api/health
   - https://danishk84-nprasa.hf.space/api/diag

`APP_ENV=TEST` should be used only in a separate test run or temporary test deployment because it runs test evidence generation before service startup.

### Frontend: Firebase Hosting

The frontend is deployed as a static Vite build.

```bash
cd frontend
npm install
npm run build
firebase deploy --only hosting
```

`firebase.json` serves `dist/`, rewrites SPA routes to `index.html`, and uses cache headers so Firebase serves the latest hashed JavaScript bundle after deployment.

## Testing and Evidence

Backend unit tests cover Rasa custom actions, action helpers, service helpers, fallback behavior, external API mocks, and API-layer behavior.

Run locally from `backend/`:

```bash
pip install -r requirements-test.txt
pytest -v
pytest --cov=rasa.actions --cov=api --cov-report=term-missing
pytest --cov=rasa.actions --cov=api --cov-report=html
pytest -v > pytest_results.txt
```

Rasa testing assets are under:

```text
backend/rasa/tests/
backend/rasa/e2e_tests/
backend/docs/RASA_TESTING_README.md
```

When `APP_ENV=TEST`, the Hugging Face backend generates structured test evidence under `/app/results` and exposes it through:

| Endpoint | Purpose |
|---|---|
| `/api/test-results` | Test evidence index |
| `/api/test-results/summary` | Text summary |
| `/api/test-results/report` | Markdown report |
| `/api/test-results/report.html` | HTML evidence report |
| `/api/test-results/evidence.csv` | CSV evidence table |
| `/api/test-results/evidence.json` | JSON evidence |
| `/api/test-results/evidence/tables` | Dataframe-style JSON rows |
| `/api/test-results/pytest` | Raw pytest output |
| `/api/test-results/rasa-e2e` | Rasa E2E output |
| `/api/test-results/rasa/nlu/intent-report` | Rasa NLU report |
| `/api/test-results/rasa/core/story-report` | Rasa Core report |

These endpoints return `404` unless `APP_ENV=TEST`.

## Examiner Notes

- Use the live Firebase link for the main user journey.
- Use the Hugging Face `/docs` page for API inspection if `ENABLE_API_DOCS=true`.
- Admin/support credentials should be provided separately for assessment access. If the database was seeded from `backend/db/schema.sql`, the default seeded admin is documented in `backend/README.md` and should be changed after deployment.
- Production should use `APP_ENV=PROD`; test evidence mode should be run separately with `APP_ENV=TEST`.
- The current architecture intentionally does not use Firebase Authentication, local SQLite auth, browser-only auth, or social registration.

## Documentation Index

| File | Purpose |
|---|---|
| `backend/README.md` | Backend overview |
| `backend/docs/API_SUMMARY.md` | Backend endpoint summary |
| `backend/docs/DEPLOYMENT.md` | Hugging Face backend deployment |
| `backend/docs/ENVIRONMENT_VARIABLES.md` | Backend environment variables |
| `backend/docs/TESTING_README.md` | Pytest and evidence generation |
| `backend/docs/RASA_TESTING_README.md` | Rasa Pro/CALM testing guidance |
| `backend/docs/TEST_EVIDENCE_NOTES.md` | Evidence interpretation notes |
| `frontend/README.md` | Frontend overview |
| `frontend/docs/DEPLOYMENT.md` | Firebase deployment |
| `frontend/docs/ENVIRONMENT_VARIABLES.md` | Frontend build variables |

## License

This repository is prepared for academic assignment submission. Check the submitted repository license file or course requirements for permitted use and distribution.
