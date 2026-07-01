import type { MusicEntry } from '@/lib/parser'

export interface TopPlayed {
  name: string
  playCount: number
}

function topByKey(subset: MusicEntry[], keyOf: (e: MusicEntry) => string, nameOf: (e: MusicEntry) => string): TopPlayed | null {
  if (subset.length === 0) return null
  const counts = new Map<string, TopPlayed>()
  for (const entry of subset) {
    const key = keyOf(entry)
    const existing = counts.get(key)
    if (existing) existing.playCount += 1
    else counts.set(key, { name: nameOf(entry), playCount: 1 })
  }
  return [...counts.values()].sort((a, b) => b.playCount - a.playCount)[0] ?? null
}

export function topTrack(subset: MusicEntry[]): TopPlayed | null {
  return topByKey(subset, e => e.trackUri || e.trackName, e => e.trackName)
}

export function topArtist(subset: MusicEntry[]): TopPlayed | null {
  return topByKey(subset, e => e.artistName, e => e.artistName)
}
