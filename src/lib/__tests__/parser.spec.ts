import { describe, it, expect } from 'vitest'
import { parseLibraryTracks, parsePlaylists } from '@/lib/parser'

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
