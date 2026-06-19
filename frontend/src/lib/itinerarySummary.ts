export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function value(data: Record<string, unknown>, ...keys: string[]) {
  for (const key of keys) {
    const current = data[key];
    if (current !== undefined && current !== null && current !== '') return current;
  }
  return undefined;
}

export function records(data: Record<string, unknown>, ...keys: string[]) {
  for (const key of keys) {
    const current = data[key];
    if (Array.isArray(current)) return current.filter(isRecord);
  }
  return [];
}

export function parseSummaryNote(note?: string): Record<string, unknown> {
  if (!note) return {};
  try {
    const parsed = JSON.parse(note);
    return isRecord(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

export function itinerarySummary(summary?: Record<string, unknown> | string, note?: string) {
  let data: Record<string, unknown> = {};

  if (typeof summary === 'string') {
    data = parseSummaryNote(summary);
  } else if (summary && Object.keys(summary).length > 0) {
    data = summary;
  } else {
    data = parseSummaryNote(note);
  }

  if (isRecord(data.data) && data.type === 'itinerary_summary') return data.data;
  if (isRecord(data.itinerary_summary)) return data.itinerary_summary;
  if (isRecord(data.summary)) return data.summary;
  return data;
}

export function summarySource(data: Record<string, unknown>) {
  const booking = isRecord(data.booking) ? data.booking : {};
  return { ...booking, ...data };
}
