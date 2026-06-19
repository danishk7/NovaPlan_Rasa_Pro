import type { Itinerary } from '../types/chat';
import { formatKg, formatMoney, formatText } from './formatters';
import { isRecord, itinerarySummary, records, summarySource, value } from './itinerarySummary';

export interface BookingRow {
  ref: string;
  origin: string;
  destination: string;
  travelDates: string;
  passengers: string;
  mode: string;
  carbon: string;
  totalPrice: string;
  title: string;
  note: string;
  summary: Record<string, unknown>;
  status?: string;
  createdAt?: string;
}

export function bookingFromItinerary(item: Itinerary): BookingRow {
  const data = itinerarySummary(item.summary, item.note);
  const source = summarySource(data);
  const itemId = String(item.itnId);
  const titleParts = item.title.split(/\s+to\s+|→|\|/).map((part) => part.trim()).filter(Boolean);
  const routeParts = item.title.split(/\s+to\s+|→/).map((part) => part.trim()).filter(Boolean);
  const noteRef = item.note?.match(/Reference:\s*#?([A-Z0-9-]+)/i)?.[1];
  const noteCarbon = item.note?.match(/Estimated emissions:\s*([0-9.]+)/i)?.[1];
  const noteMode = item.title.split('|')[1]?.trim();
  const tripPrice = isRecord(data.trip_price) ? data.trip_price : {};
  const carbon = isRecord(data.carbon) ? data.carbon : {};

  return {
    ref: formatText(value(source, 'reference', 'booking_reference') ?? noteRef ?? itemId.slice(0, 8).toUpperCase()),
    origin: formatText(value(source, 'origin', 'from') ?? routeParts[0] ?? titleParts[0]),
    destination: formatText(value(source, 'destination', 'to') ?? routeParts[1] ?? titleParts[1]),
    travelDates: formatText(value(source, 'travel_dates', 'dates') ?? item.time),
    passengers: formatText(value(source, 'num_travellers', 'travellers', 'passengers'), '1'),
    mode: formatText(value(source, 'transport_mode', 'mode') ?? noteMode),
    carbon: formatKg(value(source, 'carbon_kg', 'kg_co2e', 'carbon_total_kg') ?? value(carbon, 'kg_co2e', 'carbon_kg', 'total_kg') ?? noteCarbon),
    totalPrice: formatMoney(value(source, 'price_total', 'total_price', 'total_price_eur') ?? value(tripPrice, 'total', 'estimated_total')),
    title: item.title,
    note: item.note || '',
    summary: data,
    status: item.status,
    createdAt: item.createdAt,
  };
}

function escapeHtml(value: string) {
  const entities: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  };
  return value.replace(/[&<>"']/g, (char) => entities[char] ?? char);
}

function cell(label: string, value: unknown) {
  return `<tr><th>${escapeHtml(label)}</th><td>${escapeHtml(formatText(value))}</td></tr>`;
}

function moneyCell(label: string, value: unknown) {
  return `<tr><th>${escapeHtml(label)}</th><td>${escapeHtml(formatMoney(value))}</td></tr>`;
}

function kgCell(label: string, value: unknown) {
  return `<tr><th>${escapeHtml(label)}</th><td>${escapeHtml(formatKg(value))}</td></tr>`;
}

function compactCards(rows: Record<string, unknown>[]) {
  if (!rows.length) return '<p class="muted">No options were returned.</p>';
  return rows.slice(0, 8).map((row) => {
    const fields = Object.entries(row)
      .filter(([, value]) => value !== undefined && value !== null && value !== '' && typeof value !== 'object')
      .slice(0, 10)
      .map(([key, value]) => `<p><strong>${escapeHtml(key.replace(/_/g, ' '))}:</strong> ${escapeHtml(String(value))}</p>`)
      .join('');
    return `<div class="option">${fields}</div>`;
  }).join('');
}

function section(title: string, body: string) {
  return `<section class="section"><h2>${escapeHtml(title)}</h2>${body}</section>`;
}

function itineraryDetailsHtml(booking: BookingRow) {
  const data = itinerarySummary(booking.summary, booking.note);
  const source = summarySource(data);
  const destinationInfo = isRecord(data.destination_info) ? data.destination_info : {};
  const tripPrice = isRecord(data.trip_price) ? data.trip_price : {};
  const carbon = isRecord(data.carbon) ? data.carbon : {};
  const tickets = records(data, 'ticket_options', 'tickets', 'transport_options', 'flight_options', 'travel_options', 'options');
  const hotels = records(data, 'hotel_options', 'hotels', 'stays', 'accommodation_options');
  const description = value(source, 'destination_description', 'wiki_summary', 'about_destination', 'country_overview', 'description') ?? destinationInfo.description;

  const bookingSummary = `
    <div class="destination">
      <h3>${escapeHtml(formatText(value(source, 'destination', 'city', 'country') ?? booking.destination))}</h3>
      ${description ? `<p>${escapeHtml(formatText(description))}</p>` : ''}
      ${destinationInfo.wiki_url ? `<p><a href="${escapeHtml(String(destinationInfo.wiki_url))}">More about destination</a></p>` : ''}
    </div>
    <table>
      <tbody>
        ${cell('Book Ref.', booking.ref)}
        ${cell('Origin', value(source, 'origin', 'from') ?? booking.origin)}
        ${cell('Destination', value(source, 'destination', 'to') ?? booking.destination)}
        ${cell('Travel Dates', value(source, 'travel_dates', 'dates') ?? booking.travelDates)}
        ${cell('Travellers', value(source, 'num_travellers', 'travellers', 'passengers') ?? booking.passengers)}
        ${cell('Budget', formatMoney(value(source, 'budget_eur', 'budget')))}
        ${cell('Transport', value(source, 'transport_mode', 'mode') ?? booking.mode)}
        ${cell('Status', booking.status)}
        ${cell('Saved At', booking.createdAt)}
      </tbody>
    </table>
  `;

  const carbonBody = `
    <table>
      <tbody>
        ${kgCell('Estimated emissions', value(source, 'carbon_kg', 'kg_co2e', 'carbon_total_kg') ?? carbon.kg_co2e)}
        ${cell('Impact', value(carbon, 'label', 'impact', 'impact_label') ?? booking.carbon)}
      </tbody>
    </table>
  `;

  const priceBody = `
    <table>
      <tbody>
        ${moneyCell('Ticket total', value(tripPrice, 'ticket_total', 'transport_total', 'flight_total'))}
        ${moneyCell('Hotel total', value(tripPrice, 'hotel_total', 'accommodation_total'))}
        ${moneyCell('Ticket per traveller', value(tripPrice, 'ticket_price_per_traveller', 'ticket_price', 'flight_price'))}
        ${moneyCell('Hotel per night', value(tripPrice, 'hotel_price_per_night', 'nightly_price'))}
        ${cell('Nights', value(tripPrice, 'nights'))}
        ${moneyCell('Estimated total', value(source, 'price_total', 'total_price', 'total_price_eur', 'estimated_total') ?? tripPrice.total)}
      </tbody>
    </table>
  `;

  return [
    section('About Booking and Destination', bookingSummary),
    section('Ticket Options', compactCards(tickets)),
    section('Hotel Options', compactCards(hotels)),
    section('Carbon Footprint', carbonBody),
    section('Trip Price', priceBody),
  ].join('');
}

export function openBookingTicket(booking: BookingRow) {
  const ticket = window.open('', '_blank', 'width=980,height=720');
  if (!ticket) return;
  const safe = Object.fromEntries(Object.entries(booking).map(([key, value]) => [key, escapeHtml(String(value || ''))]));

  ticket.document.write(`
    <!doctype html>
    <html>
      <head>
        <title>NovaPlan Booking ${safe.ref}</title>
        <style>
          body { font-family: Arial, sans-serif; color: #0f172a; margin: 32px; }
          h1 { margin: 0 0 8px; }
          h2 { margin: 0 0 12px; font-size: 18px; }
          h3 { margin: 0 0 8px; font-size: 16px; color: #047857; }
          a { color: #047857; font-weight: 700; }
          .meta, .muted { color: #475569; margin-bottom: 24px; }
          .section { border: 1px solid #cbd5e1; border-radius: 8px; padding: 18px; margin-top: 18px; page-break-inside: avoid; }
          .destination { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 14px; }
          .destination p { line-height: 1.55; margin: 8px 0 0; }
          .option { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-top: 10px; }
          .option p { margin: 4px 0; line-height: 1.4; }
          table { width: 100%; border-collapse: collapse; margin-top: 16px; }
          th, td { border: 1px solid #cbd5e1; padding: 12px; text-align: left; }
          th { width: 220px; }
          th { background: #ecfdf5; }
          .actions { margin-top: 24px; }
          button { background: #059669; color: white; border: 0; padding: 10px 16px; border-radius: 8px; font-weight: 700; }
          @media print { .actions { display: none; } body { margin: 18px; } }
        </style>
      </head>
      <body>
        <h1>NovaPlan Booking Ticket</h1>
        <p class="meta">Booking reference ${safe.ref}</p>
        <p class="meta">${safe.title}</p>
        ${itineraryDetailsHtml(booking)}
        ${booking.note && booking.note.trim().startsWith('{') ? '' : `<p class="meta">${safe.note}</p>`}
        <div class="actions"><button onclick="window.print()">Download PDF / Print</button></div>
      </body>
    </html>
  `);
  ticket.document.close();
}
