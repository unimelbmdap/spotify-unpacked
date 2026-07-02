import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { ChartData } from 'chart.js'
import { parseStreamingFile, parseLibraryFile, parsePlaylistFile, entryKey, type MusicEntry } from '@/lib/parser'
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

function monthKeyAndLabel(ts: string) {
  const date = new Date(ts)
  const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
  const label = new Date(date.getFullYear(), date.getMonth()).toLocaleString('default', { month: 'short', year: 'numeric' })
  return { key, label }
}

function groupByMonth(subset: MusicEntry[]) {
  const groups = new Map<string, { label: string; entries: MusicEntry[] }>()
  for (const entry of subset) {
    const { key, label } = monthKeyAndLabel(entry.ts)
    let group = groups.get(key)
    if (!group) {
      group = { label, entries: [] }
      groups.set(key, group)
    }
    group.entries.push(entry)
  }
  return [...groups.keys()]
    .sort((a, b) => a.localeCompare(b))
    .map((key) => groups.get(key)!)
}

function byMonth(subset: MusicEntry[]) {
  return Object.fromEntries(
    groupByMonth(subset).map(({ label, entries }) => [
      label,
      entries.reduce((sum, e) => sum + Math.round(e.msPlayed / 1000 / 60), 0),
    ])
  )
}

function dateKeyAndLabel(ts: string) {
  const date = new Date(ts)
  const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  const label = date.toLocaleString('default', { day: 'numeric', month: 'short', year: 'numeric' })
  return { key, label }
}

function groupByDate(subset: MusicEntry[]) {
  const groups = new Map<string, { label: string; monthLabel: string; entries: MusicEntry[] }>()
  for (const entry of subset) {
    const { key, label } = dateKeyAndLabel(entry.ts)
    let group = groups.get(key)
    if (!group) {
      group = { label, monthLabel: monthKeyAndLabel(entry.ts).label, entries: [] }
      groups.set(key, group)
    }
    group.entries.push(entry)
  }
  return [...groups.keys()]
    .sort((a, b) => a.localeCompare(b))
    .map((key) => groups.get(key)!)
}

function byDate(subset: MusicEntry[]) {
  return Object.fromEntries(
    groupByDate(subset).map(({ label, entries }) => [
      label,
      entries.reduce((sum, e) => sum + Math.round(e.msPlayed / 1000 / 60), 0),
    ])
  )
}

export const useDataStore = defineStore('data', () => {
  const entries = ref<MusicEntry[]>([])
  const seenEntries = ref<Set<string>>(new Set())
  const files = ref<LoadedFile[]>([])
  const skippedFiles = ref<string[]>([])
  const skippedEntryCount = ref(0)
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
          const isDuplicate = files.value.some((f) => f.name === file.name && f.size === file.size)
          if (isDuplicate) {
            skippedFiles.value.push(file.name)
          } else {
            if (fileType === 'listening') {
              const newEntries = parseStreamingFile(json).filter((entry) => {
                const key = entryKey(entry)
                if (seenEntries.value.has(key)) {
                  skippedEntryCount.value++
                  return false
                }
                seenEntries.value.add(key)
                return true
              })
              entries.value.push(...newEntries)
            } else if (fileType === 'library') {
              libraryUris.value = parseLibraryFile(json)
            } else if (fileType === 'playlists') {
              playlistUris.value = parsePlaylistFile(json)
            }
            files.value.push({ name: file.name, size: file.size, type: fileType })
          }
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

  const monthlyGroups = computed(() => groupByMonth(entries.value))
  const monthLabels = computed(() => monthlyGroups.value.map(g => g.label))
  const entriesByMonth = computed(() =>
    Object.fromEntries(monthlyGroups.value.map(g => [g.label, g.entries]))
  )

  const dailyGroups = computed(() => groupByDate(entries.value))
  const listeningTimeByDate = computed(() => byDate(entries.value))
  const dateMonthLabels = computed(() => dailyGroups.value.map(g => g.monthLabel))

  function entriesForMonth(label: string) {
    return entriesByMonth.value[label] ?? []
  }

  function hourlyForMonth(label: string) {
    return byHour(entriesForMonth(label))
  }

  function listeningHoursForMonth(label: string) {
    return msToHours(sumMs(entriesForMonth(label)), 1)
  }

  const listeningTimeByDay = computed(() => byDay(entries.value))

  const uniqueTrackCount = computed(() => new Set(entries.value.map((e) => e.trackUri)).size)

  function favouriteHourOf(subset: MusicEntry[]) {
    const counts: Record<number, number> = {}
    for (const entry of subset) {
      const hour = new Date(entry.ts).getHours()
      counts[hour] = (counts[hour] ?? 0) + 1
    }
    const topHour = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]
    if (!topHour) return null
    return new Date(0, 0, 0, Number(topHour[0])).toLocaleTimeString([], { hour: 'numeric', hour12: true })
  }

  const favouriteHour = computed(() => favouriteHourOf(entries.value))

  function favouriteHourForMonth(label: string) {
    return favouriteHourOf(entriesForMonth(label))
  }

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
  const listeningTimeByDateLibrary = computed(() => byDate(libraryEntries.value))
  const listeningTimeByDateOther = computed(() => byDate(otherEntries.value))

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
    skippedFiles.value = []
    skippedEntryCount.value = 0
    entries.value = []
    seenEntries.value = new Set()
    chartData.value = {}
    libraryUris.value = new Set()
    playlistUris.value = new Set()
  }

  return {
    // files & loading state
    files,
    skippedFiles,
    skippedEntryCount,
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
    listeningTimeByDate,
    dateMonthLabels,
    listeningTimeByHour,
    listeningTimeByDay,
    uniqueTrackCount,
    favouriteHour,
    monthLabels,
    entriesForMonth,
    hourlyForMonth,
    listeningHoursForMonth,
    favouriteHourForMonth,

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
    listeningTimeByDateLibrary,
    listeningTimeByDateOther,

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
