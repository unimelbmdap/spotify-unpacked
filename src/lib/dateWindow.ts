/**
 * The study's analysis window. Streaming plays outside it are dropped at parse
 * time, so it bounds the streaming history a participant donates. It does NOT
 * bound library tracks or playlists: those are donated in full regardless of
 * this window, and playlist items carry their own addedDate/lastModifiedDate
 * from any era. Widening this window widens the streaming donation, so keep
 * it in step with the ethics approval.
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
 * because Spotify's ts is ISO-8601 and Z-suffixed. A non-string ts (missing
 * or null) is treated as out of bounds rather than thrown on, so a single
 * malformed entry drops silently instead of failing the whole file.
 */
export function isWithinBounds(ts: unknown, start: string, end: string | null): boolean {
  if (typeof ts !== 'string') return false
  const day = ts.slice(0, 10)
  if (day < start) return false
  if (end && day > end) return false
  return true
}

export function isInWindow(ts: unknown): boolean {
  return isWithinBounds(ts, WINDOW_START, WINDOW_END)
}

/** Formats the window bounds as a mid-sentence phrase, eg. 'since January 2025' or 'from January 2025 to December 2025'. */
export function formatWindowLabel(start: string, end: string | null): string {
  return end ? `from ${monthYear(start)} to ${monthYear(end)}` : `since ${monthYear(start)}`
}

export const WINDOW_LABEL = formatWindowLabel(WINDOW_START, WINDOW_END)

export const WINDOW_LABEL_CAPITALISED =
  WINDOW_LABEL.charAt(0).toUpperCase() + WINDOW_LABEL.slice(1)
