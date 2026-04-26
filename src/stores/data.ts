import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export interface LoadedFile {
  name: string
  size: number
}

import { useVisualisationStore } from '@/stores/visualisation'
import type { SpotifyStreamingHistoryRecord, SpotifyPlaylist, SpotifyLibraryTrack } from '@/types/spotify'

export const useDataStore = defineStore('data', () => {
  const files = ref<LoadedFile[]>([])
  const isLoading = ref(false)

  // Data State
  const streamingHistory = ref<SpotifyStreamingHistoryRecord[]>([])
  const playlists = ref<SpotifyPlaylist[]>([])
  const library = ref<SpotifyLibraryTrack[]>([])
  const inferences = ref<any[]>([])

  // Emotion Maps Cache
  const emotionMaps = ref<{ uri_map: Record<string, any>, name_map: Record<string, any> } | null>(null)

  const visStore = useVisualisationStore()

  const filteredHistory = computed(() => {
    let hist = streamingHistory.value

    if (visStore.dateRange.start) {
      const start = new Date(visStore.dateRange.start).getTime()
      hist = hist.filter(h => new Date(h.ts).getTime() >= start)
    }
    if (visStore.dateRange.end) {
      const end = new Date(visStore.dateRange.end).getTime()
      hist = hist.filter(h => new Date(h.ts).getTime() <= end)
    }
    if (visStore.year !== 'All') {
      hist = hist.filter(h => h.ts.startsWith(visStore.year))
    }
    if (visStore.sourceOrigin === 'Library') {
      const libIds = new Set(library.value.map(l => l.uri))
      hist = hist.filter(h => libIds.has(h.spotify_track_uri || ''))
    } else if (visStore.sourceOrigin === 'Playlist') {
      const plIds = new Set<string>()
      playlists.value.forEach(p => p.items?.forEach((i: any) => i.track?.trackUri && plIds.add(i.track.trackUri)))
      hist = hist.filter(h => plIds.has(h.spotify_track_uri || ''))
    }
    if (visStore.aiGhostToggle) {
      hist = hist.filter(h => ['autoplay', 'radio', 'recommendation'].includes(h.reason_start || ''))
    }
    return hist
  })

  const availableYears = computed(() => {
    const years = new Set<string>()
    streamingHistory.value.forEach(h => {
      if (h.ts) years.add(h.ts.split('-')[0]!)
    })
    return ['All', ...Array.from(years).sort().reverse()]
  })

  function rollingMean(dataArray: number[], windowSize: number, shouldSmooth: boolean): number[] {
    if (!shouldSmooth) return [...dataArray]
    const result: number[] = []
    for (let i = 0; i < dataArray.length; i++) {
      const start = Math.max(0, i - windowSize + 1)
      const windowSlice = dataArray.slice(start, i + 1)
      const avg = windowSlice.reduce((sum, val) => sum + val, 0) / windowSlice.length
      result.push(avg)
    }
    return result
  }

  function getAcademicDates(year: number) {
    // Approx UniMelb patterns: 
    // S1: Starts ~March 1. SWOTVAC is Week 13 (~May 24). Exams are June.
    // S2: Starts ~July 24. SWOTVAC is Week 43 (~Oct 25). Exams are Nov.
    return {
      s1_swotvic_start: `${year}-05-24`,
      s1_swotvic_end: `${year}-05-31`,
      s1_exams_start: `${year}-06-01`,
      s1_exams_end: `${year}-06-21`,
      s2_swotvic_start: `${year}-10-24`,
      s2_swotvic_end: `${year}-10-31`,
      s2_exams_start: `${year}-11-01`,
      s2_exams_end: `${year}-11-21`,
    }
  }

  const baseTimeline = computed(() => {
    const hist = filteredHistory.value
    // Explicitly listen to smoothing toggle to trigger re-computation
    const _smoothing = visStore.useRollingAverage

    const posTags = ['joy', 'love', 'happy', 'calm', 'energetic']
    const negTags = ['anger', 'sadness', 'fear', 'sad']
    const emotions = [...posTags, ...negTags, 'surprise']
    const cMap: Record<string, string> = {
      'love': '#FF69B4', 'joy': '#FFD700', 'fear': '#228B22', 'surprise': '#00BFFF',
      'sadness': '#0000FF', 'anger': '#FF0000', 'energetic': '#FFA500',
      'sad': '#4169E1', 'calm': '#B0C4DE', 'happy': '#87CEEB',
    }

    // 1. Organize into continuous dates and handle imputation
    // IMPORTANT: Clone each record to avoid mutating the source reactive objects (infinite loop)
    const sortedHist = [...hist]
      .sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime())
      .map(h => {
        // Strip any lingering imputed flags to ensure a fresh calculation
        const { imputed_500k, imputed_278k, ...clean } = h as any
        return { ...clean } as SpotifyStreamingHistoryRecord
      })

    // Nearest-neighbor imputation (Forward then Backward for gaps at start)
    if (visStore.allowImputation) {
      const columns: ('emotion_500k' | 'emotion_278k')[] = ['emotion_500k', 'emotion_278k']
      columns.forEach(col => {
        const impKey: 'imputed_500k' | 'imputed_278k' = col === 'emotion_500k' ? 'imputed_500k' : 'imputed_278k'
        let lastKnown: string | undefined = undefined
        // Forward pass
        for (let i = 0; i < sortedHist.length; i++) {
          const record = sortedHist[i]
          if (!record) continue
          const em = record[col]
          if (em && em !== 'niche_selection') {
            lastKnown = em
          } else if (lastKnown) {
            record[col] = lastKnown
            record[impKey] = true
          }
        }
        // Backward pass (for initial gap)
        let nextKnown: string | undefined = undefined
        for (let i = sortedHist.length - 1; i >= 0; i--) {
          const record = sortedHist[i]
          if (!record) continue
          const em = record[col]
          if (em && em !== 'niche_selection') {
            nextKnown = em
          } else if (nextKnown && (record[col] === undefined || record[col] === 'niche_selection')) {
            record[col] = nextKnown
            record[impKey] = true
          }
        }
      })

      // After imputation, update emotion_final status ONLY for newly filled gaps
      sortedHist.forEach(record => {
        if (record.emotion_final === 'niche_selection' && (record.emotion_500k || record.emotion_278k)) {
          record.emotion_final = record.emotion_500k || record.emotion_278k
        }
      })
    }

    const dates: string[] = []
    if (sortedHist.length > 0) {
      const allTimestamps = sortedHist.map(h => new Date(h.ts).getTime())
      const start = new Date(new Date(Math.min(...allTimestamps)).toISOString().split('T')[0]!)
      const end = new Date(new Date(Math.max(...allTimestamps)).toISOString().split('T')[0]!)

      const current = new Date(start)
      while (current <= end) {
        dates.push(current.toISOString().split('T')[0]!)
        current.setDate(current.getDate() + 1)
      }
    }

    // 2. Compute timeline sigs for 500k and 278k
    function computeSig(column: 'emotion_500k' | 'emotion_278k') {
      const dailyTotalMs: Record<string, number> = {}
      const dailyEmotionMs: Record<string, Record<string, number>> = {}

      sortedHist.forEach(h => {
        const d = h.ts.split('T')[0] as string
        const em = h[column] as string | undefined

        // Sum ALL ms_played to the daily total to ensure 100% representation
        dailyTotalMs[d] = (dailyTotalMs[d] || 0) + h.ms_played

        if (em && em !== 'niche_selection') {
          if (!dailyEmotionMs[d]) dailyEmotionMs[d] = {}
          dailyEmotionMs[d]![em] = (dailyEmotionMs[d]![em] || 0) + h.ms_played
        }
      })

      const rawPerc: Record<string, number[]> = {}
      emotions.forEach(e => rawPerc[e] = [])
      dates.forEach(d => {
        const total = dailyTotalMs[d] || 0
        emotions.forEach(e => {
          if (total > 0) {
            rawPerc[e]!.push(((dailyEmotionMs[d]?.[e] || 0) / total) * 100)
          } else {
            rawPerc[e]!.push(0)
          }
        })
      })

      const sig: Record<string, number[]> = {}
      emotions.forEach(e => sig[e] = rollingMean(rawPerc[e]!, 7, _smoothing))
      return sig
    }

    const sig500 = computeSig('emotion_500k')
    const sig278 = computeSig('emotion_278k')

    // (Moved to liveChartData to prevent recompute on scroll)

    // 3. Tug Of War
    const tugPos = dates.map((_, i) => {
      let p500 = 0; posTags.forEach(t => p500 += (sig500[t] ? sig500[t]![i] as number : 0))
      let p278 = 0; posTags.forEach(t => p278 += (sig278[t] ? sig278[t]![i] as number : 0))
      return (p500 + p278) / 2
    })
    const tugNeg = dates.map((_, i) => {
      let n500 = 0; negTags.forEach(t => n500 += (sig500[t] ? sig500[t]![i] as number : 0))
      let n278 = 0; negTags.forEach(t => n278 += (sig278[t] ? sig278[t]![i] as number : 0))
      return -(n500 + n278) / 2
    })

    // 4. Coverage Status
    const coverageCounts: Record<string, { k: number, i: number, n: number }> = {}
    sortedHist.forEach(h => {
      const d = h.ts.split('T')[0] as string
      if (!coverageCounts[d]) coverageCounts[d] = { k: 0, i: 0, n: 0 }

      const isObserved = (h.emotion_500k && h.imputed_500k !== true) || (h.emotion_278k && h.imputed_278k !== true)
      const isImputed = !isObserved && (h.emotion_500k || h.emotion_278k)

      if (isObserved) {
        coverageCounts[d]!.k++ // BLUE - Observed
      } else if (isImputed) {
        coverageCounts[d]!.i++ // AMBER - Imputed
      } else {
        coverageCounts[d]!.n++ // GRAY - Niche
      }
    })
    const rawK = dates.map(d => coverageCounts[d]?.k || 0)
    const rawI = dates.map(d => coverageCounts[d]?.i || 0)
    const rawN = dates.map(d => coverageCounts[d]?.n || 0)
    const covKaggle = rollingMean(rawK, 7, _smoothing)
    const covImputed = rollingMean(rawI, 7, _smoothing)
    const covNiche = rollingMean(rawN, 7, _smoothing)

    return {
      sig500, sig278, tugPos, tugNeg, covKaggle, covImputed, covNiche, dates, cMap, emotions, availableYears
    }
  })

  const liveChartData = computed<Record<string, any>>(() => {
    const base = baseTimeline.value

    const mapDatasets = (sig: Record<string, number[]>, filterList: string[]) => {
      return filterList.map(em => ({
        label: em,
        borderColor: base.cMap[em],
        backgroundColor: base.cMap[em],
        data: sig[em],
        fill: false,
        tension: 0.2
      }))
    }

    return {
      line500k: { labels: base.dates, datasets: mapDatasets(base.sig500, ['joy', 'love', 'surprise', 'sadness', 'anger', 'fear']) },
      line278k: { labels: base.dates, datasets: mapDatasets(base.sig278, ['happy', 'energetic', 'sad', 'calm']) },
      tugOfWar: {
        labels: base.dates,
        datasets: [
          { label: 'Positive', backgroundColor: '#32CD32', data: base.tugPos },
          { label: 'Negative', backgroundColor: '#DC143C', data: base.tugNeg }
        ]
      },
      matchCoverage: {
        labels: base.dates,
        datasets: [
          { label: 'Observed Match', backgroundColor: '#4682B4', data: base.covKaggle, fill: true, stacked: true },
          { label: 'Imputed Mood', backgroundColor: '#F0B35A', data: base.covImputed, fill: true, stacked: true },
          { label: 'Niche Selection', backgroundColor: '#D3D3D3', data: base.covNiche, fill: true, stacked: true }
        ]
      }
    }
  })

  const radarChartData = computed<Record<string, any>>(() => {
    const base = baseTimeline.value

    const ekmanEmotions = ['joy', 'love', 'surprise', 'sadness', 'anger', 'fear']
    const thayerEmotions = ['happy', 'energetic', 'sad', 'calm']

    // Extract middle slice for Radar
    const getRadar = (sig: Record<string, number[]>, allowedEmotions: string[]) => {
      const window = visStore.scrollWindow || [0, base.dates.length]
      const startIndex = Math.max(0, window[0])
      const endIndex = Math.min(base.dates.length, window[1] || base.dates.length)
      const middleIndex = Math.floor((startIndex + endIndex) / 2)

      const vals = allowedEmotions.map(e => {
        if (!sig[e] || sig[e]![middleIndex] === undefined) return 0
        return sig[e]![middleIndex]
      })

      return {
        labels: allowedEmotions,
        datasets: [{
          label: 'Focused Day %',
          data: vals,
          backgroundColor: allowedEmotions.map(e => base.cMap[e] || '#cccccc'),
          borderColor: allowedEmotions.map(e => base.cMap[e] || '#cccccc'),
          borderWidth: 1
        }]
      }
    }

    const windowSpan = visStore.scrollWindow || [0, base.dates.length]
    const midIdx = Math.floor((Math.max(0, windowSpan[0]) + Math.min(base.dates.length, windowSpan[1] || base.dates.length)) / 2)
    const radarDate = base.dates[midIdx] || 'No Data'

    return {
      radarDate,
      radar500k: getRadar(base.sig500, ekmanEmotions),
      radar278k: getRadar(base.sig278, thayerEmotions),
    }
  })

  const fileCount = computed(() => files.value.length)
  const hasData = computed(() => streamingHistory.value.length > 0 || library.value.length > 0 || playlists.value.length > 0)

  function getChartData(chartType: string): any | undefined {
    return liveChartData.value[chartType]
  }

  async function _parseAndAddFiles(rawFiles: File[]) {
    const newFilesInfo = rawFiles.map((f) => ({
      name: f.name,
      size: f.size,
    }))
    files.value.push(...newFilesInfo)

    for (const file of rawFiles) {
      try {
        const text = await file.text()
        const parsed = JSON.parse(text)

        const fname = file.name

        if (fname.includes('Streaming_History') && fname.includes('Audio')) {
          const streamRecords = parsed as SpotifyStreamingHistoryRecord[]

          // Map emotions dynamically
          streamRecords.forEach(record => {
            const track = (record.master_metadata_track_name || '').toLowerCase().trim()
            const artist = (record.master_metadata_album_artist_name || '').toLowerCase().trim()
            const uri = record.spotify_track_uri || ''

            const nameKey = `${track}|||${artist}`

            // Priority 1: 500k mapping (Name-based)
            if (emotionMaps.value?.name_map[nameKey]) {
              const feats = emotionMaps.value.name_map[nameKey]
              record.emotion_500k = feats.emotion_mapped
              record.features_500k = feats
            }
            // Priority 2: 278k mapping (URI-based)
            if (emotionMaps.value?.uri_map[uri]) {
              const feats = emotionMaps.value.uri_map[uri]
              record.emotion_278k = feats.emotion_mapped
              record.features_278k = feats
            }

            if (record.emotion_500k) {
              record.emotion_final = record.emotion_500k
            } else if (record.emotion_278k) {
              record.emotion_final = record.emotion_278k
            } else {
              record.emotion_final = 'niche_selection'
            }
          })

          streamingHistory.value.push(...streamRecords)
        } else if (fname.includes('Playlist') && parsed.playlists) {
          playlists.value.push(...(parsed.playlists as SpotifyPlaylist[]))
        } else if (fname.includes('YourLibrary') && parsed.tracks) {
          library.value.push(...(parsed.tracks as SpotifyLibraryTrack[]))
        } else if (fname.includes('Inferences') && parsed.inferences) {
          inferences.value.push(...parsed.inferences)
        }
      } catch (err) {
        console.error(`Error parsing ${file.name}:`, err)
      }
    }
  }

  async function ensureEmotionMaps() {
    if (emotionMaps.value) return;
    try {
      const res = await fetch('/emotion_map.json')
      if (res.ok) {
        emotionMaps.value = await res.json()
      } else {
        console.warn("Could not fetch emotion_map.json (did you run build_emotion_map.py?)")
        emotionMaps.value = { uri_map: {}, name_map: {} }
      }
    } catch (e) {
      console.warn("Failed to load emotion maps:", e)
      emotionMaps.value = { uri_map: {}, name_map: {} }
    }
  }

  async function loadFiles(rawFiles: File[]) {
    isLoading.value = true
    await ensureEmotionMaps()
    clear() // Clear existing first for fresh load
    await _parseAndAddFiles(rawFiles)
    isLoading.value = false
  }

  async function addFiles(rawFiles: File[]) {
    isLoading.value = true
    await ensureEmotionMaps()
    await _parseAndAddFiles(rawFiles)
    isLoading.value = false
  }

  function clear() {
    files.value = []
    streamingHistory.value = []
    playlists.value = []
    library.value = []
    inferences.value = []
  }

  return {
    files,
    isLoading,
    fileCount,
    hasData,
    streamingHistory,
    playlists,
    library,
    inferences,
    liveChartData,
    radarChartData,
    getChartData,
    loadFiles,
    addFiles,
    clear,
    filteredHistory,
    baseTimeline,
    availableYears,
    getAcademicDates
  }
})
