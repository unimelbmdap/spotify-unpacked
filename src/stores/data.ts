import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { ChartData } from 'chart.js'
import { parseStreamingFile, parseLibraryFile, parsePlaylistFile, type MusicEntry } from '@/lib/parser'
import { classifyFile, type FileTypeKey, fileTypes } from '@/lib/fileTypes'

export interface LoadedFile {
  name: string
  size: number
  type: FileTypeKey | 'unrecognised'
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
  }
  finally {
  isLoading.value = false}
}

const fileTypeStatus = computed(() => {
  const uploaded = new Set(files.value.map((f) => f.type))
  return Object.fromEntries(
    fileTypes.map((ft) => [ft.key, uploaded.has(ft.key)])
  ) as Record<FileTypeKey, boolean>
})

const listeningTimeHours = computed(() => {
  const totalMs = entries.value.reduce((sum, e) => sum + e.msPlayed, 0)
  return Math.round(totalMs / 1000 / 60 / 60)
})

const listeningTimeByMonth = computed(() => {
  const counts: Record<string, number> = {}
  for (const entry of entries.value) {
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
})

const uniqueTrackCount = computed(() => {
  return new Set(entries.value.map((e) => e.trackUri)).size
})

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

const listeningTimeByHour = computed(() => {
  const totals = Array(24).fill(0)
  for (const entry of entries.value) {
    const hour = new Date(entry.ts).getHours()
    totals[hour] += entry.msPlayed
  }
  return totals.map(ms => Math.round((ms / 1000 / 60 / 60) * 10) / 10)
})

const listeningTimeByDay = computed(() => {
  const totals = Array(7).fill(0) // Mon=0 … Sun=6
  for (const entry of entries.value) {
    const dow = new Date(entry.ts).getDay() // 0=Sun, 1=Mon … 6=Sat
    const idx = dow === 0 ? 6 : dow - 1
    totals[idx] += entry.msPlayed
  }
  return totals.map(ms => Math.round((ms / 1000 / 60 / 60) * 10) / 10)
})

const combinedLibraryUris = computed(() => new Set([...libraryUris.value, ...playlistUris.value]))

function byHour(subset: MusicEntry[]) {
  const totals = Array(24).fill(0)
  for (const entry of subset) {
    const hour = new Date(entry.ts).getHours()
    totals[hour] += entry.msPlayed
  }
  return totals.map(ms => Math.round((ms / 1000 / 60 / 60) * 10) / 10)
}

function byDay(subset: MusicEntry[]) {
  const totals = Array(7).fill(0)
  for (const entry of subset) {
    const dow = new Date(entry.ts).getDay()
    const idx = dow === 0 ? 6 : dow - 1
    totals[idx] += entry.msPlayed
  }
  return totals.map(ms => Math.round((ms / 1000 / 60 / 60) * 10) / 10)
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

const libraryEntries = computed(() => entries.value.filter(e => combinedLibraryUris.value.has(e.trackUri)))
const otherEntries = computed(() => entries.value.filter(e => !combinedLibraryUris.value.has(e.trackUri)))

const listeningTimeHoursLibrary = computed(() =>
  Math.round(libraryEntries.value.reduce((sum, e) => sum + e.msPlayed, 0) / 1000 / 60 / 60)
)
const listeningTimeHoursOther = computed(() =>
  Math.round(otherEntries.value.reduce((sum, e) => sum + e.msPlayed, 0) / 1000 / 60 / 60)
)

const listeningTimeByHourLibrary = computed(() => byHour(libraryEntries.value))
const listeningTimeByHourOther = computed(() => byHour(otherEntries.value))
const listeningTimeByDayLibrary = computed(() => byDay(entries.value.filter(e => combinedLibraryUris.value.has(e.trackUri))))
const listeningTimeByDayOther = computed(() => byDay(entries.value.filter(e => !combinedLibraryUris.value.has(e.trackUri))))
const listeningTimeByMonthLibrary = computed(() => byMonth(entries.value.filter(e => combinedLibraryUris.value.has(e.trackUri))))
const listeningTimeByMonthOther = computed(() => byMonth(entries.value.filter(e => !combinedLibraryUris.value.has(e.trackUri))))

function clear() {
  files.value = []
  entries.value = []
  chartData.value = {}
}

  return { files, entries, isLoading, fileCount, fileTypeStatus, hasData, chartData, getChartData, loadFiles, clear, listeningTimeHours, listeningTimeHoursLibrary, listeningTimeHoursOther, listeningTimeByMonth, uniqueTrackCount, favouriteHour, listeningTimeByHour, listeningTimeByDay, listeningTimeByHourLibrary, listeningTimeByHourOther, listeningTimeByDayLibrary, listeningTimeByDayOther, listeningTimeByMonthLibrary, listeningTimeByMonthOther }
})
