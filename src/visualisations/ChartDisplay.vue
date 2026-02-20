<script setup lang="ts">
import { computed } from 'vue'
import { useDark } from '@vueuse/core'
import { useVisualisationStore } from '@/stores/visualisation'
import { useDataStore } from '@/stores/data'
import { Bar, Bubble, Doughnut, Line, Pie, PolarArea, Radar, Scatter } from 'vue-chartjs'

const visStore = useVisualisationStore()
const dataStore = useDataStore()
const isDark = useDark({ storageKey: 'spotify-unpacked-colour-mode' })

// Each vue-chartjs component expects its specific ChartData variant (e.g. ChartData<"bar">),
// but data is selected dynamically at runtime. The v-if guards in the template ensure correctness.
const currentData = computed(() => dataStore.getChartData(visStore.selectedChart) as any)

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
        ticks: { color: textColour, autoSkip: false, maxRotation: 0, minRotation: 0 },
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
      :data="currentData"
      :options="cartesianOptions"
    />
    <Line
      v-else-if="visStore.selectedChart === 'line'"
      :key="`line-${isDark}`"
      :data="currentData"
      :options="cartesianOptions"
    />
    <Pie
      v-else-if="visStore.selectedChart === 'pie'"
      :key="`pie-${isDark}`"
      :data="currentData"
      :options="simpleOptions"
    />
    <Doughnut
      v-else-if="visStore.selectedChart === 'doughnut'"
      :key="`doughnut-${isDark}`"
      :data="currentData"
      :options="simpleOptions"
    />
    <Radar
      v-else-if="visStore.selectedChart === 'radar'"
      :key="`radar-${isDark}`"
      :data="currentData"
      :options="radialOptions"
    />
    <PolarArea
      v-else-if="visStore.selectedChart === 'polarArea'"
      :key="`polar-${isDark}`"
      :data="currentData"
      :options="radialOptions"
    />
    <Bubble
      v-else-if="visStore.selectedChart === 'bubble'"
      :key="`bubble-${isDark}`"
      :data="currentData"
      :options="cartesianOptions"
    />
    <Scatter
      v-else-if="visStore.selectedChart === 'scatter'"
      :key="`scatter-${isDark}`"
      :data="currentData"
      :options="cartesianOptions"
    />
  </template>
  <p v-else class="text-muted-foreground text-sm text-center">
    No data available for this chart type.
  </p>
</template>
