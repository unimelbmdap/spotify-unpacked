/**
 * The study's analysis window. Plays outside it are dropped at parse time, and
 * because the donation is built from parsed entries, this is also the data
 * minimisation boundary for what a participant donates. Widening it widens the
 * donation, so keep it in step with the ethics approval.
 */
export const WINDOW_START = '2025-01-01'

/** null means no upper bound: include everything up to the present. */
export const WINDOW_END: string | null = null

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
] as const

/** 'YYYY-MM-DD' to 'Month YYYY'. */
function monthYear(day: string): string {
  const year = day.slice(0, 4)
  const month = MONTHS[Number(day.slice(5, 7)) - 1] ?? ''
  return `${month} ${year}`
}

/**
 * Both bounds are inclusive and compared on the date portion only, so setting
 * end to '2025-12-31' includes all of 31 December rather than cutting at
 * midnight. The comparison is a lexicographic string match, which is valid
 * because Spotify's ts is ISO-8601 and Z-suffixed.
 */
export function isWithinBounds(ts: string, start: string, end: string | null): boolean {
  const day = ts.slice(0, 10)
  if (day < start) return false
  if (end && day > end) return false
  return true
}

export function isInWindow(ts: string): boolean {
  return isWithinBounds(ts, WINDOW_START, WINDOW_END)
}

export const WINDOW_LABEL = WINDOW_END
  ? `${monthYear(WINDOW_START)} to ${monthYear(WINDOW_END)}`
  : `since ${monthYear(WINDOW_START)}`

export const WINDOW_LABEL_CAPITALISED =
  WINDOW_LABEL.charAt(0).toUpperCase() + WINDOW_LABEL.slice(1)
