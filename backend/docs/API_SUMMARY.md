# NovaPlan Backend API Summary

All application API routes are mounted under `/api` by `hf_proxy.py`. Authentication uses JWT bearer tokens issued by `/api/login` and `/api/register`.

| Method | Path | Purpose | Auth |
|---|---|---|---|
| `GET` | `/api/health` | Aggregate backend health. | No |
| `GET` | `/api/health/database` | Neon PostgreSQL health check. | No |
| `GET` | `/api/health/db` | Legacy database health alias. | No |
| `GET` | `/api/health/rasa` | Rasa server health. | No |
| `GET` | `/api/health/actions` | Rasa action server health. | No |
| `GET` | `/api/health/integrations` | External API reachability summary. | No |
| `POST` | `/api/register` | Register a user and return JWT/user profile. | No |
| `POST` | `/api/login` | Authenticate user/admin/support and return JWT/user profile. | No |
| `GET` | `/api/users` | List users. | Admin |
| `PATCH` | `/api/users/{user_id}/role` | Update user role. | Admin |
| `DELETE` | `/api/users/{user_id}` | Delete user. | Admin |
| `GET` | `/api/profile/{user_id}` | Read profile. | Self, admin, support |
| `PATCH` | `/api/profile/{user_id}` | Update profile. Non-admin users cannot update role. | Self or admin |
| `POST` | `/api/contact` | Submit public contact form. | No |
| `GET` | `/api/contacts` | List contact messages. | Admin or support |
| `GET` | `/api/sessions/user/{user_id}` | Get or create a user chat session. | Self, admin, support |
| `GET` | `/api/sessions` | List chat/support sessions. | Admin or support |
| `GET` | `/api/sessions/{ses_id}/conversations` | List conversations for a session. | Session owner, admin, support |
| `POST` | `/api/sessions/{ses_id}/request-human` | Mark session for human support. | Session owner, admin, support |
| `POST` | `/api/conversations` | Save a conversation message. | Authenticated; user scoped to own session |
| `GET` | `/api/itineraries/{user_id}` | List saved itineraries. | Self, admin, support |
| `POST` | `/api/itineraries` | Save itinerary. | Self, admin, support |
| `POST` | `/api/rasa/webhook` | Frontend chatbot proxy to Rasa REST webhook with itinerary persistence post-processing. | No |
| `GET` | `/api/rasa/health` | Direct Rasa proxy health. | No |
| `GET` | `/api/diag` | Runtime diagnostic payload with masked environment status. | No |
| `GET` | `/api/test-results*` | Runtime test evidence artifacts. Returns `404` unless `APP_ENV=TEST`. | Test mode only |

Swagger/OpenAPI is exposed only when `ENABLE_API_DOCS=true`.
