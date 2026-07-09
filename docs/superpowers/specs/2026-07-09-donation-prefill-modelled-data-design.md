# Donation prefill from dashboard (modelled-data bundle) — design

**Date:** 2026-07-09
**Status:** Draft for review
**Project:** spotify-unpacked
**Goal:** Let a donor who has already loaded their Spotify export on the dashboard
donate it from `/donate` without re-selecting files, where the donated bundle is a
**reconstruction of the modelled (parsed, filtered) data** rather than the raw export.
The dashboard stays fully client-side; the backend is only ever contacted on donation
submit.

This supersedes the deferred follow-up in
`docs/superpowers/specs/2026-07-01-participant-code-whitelist-design.md:129`, which
assumed retaining raw `File[]` in shared state. We are **not** retaining raw files.

---

## 1. Decisions (settled in brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| What is donated | A reconstruction of the parsed/modelled store state, not raw export files | Most conservative; matches what the participant actually saw; sensitive fields never present in the store to begin with |
| Sensitive fields | Never included, either way (`ip_addr`, `conn_country`, `incognito_mode`) | Privacy; the app never reads them |
| Filtering flow-through | Automatic, by construction | Payload is serialised from post-filter store state, so the June-2025 cut, music-only filter, de-dup, and any future filter UI are all reflected |
| Library / playlists fidelity | Enrich parsing to retain non-sensitive descriptive fields | URIs alone are too thin for research; descriptive fields (names, dates) are not sensitive |
| Raw `File` retention | None | Avoids ~100-200 MB in-browser retention and the risk of donating invalid/partial JSON |
| Adjustability | A single payload-builder module is the scope boundary | Widening/narrowing later (more fields, or scrubbed-raw) is a localised change |
| Backend | Unchanged | It already zips whatever `.json` files are POSTed |
| Handoff transport | In-memory Pinia store only; no local/session persistence | Ephemeral, matches current behaviour |

---

## 2. Architecture & data flow

```
 Dashboard ingest (unchanged filtering)
 ┌─────────────────────────────┐
 │ DataPanel → FileDropZone     │─┐
 │ UploadPanel (central)        │─┼─▶ dataStore.loadFiles()  ──▶  parsed + enriched store state
 └─────────────────────────────┘─┘        (entries, enriched library/playlist model,
                                            file metadata; NO raw File blobs)
                                                          │
                                                          ▼
                                         src/lib/donationPayload.ts  ← the scope boundary
                                                          │  reconstructs named JSON File[]
                                                          ▼
 /donate  code → consent → (store data or loader) → submit
                                                          │  existing api.donate() multipart
                                                          ▼
                             FastAPI /api/donate  →  zips POSTed .json into bundle.zip (unchanged)
```

**Two ingest paths, one store.** The dashboard has two drop UIs feeding the *same*
`dataStore.loadFiles()`: `DataPanel`'s `FileDropZone` (a compact sidebar present on
every data view) and the central `UploadPanel` (dashboard-only, with per-file-type
completeness cards). Because donation serialises **store state**, it prefills correctly
regardless of which UI the donor used. No unification work is needed beyond relying on
the store as the single source of truth.

---

## 3. `src/lib/donationPayload.ts` — the scope boundary

The one module that defines what leaves the browser. Pure function of store state →
`File[]`. It emits one named JSON file per **present** type (skips empty types):

- `streaming_history.json` — the kept/filtered plays (music-only, post-2025-06-01,
  de-duplicated, as already held in `store.entries`).
- `your_library.json` — library tracks with descriptive fields.
- `playlists.json` — playlists with names, dates, and their tracks' descriptive fields.

### 3.1 Field policy

**Chosen shape (confirm at review): preserve the original Spotify field names**
(snake_case) for the fields we keep, so the bundle reads as a redacted Spotify export
that researchers can process with familiar tooling. Alternative considered: emit the
app's internal camelCase `MusicEntry` shape (simpler, bespoke schema). Either way the
field *set* is identical and lives in this one module.

**Streaming history — included fields** (from the raw entry, kept post-filter):
`ts`, `platform`, `ms_played`, `master_metadata_track_name`,
`master_metadata_album_artist_name`, `master_metadata_album_album_name`,
`spotify_track_uri`, `reason_start`, `reason_end`, `shuffle`, `skipped`.

**Streaming history — excluded:**
- `ip_addr`, `conn_country` — sensitive (location / network).
- `incognito_mode` — behaviourally sensitive (private sessions).
- `offline`, `offline_timestamp` — dropped for now (conservative; re-add here if research needs them).
- episode/audiobook fields — the current music-only filter (`master_metadata_track_name != null`)
  means these rows never survive, so podcasts/audiobooks are **not** donated. Noted as a
  scope consequence, adjustable in the parser + this module together.

**Library (`your_library.json`) — per track:** `uri`, `track` (name), `artist`, `album`
(the non-sensitive descriptive fields Spotify's `YourLibrary.json` carries under `tracks[]`).

**Playlists (`playlists.json`) — per playlist:** `name`, `lastModifiedDate`, and `items[]`
with `track.{trackName, artistName, albumName, trackUri}` and `addedDate`. No follower
counts or descriptions unless later deemed useful.

### 3.2 Guarantees

- Only reconstructed JSON is emitted → invalid/partial source files can never be donated.
- Sensitive keys are absent by construction (never copied in).
- Output is deterministic given store state → testable.

---

## 4. Store changes (`src/stores/data.ts`, `src/lib/parser.ts`)

- **Enrich library/playlist parsing.** Extend `parseLibraryFile` / `parsePlaylistFile`
  to return the enriched (descriptive, non-sensitive) structures described in §3.1, and
  store them. The existing URI sets used by the viz (`libraryUris`, `playlistUris`) are
  derived from the enriched structures, so dashboard behaviour is unchanged.
- **No raw `File` retention.** `LoadedFile` stays `{ name, size, type }`.
- **`clear()`** must also reset the new enriched library/playlist state.
- Streaming history needs **no** store change: `store.entries` already holds the modelled
  plays the payload builder serialises.

---

## 5. Donate flow (`src/views/DonateView.vue`)

Steps: `code → form → done` (unchanged skeleton). The `form` step gains a **data source**
section above the existing consent block:

- **If `dataStore.hasData`:** show a summary derived from the store, e.g.
  *"N plays since Jun 2025 · library of M tracks · K playlists"*, plus a
  **"Load different data"** action (clears the store and reveals the loader). No raw
  file list to manage; the donor reviews the summary, not individual files.
- **If not:** render `FileDropZone`, which populates the same store via the identical
  `loadFiles` pipeline. After loading, the summary appears.

**Submit** (`onSubmit`): build `File[]` via `donationPayload.ts`, append to the existing
`FormData`, and POST through the current `api.donate()` (XHR progress unchanged). The
client-side size/count limits (`MAX_FILES`, `MAX_BYTES_PER_FILE`, `MAX_BYTES_PER_REQUEST`)
are recomputed on the **reconstructed** files (which are smaller than the raw export).

**Gating unchanged.** Consent must be accepted before submit; the backend re-enforces
consent version, code validity, extension, and size limits. Prefill only makes files
ready, it never auto-submits.

**Single dataset / store reuse.** Donate reuses the same global store, so "Load different
data" (clear + reload) also updates the dashboard. This is acceptable: one dataset per
session.

**`FileDropZone` coupling.** It imports `useDataStore()` only to show a file count. Under
this single-store design that coupling is harmless when reused on `/donate`, so the old
"decouple `FileDropZone`" follow-up is **not** needed here.

---

## 6. Backend

No changes. `/api/donate` continues to accept multipart `.json` files and zip them
server-side into `bundle.zip`. Named reconstructed files (`streaming_history.json`, etc.)
keep the stored bundle intelligible.

---

## 7. Testing

- **`donationPayload.ts` (unit):**
  - filtering reflected (only kept plays serialised);
  - enriched library/playlist shape correct;
  - empty types omitted (e.g. no library loaded → no `your_library.json`);
  - **regression guard:** assert no sensitive keys (`ip_addr`, `conn_country`,
    `incognito_mode`) appear anywhere in the emitted payload.
- **Store / parser (unit):** enriched parsing retains descriptive fields, excludes
  sensitive ones; viz URI sets still derived correctly; `clear()` resets enriched state.
- **`DonateView` (component):** store-present path shows summary and donates store data;
  no-data path falls back to loader; correct summary counts; consent still gates submit;
  oversized reconstructed payload surfaces the size error.
- **E2E (Playwright):** load on dashboard (both `DataPanel` and `UploadPanel`, including a
  zip-expanded input) → `/donate` → submit against a mocked backend; plus a
  reload-then-`/donate` case exercising the loader fallback.

---

## 8. Scope / non-goals

- **In scope:** donationPayload builder; enriched library/playlist parsing; DonateView
  prefill + loader fallback; tests.
- **Out of scope (noted):**
  - Zip-expansion code duplication (`unzipFile` vs the inline logic in `useFileDrop`) and
    the missing `dataTransfer.files` fallback when `webkitGetAsEntry` is unavailable —
    good small follow-up cleanup, not part of this work.
  - Explicit filter UI (exclude by type/date). The architecture supports it (payload
    derives from store), but no UI is built now.
  - Any change to consent text (MDAP-owned). Consent copy should describe that a
    *modelled subset* is donated; flag for coordination.

---

## 9. Decisions to confirm at review

1. **Field-name shape:** original Spotify snake_case (recommended, research-friendly) vs
   app-internal `MusicEntry` camelCase.
2. **Excluded-but-non-sensitive listening fields** (`offline`, `offline_timestamp`):
   keep excluded for now — confirm acceptable.
3. **Podcasts/audiobooks excluded** as a consequence of the music-only filter — confirm
   acceptable for the conservative start.
