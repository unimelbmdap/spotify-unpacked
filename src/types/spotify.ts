export interface SpotifyStreamingHistoryRecord {
  ts: string;
  username: string;
  platform: string;
  ms_played: number;
  conn_country: string;
  ip_addr_decrypted: string;
  user_agent_decrypted: string;
  master_metadata_track_name: string | null;
  master_metadata_album_artist_name: string | null;
  master_metadata_album_album_name: string | null;
  spotify_track_uri: string | null;
  episode_name: string | null;
  episode_show_name: string | null;
  spotify_episode_uri: string | null;
  reason_start: string;
  reason_end: string;
  shuffle: boolean;
  skipped: boolean;
  offline: boolean;
  offline_timestamp: number;
  incognito_mode: boolean;
  emotion_label?: string; // Appended locally from Kaggle maps (Legacy)
  features?: any; // Legacy
  
  // Dashboard Specific fields
  emotion_500k?: string;
  features_500k?: any;
  emotion_278k?: string;
  features_278k?: any;
  emotion_final?: string;
  imputed_500k?: boolean;
  imputed_278k?: boolean;
}

export interface SpotifyPlaylistTrack {
  trackName: string;
  artistName: string;
  albumName: string;
  trackUri: string;
}

export interface SpotifyPlaylistItem {
  track: SpotifyPlaylistTrack;
  episode: any;
  localTrack: any;
  addedDate: string;
}

export interface SpotifyPlaylist {
  name: string;
  lastModifiedDate: string;
  description: string;
  numberOfFollowers: number;
  items: SpotifyPlaylistItem[];
}

export interface SpotifyLibraryTrack {
  artist: string;
  album: string;
  track: string;
  uri: string;
}

export interface SpotifyInference {
  [key: string]: any; // Just strings typically
}
