# NovaPlan Frontend

React/Vite TypeScript frontend for NovaPlan.ai, deployed as a Firebase static website.

## Architecture

The frontend integrates with the Hugging Face backend for all application APIs and chatbot traffic:

- `VITE_AUTH_API_BASE_URL` - required backend API base URL for login, registration, users, contacts, support sessions, conversations, and itineraries.
- `VITE_API_BASE_URL` + `VITE_RASA_WEBHOOK` - backend Rasa proxy used for chatbot messages.
- `USER_ACCEPTANCE_SURVEY_URL` - static frontend config value in `src/config/config.ts`, used by the booking confirmation survey prompt.

There is no Firebase Authentication, browser/local authentication fallback, SQLite dependency, or frontend-owned backend logic. Login and registration always call the deployed backend APIs.

Supplemental delivery documentation is available under `docs/`:

| File | Purpose |
|---|---|
| `docs/DEPLOYMENT.md` | Firebase deployment |
| `docs/ENVIRONMENT_VARIABLES.md` | Frontend build-time environment variables |

## Required Environment

Copy `.env.example` and set the deployed backend URL:

```env
VITE_API_BASE_URL=https://danishk84-nprasa.hf.space
VITE_RASA_WEBHOOK=/api/rasa/webhook
VITE_AUTH_API_BASE_URL=https://danishk84-nprasa.hf.space
```

## Local Development

```bash
npm install
npm run dev
```

## Validation

```bash
npm run lint
npm run build
```

## Firebase Deployment

Firebase hosting serves the generated `dist` folder.

```bash
npm run build
firebase deploy --only hosting
```
