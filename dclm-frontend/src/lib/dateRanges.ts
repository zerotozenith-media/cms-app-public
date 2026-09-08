/**
 * Named date ranges for the filter dropdowns.
 *
 * Named periods rather than two date boxes: a leader wanting last month
 * should not have to work out its first and last day.
 */
export const DATE_RANGES = [
  { key: 'all', label: 'Any date' },
  { key: 'this-month', label: 'This month' },
  { key: 'last-month', label: 'Last month' },
  { key: 'last-3', label: 'Last 3 months' },
  { key: 'this-year', label: 'This year' },
  { key: 'last-year', label: 'Last year' },
] as const;

export type DateRangeKey = typeof DATE_RANGES[number]['key'];

function iso(d: Date) {
  return d.toISOString().slice(0, 10);
}

/** The first and last day of a range, or null for "any date". */
export function rangeBounds(key: DateRangeKey): [string, string] | null {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth();
  switch (key) {
    case 'this-month': return [iso(new Date(y, m, 1)), iso(new Date(y, m + 1, 0))];
    case 'last-month': return [iso(new Date(y, m - 1, 1)), iso(new Date(y, m, 0))];
    case 'last-3':     return [iso(new Date(y, m - 2, 1)), iso(new Date(y, m + 1, 0))];
    case 'this-year':  return [`${y}-01-01`, `${y}-12-31`];
    case 'last-year':  return [`${y - 1}-01-01`, `${y - 1}-12-31`];
    default: return null;
  }
}

export function inRange(date: string, key: DateRangeKey) {
  const b = rangeBounds(key);
  return !b || (date >= b[0] && date <= b[1]);
}
