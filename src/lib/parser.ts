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

export function parseLibraryFile(raw: unknown): Set<string> {
  if (typeof raw !== 'object' || raw === null) return new Set()
  const { tracks } = raw as { tracks?: Array<{ uri?: string }> }
  if (!Array.isArray(tracks)) return new Set()
  return new Set(tracks.map(t => t.uri).filter((uri): uri is string => typeof uri === 'string'))
}

export function parsePlaylistFile(raw: unknown): Set<string> {
  if (typeof raw !== 'object' || raw === null) return new Set()
  const { playlists } = raw as { playlists?: Array<{ items?: Array<{ track?: { trackUri?: string } }> }> }
  if (!Array.isArray(playlists)) return new Set()
  const uris = new Set<string>()
  for (const playlist of playlists) {
    for (const item of playlist.items ?? []) {
      if (item.track?.trackUri) uris.add(item.track.trackUri)
    }
  }
  return uris
}
