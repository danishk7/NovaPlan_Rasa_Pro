export function formatText(value: unknown, fallback = '-') {
  if (value === undefined || value === null || value === '') return fallback;
  return String(value);
}

export function formatMoney(value: unknown) {
  if (value === undefined || value === null || value === '') return '-';
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? `EUR ${numberValue.toFixed(2)}` : `EUR ${String(value)}`;
}

export function formatKg(value: unknown) {
  if (value === undefined || value === null || value === '') return '-';
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? `${numberValue.toFixed(1)} kg CO2e` : `${String(value)} kg CO2e`;
}
