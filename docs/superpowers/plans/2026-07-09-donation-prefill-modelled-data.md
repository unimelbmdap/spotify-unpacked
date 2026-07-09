# Donation prefill from dashboard (modelled-data bundle) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a donor who already loaded their Spotify export on the dashboard donate it from `/donate` without re-selecting files, sending a reconstruction of the parsed/modelled data (never raw files, never sensitive fields).

**Architecture:** The dashboard's ingest already parses files into a Pinia store. We enrich the store's library/playlist model, add a single pure `donationPayload.ts` builder that serialises store state into named JSON `File[]`, and rewire `DonateView` to donate from the store (with a drop-zone fallback). The backend is unchanged: it zips whatever `.json` files are POSTed.

**Tech Stack:** Vue 3 (`<script setup>`), Pinia (setup stores), TypeScript, Vitest + @vue/test-utils, Playwright (e2e), JSZip.

## Global Constraints

- **Spec:** `docs/superpowers/specs/2026-07-09-donation-prefill-modelled-data-design.md` (authoritative).
- **Schema verified against real exports on 2026-07-09** (gitignored `local/Datasets/…`). Confirmed:
  streaming records carry exactly the field set in `parser.ts` (incl. the excluded
  `conn_country`/`ip_addr`/`offline`/`offline_timestamp`/`incognito_mode`); `YourLibrary.json`
  `tracks[]` = `{artist, album, track, uri}`; playlist items =
  `{track: {trackName, artistName, albumName, trackUri}, episode, audiobook, localTrack, addedDate}`
  (`addedDate` present → kept); playlist top-level also has `collaborators` (third-party
  identifiers), `description`, `numberOfFollowers` → all excluded. Do NOT commit any file
  under `local/`; tests use synthetic fixtures only.
- **Never emit sensitive keys** anywhere in a donation payload: `ip_addr`, `conn_country`, `incognito_mode`, `offline`, `offline_timestamp`, episode/audiobook fields, playlist `description`, playlist follower counts.
- **Conservative defaults (spec §9), keep for this build:** streaming = music-only, post-`2025-06-01` (already enforced by `parseStreamingFile`); no podcasts/audiobooks; no `search`/`aidj`; field-name shape = **original Spotify snake_case** for streaming.
- **No raw `File` retention; no local/session persistence.** In-memory Pinia only.
- **Backend unchanged.** Do not touch `backend/`.
- **Australian English** in identifiers/comments (e.g. `summarise`, `behaviour`); keep external field names (`ms_played`, `color`, Spotify keys) verbatim.
- **No em-dashes** in prose/comments.
- **Consent is a ship-time dependency (spec §6a), not a code task here.** Do not edit `backend/consent/*`.
- **Commands:** unit test `npx vitest run <path>`; type-check `npm run type-check`; e2e `npm run test:e2e`.

---

## File Structure

- **Create** `src/lib/donationPayload.ts` — pure builder: `DonationSource` → named JSON `File[]`, plus `hasDonatableData`.
- **Create** `src/lib/__tests__/donationPayload.spec.ts` — builder unit tests incl. recursive sensitive-key guard.
- **Create** `src/lib/__tests__/parser.spec.ts` — enriched library/playlist parsing tests.
- **Create** `src/stores/__tests__/data.spec.ts` — store merge/derive/clear/gate tests.
- **Create** `e2e/donate-prefill.spec.ts` — dashboard-load → donate happy path (mocked backend).
- **Modify** `src/lib/parser.ts` — add `LibraryTrack`, `Playlist`, `PlaylistItem`, `PlaylistTrack` types + `parseLibraryTracks`, `parsePlaylists`; remove `parseLibraryFile`, `parsePlaylistFile`.
- **Modify** `src/stores/data.ts` — retain enriched `libraryTracks`/`playlists`, merge across files, derive URI sets, expose new state + `hasDonatableData`, update `clear()`.
- **Modify** `src/views/DonateView.vue` — donate from store; data-source section (summary vs `FileDropZone` fallback); gate on `hasDonatableData`; build files at submit.
- **Modify** `src/views/__tests__/DonateView.spec.ts` — update to the store-driven flow.

---

## Task 1: Enriched library/playlist parsing

**Files:**
- Modify: `src/lib/parser.ts`
- Test: `src/lib/__tests__/parser.spec.ts` (create)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `interface LibraryTrack { artist: string | null; album: string | null; track: string | null; uri: string }`
  - `interface PlaylistTrack { trackName: string | null; artistName: string | null; albumName: string | null; trackUri: string }`
  - `interface PlaylistItem { track: PlaylistTrack | null; addedDate: string | null }`
  - `interface Playlist { name: string; lastModifiedDate: string | null; items: PlaylistItem[] }`
  - `parseLibraryTracks(raw: unknown): LibraryTrack[]`
  - `parsePlaylists(raw: unknown): Playlist[]`

- [ ] **Step 1: Write the failing test**

Create `src/lib/__tests__/parser.spec.ts`:

```ts
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/lib/__tests__/parser.spec.ts`
Expected: FAIL, `parseLibraryTracks`/`parsePlaylists` not exported.

- [ ] **Step 3: Write minimal implementation**

In `src/lib/parser.ts`, **remove** the existing `parseLibraryFile` and `parsePlaylistFile` functions (lines 56-74) and **add** in their place:

```ts
export interface LibraryTrack {
  artist: string | null
  album: string | null
  track: string | null
  uri: string
}

export interface PlaylistTrack {
  trackName: string | null
  artistName: string | null
  albumName: string | null
  trackUri: string
}

export interface PlaylistItem {
  track: PlaylistTrack | null
  addedDate: string | null
}

export interface Playlist {
  name: string
  lastModifiedDate: string | null
  items: PlaylistItem[]
}

const asString = (value: unknown): string | null => (typeof value === 'string' ? value : null)

export function parseLibraryTracks(raw: unknown): LibraryTrack[] {
  if (typeof raw !== 'object' || raw === null) return []
  const { tracks } = raw as { tracks?: unknown }
  if (!Array.isArray(tracks)) return []
  return tracks
    .filter(
      (t): t is Record<string, unknown> =>
        typeof t === 'object' && t !== null && typeof (t as { uri?: unknown }).uri === 'string',
    )
    .map((t) => ({
      artist: asString(t.artist),
      album: asString(t.album),
      track: asString(t.track),
      uri: t.uri as string,
    }))
}

function toPlaylistItem(raw: unknown): PlaylistItem {
  const item = (typeof raw === 'object' && raw !== null ? raw : {}) as {
    track?: unknown
    addedDate?: unknown
  }
  const t = item.track
  const track: PlaylistTrack | null =
    typeof t === 'object' && t !== null
      ? {
          trackName: asString((t as Record<string, unknown>).trackName),
          artistName: asString((t as Record<string, unknown>).artistName),
          albumName: asString((t as Record<string, unknown>).albumName),
          trackUri: asString((t as Record<string, unknown>).trackUri) ?? '',
        }
      : null
  return { track, addedDate: asString(item.addedDate) }
}

export function parsePlaylists(raw: unknown): Playlist[] {
  if (typeof raw !== 'object' || raw === null) return []
  const { playlists } = raw as { playlists?: unknown }
  if (!Array.isArray(playlists)) return []
  return playlists.map((p) => {
    const pl = (typeof p === 'object' && p !== null ? p : {}) as {
      name?: unknown
      lastModifiedDate?: unknown
      items?: unknown
    }
    return {
      name: asString(pl.name) ?? '',
      lastModifiedDate: asString(pl.lastModifiedDate),
      items: Array.isArray(pl.items) ? pl.items.map(toPlaylistItem) : [],
    }
  })
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/lib/__tests__/parser.spec.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/lib/parser.ts src/lib/__tests__/parser.spec.ts
git commit -m "feat(parser): enriched library/playlist parsing (descriptive fields, no description/followers)"
```

---

## Task 2: Store retains enriched state, merges across files, derives URI sets

**Files:**
- Modify: `src/stores/data.ts`
- Test: `src/stores/__tests__/data.spec.ts` (create)

**Interfaces:**
- Consumes: `parseLibraryTracks`, `parsePlaylists`, `LibraryTrack`, `Playlist` (Task 1).
- Produces (added to the store's returned object; consumed as unwrapped values on the
  store proxy, e.g. `store.playlists`, `store.libraryTracks`, `store.hasDonatableData`):
  - `libraryTracks` — `LibraryTrack[]`
  - `playlists` — `Playlist[]`
  - `hasDonatableData` — `boolean`
  - (`libraryUris`/`playlistUris` stay internal, converted from `ref` to `computed`.)

- [ ] **Step 1: Write the failing test**

Create `src/stores/__tests__/data.spec.ts`:

```ts
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/stores/__tests__/data.spec.ts`
Expected: FAIL (`store.playlists`/`store.libraryTracks`/`store.hasDonatableData` undefined).

- [ ] **Step 3: Write minimal implementation**

In `src/stores/data.ts`:

3a. Update the import (line 4):

```ts
import { parseStreamingFile, parseLibraryTracks, parsePlaylists, entryKey, type MusicEntry, type LibraryTrack, type Playlist } from '@/lib/parser'
```

3b. Replace the two URI refs (lines 120-121):

```ts
  const libraryTracks = ref<LibraryTrack[]>([])
  const playlists = ref<Playlist[]>([])

  const libraryUris = computed(() => new Set(libraryTracks.value.map((t) => t.uri)))
  const playlistUris = computed(() => {
    const uris = new Set<string>()
    for (const playlist of playlists.value) {
      for (const item of playlist.items) {
        if (item.track?.trackUri) uris.add(item.track.trackUri)
      }
    }
    return uris
  })

  function mergeLibraryTracks(existing: LibraryTrack[], incoming: LibraryTrack[]): LibraryTrack[] {
    const byUri = new Map(existing.map((t) => [t.uri, t]))
    for (const track of incoming) if (!byUri.has(track.uri)) byUri.set(track.uri, track)
    return [...byUri.values()]
  }
```

3c. In `loadFiles`, replace the `library`/`playlists` branches (lines 153-157):

```ts
            } else if (fileType === 'library') {
              libraryTracks.value = mergeLibraryTracks(libraryTracks.value, parseLibraryTracks(json))
            } else if (fileType === 'playlists') {
              playlists.value = [...playlists.value, ...parsePlaylists(json)]
            }
```

3d. Add the gate computed (near `hasData`, line 124):

```ts
  const hasDonatableData = computed(
    () => entries.value.length > 0 || libraryTracks.value.length > 0 || playlists.value.length > 0,
  )
```

3e. In `clear()` (lines 296-305), replace the two URI resets:

```ts
    libraryTracks.value = []
    playlists.value = []
```

3f. Add to the returned object (in the `// files & loading state` group, near `hasLibraryData`):

```ts
    libraryTracks,
    playlists,
    hasDonatableData,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/stores/__tests__/data.spec.ts`
Then the full suite + types: `npx vitest run && npm run type-check`
Expected: PASS; type-check clean (confirms no remaining references to the removed `parseLibraryFile`/`parsePlaylistFile`).

- [ ] **Step 5: Commit**

```bash
git add src/stores/data.ts src/stores/__tests__/data.spec.ts
git commit -m "feat(store): retain+merge enriched library/playlists, derive URIs, add hasDonatableData"
```

---

## Task 3: `donationPayload.ts` builder

**Files:**
- Create: `src/lib/donationPayload.ts`
- Test: `src/lib/__tests__/donationPayload.spec.ts` (create)

**Interfaces:**
- Consumes: `MusicEntry`, `LibraryTrack`, `Playlist` (Tasks 1).
- Produces:
  - `interface DonationSource { entries: MusicEntry[]; libraryTracks: LibraryTrack[]; playlists: Playlist[] }`
  - `buildDonationFiles(source: DonationSource): File[]`
  - `hasDonatableData(source: DonationSource): boolean`

- [ ] **Step 1: Write the failing test**

Create `src/lib/__tests__/donationPayload.spec.ts`:

```ts
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/lib/__tests__/donationPayload.spec.ts`
Expected: FAIL, module not found.

- [ ] **Step 3: Write minimal implementation**

Create `src/lib/donationPayload.ts`:

```ts
import type { LibraryTrack, MusicEntry, Playlist } from '@/lib/parser'

/**
 * The single scope boundary for what leaves the browser. To widen or narrow the
 * donated data later (more fields, or a scrubbed-raw variant) change only this file.
 * We emit a reduced, modelled subset, never raw files, and never sensitive fields.
 */
export interface DonationSource {
  entries: MusicEntry[]
  libraryTracks: LibraryTrack[]
  playlists: Playlist[]
}

/** Map the app's internal MusicEntry back to Spotify's original snake_case field names. */
function streamingRecord(entry: MusicEntry) {
  return {
    ts: entry.ts,
    platform: entry.platform,
    ms_played: entry.msPlayed,
    master_metadata_track_name: entry.trackName,
    master_metadata_album_artist_name: entry.artistName,
    master_metadata_album_album_name: entry.albumName,
    spotify_track_uri: entry.trackUri,
    reason_start: entry.reasonStart,
    reason_end: entry.reasonEnd,
    shuffle: entry.shuffle,
    skipped: entry.skipped,
  }
}

function jsonFile(name: string, data: unknown): File {
  return new File([JSON.stringify(data)], name, { type: 'application/json' })
}

export function buildDonationFiles(source: DonationSource): File[] {
  const files: File[] = []
  if (source.entries.length > 0) {
    files.push(jsonFile('streaming_history.json', source.entries.map(streamingRecord)))
  }
  if (source.libraryTracks.length > 0) {
    files.push(jsonFile('your_library.json', { tracks: source.libraryTracks }))
  }
  if (source.playlists.length > 0) {
    files.push(jsonFile('playlists.json', { playlists: source.playlists }))
  }
  return files
}

export function hasDonatableData(source: DonationSource): boolean {
  return source.entries.length > 0 || source.libraryTracks.length > 0 || source.playlists.length > 0
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/lib/__tests__/donationPayload.spec.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/lib/donationPayload.ts src/lib/__tests__/donationPayload.spec.ts
git commit -m "feat(donation): payload builder serialising modelled store state to named JSON files"
```

---

## Task 4: Rewire `DonateView` to donate from the store

**Files:**
- Modify: `src/views/DonateView.vue`
- Test: `src/views/__tests__/DonateView.spec.ts`

**Interfaces:**
- Consumes: `useDataStore` (Task 2: `entries`, `libraryTracks`, `playlists`, `hasDonatableData`, `loadFiles`, `clear`); `buildDonationFiles` (Task 3); `FileDropZone` (existing, emits `filesDropped: [File[]]`).
- Produces: no exported symbols (view component).

- [ ] **Step 1: Write the failing test**

Replace `src/views/__tests__/DonateView.spec.ts` with:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/lib/api', () => {
  class ApiError extends Error {
    status: number
    constructor(status: number, message: string) {
      super(message)
      this.status = status
    }
  }
  return { ApiError, checkCode: vi.fn(), getConsent: vi.fn(), donate: vi.fn() }
})

import DonateView from '../DonateView.vue'
import * as api from '@/lib/api'
import { useDataStore } from '@/stores/data'

const mountView = () => mount(DonateView, { global: { stubs: { RouterLink: true } } })

async function advanceToFormStep(wrapper: ReturnType<typeof mountView>) {
  await wrapper.find('[data-test="code-input"]').setValue('MDAP-2026-001')
  await wrapper.find('[data-test="check-code"]').trigger('click')
  await flushPromises()
}

const streamingFile = () =>
  new File(
    [
      JSON.stringify([
        {
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
        },
      ]),
    ],
    'Streaming_History_audio_2025.json',
    { type: 'application/json' },
  )

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  vi.mocked(api.getConsent).mockResolvedValue({ version: 'v1.0', text: 'CONSENT TEXT' })
})

describe('DonateView', () => {
  it('advances to the consent step when the code is valid', async () => {
    vi.mocked(api.checkCode).mockResolvedValue({ valid: true })
    const wrapper = mountView()
    await advanceToFormStep(wrapper)
    expect(wrapper.text()).toContain('CONSENT TEXT')
  })

  it('cannot submit when the store has no donatable data', async () => {
    vi.mocked(api.checkCode).mockResolvedValue({ valid: true })
    const wrapper = mountView()
    await advanceToFormStep(wrapper)
    await wrapper.find('[data-test="consent-checkbox"]').setValue(true)
    expect(wrapper.find('[data-test="submit-donation"]').attributes('disabled')).toBeDefined()
  })

  it('donates only reconstructed files built from the store', async () => {
    vi.mocked(api.checkCode).mockResolvedValue({ valid: true })
    vi.mocked(api.donate).mockResolvedValue({ donation_id: 42, results: [] })
    const store = useDataStore()
    await store.loadFiles([streamingFile()])

    const wrapper = mountView()
    await advanceToFormStep(wrapper)
    await wrapper.find('[data-test="consent-checkbox"]').setValue(true)
    await wrapper.find('[data-test="submit-donation"]').trigger('click')
    await flushPromises()

    expect(api.donate).toHaveBeenCalled()
    const form = vi.mocked(api.donate).mock.calls[0][0] as FormData
    const donated = form.getAll('files') as File[]
    expect(donated.map((f) => f.name)).toEqual(['streaming_history.json'])
    expect(wrapper.text()).toContain('42')
  })

  it('falls back to the drop-zone loader when the store has no data', async () => {
    vi.mocked(api.checkCode).mockResolvedValue({ valid: true })
    const wrapper = mountView()
    await advanceToFormStep(wrapper)
    // No store data: show the loader (FileDropZone renders a file input), not the summary.
    expect(wrapper.find('[data-test="donation-summary"]').exists()).toBe(false)
    expect(wrapper.find('input[type="file"]').exists()).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/views/__tests__/DonateView.spec.ts`
Expected: FAIL (submit still gated by the old local `files` picker; no `files` FormData built from the store).

- [ ] **Step 3: Write minimal implementation**

Replace `src/views/DonateView.vue` with:

```vue
<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Button } from '@/components/ui/button'
import FileDropZone from '@/components/FileDropZone.vue'
import { useDataStore } from '@/stores/data'
import { buildDonationFiles } from '@/lib/donationPayload'
import { ApiError, checkCode, donate, getConsent, type Consent, type DonationResponse } from '@/lib/api'

// Client-side mirrors of the backend limits, for early feedback only. The
// backend re-enforces them authoritatively.
const MAX_FILES = 10
const MAX_BYTES_PER_FILE = 50 * 1024 * 1024
const MAX_BYTES_PER_REQUEST = 200 * 1024 * 1024

const appVersion = typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : 'dev'

const dataStore = useDataStore()

type Step = 'code' | 'form' | 'done'
const step = ref<Step>('code')

// Step 1: code.
const code = ref('')
const checking = ref(false)
const codeError = ref('')

// Step 2: consent.
const consent = ref<Consent | null>(null)
const consentAccepted = ref(false)

// Submit.
const submitting = ref(false)
const progress = ref(0)
const submitError = ref('')
const result = ref<DonationResponse | null>(null)

const summary = computed(() => {
  const parts: string[] = []
  if (dataStore.entries.length > 0) parts.push(`${dataStore.entries.length.toLocaleString()} plays`)
  if (dataStore.libraryTracks.length > 0) parts.push(`library of ${dataStore.libraryTracks.length} tracks`)
  if (dataStore.playlists.length > 0) parts.push(`${dataStore.playlists.length} playlists`)
  return parts.join(' · ')
})

async function onCheckCode() {
  const value = code.value.trim()
  codeError.value = ''
  if (!value) {
    codeError.value = 'Please enter your participant code.'
    return
  }
  checking.value = true
  try {
    const { valid } = await checkCode(value)
    if (!valid) {
      codeError.value = 'Code not recognised or already used.'
      return
    }
    consent.value = await getConsent()
    step.value = 'form'
  } catch (err) {
    codeError.value =
      err instanceof ApiError && err.status === 429
        ? 'Too many attempts. Please wait a moment and try again.'
        : 'Could not check your code. Please try again.'
  } finally {
    checking.value = false
  }
}

function onFilesDropped(files: File[]) {
  dataStore.loadFiles(files)
}

function onLoadDifferent() {
  dataStore.clear()
}

const canSubmit = computed(
  () => consentAccepted.value && dataStore.hasDonatableData && !submitting.value,
)

async function onSubmit() {
  if (!canSubmit.value || !consent.value) return
  submitError.value = ''

  const files = buildDonationFiles({
    entries: dataStore.entries,
    libraryTracks: dataStore.libraryTracks,
    playlists: dataStore.playlists,
  })

  if (files.length === 0) {
    submitError.value = 'There is no data to donate. Please load your Spotify files first.'
    return
  }
  if (files.length > MAX_FILES) {
    submitError.value = `The donation would contain more than ${MAX_FILES} files.`
    return
  }
  if (files.some((f) => f.size > MAX_BYTES_PER_FILE)) {
    submitError.value = 'One of the donation files is larger than 50 MB.'
    return
  }
  if (files.reduce((sum, f) => sum + f.size, 0) > MAX_BYTES_PER_REQUEST) {
    submitError.value = 'Your donation totals more than 200 MB.'
    return
  }

  submitting.value = true
  progress.value = 0

  const form = new FormData()
  form.append('participant_code', code.value.trim())
  form.append('consent_version', consent.value.version)
  form.append('consent_accepted', 'true')
  form.append('app_version', appVersion)
  for (const f of files) form.append('files', f, f.name)

  try {
    result.value = await donate(form, (p) => (progress.value = p))
    step.value = 'done'
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      step.value = 'code'
      codeError.value = 'Your code is invalid or already used. Please re-enter it.'
    } else if (err instanceof ApiError && err.status === 409) {
      submitError.value = 'The consent form has been updated. Please reload and try again.'
    } else if (err instanceof ApiError && err.status === 413) {
      submitError.value = 'Your files are too large. Please check the size limits.'
    } else {
      submitError.value = 'Sorry, we could not receive your donation. Please try again.'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="mx-auto flex h-full w-full max-w-xl flex-col gap-6 p-8">
    <header class="flex items-center justify-between">
      <h1 class="text-lg font-semibold">Donate your Spotify data</h1>
      <RouterLink to="/">
        <Button variant="outline" size="sm">Back to Dashboard</Button>
      </RouterLink>
    </header>

    <!-- Step 1: participant code -->
    <section v-if="step === 'code'" class="flex flex-col gap-3">
      <label for="participant-code" class="text-sm font-medium">Participant code</label>
      <input
        id="participant-code"
        data-test="code-input"
        v-model="code"
        type="text"
        placeholder="e.g. MDAP-2026-001"
        class="border-input rounded-md border px-3 py-2 text-sm"
        @keyup.enter="onCheckCode"
      />
      <p v-if="codeError" data-test="code-error" class="text-destructive text-sm">
        {{ codeError }}
      </p>
      <Button data-test="check-code" :disabled="checking" @click="onCheckCode">
        {{ checking ? 'Checking…' : 'Continue' }}
      </Button>
    </section>

    <!-- Step 2: consent + data source -->
    <section v-else-if="step === 'form'" class="flex flex-col gap-4">
      <div
        class="bg-muted/40 max-h-48 overflow-y-auto rounded-md border p-3 text-sm whitespace-pre-line"
      >
        {{ consent?.text }}
      </div>

      <label class="flex items-center gap-2 text-sm">
        <input data-test="consent-checkbox" v-model="consentAccepted" type="checkbox" />
        I have read and accept the consent terms.
      </label>

      <div class="flex flex-col gap-2">
        <template v-if="dataStore.hasDonatableData">
          <p data-test="donation-summary" class="text-sm">
            We will donate the data you loaded: {{ summary }}.
          </p>
          <button type="button" class="text-muted-foreground text-left text-xs underline" @click="onLoadDifferent">
            Load different data
          </button>
        </template>
        <template v-else>
          <p class="text-muted-foreground text-sm">Load your Spotify files to donate.</p>
          <FileDropZone @files-dropped="onFilesDropped" />
        </template>
      </div>

      <p v-if="submitting" class="text-muted-foreground text-sm">Uploading… {{ progress }}%</p>
      <p v-if="submitError" data-test="submit-error" class="text-destructive text-sm">
        {{ submitError }}
      </p>

      <Button data-test="submit-donation" :disabled="!canSubmit" @click="onSubmit">
        {{ submitting ? 'Submitting…' : 'Submit donation' }}
      </Button>
    </section>

    <!-- Step 3: done -->
    <section v-else class="flex flex-col gap-3">
      <p class="text-sm font-medium">Thank you — your data has been received.</p>
      <p class="text-muted-foreground text-sm">Reference number: {{ result?.donation_id }}</p>
      <RouterLink to="/">
        <Button variant="outline" size="sm">Back to Dashboard</Button>
      </RouterLink>
    </section>
  </div>
</template>
```

Note: the em-dash in the "Thank you — your data" line is pre-existing UI copy; leave it as-is (constraint applies to code/comments, not this existing string) unless you are separately asked to change copy.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/views/__tests__/DonateView.spec.ts && npm run type-check`
Expected: PASS (3 tests); type-check clean.

- [ ] **Step 5: Commit**

```bash
git add src/views/DonateView.vue src/views/__tests__/DonateView.spec.ts
git commit -m "feat(donate): donate modelled data from the store with a drop-zone fallback"
```

---

## Task 5: End-to-end happy path (dashboard load → donate)

**Files:**
- Create: `e2e/donate-prefill.spec.ts`

**Interfaces:**
- Consumes: the running app (`FileDropZone` on `/`, `DonateView` on `/donate`) and the donation API, mocked via Playwright route interception.

- [ ] **Step 1: Write the test**

Create `e2e/donate-prefill.spec.ts`:

```ts
import { test, expect } from '@playwright/test'

const streaming = JSON.stringify([
  {
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
  },
])

test('data loaded on the dashboard is offered for donation without re-selecting files', async ({ page }) => {
  // Mock the donation backend.
  await page.route('**/api/codes/validate', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ valid: true }) }),
  )
  await page.route('**/api/consent', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ version: 'v1.0', text: 'CONSENT' }) }),
  )
  await page.route('**/api/donate', (route) =>
    route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ donation_id: 7, results: [] }) }),
  )

  await page.goto('/')

  // Load a file on the dashboard via the first hidden file input (the dashboard
  // renders two: DataPanel's FileDropZone and UploadPanel).
  await page.locator('input[type="file"]').first().setInputFiles({
    name: 'Streaming_History_audio_2025.json',
    mimeType: 'application/json',
    buffer: Buffer.from(streaming),
  })

  // Go to donate; the loaded data should be pre-offered.
  // Navigate WITHIN the SPA via the in-app link (ControlsPanel's "Donate Your Data"
  // RouterLink). A full page.goto('/donate') would reload the app and wipe the
  // in-memory store, which is exactly the reload-fallback case, not this one.
  await page.getByRole('link', { name: 'Donate Your Data' }).click()
  await expect(page).toHaveURL(/\/donate$/)
  await page.fill('[data-test="code-input"]', 'MDAP-2026-001')
  await page.click('[data-test="check-code"]')
  await expect(page.locator('[data-test="donation-summary"]')).toContainText('1 plays')

  await page.check('[data-test="consent-checkbox"]')
  await page.click('[data-test="submit-donation"]')
  await expect(page.getByText('Reference number: 7')).toBeVisible()
})
```

- [ ] **Step 2: Run the test**

Run: `npm run test:e2e -- donate-prefill`
Expected: PASS. This exercises the true prefill guarantee: files loaded on `/` survive SPA navigation to `/donate` and are offered without re-selection.

- [ ] **Step 3: Commit**

```bash
git add e2e/donate-prefill.spec.ts
git commit -m "test(e2e): dashboard-loaded data is offered for donation without re-selecting"
```

---

## Final verification

- [ ] **Full unit suite:** `npx vitest run` — all pass.
- [ ] **Types:** `npm run type-check` — clean.
- [ ] **Lint (non-mutating check):** `npx oxlint .` then `npx eslint .` — clean. Avoid `npm run lint`, which runs with `--fix` and would mutate files during verification.
- [ ] **E2E:** `npm run test:e2e -- donate-prefill` — pass.
- [ ] Confirm no reference to removed `parseLibraryFile`/`parsePlaylistFile` remains: `git grep -n "parseLibraryFile\|parsePlaylistFile" src` returns nothing.

## Deferred (spec, not this plan)

- §6a consent text + `consent_version` bump (ethics-owned; ship blocker).
- §9 confirmations (field-name shape, `offline*` exclusion, podcasts/audiobooks, search/AIDJ) — built conservatively; revisit with MDAP.
- **Library sub-collections beyond `tracks`** — real `YourLibrary.json` also holds `albums`, `artists`, `shows`, `episodes`, `bannedTracks`, `bannedArtists`, `other`. The store models only `tracks` (as today's viz does), so donation includes tracks only. Enriching to saved albums/artists is a future, localised change in the parser + `donationPayload.ts`.
- **Playlist non-track items** — items whose `track` is null (episode/audiobook/local-track entries) donate as `{ track: null, addedDate }`; their `episode`/`audiobook`/`localTrack` payloads are intentionally dropped (music-curation focus).
- Zip-expansion code duplication + `dataTransfer.files` fallback (spec §8) — separate cleanup.
