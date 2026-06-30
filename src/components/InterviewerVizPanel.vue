<script setup lang="ts">
import { useDataStore } from '@/stores/data'
import { computed } from 'vue'
import {useChartOptions} from '@/composables/useChartOptions'
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card'
import { Line, PolarArea } from 'vue-chartjs'
import type { TooltipItem } from 'chart.js'
import BanCard from '@/components/BanCard.vue'

const datastore = useDataStore()
const {cartesianOptions, radialOptions, isDark} = useChartOptions()

const stackedBarData = computed(() => {
  const lib = datastore.listeningTimeByMonthLibrary
  const other = datastore.listeningTimeByMonthOther
  const labels = Object.keys(datastore.listeningTimeByMonth)
  if (labels.length === 0) return null
  return {
    labels,
    datasets: [
      {
        label: 'Library & playlists',
        backgroundColor: 'hsla(141, 72%, 42%, 0.35)',
        borderColor: 'hsla(141, 72%, 42%, 1)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        data: labels.map(l => lib[l] ?? 0),
      },
      {
        label: 'Algorithm & other',
        backgroundColor: 'hsla(280, 58%, 52%, 0.35)',
        borderColor: 'hsla(280, 58%, 52%, 1)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        data: labels.map(l => other[l] ?? 0),
      },
    ],
  }
})

const stackedBarOptions = computed(() => {
  const base = cartesianOptions.value
  return {
    ...base,
    scales: {
      x: { ...base.scales.x, stacked: true },
      y: { ...base.scales.y, stacked: true },
    },
  }
})

const hourLabelsAll = Array.from({ length: 24 }, (_, i) => {
  if (i === 0) return '12am'
  if (i < 12) return `${i}am`
  if (i === 12) return '12pm'
  return `${i - 12}pm`
})
const hourLabels = hourLabelsAll.map((label, i) => [0, 6, 12, 18].includes(i) ? label : '')
const hourColorsLibrary = Array.from({length: 24}, (_, i) => `hsla(141, 62%, ${30 + Math.round((i / 23) * 32)}%, 0.8)`)
const hourColorsOther = Array.from({length: 24}, (_, i) => `hsla(280, 55%, ${30 + Math.round((i / 23) * 32)}%, 0.8)`)

function makePolarHourData(hours: number[], colors: string[]) {
  if (hours.every(v => v === 0)) return null
  return { labels: hourLabels, datasets: [{ backgroundColor: colors, data: hours }] }
}

const hourlyPolarDataLibrary = computed(() => makePolarHourData(datastore.listeningTimeByHourLibrary, hourColorsLibrary))
const hourlyPolarDataOther = computed(() => makePolarHourData(datastore.listeningTimeByHourOther, hourColorsOther))

const hourlyPolarOptions = computed(() => {
  const base = radialOptions.value
  return {
    ...base,
    scales: {
      r: {
        ...base.scales.r,
        ticks: { display: false },
        pointLabels: { ...base.scales.r.pointLabels, display: true },
      },
    },
    plugins: {
      ...base.plugins,
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context: TooltipItem<'polarArea'>) =>
            `${hourLabelsAll[context.dataIndex]}: ${context.formattedValue} hours`,
        },
      },
    },
  }
})

const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const dayColorsLibrary = Array.from({length: 7}, (_, i) => `hsla(141, 62%, ${33 + Math.round((i / 6) * 30)}%, 0.8)`)
const dayColorsOther = Array.from({length: 7}, (_, i) => `hsla(280, 55%, ${33 + Math.round((i / 6) * 30)}%, 0.8)`)

function makePolarDayData(days: number[], colors: string[]) {
  if (days.every(v => v === 0)) return null
  return { labels: dayLabels, datasets: [{ backgroundColor: colors, data: days }] }
}

const dayPolarDataLibrary = computed(() => makePolarDayData(datastore.listeningTimeByDayLibrary, dayColorsLibrary))
const dayPolarDataOther = computed(() => makePolarDayData(datastore.listeningTimeByDayOther, dayColorsOther))

const dayPolarOptions = computed(() => {
  const base = radialOptions.value
  return {
    ...base,
    scales: {
      r: {
        ...base.scales.r,
        ticks: { display: false },
        pointLabels: { ...base.scales.r.pointLabels, display: true },
      },
    },
    plugins: {
      ...base.plugins,
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context: TooltipItem<'polarArea'>) =>
            `${context.label}: ${context.formattedValue} hours`,
        },
      },
    },
  }
})
</script>

<template>
  <div class="h-full overflow-y-auto p-4">
    <div class="grid grid-cols-3 gap-4 mb-6">
      <BanCard label="Library & playlists" :value="datastore.listeningTimeHoursLibrary.toLocaleString()" unit="hours" />
      <BanCard label="Algorithm & other" :value="datastore.listeningTimeHoursOther.toLocaleString()" unit="hours" />
      <BanCard label="Favourite time of day" :value="datastore.favouriteHour ?? '-'"/>
    </div>

    <div class="grid flex-1 grid-cols-1 gap-4 mb-4">
      <Card class="flex flex-col">
        <CardHeader><CardTitle>Listening over time</CardTitle></CardHeader>
        <CardContent class="relative flex-1">
          <div class="h-72 p-4 pt-0">
            <Line v-if="stackedBarData" :key="`stacked-bar-${isDark}`" :data="stackedBarData" :options="stackedBarOptions" />
            <p v-else class="text-muted-foreground text-center text-sm">No data available.</p>
          </div>
        </CardContent>
      </Card>
    </div>

    <div class="grid flex-1 grid-cols-2 gap-4 mb-4">
      <Card class="flex flex-col">
        <CardHeader><CardTitle>Time of day — library & playlists</CardTitle></CardHeader>
        <CardContent class="relative flex-1">
          <div class="h-72 p-4 pt-0">
            <PolarArea v-if="hourlyPolarDataLibrary" :key="`hourly-polar-lib-${isDark}`" :data="hourlyPolarDataLibrary" :options="hourlyPolarOptions" />
            <p v-else class="text-muted-foreground text-center text-sm">No data available.</p>
          </div>
        </CardContent>
      </Card>

      <Card class="flex flex-col">
        <CardHeader><CardTitle>Time of day — algorithm & other</CardTitle></CardHeader>
        <CardContent class="relative flex-1">
          <div class="h-72 p-4 pt-0">
            <PolarArea v-if="hourlyPolarDataOther" :key="`hourly-polar-other-${isDark}`" :data="hourlyPolarDataOther" :options="hourlyPolarOptions" />
            <p v-else class="text-muted-foreground text-center text-sm">No data available.</p>
          </div>
        </CardContent>
      </Card>
    </div>

    <div class="grid flex-1 grid-cols-2 gap-4">
      <Card class="flex flex-col">
        <CardHeader><CardTitle>Day of week — library & playlists</CardTitle></CardHeader>
        <CardContent class="relative flex-1">
          <div class="h-72 p-4 pt-0">
            <PolarArea v-if="dayPolarDataLibrary" :key="`day-polar-lib-${isDark}`" :data="dayPolarDataLibrary" :options="dayPolarOptions" />
            <p v-else class="text-muted-foreground text-center text-sm">No data available.</p>
          </div>
        </CardContent>
      </Card>

      <Card class="flex flex-col">
        <CardHeader><CardTitle>Day of week — algorithm & other</CardTitle></CardHeader>
        <CardContent class="relative flex-1">
          <div class="h-72 p-4 pt-0">
            <PolarArea v-if="dayPolarDataOther" :key="`day-polar-other-${isDark}`" :data="dayPolarDataOther" :options="dayPolarOptions" />
            <p v-else class="text-muted-foreground text-center text-sm">No data available.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>

</template>
