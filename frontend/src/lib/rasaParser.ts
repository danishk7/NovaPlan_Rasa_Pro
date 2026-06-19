export interface RasaButton {
  title: string;
  payload: string;
}

export type RasaCustomType =
  | 'transport_options'
  | 'hotel_carousel'
  | 'carbon_card'
  | 'cultural_tips'
  | 'offset_programs'
  | 'itinerary_summary'
  | 'quick_reply'
  | 'escalation_banner'
  | string;

export interface RasaCustomPayload {
  type: RasaCustomType;
  data: Record<string, unknown>;
}

export interface RasaBotMessage {
  text?: string;
  custom?: RasaCustomPayload;
  buttons?: RasaButton[];
}

const payloadTextMap: Record<string, string> = {
  '/book_trip': 'I want to plan a trip',
  book_trip: 'I want to plan a trip',
  '/request_carbon_info': 'I want to check my carbon footprint',
  request_carbon_info: 'I want to check my carbon footprint',
  '/request_eco_hotels': 'Find eco hotels',
  request_eco_hotels: 'Find eco hotels',
  '/request_cultural_info': 'Show cultural tips',
  request_cultural_info: 'Show cultural tips',
  '/escalate_to_human': 'I want to speak to a human',
  escalate_to_human: 'I want to speak to a human',
  '/confirm_booking': 'confirm',
  confirm_booking: 'confirm',
  '/confirm_trip': 'confirm',
  confirm_trip: 'confirm',
  confirm: 'confirm',
  '/modify_booking': 'modify',
  modify_booking: 'modify',
  '/modify_trip': 'modify',
  modify_trip: 'modify',
  modify: 'modify',
  '/cancel_booking': 'cancel',
  cancel_booking: 'cancel',
  '/cancel_trip': 'cancel',
  cancel_trip: 'cancel',
  cancel: 'cancel',
  '/restart': 'start again',
  restart: 'start again',
};

const knownCustomTypes = new Set<string>([
  'transport_options',
  'hotel_carousel',
  'carbon_card',
  'cultural_tips',
  'offset_programs',
  'itinerary_summary',
  'quick_reply',
  'escalation_banner',
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function parseButton(value: unknown): RasaButton | null {
  if (!isRecord(value) || typeof value.title !== 'string') {
    return null;
  }

  return {
    title: value.title,
    payload: typeof value.payload === 'string' ? value.payload : value.title,
  };
}

function payloadData(value: Record<string, unknown>) {
  if (isRecord(value.data)) {
    return value.data;
  }

  const { type: _type, ...rest } = value;
  return rest;
}

function parseCustom(value: unknown): RasaCustomPayload | undefined {
  if (!isRecord(value)) {
    return undefined;
  }

  if (typeof value.type === 'string') {
    return {
      type: value.type,
      data: payloadData(value),
    };
  }

  // Defensive support for older backend payloads that may send { itinerary_summary: {...} }
  // instead of { type: 'itinerary_summary', data: {...} }.
  for (const [key, val] of Object.entries(value)) {
    if (knownCustomTypes.has(key)) {
      return {
        type: key,
        data: isRecord(val) ? val : { value: val },
      };
    }
  }

  return undefined;
}

export function parseRasaResponses(raw: unknown): RasaBotMessage[] {
  if (!Array.isArray(raw)) {
    return [];
  }

  return raw.map((item) => {
    const row = isRecord(item) ? item : {};
    const buttons = Array.isArray(row.buttons) ? row.buttons.map(parseButton).filter((button): button is RasaButton => Boolean(button)) : undefined;

    return {
      text: typeof row.text === 'string' ? row.text : undefined,
      custom: parseCustom(row.custom),
      buttons: buttons?.length ? buttons : undefined,
    };
  });
}

export function buttonSendText(button: RasaButton): string {
  const payload = button.payload?.trim();

  if (!payload) {
    return button.title;
  }

  if (/^\/?SetSlots\(/i.test(payload)) {
    return button.title;
  }

  return payloadTextMap[payload] ?? payloadTextMap[payload.replace(/^\//, '')] ?? payload;
}
