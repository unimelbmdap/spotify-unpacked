export interface MusicEntry {
  ts: string
  platform: string
  msPlayed: number
  trackName: string
  artistName: string
  albumName: string
  trackUri: string
  reasonStart: string
  reasonEnd: string
  shuffle: boolean
  skipped: boolean
  episodeName: string | null
  episodeShowName: string | null
  spotifyEpisodeUri: string | null
  audiobookTitle: string | null
  audiobookUri: string | null
  audiobookChapterUri: string | null
  audiobookChapterTitle: string | null
}

export function entryKey(entry: MusicEntry): string {
  return `${entry.ts}|${entry.trackUri}|${entry.msPlayed}`
}

export function parseStreamingFile(raw: unknown): MusicEntry[] {
  if (!Array.isArray(raw)) return []

  return raw
    .filter((entry) =>
      entry.ts >= '2025-06-01' &&
      entry.master_metadata_track_name !== null &&
      entry.spotify_track_uri !== null
    )
    .map((entry) => ({
      ts: entry.ts,
      platform: entry.platform,
      msPlayed: entry.ms_played,
      trackName: entry.master_metadata_track_name,
      artistName: entry.master_metadata_album_artist_name,
      albumName: entry.master_metadata_album_album_name,
      trackUri: entry.spotify_track_uri,
      reasonStart: entry.reason_start,
      reasonEnd: entry.reason_end,
      shuffle: entry.shuffle,
      skipped: entry.skipped,
      episodeName: entry.episode_name,
      episodeShowName: entry.episode_show_name,
      spotifyEpisodeUri: entry.spotify_episode_uri,
      audiobookTitle: entry.audiobook_title,
      audiobookUri: entry.audiobook_uri,
      audiobookChapterUri: entry.audiobook_chapter_uri,
      audiobookChapterTitle: entry.audiobook_chapter_title,
    }))}

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
