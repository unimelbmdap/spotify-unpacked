<script setup lang="ts">
import { computed } from 'vue'
import { useDark } from '@vueuse/core'
import { useVisualisationStore } from '@/stores/visualisation'
import { useDataStore } from '@/stores/data'
import { Bar, Bubble, Doughnut, Line, Pie, PolarArea, Radar, Scatter } from 'vue-chartjs'
import type { ChartData } from 'chart.js'

const visStore = useVisualisationStore()
const dataStore = useDataStore()
const isDark = useDark({ storageKey: 'spotify-unpacked-colour-mode' })

// Each vue-chartjs component expects its specific ChartData variant (e.g. ChartData<"bar">),
// but data is selected dynamically at runtime. The v-if guards in the template ensure correctness.
const currentData = computed<ChartData | undefined>(() =>
  dataStore.getChartData(visStore.selectedChart),
)
const baseOptions = computed(() => {
  const textColour = isDark.value ? 'rgba(255,255,255,0.85)' : 'rgba(0,0,0,0.8)'
  const gridColour = isDark.value ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'
  return { textColour, gridColour }
})

const cartesianOptions = computed(() => {
  const { textColour, gridColour } = baseOptions.value
  return {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        ticks: { 
          color: textColour, autoSkip: false, maxRotation: 0, minRotation: 0,
         callback:  (_value: number | string, index: number) => {
            const labels = currentData.value?.labels as string[] | undefined
            const current = labels?.[index]
            const prev = index > 0 ? labels?.[index - 1] : undefined

            const raw = labels?.[index]
            const label = typeof raw === 'string' ? raw : ''
            if (!/^\d{4}-\d{2}(-\d{2})?$/.test(label)) return label || ''

            if (!current) return ''

            const currentMonth = current.slice(0, 7) // YYYY-MM
            const prevMonth = prev?.slice(0, 7)

            if (index === 0 || currentMonth !== prevMonth) {
              const [year, month] = currentMonth.split('-')
              return new Date(`${year}-${month}-01T00:00:00Z`).toLocaleDateString('en-GB', { month: 'short' })
            }

            return ''}},
        grid: { color: gridColour },
      },
      y: { ticks: { color: textColour }, grid: { color: gridColour } },
    },
    plugins: { legend: { labels: { color: textColour } } },
  }
})

const radialOptions = computed(() => {
  const { textColour, gridColour } = baseOptions.value
  return {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        ticks: { color: textColour, backdropColor: 'transparent' },
        grid: { color: gridColour },
        pointLabels: { color: textColour },
      },
    },
    plugins: { legend: { labels: { color: textColour } } },
  }
})

const simpleOptions = computed(() => {
  const { textColour } = baseOptions.value
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: textColour } } },
  }
})
</script>

<template>
  <template v-if="currentData">
    <Bar
      v-if="visStore.selectedChart === 'bar'"
      :key="`bar-${isDark}`"
      :data="currentData as never"
      :options="cartesianOptions"
    />
    <Line
      v-else-if="visStore.selectedChart === 'line'"
      :key="`line-${isDark}`"
      :data="currentData as never"
      :options="cartesianOptions"
    />
    <Pie
      v-else-if="visStore.selectedChart === 'pie'"
      :key="`pie-${isDark}`"
      :data="currentData as never"
      :options="simpleOptions"
    />
    <Doughnut
      v-else-if="visStore.selectedChart === 'doughnut'"
      :key="`doughnut-${isDark}`"
      :data="currentData as never"
      :options="simpleOptions"
    />
    <Radar
      v-else-if="visStore.selectedChart === 'radar'"
      :key="`radar-${isDark}`"
      :data="currentData as never"
      :options="radialOptions"
    />
    <PolarArea
      v-else-if="visStore.selectedChart === 'polarArea'"
      :key="`polar-${isDark}`"
      :data="currentData as never"
      :options="radialOptions"
    />
    <Bubble
      v-else-if="visStore.selectedChart === 'bubble'"
      :key="`bubble-${isDark}`"
      :data="currentData as never"
      :options="cartesianOptions"
    />
    <Scatter
      v-else-if="visStore.selectedChart === 'scatter'"
      :key="`scatter-${isDark}`"
      :data="currentData as never"
      :options="cartesianOptions"
    />
  </template>
  <p v-else class="text-muted-foreground text-sm text-center">
    No data available for this chart type.
  </p>
</template>
