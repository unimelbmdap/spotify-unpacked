import { describe, it, expect } from 'vitest'
import { isInWindow, WINDOW_LABEL, WINDOW_LABEL_CAPITALISED } from '@/lib/dateWindow'

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

describe('window copy', () => {
  it('reads as a mid-sentence phrase', () => {
    expect(WINDOW_LABEL).toBe('since January 2025')
  })

  it('offers a capitalised form for standalone captions', () => {
    expect(WINDOW_LABEL_CAPITALISED).toBe('Since January 2025')
  })
})
