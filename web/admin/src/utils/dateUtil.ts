import { format, isValid, parseISO } from 'date-fns';

const DATE_TIME_FORMAT = 'yyyy-MM-dd HH:mm:ss';
const DATE_FORMAT = 'yyyy-MM-dd';

type DateValue = Date | number | string | null | undefined;

function normalizeDate(value: DateValue): Date | number | null {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  if (value instanceof Date || typeof value === 'number') {
    return value;
  }

  const text = String(value).trim();
  if (!text) {
    return null;
  }

  const parsed = parseISO(text);
  if (isValid(parsed)) {
    return parsed;
  }

  const fallback = new Date(text);
  return isValid(fallback) ? fallback : null;
}

export function formatToDateTime(date: DateValue, formatStr = DATE_TIME_FORMAT): string {
  const normalized = normalizeDate(date);
  return normalized === null ? '' : format(normalized, formatStr);
}

export function formatToDate(date: DateValue, formatStr = DATE_FORMAT): string {
  const normalized = normalizeDate(date);
  return normalized === null ? '' : format(normalized, formatStr);
}
