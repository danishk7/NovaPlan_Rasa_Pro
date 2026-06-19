# NovaPlan Frontend Environment Variables

Vite variables are build-time configuration. They must be available before running `npm run build`.

| Variable | Required | Purpose | Expected format | Used by | Secret |
|---|---:|---|---|---|---:|
| `VITE_API_BASE_URL` | Yes | Hugging Face backend base URL for Rasa webhook calls. | `https://danishk84-nprasa.hf.space` | `src/config/config.ts`, `src/lib/api.ts` | No |
| `VITE_RASA_WEBHOOK` | No | Rasa proxy path under the backend. | `/api/rasa/webhook` | `src/config/config.ts`, `src/lib/api.ts` | No |
| `VITE_AUTH_API_BASE_URL` | Yes | Backend API base URL for auth, users, contacts, sessions, conversations, and itineraries. | `https://danishk84-nprasa.hf.space` | `src/config/config.ts`, `src/lib/api.ts` | No |
| `USER_ACCEPTANCE_SURVEY_URL` | No env variable | Static config value for the post-booking survey button. | `https://forms.gle/Mj1LLfasTfAnhq6s7` | `src/config/config.ts`, `src/components/chatbot/SurveyFeedback.tsx` | No |

The frontend does not use Firebase Authentication, browser-only auth, local auth fallback, SQLite, or frontend secrets.
