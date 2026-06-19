import type { Airport } from '../types/chat';

export const AIRPORTS: Airport[] = [
  { code: 'LHR', name: 'Heathrow Airport', city: 'London', lat: 51.47, lon: -0.4543 },
  { code: 'LGW', name: 'Gatwick Airport', city: 'London', lat: 51.1537, lon: -0.1821 },
  { code: 'JFK', name: 'John F. Kennedy International Airport', city: 'New York', lat: 40.6413, lon: -73.7781 },
  { code: 'EWR', name: 'Newark Liberty International Airport', city: 'New York', lat: 40.6895, lon: -74.1745 },
  { code: 'LAX', name: 'Los Angeles International Airport', city: 'Los Angeles', lat: 33.9416, lon: -118.4085 },
  { code: 'CDG', name: 'Charles de Gaulle Airport', city: 'Paris', lat: 49.0097, lon: 2.5479 },
  { code: 'FRA', name: 'Frankfurt Airport', city: 'Frankfurt', lat: 50.0379, lon: 8.5622 },
  { code: 'BER', name: 'Berlin Brandenburg Airport', city: 'Berlin', lat: 52.3667, lon: 13.5033 },
  { code: 'DXB', name: 'Dubai International Airport', city: 'Dubai', lat: 25.2532, lon: 55.3657 },
  { code: 'SIN', name: 'Singapore Changi Airport', city: 'Singapore', lat: 1.3644, lon: 103.9915 },
  { code: 'HND', name: 'Tokyo Haneda Airport', city: 'Tokyo', lat: 35.5494, lon: 139.7798 },
  { code: 'SYD', name: 'Sydney Airport', city: 'Sydney', lat: -33.9399, lon: 151.1753 },
];
