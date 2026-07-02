export const fileTypes = [
  {
    key: 'listening',
    label: 'Listening history',
    what: 'Every song listened to, when played, and for how long.',
    file: 'Streaming_History_audio_yyyy-yyyy_n.json',
    why: 'Understand listening patterns across time and seasons.',
    pattern: /streaming_history/i,
    optional: false,
  },
  {
    key: 'library',
    label: 'Your library',
    what: 'What we see: Liked songs, saved playlists',
    file: 'YourLibrary.json',
    why: 'Shows patterns of curation, how much of your listening patterns comes from your library vs Spotify algorithm',
    pattern: /yourlibrary/i,
    optional: false,
  },
  {
    key: 'playlists',
    label: 'Your playlists',
    what: 'All playlists you\'ve created, including their tracks and metadata.',
    file: 'Playlist1.json',
    why: 'Analyse your curation habits and playlist listening patterns.',
    pattern: /playlist/i,
    optional: false,
  },
  {
    key: 'search',
    label: 'Search history',
    what: 'All search queries (artists, songs, keywords)',
    file: 'SearchQueries.json',
    why: 'Reveals frequency of searches but we ignore the search terminology',
    pattern: /searchqueries/i,
    optional: false,
  },
  {
    key: 'aidj',
    label: 'AI DJ history (optional)',
    what: 'Tracks queued by Spotify\'s AI DJ feature.',
    file: 'AIDJQueue.json',
    why: 'Reveals what the algorithm thought you\'d enjoy and whether you actually listened.',
    pattern: /aidjqueue/i,
    optional: true,
  },
] as const

export type FileTypeKey = typeof fileTypes[number]['key']

export function classifyFile(filename: string): FileTypeKey | 'unrecognised' {
  const match = fileTypes.find((ft) => ft.pattern.test(filename))
  return match ? match.key : 'unrecognised'
}
