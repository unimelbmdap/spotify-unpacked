import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDataStore } from '@/stores/data'

const jsonFile = (name: string, data: unknown) =>
  new File([JSON.stringify(data)], name, { type: 'application/json' })

beforeEach(() => setActivePinia(createPinia()))

describe('useDataStore enriched library/playlists', () => {
  it('merges playlists across multiple Playlist files instead of overwriting', async () => {
    const store = useDataStore()
    await store.loadFiles([
      jsonFile('Playlist1.json', { playlists: [{ name: 'one', items: [] }] }),
      jsonFile('Playlist2.json', { playlists: [{ name: 'two', items: [] }] }),
    ])
    expect(store.playlists.map((p) => p.name)).toEqual(['one', 'two'])
  })

  it('derives library+playlist URIs (hasLibraryData) and exposes hasDonatableData', async () => {
    const store = useDataStore()
    expect(store.hasDonatableData).toBe(false)
    await store.loadFiles([
      jsonFile('YourLibrary.json', {
        tracks: [{ artist: 'A', album: 'B', track: 'C', uri: 'spotify:track:1' }],
      }),
      jsonFile('Playlist1.json', {
        playlists: [
          {
            name: 'gym',
            items: [{ track: { trackName: 'C', artistName: 'A', albumName: 'B', trackUri: 'spotify:track:2' } }],
          },
        ],
      }),
    ])
    expect(store.libraryTracks).toHaveLength(1)
    expect(store.playlists).toHaveLength(1)
    // hasLibraryData is true only when BOTH the library and playlist URI sets are
    // non-empty, which proves playlistUris is derived from the enriched items.
    expect(store.hasLibraryData).toBe(true)
    expect(store.hasDonatableData).toBe(true)
  })

  it('a search-only load sets hasData but NOT hasDonatableData (the gate)', async () => {
    const store = useDataStore()
    await store.loadFiles([jsonFile('SearchQueries.json', [])])
    expect(store.hasData).toBe(true) // file metadata recorded
    expect(store.hasDonatableData).toBe(false) // nothing modelled to donate
  })

  it('clear() resets enriched state', async () => {
    const store = useDataStore()
    await store.loadFiles([jsonFile('Playlist1.json', { playlists: [{ name: 'one', items: [] }] })])
    store.clear()
    expect(store.playlists).toEqual([])
    expect(store.libraryTracks).toEqual([])
    expect(store.hasDonatableData).toBe(false)
  })
})
