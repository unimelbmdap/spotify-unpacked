import { describe, it, expect } from 'vitest'
import {
  isInWindow,
  isWithinBounds,
  formatWindowLabel,
  WINDOW_LABEL,
  WINDOW_LABEL_CAPITALISED,
} from '@/lib/dateWindow'

describe('isInWindow', () => {
  it('excludes a play before the start', () => {
    expect(isInWindow('2024-12-31T23:59:59Z')).toBe(false)
  })

  it('includes a play on the start date, which is inclusive', () => {
    expect(isInWindow('2025-01-01T00:00:00Z')).toBe(true)
  })

  it('includes a play after the start', () => {
    expect(isInWindow('2025-07-01T10:00:00Z')).toBe(true)
  })

  it('includes a play beyond the calendar year, proving there is no upper bound', () => {
    expect(isInWindow('2026-04-01T08:00:00Z')).toBe(true)
  })
})

describe('isWithinBounds', () => {
  it('includes a play at the last instant of the end date, proving the end bound is not cut at midnight', () => {
    expect(isWithinBounds('2025-12-31T23:59:59Z', '2025-01-01', '2025-12-31')).toBe(true)
  })

  it('excludes a play on the day after an explicit end date', () => {
    expect(isWithinBounds('2026-01-01T00:00:00Z', '2025-01-01', '2025-12-31')).toBe(false)
  })

  it('includes a play on the start date, which is inclusive', () => {
    expect(isWithinBounds('2025-01-01T00:00:00Z', '2025-01-01', '2025-12-31')).toBe(true)
  })

  it('excludes a play before the start date', () => {
    expect(isWithinBounds('2024-12-31T23:59:59Z', '2025-01-01', '2025-12-31')).toBe(false)
  })

  it('includes everything after the start when the end is unbounded', () => {
    expect(isWithinBounds('2099-01-01T00:00:00Z', '2025-01-01', null)).toBe(true)
  })

  it('excludes a non-string ts instead of throwing, so a malformed entry drops rather than failing the whole file', () => {
    expect(isWithinBounds(undefined, '2025-01-01', null)).toBe(false)
    expect(isWithinBounds(null, '2025-01-01', null)).toBe(false)
  })
})

describe('formatWindowLabel', () => {
  it('reads as a mid-sentence phrase when open-ended', () => {
    expect(formatWindowLabel('2025-01-01', null)).toBe('since January 2025')
  })

  it('reads as a grammatical mid-sentence phrase when bounded', () => {
    expect(formatWindowLabel('2025-01-01', '2025-12-31')).toBe('from January 2025 to December 2025')
  })
})

describe('window copy', () => {
  it('reads as a mid-sentence phrase', () => {
    expect(WINDOW_LABEL).toBe('since January 2025')
  })

  it('offers a capitalised form for standalone captions', () => {
    expect(WINDOW_LABEL_CAPITALISED).toBe('Since January 2025')
  })
})
