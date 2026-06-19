import { CONFIG } from '../config/config';
import { AIRPORTS } from './travelMetadata';
import type { Airport } from '../types/chat';

interface GeoResult {
  name: string;
  country?: string;
  latitude: number;
  longitude: number;
}

export interface ClimateSnapshot {
  location: string;
  temperature: number;
  windSpeed: number;
  conditionCode: number;
  airQualityIndex?: number;
  particulateMatter?: number;
  airport: Airport & { distanceKm: number };
}

export async function getClimateSnapshot(query: string): Promise<ClimateSnapshot> {
  const location = query.trim() || 'London';
  const geo = await geocode(location);
  const [weather, air] = await Promise.all([fetchWeather(geo), fetchAirQuality(geo)]);
  const airport = nearestAirport(geo.latitude, geo.longitude);

  return {
    location: `${geo.name}${geo.country ? `, ${geo.country}` : ''}`,
    temperature: Math.round(weather.current.temperature_2m),
    windSpeed: Math.round(weather.current.wind_speed_10m),
    conditionCode: weather.current.weather_code,
    airQualityIndex: air.current?.european_aqi,
    particulateMatter: air.current?.pm2_5,
    airport,
  };
}

async function geocode(query: string): Promise<GeoResult> {
  const params = new URLSearchParams({ name: query, count: '1', language: 'en', format: 'json' });
  const response = await fetch(`${CONFIG.OPEN_METEO_GEOCODE_URL}?${params}`);
  if (!response.ok) {
    throw new Error('Unable to load location data');
  }
  const data = await response.json();
  const result = data.results?.[0];

  if (!result) {
    throw new Error('Location not found');
  }

  return result;
}

async function fetchWeather(geo: GeoResult) {
  const params = new URLSearchParams({
    latitude: String(geo.latitude),
    longitude: String(geo.longitude),
    current: 'temperature_2m,wind_speed_10m,weather_code',
  });
  const response = await fetch(`${CONFIG.OPEN_METEO_FORECAST_URL}?${params}`);
  if (!response.ok) {
    throw new Error('Unable to load weather data');
  }
  return response.json();
}

async function fetchAirQuality(geo: GeoResult) {
  const params = new URLSearchParams({
    latitude: String(geo.latitude),
    longitude: String(geo.longitude),
    current: 'european_aqi,pm2_5',
  });
  const response = await fetch(`${CONFIG.OPEN_METEO_AIR_QUALITY_URL}?${params}`);
  if (!response.ok) {
    throw new Error('Unable to load air quality data');
  }
  return response.json();
}

function nearestAirport(lat: number, lon: number) {
  return AIRPORTS
    .map((airport) => ({ ...airport, distanceKm: Math.round(distanceKm(lat, lon, airport.lat, airport.lon)) }))
    .sort((a, b) => a.distanceKm - b.distanceKm)[0];
}

function distanceKm(lat1: number, lon1: number, lat2: number, lon2: number) {
  const radius = 6371;
  const dLat = toRadians(lat2 - lat1);
  const dLon = toRadians(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  return radius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function toRadians(value: number) {
  return (value * Math.PI) / 180;
}
