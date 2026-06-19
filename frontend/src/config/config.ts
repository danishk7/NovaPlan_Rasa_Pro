const DEFAULT_BACKEND_URL = 'https://danishk84-nprasa.hf.space';

function normalizeUrl(value: unknown, fallback = DEFAULT_BACKEND_URL) {
  const url = typeof value === 'string' ? value.trim() : '';
  return (url || fallback).replace(/\/$/, '');
}

const apiBaseUrl = normalizeUrl(import.meta.env.VITE_API_BASE_URL);
const authApiBaseUrl = normalizeUrl(import.meta.env.VITE_AUTH_API_BASE_URL, apiBaseUrl);

export const CONFIG = {
  AUTH_API_BASE_URL: authApiBaseUrl,
  API_BASE_URL: apiBaseUrl,
  RASA_WEBHOOK: import.meta.env.VITE_RASA_WEBHOOK ?? '/api/rasa/webhook',
  USER_ACCEPTANCE_SURVEY_URL: 'https://forms.gle/Mj1LLfasTfAnhq6s7',
  OPEN_METEO_GEOCODE_URL: 'https://geocoding-api.open-meteo.com/v1/search',
  OPEN_METEO_FORECAST_URL: 'https://api.open-meteo.com/v1/forecast',
  OPEN_METEO_AIR_QUALITY_URL: 'https://air-quality-api.open-meteo.com/v1/air-quality',
};

export function getAuthApiBaseUrl() {
  return normalizeUrl(CONFIG.AUTH_API_BASE_URL, apiBaseUrl);
}
