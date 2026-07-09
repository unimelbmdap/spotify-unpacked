import type { LibraryTrack, MusicEntry, Playlist, PlaylistItem } from '@/lib/parser'

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

/**
 * Explicit allowlist for a saved-library track. Rebuilding the object here (rather
 * than passing the model through) keeps this module the sole scope boundary: even if
 * an upstream change let extra keys onto a LibraryTrack, they cannot leave the browser.
 */
function libraryRecord(track: LibraryTrack) {
  return {
    artist: track.artist,
    album: track.album,
    track: track.track,
    uri: track.uri,
  }
}

/** Explicit allowlist for a playlist item (drops any episode/audiobook/local payload). */
function playlistItemRecord(item: PlaylistItem) {
  return {
    addedDate: item.addedDate,
    track: item.track
      ? {
          trackName: item.track.trackName,
          artistName: item.track.artistName,
          albumName: item.track.albumName,
          trackUri: item.track.trackUri,
        }
      : null,
  }
}

/** Explicit allowlist for a playlist (drops description, numberOfFollowers, collaborators). */
function playlistRecord(playlist: Playlist) {
  return {
    name: playlist.name,
    lastModifiedDate: playlist.lastModifiedDate,
    items: playlist.items.map(playlistItemRecord),
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
    files.push(jsonFile('your_library.json', { tracks: source.libraryTracks.map(libraryRecord) }))
  }
  if (source.playlists.length > 0) {
    files.push(jsonFile('playlists.json', { playlists: source.playlists.map(playlistRecord) }))
  }
  return files
}

export function hasDonatableData(source: DonationSource): boolean {
  return source.entries.length > 0 || source.libraryTracks.length > 0 || source.playlists.length > 0
}
