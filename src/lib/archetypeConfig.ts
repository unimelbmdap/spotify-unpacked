const receptiveness = {
  label: 'Receptiveness',
  shortLabel: 'Receptive',
  algorithmic: {min: 0.2, max: 0.7, weight: 1},
  description: 'Receptiveness is associated with algorithmic affordances like the platform recommendations for algorithmic-driven discovery. This is interpreted as high trust in the curation of their listening experience by the platform.',
}

const responsiveness = {
  label: 'Responsiveness',
  shortLabel: 'Responsive',
  description: 'Responsiveness is associated with active searching for new music, using shuffle, and using skip to curate the listening experience. This is interpreted as being responsive to the platform\'s suggestions and interactions.',
  // Each band is [min, max] over the raw rate (0-1), scored as the position of the
  // rate within the band, clamped to [0, 1]. A blank min defaults to 0 ("from the
  // very minimum"), a blank max defaults to 1 ("to the very maximum").
  shuffle: { min: 0.1, weight: 1 / 3 },
  skip: { min: 0.05, weight: 1 / 3 },
  reason: { max: 0.1, weight: 1 / 3 },
}

const deliberate = {
  label: 'Deliberate',
  shortLabel: 'Deliberate',
  description: 'Deliberate listening is associated with relying on a user\'s Spotify library and fixed ordering of playlists and albums. This is interpreted as a more deliberate and user-directed curation of the listening experience',
  // Reuses responsiveness's thresholds as the band edge, but with min/max swapped so
  // the score is highest at the low end and fades to 0 by the threshold (reason), or
  // the reverse for skip, which should be above the threshold.
  // Shuffle uses its own, wider fade-to-zero edge (1.0) rather than responsiveness's
  // 0.1, since shuffle usage is common enough that a 10% cutoff left almost no one
  // with any deliberate credit for it.
  shuffle: { min: 1.0, max: 0, weight: 1 / 4 },
  skip: { min: responsiveness.skip.min, max: 0, weight: 1 / 4 },
  reason: { min: responsiveness.reason.max, max: 0, weight: 1 / 4 },
  // True mirror of receptiveness's algorithmic band: same edges, swapped, so
  // deliberate.algorithmic == 1 - receptiveness.algorithmic at every rate.
  algorithmic: { min: receptiveness.algorithmic.max, max: receptiveness.algorithmic.min, weight: 1 / 4 },
}

export const archetypeConfig = { receptiveness, responsiveness, deliberate }

export function bandScore(rate: number, band: { min?: number; max?: number }) {
  const lo = band.min ?? 0
  const hi = band.max ?? 1
  return Math.min(Math.max((rate - lo) / (hi - lo), 0), 1)
}

// 'fwdbtn' is excluded here since it's the same underlying event Spotify's
// `skipped` field already captures (counted separately via skipRate).
export const responsiveReasonEndValues = ['endplay', 'backbtn']
export const responsiveReasonStartValues = ['popup']
