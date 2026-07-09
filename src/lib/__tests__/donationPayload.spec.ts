import { describe, it, expect } from 'vitest'
import { buildDonationFiles, hasDonatableData } from '@/lib/donationPayload'
import type { MusicEntry } from '@/lib/parser'

const entry = (over: Partial<MusicEntry> = {}): MusicEntry => ({
  ts: '2025-07-01T10:00:00Z',
  platform: 'ios',
  msPlayed: 1000,
  trackName: 'Song',
  artistName: 'Artist',
  albumName: 'Album',
  trackUri: 'spotify:track:1',
  reasonStart: 'trackdone',
  reasonEnd: 'trackdone',
  shuffle: false,
  skipped: false,
  episodeName: null,
  episodeShowName: null,
  spotifyEpisodeUri: null,
  audiobookTitle: null,
  audiobookUri: null,
  audiobookChapterUri: null,
  audiobookChapterTitle: null,
  ...over,
})

const readFile = async (file: File) => JSON.parse(await file.text())

const SENSITIVE_KEYS = [
  'ip_addr',
  'conn_country',
  'incognito_mode',
  'offline',
  'offline_timestamp',
  'episode_name',
  'episode_show_name',
  'spotify_episode_uri',
  'audiobook_title',
  'audiobook_uri',
  'audiobook_chapter_uri',
  'audiobook_chapter_title',
  'description',
  'numberOfFollowers',
  'collaborators',
]

function collectKeys(value: unknown, keys = new Set<string>()): Set<string> {
  if (Array.isArray(value)) value.forEach((v) => collectKeys(v, keys))
  else if (value && typeof value === 'object')
    for (const [k, v] of Object.entries(value)) {
      keys.add(k)
      collectKeys(v, keys)
    }
  return keys
}

describe('buildDonationFiles', () => {
  it('emits streaming_history.json with original Spotify snake_case field names', async () => {
    const [file] = buildDonationFiles({ entries: [entry()], libraryTracks: [], playlists: [] })
    expect(file.name).toBe('streaming_history.json')
    const rows = await readFile(file)
    expect(rows[0]).toEqual({
      ts: '2025-07-01T10:00:00Z',
      platform: 'ios',
      ms_played: 1000,
      master_metadata_track_name: 'Song',
      master_metadata_album_artist_name: 'Artist',
      master_metadata_album_album_name: 'Album',
      spotify_track_uri: 'spotify:track:1',
      reason_start: 'trackdone',
      reason_end: 'trackdone',
      shuffle: false,
      skipped: false,
    })
  })

  it('omits a file for an empty type', () => {
    const names = buildDonationFiles({
      entries: [],
      libraryTracks: [{ artist: 'A', album: 'B', track: 'C', uri: 'spotify:track:1' }],
      playlists: [],
    }).map((f) => f.name)
    expect(names).toEqual(['your_library.json'])
  })

  it('produces no files when nothing is modelled', () => {
    expect(buildDonationFiles({ entries: [], libraryTracks: [], playlists: [] })).toEqual([])
    expect(hasDonatableData({ entries: [], libraryTracks: [], playlists: [] })).toBe(false)
  })

  it('never includes sensitive keys anywhere in the payload', async () => {
    const files = buildDonationFiles({
      entries: [entry()],
      libraryTracks: [{ artist: 'A', album: 'B', track: 'C', uri: 'spotify:track:1' }],
      playlists: [
        {
          name: 'gym',
          lastModifiedDate: '2026-01-01',
          items: [
            {
              addedDate: '2026-01-02',
              track: { trackName: 'C', artistName: 'A', albumName: 'B', trackUri: 'spotify:track:1' },
            },
          ],
        },
      ],
    })
    const allKeys = new Set<string>()
    for (const file of files) collectKeys(await readFile(file), allKeys)
    for (const key of SENSITIVE_KEYS) expect(allKeys.has(key)).toBe(false)
  })
})
