# NovaPlan Frontend Deployment

The frontend is a React/Vite TypeScript static website deployed to Firebase Hosting.

## Build-Time Environment

Set the Vite variables before building:

```env
VITE_API_BASE_URL=https://danishk84-nprasa.hf.space
VITE_RASA_WEBHOOK=/api/rasa/webhook
VITE_AUTH_API_BASE_URL=https://danishk84-nprasa.hf.space
```

## Validation

```bash
npm install
npm run lint
npm run build
```

## Firebase Hosting

`firebase.json` is configured to deploy the `dist` folder and rewrite SPA routes to `index.html`.

```bash
npm run build
firebase deploy --only hosting
```

Firebase hosts only the static frontend. Authentication, APIs, Rasa proxying, and database access are owned by the Hugging Face backend.
