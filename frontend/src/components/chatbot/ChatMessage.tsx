import type { ReactNode } from 'react';
import type { ChatMessage as MessageType } from '../../types/chat';
import { buttonSendText, type RasaButton } from '../../lib/rasaParser';
import { formatKg, formatMoney, formatText } from '../../lib/formatters';
import { isRecord, records, value } from '../../lib/itinerarySummary';
import SurveyFeedback from './SurveyFeedback';

interface Props {
  message: MessageType;
  onQuickReply?: (text: string) => void;
  onRequestHuman?: () => void;
  interactive?: boolean;
}

type QuickReply = string | { title?: string; payload?: string };

function renderInlineMarkdown(source: string) {
  return source.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={index}>{part.slice(2, -2)}</strong>;
    if (part.startsWith('*') && part.endsWith('*')) return <em key={index}>{part.slice(1, -1)}</em>;
    return part;
  });
}

function renderMarkdownLite(source: string): ReactNode[] {
  return source.split('\n').map((line, index) => {
    const numbered = line.match(/^\s*(\d+)\.\s+(.+)$/);
    const bullet = line.match(/^\s*[-*]\s+(.+)$/);
    return (
      <span key={index} className={numbered || bullet ? 'block pl-1' : undefined}>
        {numbered ? <><span className="font-bold text-emerald-700">{numbered[1]}.</span> {renderInlineMarkdown(numbered[2])}</> : null}
        {bullet ? <>- {renderInlineMarkdown(bullet[1])}</> : null}
        {!numbered && !bullet ? renderInlineMarkdown(line) : null}
        {index < source.split('\n').length - 1 ? <br /> : null}
      </span>
    );
  });
}

function stripButtonEcho(messageText: string, buttons?: RasaButton[]) {
  const trimmed = messageText.trim();
  if (/^\/?SetSlots\(/i.test(trimmed)) return '';
  if (!buttons?.length) return messageText;
  let cleaned = messageText;
  for (const button of buttons) {
    cleaned = cleaned.replace(button.title, '').replace(button.payload, '');
  }
  cleaned = cleaned.replace(/\s*\|\s*(?=\||$)/g, ' ').replace(/\s{2,}/g, ' ').trim();
  return cleaned || messageText;
}

function quickReplyLabel(reply: QuickReply) {
  return typeof reply === 'string' ? reply : reply.title ?? reply.payload ?? '';
}

function quickReplyPayload(reply: QuickReply) {
  return typeof reply === 'string' ? reply : reply.payload ?? reply.title ?? '';
}

export default function ChatMessage({ message, onQuickReply, onRequestHuman, interactive = true }: Props) {
  const isUser = message.sender === 'user';
  const isSupport = message.sender === 'support';
  const custom = message.rasa?.custom;
  const data = custom?.data ?? {};
  const visibleText = stripButtonEcho(message.text, message.rasa?.buttons);

  const sendQuickReply = (payload: string, label?: string) => {
    if (interactive && payload) onQuickReply?.(buttonSendText({ title: label ?? payload, payload }));
  };

  const renderCustom = () => {
    if (!custom?.type) return null;

    switch (custom.type) {
      case 'transport_options': {
        const options = records(data, 'options', 'transport_options', 'items', 'results');
        return (
          <section className="mt-3 space-y-3 rounded-lg border border-sky-200 bg-sky-50 p-4 text-xs">
            <div>
              <p className="font-bold text-sky-900">Travel options</p>
              <p className="text-slate-600">
                {formatText(value(data, 'origin', 'from'))} to {formatText(value(data, 'destination', 'to'))}
                {data.api_source ? ` - ${formatText(data.api_source)} data` : ''}
              </p>
            </div>
            {options.length === 0 && <p className="text-slate-600">No live options were returned yet.</p>}
            {options.map((option, index) => {
              const mode = formatText(value(option, 'mode', 'transport_mode', 'type'));
              return (
                <button
                  key={`${mode}-${index}`}
                  type="button"
                  onClick={() => sendQuickReply(`I choose ${mode}`, mode)}
                  disabled={!interactive}
                  className="block w-full rounded-lg border border-slate-200 bg-white p-3 text-left transition hover:border-sky-400 disabled:cursor-default disabled:hover:border-slate-200"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-bold capitalize text-slate-950">{mode}</span>
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-700">{formatMoney(value(option, 'price_eur', 'price', 'cost', 'total_price'))}</span>
                  </div>
                  <div className="mt-2 grid gap-1 text-slate-600 sm:grid-cols-2">
                    <span>Duration: {formatText(value(option, 'duration', 'duration_text'))}</span>
                    <span>Carbon: {formatKg(value(option, 'emissions_kg', 'kg_co2e', 'emissions', 'carbon_kg'))}</span>
                    {value(option, 'provider', 'airline', 'carrier') && <span>Provider: {formatText(value(option, 'provider', 'airline', 'carrier'))}</span>}
                    {value(option, 'departure_time', 'depart_at', 'departure', 'departure_at') && <span>Depart: {formatText(value(option, 'departure_time', 'depart_at', 'departure', 'departure_at'))}</span>}
                    {value(option, 'return_time', 'return_at', 'return') && <span>Return: {formatText(value(option, 'return_time', 'return_at', 'return'))}</span>}
                  </div>
                </button>
              );
            })}
          </section>
        );
      }

      case 'hotel_carousel': {
        const hotels = records(data, 'hotels', 'options', 'items', 'results');
        return (
          <section className="mt-3 space-y-2 rounded-lg border border-slate-200 bg-white p-4 text-xs">
            <p className="font-bold text-emerald-800">Hotels in {formatText(value(data, 'destination', 'city'))}</p>
            {hotels.length === 0 && <p className="text-slate-600">No hotel cards were returned yet.</p>}
            {hotels.map((hotel, index) => (
              <div key={index} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="font-semibold text-slate-950">{formatText(value(hotel, 'name', 'title'))}</p>
                <p className="text-slate-600">{formatMoney(value(hotel, 'price_eur', 'price', 'nightly_price'))} - Rating {formatText(value(hotel, 'rating', 'stars'))}</p>
                {value(hotel, 'address', 'location') && <p className="mt-1 text-slate-500">{formatText(value(hotel, 'address', 'location'))}</p>}
              </div>
            ))}
          </section>
        );
      }

      case 'carbon_card': {
        const total = value(data, 'kg_co2e', 'carbon_kg', 'carbon_total_kg', 'total_kg');
        return (
          <section className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-xs">
            <p className="font-bold text-emerald-900">Carbon estimate: {formatKg(total)} ({formatText(value(data, 'mode', 'transport_mode'))})</p>
            {value(data, 'per_person', 'per_traveller_kg') !== undefined && <p className="text-slate-600">Per traveller: {formatKg(value(data, 'per_person', 'per_traveller_kg'))}</p>}
            <p className="text-slate-600">{formatText(value(data, 'label', 'impact', 'impact_label'), 'Carbon estimate')} - Source: {formatText(value(data, 'source', 'api_source'), 'NovaPlan')}</p>
          </section>
        );
      }

      case 'cultural_tips': {
        const blocks = isRecord(data.data) ? (data.data as Record<string, { tips?: string[]; category?: string }>) : undefined;
        const fallbackTips = ['country_overview', 'eco_activities', 'responsible_tips', 'tips']
          .flatMap((key) => (Array.isArray(data[key]) ? (data[key] as string[]) : []))
          .slice(0, 6);
        return (
          <section className="mt-3 rounded-lg border border-slate-200 bg-white p-4 text-xs">
            <p className="font-bold text-emerald-800">Culture and responsible travel: {formatText(data.destination)}</p>
            {blocks
              ? Object.entries(blocks).map(([key, block]) => (
                  <div key={key} className="mt-3 border-t border-slate-100 pt-3">
                    <p className="font-semibold text-slate-950">{block.category ?? key.replace(/_/g, ' ')}</p>
                    <ul className="mt-1 list-disc pl-4 text-slate-600">
                      {(block.tips ?? []).slice(0, 3).map((tip, index) => <li key={index}>{tip}</li>)}
                    </ul>
                  </div>
                ))
              : fallbackTips.map((tip, index) => <p key={index} className="mt-2 text-slate-600">- {tip}</p>)}
          </section>
        );
      }

      case 'offset_programs':
        return (
          <section className="mt-3 rounded-lg border border-slate-200 bg-white p-4 text-xs">
            <p className="font-bold text-emerald-800">Offset programs ({formatText(value(data, 'carbon_tonnes', 'tonnes'))} t CO2)</p>
            {records(data, 'programs', 'options').map((program, index) => (
              <div key={index} className="mt-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="font-semibold text-slate-950">{formatText(program.name)}</p>
                <p className="text-slate-600">{formatMoney(value(program, 'cost_per_tonne', 'price'))}/tonne</p>
              </div>
            ))}
          </section>
        );

      case 'itinerary_summary': {
        const isConfirmed = data.status === 'confirmed' || data.confirmed === true;
        const travelDates = value(data, 'travel_dates', 'dates') ?? [value(data, 'start_date', 'departure_date'), value(data, 'end_date', 'return_date')].filter(Boolean).join(' to ');
        const destination = formatText(value(data, 'destination', 'city', 'country'));
        const aboutDestination = value(data, 'destination_description', 'wiki_summary', 'about_destination', 'country_overview', 'description');
        const tickets = records(data, 'ticket_options', 'tickets', 'transport_options', 'flight_options', 'travel_options', 'options');
        const hotels = records(data, 'hotel_options', 'hotels', 'stays', 'accommodation_options');
        const carbonRows = records(data, 'carbon_breakdown', 'emissions_breakdown', 'carbon_options');
        const explicitTotal = value(data, 'price_total', 'total_price', 'total_price_eur', 'trip_price', 'total_cost', 'estimated_total');
        return (
          <>
            <section className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-xs">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-sm font-black text-emerald-900">{isConfirmed ? 'Booking confirmed' : 'Trip Summary'}</p>
                {value(data, 'reference', 'booking_reference') && <p className="text-slate-600">Reference #{formatText(value(data, 'reference', 'booking_reference'))}</p>}
              </div>
              <span className="rounded-full bg-white px-3 py-1 font-bold text-emerald-800">{formatText(data.status, isConfirmed ? 'confirmed' : 'draft')}</span>
            </div>

            {(destination !== '-' || aboutDestination) && (
              <div className="mt-4 rounded-lg border border-emerald-100 bg-white p-3">
                <p className="font-black text-slate-950">About booking and destination</p>
                {destination !== '-' && <p className="mt-1 font-semibold text-emerald-800">{destination}</p>}
                {aboutDestination && <p className="mt-2 text-sm leading-6 text-slate-600">{formatText(aboutDestination)}</p>}
              </div>
            )}

            <dl className="mt-4 grid gap-3 sm:grid-cols-2">
              <SummaryItem label="Route" value={`${formatText(data.origin)} to ${formatText(data.destination)}`} />
              <SummaryItem label="Dates" value={formatText(travelDates)} />
              <SummaryItem label="Travellers" value={formatText(value(data, 'num_travellers', 'travellers'))} />
              <SummaryItem label="Budget" value={formatMoney(value(data, 'budget_eur', 'budget'))} />
              <SummaryItem label="Transport" value={formatText(value(data, 'transport_mode', 'mode'))} />
              <SummaryItem label="Trip price" value={formatMoney(value(data, 'price_total', 'total_price', 'total_price_eur'))} />
              <SummaryItem label="Carbon" value={formatKg(value(data, 'carbon_kg', 'kg_co2e', 'carbon_total_kg'))} />
              <SummaryItem label="Live tickets" value={value(data, 'ticket_options_fetched') ? 'Fetched' : 'Skipped / unavailable'} />
            </dl>

            <OptionSection title="Ticket options" rows={tickets} empty="No ticket options were returned yet." />
            <OptionSection title="Hotel options" rows={hotels} empty="No hotel options were returned yet." />

            <div className="mt-3 rounded-lg border border-emerald-100 bg-white p-3">
              <p className="font-black text-slate-950">Carbon footprint</p>
              <p className="mt-1 text-slate-600">{formatKg(value(data, 'carbon_kg', 'kg_co2e', 'carbon_total_kg', 'total_kg'))}</p>
              {carbonRows.length > 0 && <CompactRows rows={carbonRows} />}
            </div>

            <div className="mt-3 rounded-lg border border-emerald-100 bg-white p-3">
              <p className="font-black text-slate-950">Trip price</p>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                <SummaryItem label="Transport" value={formatMoney(value(data, 'transport_price', 'ticket_price', 'flight_price'))} />
                <SummaryItem label="Hotel" value={formatMoney(value(data, 'hotel_price', 'accommodation_price'))} />
                <SummaryItem label="Carbon offset" value={formatMoney(value(data, 'offset_price', 'carbon_offset_price'))} />
                <SummaryItem label="Estimated total" value={formatMoney(explicitTotal)} />
              </div>
            </div>

            {!isConfirmed && (
              <div className="mt-4 flex flex-wrap gap-2">
                <button type="button" onClick={() => sendQuickReply('confirm', 'Confirm')} className="rounded-lg bg-emerald-600 px-3 py-2 font-bold text-white">Confirm</button>
                <button type="button" onClick={() => sendQuickReply('modify', 'Modify')} className="rounded-lg border border-slate-300 px-3 py-2 font-bold text-slate-800 hover:border-emerald-500">Modify</button>
                <button type="button" onClick={() => sendQuickReply('cancel', 'Cancel')} className="rounded-lg border border-red-200 px-3 py-2 font-bold text-red-700 hover:bg-red-50">Cancel</button>
              </div>
            )}
            </section>
            {interactive && isConfirmed && <SurveyFeedback />}
          </>
        );
      }

      case 'quick_reply': {
        const replies = Array.isArray(data.replies) ? (data.replies as QuickReply[]) : Array.isArray(data.buttons) ? (data.buttons as QuickReply[]) : [];
        return (
          <div className="mt-3 flex flex-wrap gap-2">
            {replies.map((reply, index) => {
              const label = quickReplyLabel(reply);
              const payload = quickReplyPayload(reply);
              return (
                <button key={`${label}-${index}`} type="button" disabled={!interactive} onClick={() => sendQuickReply(payload, label)} className="rounded-lg border border-slate-300 px-3 py-2 text-xs hover:border-emerald-500 disabled:cursor-default disabled:hover:border-slate-300">
                  {label}
                </button>
              );
            })}
          </div>
        );
      }

      case 'escalation_banner':
        return (
          <section className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-xs">
            <p className="font-black text-amber-900">Human support requested</p>
            <p className="mt-1 text-slate-600">A support agent can now join this conversation from the support console.</p>
            {value(data, 'ticket_id', 'id') && <p className="mt-2 text-slate-600">Ticket #{formatText(value(data, 'ticket_id', 'id'))} - Priority: {formatText(value(data, 'severity', 'priority'))}</p>}
            {interactive && (
              <button type="button" onClick={onRequestHuman} className="mt-3 rounded-lg bg-amber-400 px-3 py-2 font-bold text-slate-950">
                Notify support team
              </button>
            )}
          </section>
        );

      default:
        return null;
    }
  };

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[90%] rounded-lg px-4 py-3 text-sm leading-6 sm:max-w-[82%] ${
          isUser ? 'bg-emerald-600 text-white' : isSupport ? 'bg-amber-400 text-slate-950' : 'border border-slate-200 bg-white text-slate-800'
        }`}
      >
        {visibleText && <p className="whitespace-pre-wrap">{renderMarkdownLite(visibleText)}</p>}
        {renderCustom()}
        {message.rasa?.buttons && (
          <div className="mt-3 flex flex-wrap gap-2">
            {message.rasa.buttons.map((button) => (
              <button key={`${button.title}-${button.payload}`} type="button" disabled={!interactive} onClick={() => interactive && onQuickReply?.(buttonSendText(button))} className="rounded-lg border border-slate-300 px-3 py-2 text-xs hover:border-emerald-500 disabled:cursor-default disabled:hover:border-slate-300">
                {button.title}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <dt className="text-[10px] font-black uppercase tracking-widest text-slate-500">{label}</dt>
      <dd className="mt-1 font-semibold text-slate-950">{value}</dd>
    </div>
  );
}

function OptionSection({ title, rows, empty }: { title: string; rows: Record<string, unknown>[]; empty: string }) {
  return (
    <div className="mt-3 rounded-lg border border-emerald-100 bg-white p-3">
      <p className="font-black text-slate-950">{title}</p>
      {rows.length === 0 ? <p className="mt-1 text-slate-500">{empty}</p> : <CompactRows rows={rows} />}
    </div>
  );
}

function CompactRows({ rows }: { rows: Record<string, unknown>[] }) {
  return (
    <div className="mt-2 space-y-2">
      {rows.slice(0, 5).map((row, rowIndex) => (
        <div key={rowIndex} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
          <div className="grid gap-1 sm:grid-cols-2">
            {Object.entries(row)
              .filter(([, current]) => current !== undefined && current !== null && current !== '' && typeof current !== 'object')
              .slice(0, 8)
              .map(([key, current]) => (
                <p key={key} className="text-slate-600">
                  <span className="font-semibold text-slate-800">{key.replace(/_/g, ' ')}:</span> {String(current)}
                </p>
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}
