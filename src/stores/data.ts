import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { ChartData } from 'chart.js'

export interface LoadedFile {
  name: string
  size: number
}

type ExtendedRow = {
  ts?: string
  endTime?: string
  ms_played?: number
  msPlayed?: number
}

function getTimestamp(row: ExtendedRow): string | null {
  return row.ts ?? row.endTime ?? null
}

function getMs(row: ExtendedRow): number {
  return row.ms_played ?? row.msPlayed ?? 0
}

function isExtendedAudioFile(file: File): boolean {
  return file.name.toLowerCase().includes('streaming_history_audio')
}

async function parseExtendedRows(rawFiles: File[]): Promise<ExtendedRow[]> {
  const targetFiles = rawFiles.filter(isExtendedAudioFile)
  const parsedBatches = await Promise.all(
    targetFiles.map(async (file) => {
      try {
        const content = await file.text()
        const parsed = JSON.parse(content) as unknown
        if (!Array.isArray(parsed)) return []
        return parsed.filter((item): item is ExtendedRow => typeof item === 'object' && item !== null)
      } catch {
        return []
      }
    }),
  )

  return parsedBatches.flat()
}

function aggregateListeningByMonth(rows: ExtendedRow[], year: number): {
  labels: string[]
  data: number[]
} {
  const totals = new Map<string, number>()

  for (const row of rows) {
    const ts = getTimestamp(row)
    if (!ts) continue

    const date = new Date(ts)
    if (Number.isNaN(date.getTime())) continue
    if (date.getUTCFullYear() !== year) continue

    const monthKey = date.toISOString().slice(0, 7)
    const minutes = getMs(row) / 60000
    totals.set(monthKey, (totals.get(monthKey) ?? 0) + minutes)
  }

  const labels: string[] = []
  const start = new Date(Date.UTC(year, 0, 1))
  const end = new Date(Date.UTC(year + 1, 0, 1))

  for (let cursor = new Date(start); cursor < end; cursor.setUTCDate(cursor.getUTCDate() + 1)) {
    labels.push(cursor.toISOString().slice(0, 10))
  }

  const data = labels.map((label) => Number((totals.get(label)?? 0).toFixed(2)))


  return { labels, data }
}


function aggregateListeningByDay(rows: ExtendedRow[], year: number): {
  labels: string[]
  data: number[]
} {
  const totals = new Map<string, number>()

  for (const row of rows) {
    const ts = getTimestamp(row)
    if (!ts) continue

    const date = new Date(ts)
    if (Number.isNaN(date.getTime())) continue
    if (date.getUTCFullYear() !== year) continue

    const dayKey = date.toISOString().slice(0,10)
    const minutes = getMs(row) / 60000
    totals.set(dayKey, (totals.get(dayKey) ?? 0) + minutes)
  }


  const labels: string[] = []
  const start = new Date(Date.UTC(year, 0, 1))
  const end = new Date(Date.UTC(year + 1, 0, 1))

  for (let cursor = new Date(start); cursor < end; cursor.setUTCDate(cursor.getUTCDate() + 1)) {
    labels.push(cursor.toISOString().slice(0, 10))
  }

  const data = labels.map((label) => Number((totals.get(label)?? 0).toFixed(2)))
  return { labels, data }
}

const dummyChartData: Record<string, ChartData> = {
  bar: {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      { label: 'Streams', backgroundColor: '#6366f1', data: [120, 190, 80, 140, 200, 160] },
    ],
  },
  line: {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      {
        label: 'Listeners',
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99,102,241,0.2)',
        data: [65, 59, 80, 81, 56, 72],
        fill: true,
        tension: 0.2,
      },
    ],
  },
  pie: {
    labels: ['Pop', 'Rock', 'Jazz', 'Hip-Hop', 'Electronic'],
    datasets: [
      {
        backgroundColor: ['#6366f1', '#ec4899', '#f59e0b', '#10b981', '#3b82f6'],
        data: [30, 20, 15, 25, 10],
      },
    ],
  },
  doughnut: {
    labels: ['Mobile', 'Desktop', 'Tablet', 'Smart TV'],
    datasets: [
      { backgroundColor: ['#6366f1', '#ec4899', '#f59e0b', '#10b981'], data: [45, 30, 15, 10] },
    ],
  },
  radar: {
    labels: ['Energy', 'Danceability', 'Valence', 'Acousticness', 'Tempo', 'Speechiness'],
    datasets: [
      {
        label: 'Track A',
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99,102,241,0.2)',
        data: [80, 65, 70, 30, 55, 40],
      },
      {
        label: 'Track B',
        borderColor: '#ec4899',
        backgroundColor: 'rgba(236,72,153,0.2)',
        data: [50, 80, 60, 70, 45, 30],
      },
    ],
  },
  polarArea: {
    labels: ['Acousticness', 'Danceability', 'Energy', 'Instrumentalness', 'Liveness'],
    datasets: [
      {
        backgroundColor: ['#6366f1', '#ec4899', '#f59e0b', '#10b981', '#3b82f6'],
        data: [70, 85, 60, 30, 45],
      },
    ],
  },
  bubble: {
    datasets: [
      {
        label: 'Playlist A',
        backgroundColor: 'rgba(99,102,241,0.5)',
        data: [
          { x: 10, y: 20, r: 15 },
          { x: 25, y: 35, r: 10 },
          { x: 40, y: 10, r: 20 },
        ],
      },
      {
        label: 'Playlist B',
        backgroundColor: 'rgba(236,72,153,0.5)',
        data: [
          { x: 15, y: 40, r: 12 },
          { x: 30, y: 25, r: 18 },
          { x: 50, y: 30, r: 8 },
        ],
      },
    ],
  },
  scatter: {
    datasets: [
      {
        label: 'Tempo vs Energy',
        backgroundColor: '#6366f1',
        data: [
          { x: 80, y: 40 },
          { x: 100, y: 60 },
          { x: 120, y: 75 },
          { x: 140, y: 55 },
          { x: 160, y: 85 },
          { x: 90, y: 50 },
          { x: 110, y: 70 },
        ],
      },
    ],
  },
}

export const useDataStore = defineStore('data', () => {
  const files = ref<LoadedFile[]>([])
  const isLoading = ref(false)
  const chartData = ref<Record<string, ChartData>>({ ...dummyChartData })
  const extendedRows = ref<ExtendedRow[]>([])

  const fileCount = computed(() => files.value.length)
  const hasData = computed(() => files.value.length > 0)

  function getChartData(chartType: string): ChartData | undefined {
    return chartData.value[chartType]
  }

  function updateLineChartFromExtendedRows(year = 2025) {
    const { labels, data } = aggregateListeningByDay(extendedRows.value, year)
    const pointRadii = data.map((value) => (value !== 0 ? 2.5 : 0))
    const pointHoverRadii = data.map((value) => (value !== 0 ? 4 : 0))

    chartData.value.line = {
      labels,
      datasets: [
        {
          label: `Listening minutes (${year})`,
          borderColor: '#1DB954',
          backgroundColor: 'rgba(29,185,84,0.2)',
          data,
          fill: true,
          tension: 0.2,
          pointRadius: pointRadii,
          pointHoverRadius: pointHoverRadii,
          pointHitRadius: 8,
        },
      ],
    }
  }



  async function loadFiles(rawFiles: File[]) {
    isLoading.value = true
    try {
      files.value = rawFiles.map((f) => ({
        name: f.name,
        size: f.size,
      }))

      extendedRows.value = await parseExtendedRows(rawFiles)
      updateLineChartFromExtendedRows()
    } finally {
      isLoading.value = false
    }
  }

  async function addFiles(rawFiles: File[]) {
    isLoading.value = true
    try {
      const newFiles = rawFiles.map((f) => ({
        name: f.name,
        size: f.size,
      }))

      files.value.push(...newFiles)

      const parsedRows = await parseExtendedRows(rawFiles)
      extendedRows.value.push(...parsedRows)
      updateLineChartFromExtendedRows()
    } finally {
      isLoading.value = false
    }
  }

  function clear() {
    files.value = []
    extendedRows.value = []
    chartData.value = { ...dummyChartData }
  }

  return { files, isLoading, fileCount, hasData, chartData, getChartData, loadFiles, addFiles, clear }
})
