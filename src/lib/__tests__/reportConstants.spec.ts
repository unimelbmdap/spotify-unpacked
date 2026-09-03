/**
 * The PDF report generator (reports/donation_reports) keeps its own copy of the
 * analysis window and archetype scoring constants in constants.json. This test
 * fails if that file and the frontend's TypeScript sources drift apart, so the
 * web dashboard and the PDF keep scoring donors the same way.
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import { archetypeConfig, responsiveReasonEndValues, responsiveReasonStartValues } from '../archetypeConfig'
import { WINDOW_START } from '../dateWindow'

type Band = { min?: number; max?: number; weight: number }

const constantsPath = resolve(__dirname, '../../../reports/donation_reports/constants.json')
const shared = JSON.parse(readFileSync(constantsPath, 'utf8')) as {
  window_start: string
  bar_chart_months_shown: number
  archetypes: Record<string, Record<string, Band>>
  responsive_reason_end_values: string[]
  responsive_reason_start_values: string[]
}

// The Python side names archetypes by their short form.
const KEY_MAP = {
  receptive: archetypeConfig.receptiveness,
  responsive: archetypeConfig.responsiveness,
  deliberate: archetypeConfig.deliberate,
} as const

function bandsOf(config: Record<string, unknown>): Record<string, Band> {
  const out: Record<string, Band> = {}
  for (const [key, value] of Object.entries(config)) {
    if (typeof value === 'object' && value !== null && 'weight' in value) {
      out[key] = value as Band
    }
  }
  return out
}

describe('report generator constants match the frontend', () => {
  it('analysis window start', () => {
    expect(shared.window_start).toBe(WINDOW_START)
  })

  it('months shown in the monthly charts', () => {
    // The frontend has no single constant for this; the PDF shows the
    // trailing year, which is what the dashboard's month explorer covers.
    expect(shared.bar_chart_months_shown).toBe(12)
  })

  it('archetype bands and weights', () => {
    expect(Object.keys(shared.archetypes).sort()).toEqual(Object.keys(KEY_MAP).sort())
    for (const [key, tsConfig] of Object.entries(KEY_MAP)) {
      const tsBands = bandsOf(tsConfig)
      const pyBands = shared.archetypes[key] ?? {}
      expect(Object.keys(pyBands).sort(), key).toEqual(Object.keys(tsBands).sort())
      for (const [metric, tsBand] of Object.entries(tsBands)) {
        const pyBand = pyBands[metric]
        expect(pyBand, `${key}.${metric}`).toBeDefined()
        if (!pyBand) continue
        expect(pyBand.min ?? 0, `${key}.${metric}.min`).toBeCloseTo(tsBand.min ?? 0, 12)
        expect(pyBand.max ?? 1, `${key}.${metric}.max`).toBeCloseTo(tsBand.max ?? 1, 12)
        expect(pyBand.weight, `${key}.${metric}.weight`).toBeCloseTo(tsBand.weight, 12)
      }
    }
  })

  it('responsive reason values', () => {
    expect([...shared.responsive_reason_end_values].sort()).toEqual([...responsiveReasonEndValues].sort())
    expect([...shared.responsive_reason_start_values].sort()).toEqual([...responsiveReasonStartValues].sort())
  })
})
