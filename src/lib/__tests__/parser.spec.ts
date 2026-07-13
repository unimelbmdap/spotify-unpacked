import { describe, it, expect } from 'vitest'
import { parseLibraryTracks, parsePlaylists, parseStreamingFile } from '@/lib/parser'

describe('parseLibraryTracks', () => {
  it('keeps descriptive fields and requires a uri', () => {
    const raw = {
      tracks: [
        { artist: 'A', album: 'B', track: 'C', uri: 'spotify:track:1' },
        { artist: 'D', album: 'E', track: 'F' }, // no uri -> dropped
      ],
    }
    expect(parseLibraryTracks(raw)).toEqual([
      { artist: 'A', album: 'B', track: 'C', uri: 'spotify:track:1' },
    ])
  })

  it('returns [] for malformed input', () => {
    expect(parseLibraryTracks(null)).toEqual([])
    expect(parseLibraryTracks({})).toEqual([])
  })
})

describe('parsePlaylists', () => {
  it('keeps name, lastModifiedDate and track fields but not description', () => {
    const raw = {
      playlists: [
        {
          name: 'gym',
          lastModifiedDate: '2026-01-01',
          description: 'SECRET NOTE',
          numberOfFollowers: 5,
          items: [
            {
              addedDate: '2026-01-02',
              track: {
                trackName: 'C',
                artistName: 'A',
                albumName: 'B',
                trackUri: 'spotify:track:1',
              },
            },
            { addedDate: null, track: null }, // local/episode item
          ],
        },
      ],
    }
    const result = parsePlaylists(raw)
    expect(result).toEqual([
      {
        name: 'gym',
        lastModifiedDate: '2026-01-01',
        items: [
          {
            addedDate: '2026-01-02',
            track: { trackName: 'C', artistName: 'A', albumName: 'B', trackUri: 'spotify:track:1' },
          },
          { addedDate: null, track: null },
        ],
      },
    ])
    expect(JSON.stringify(result)).not.toContain('SECRET NOTE')
    expect(JSON.stringify(result)).not.toContain('numberOfFollowers')
  })

  it('returns [] for malformed input', () => {
    expect(parsePlaylists(null)).toEqual([])
    expect(parsePlaylists({ playlists: 'nope' })).toEqual([])
  })
})

describe('parseStreamingFile', () => {
  const play = (ts: string) => ({
    ts,
    platform: 'osx',
    ms_played: 1000,
    master_metadata_track_name: 'Song',
    master_metadata_album_artist_name: 'Artist',
    master_metadata_album_album_name: 'Album',
    spotify_track_uri: 'spotify:track:1',
    reason_start: 'clickrow',
    reason_end: 'trackdone',
    shuffle: false,
    skipped: false,
  })

  it('drops a play from before the window starts', () => {
    expect(parseStreamingFile([play('2024-12-31T23:59:59Z')])).toEqual([])
  })

  it('keeps a play on the first day of the window', () => {
    const result = parseStreamingFile([play('2025-01-01T00:00:00Z')])
    expect(result).toHaveLength(1)
    expect(result[0]?.ts).toBe('2025-01-01T00:00:00Z')
  })

  it('keeps a play beyond the calendar year, because the window has no upper bound', () => {
    const result = parseStreamingFile([play('2026-04-01T08:00:00Z')])
    expect(result).toHaveLength(1)
  })

  it('drops entries with no track name or no track uri', () => {
    const noName = { ...play('2025-07-01T10:00:00Z'), master_metadata_track_name: null }
    const noUri = { ...play('2025-07-01T10:00:00Z'), spotify_track_uri: null }
    expect(parseStreamingFile([noName, noUri])).toEqual([])
  })

  it('returns an empty array for a non-array payload', () => {
    expect(parseStreamingFile({ not: 'an array' })).toEqual([])
  })
})
