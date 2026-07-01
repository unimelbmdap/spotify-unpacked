import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { ChartData } from 'chart.js'
import { parseStreamingFile, parseLibraryFile, parsePlaylistFile, type MusicEntry } from '@/lib/parser'
import { classifyFile, type FileTypeKey, fileTypes } from '@/lib/fileTypes'
import {
  archetypeConfig,
  bandScore,
  responsiveReasonEndValues,
  responsiveReasonStartValues,
} from '@/lib/archetypeConfig'

export interface LoadedFile {
  name: string
  size: number
  type: FileTypeKey | 'unrecognised'
}

function sumMs(subset: MusicEntry[]) {
  return subset.reduce((sum, e) => sum + e.msPlayed, 0)
}

function msToHours(ms: number, decimals = 0) {
  const factor = 10 ** decimals
  return Math.round((ms / 1000 / 60 / 60) * factor) / factor
}

function byHour(subset: MusicEntry[]) {
  const totals = Array(24).fill(0)
  for (const entry of subset) {
    const hour = new Date(entry.ts).getHours()
    totals[hour] += entry.msPlayed
  }
  return totals.map(ms => msToHours(ms, 1))
}

function byDay(subset: MusicEntry[]) {
  const totals = Array(7).fill(0) // Mon=0 … Sun=6
  for (const entry of subset) {
    const dow = new Date(entry.ts).getDay() // 0=Sun, 1=Mon … 6=Sat
    const idx = dow === 0 ? 6 : dow - 1
    totals[idx] += entry.msPlayed
  }
  return totals.map(ms => msToHours(ms, 1))
}

function byMonth(subset: MusicEntry[]) {
  const counts: Record<string, number> = {}
  for (const entry of subset) {
    const date = new Date(entry.ts)
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
    counts[key] = (counts[key] ?? 0) + Math.round(entry.msPlayed / 1000 / 60)
  }
  return Object.fromEntries(
    Object.entries(counts)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, val]) => {
        const [year, month] = key.split('-')
        const label = new Date(Number(year), Number(month) - 1)
          .toLocaleString('default', { month: 'short', year: 'numeric' })
        return [label, val]
      })
  )
}

export const useDataStore = defineStore('data', () => {
  const entries = ref<MusicEntry[]>([])
  const files = ref<LoadedFile[]>([])
  const isLoading = ref(false)
  const chartData = ref<Record<string, ChartData>>({})

  const playlistUris = ref<Set<string>>(new Set())
  const libraryUris = ref<Set<string>>(new Set())

  const fileCount = computed(() => files.value.length)
  const hasData = computed(() => files.value.length > 0)

  function getChartData(chartType: string): ChartData | undefined {
    return chartData.value[chartType]
  }

  async function loadFiles(rawFiles: File[]) {
    isLoading.value = true
    try {
      for (const file of rawFiles) {
        try {
          const text = await file.text()
          const json = JSON.parse(text)
          const fileType = classifyFile(file.name)
          if (fileType === 'listening') {
            entries.value.push(...parseStreamingFile(json))
          } else if (fileType === 'library') {
            libraryUris.value = parseLibraryFile(json)
          } else if (fileType === 'playlists') {
            playlistUris.value = parsePlaylistFile(json)
          }
          files.value.push({ name: file.name, size: file.size, type: fileType })
        } catch {
          // skip files that can't be parsed
        }
      }
    } finally {
      isLoading.value = false
    }
  }

  const fileTypeStatus = computed(() => {
    const uploaded = new Set(files.value.map((f) => f.type))
    return Object.fromEntries(
      fileTypes.map((ft) => [ft.key, uploaded.has(ft.key)])
    ) as Record<FileTypeKey, boolean>
  })

  const listeningTimeHours = computed(() => msToHours(sumMs(entries.value)))
  const listeningTimeByMonth = computed(() => byMonth(entries.value))
  const listeningTimeByHour = computed(() => byHour(entries.value))
  const listeningTimeByDay = computed(() => byDay(entries.value))

  const uniqueTrackCount = computed(() => new Set(entries.value.map((e) => e.trackUri)).size)

  const favouriteHour = computed(() => {
    const counts: Record<number, number> = {}
    for (const entry of entries.value) {
      const hour = new Date(entry.ts).getHours()
      counts[hour] = (counts[hour] ?? 0) + 1
    }
    const topHour = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]
    if (!topHour) return null
    return new Date(0, 0, 0, Number(topHour[0])).toLocaleTimeString([], { hour: 'numeric', hour12: true })
  })

  const combinedLibraryUris = computed(() => new Set([...libraryUris.value, ...playlistUris.value]))
  const hasLibraryData = computed(() => libraryUris.value.size > 0 && playlistUris.value.size > 0)

  const libraryEntries = computed(() => entries.value.filter(e => combinedLibraryUris.value.has(e.trackUri)))
  const otherEntries = computed(() => entries.value.filter(e => !combinedLibraryUris.value.has(e.trackUri)))

  const listeningTimeHoursLibrary = computed(() => msToHours(sumMs(libraryEntries.value)))
  const listeningTimeHoursOther = computed(() => msToHours(sumMs(otherEntries.value)))

  const listeningTimePercentLibrary = computed(() => {
    const total = sumMs(entries.value)
    return total === 0 ? 0 : Math.round((sumMs(libraryEntries.value) / total) * 100)
  })
  const listeningTimePercentOther = computed(() => {
    const total = sumMs(entries.value)
    return total === 0 ? 0 : Math.round((sumMs(otherEntries.value) / total) * 100)
  })

  const listeningTimeByHourLibrary = computed(() => byHour(libraryEntries.value))
  const listeningTimeByHourOther = computed(() => byHour(otherEntries.value))
  const listeningTimeByDayLibrary = computed(() => byDay(libraryEntries.value))
  const listeningTimeByDayOther = computed(() => byDay(otherEntries.value))
  const listeningTimeByMonthLibrary = computed(() => byMonth(libraryEntries.value))
  const listeningTimeByMonthOther = computed(() => byMonth(otherEntries.value))

  const shuffleRate = computed(() => {
    if (entries.value.length === 0) return 0
    return entries.value.filter(e => e.shuffle === true).length / entries.value.length
  })

  const skipRate = computed(() => {
    if (entries.value.length === 0) return 0
    return entries.value.filter(e => e.skipped === true).length / entries.value.length
  })

  const responsiveReasonRate = computed(() => {
    if (entries.value.length === 0) return 0
    return entries.value.filter(e =>
      responsiveReasonEndValues.includes(e.reasonEnd) || responsiveReasonStartValues.includes(e.reasonStart)
    ).length / entries.value.length
  })

  const algorithmicRate = computed(() => {
    const totalMs = sumMs(entries.value)
    return totalMs === 0 ? 0 : sumMs(otherEntries.value) / totalMs
  })

  const receptiveness = computed(() => {
    const cfg = archetypeConfig.receptiveness
    return cfg.algorithmic.weight * bandScore(algorithmicRate.value, cfg.algorithmic)
  })

  const deliberate = computed(() => {
    const cfg = archetypeConfig.deliberate
    return (
      cfg.shuffle.weight * bandScore(shuffleRate.value, cfg.shuffle) +
      cfg.skip.weight * bandScore(skipRate.value, cfg.skip) +
      cfg.reason.weight * bandScore(responsiveReasonRate.value, cfg.reason) +
      cfg.algorithmic.weight * bandScore(algorithmicRate.value, cfg.algorithmic)
    )
  })

  const responsiveness = computed(() => {
    const cfg = archetypeConfig.responsiveness
    return (
      cfg.shuffle.weight * bandScore(shuffleRate.value, cfg.shuffle) +
      cfg.skip.weight * bandScore(skipRate.value, cfg.skip) +
      cfg.reason.weight * bandScore(responsiveReasonRate.value, cfg.reason)
    )
  })

  function clear() {
    files.value = []
    entries.value = []
    chartData.value = {}
    libraryUris.value = new Set()
    playlistUris.value = new Set()
  }

  return {
    // files & loading state
    files,
    entries,
    isLoading,
    fileCount,
    fileTypeStatus,
    hasData,
    hasLibraryData,
    chartData,
    getChartData,
    loadFiles,
    clear,

    // listening time, overall & by period
    listeningTimeHours,
    listeningTimeByMonth,
    listeningTimeByHour,
    listeningTimeByDay,
    uniqueTrackCount,
    favouriteHour,

    // listening time, split by library/playlists vs algorithm & other
    listeningTimeHoursLibrary,
    listeningTimeHoursOther,
    listeningTimePercentLibrary,
    listeningTimePercentOther,
    listeningTimeByHourLibrary,
    listeningTimeByHourOther,
    listeningTimeByDayLibrary,
    listeningTimeByDayOther,
    listeningTimeByMonthLibrary,
    listeningTimeByMonthOther,

    // listening archetype scores
    shuffleRate,
    skipRate,
    responsiveReasonRate,
    algorithmicRate,
    receptiveness,
    responsiveness,
    deliberate,
  }
})
