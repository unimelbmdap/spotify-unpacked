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

const lineData = computed(() => datastore.listeningTimeByMonth ? {
  labels: Object.keys(datastore.listeningTimeByMonth),
  datasets: [
    {
      label: 'Minutes played',
      borderColor: '#6366f1',
      backgroundColor: 'rgba(99,102,241,0.1)',
      fill: true,
      tension: 0.3,
      data: Object.values(datastore.listeningTimeByMonth),
    },
  ],
} : null)

const lineDataHours = computed(() => datastore.listeningTimeByMonth ? {
  labels: Object.keys(datastore.listeningTimeByMonth),
  datasets: [
    {
      label: 'Hours played',
      borderColor: '#6366f1',
      backgroundColor: 'rgba(99,102,241,0.1)',
      fill: true,
      tension: 0.3,
      data: Object.values(datastore.listeningTimeByMonth).map(m => Math.round((m / 60) * 10) / 10),
    },
  ],
} : null)

const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const dayColors = dayLabels.map((_, i) => `hsla(${Math.round((i / 7) * 360)}, 65%, 58%, 0.75)`)

const dayPolarData = computed(() => {
  const days = datastore.listeningTimeByDay
  if (days.every(v => v === 0)) return null
  return {
    labels: dayLabels,
    datasets: [{ backgroundColor: dayColors, data: days }],
  }
})

const dayPolarOptions = computed(() => {
  const base = radialOptions.value
  return {
    ...base,
    scales: {
      r: {
        ...base.scales?.r,
        ticks: { display: false },
        pointLabels: { ...base.scales?.r?.pointLabels, display: true },
      },
    },
    plugins: {
      ...base.plugins,
      legend: { display: false },
      tooltip: {
        callbacks:{label: (context) => `${context.label}: ${context.formattedValue} hours`,
        },
      }
    },
  }
})

const hourLabelsAll = Array.from({ length: 24 }, (_, i) => {
  if (i === 0) return '12am'
  if (i < 12) return `${i}am`
  if (i === 12) return '12pm'
  return `${i - 12}pm`
})

const hourLabels = hourLabelsAll.map((label, i) =>
  [0, 6, 12, 18].includes(i) ? label : ''
)
const hourColors = hourLabels.map((_, i) => `hsla(${Math.round((i / 24) * 360)}, 65%, 58%, 0.75)`)

const hourlyPolarData = computed(() => {
  const hours = datastore.listeningTimeByHour
  if (hours.every(v => v === 0)) return null
  return {
    labels: hourLabels,
    datasets: [{ backgroundColor: hourColors, data: hours }],
  }
})

const hourlyPolarOptions = computed(() => {
  const base = radialOptions.value
  return {
    ...base,
    scales: {
      r: {
        ...base.scales?.r,
        ticks: { display: false },
        pointLabels: { ...base.scales?.r?.pointLabels, display: true },
      },
    },
    plugins: {
      ...base.plugins,
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context: TooltipItem<'polarArea'>) => `${hourLabelsAll[context.dataIndex]}: ${context.formattedValue} hours`,
        },
      },
    },
  }
})
</script>

<template>
  <div>
    <div class="grid grid-cols-3 gap-4 mb-6">
      <BanCard label="Listening time in 2025" :value="datastore.listeningTimeHours.toLocaleString()" unit="hours" />
      <BanCard label="Unique songs" :value="datastore.uniqueTrackCount.toLocaleString()" />
      <BanCard label="Favourite time of day" :value="datastore.favouriteHour ?? '-'"/>
    </div>

    <div class="grid flex-1 grid-cols-2 gap-4">
      <Card class="flex flex-col">
    <CardHeader><CardTitle>Listening by time of day</CardTitle></CardHeader>
    <CardContent class="relative flex-1">
      <div class="h-72 p-4 pt-0">
        <PolarArea v-if="hourlyPolarData" :key="`hourly-polar-${isDark}`" :data="hourlyPolarData" :options="hourlyPolarOptions" />
        <p v-else class="text-muted-foreground text-center text-sm">No data available.</p>
      </div>
    </CardContent>
  </Card>

  <Card class="flex flex-col">
    <CardHeader><CardTitle>Listening by day of week</CardTitle></CardHeader>
    <CardContent class="relative flex-1">
      <div class="h-72 p-4 pt-0">
        <PolarArea v-if="dayPolarData" :key="`day-polar-${isDark}`" :data="dayPolarData" :options="dayPolarOptions" />
        <p v-else class="text-muted-foreground text-center text-sm">No data available.</p>
      </div>
    </CardContent>
  </Card>
</div>

    <div class="grid flex-1 grid-cols-2 gap-4">
      <Card class="flex flex-col">
    <CardHeader><CardTitle>Listening over time</CardTitle></CardHeader>
    <CardContent class="relative flex-1">
      <div class="h-72 p-4 pt-0">
        <Line v-if="lineData" :key="`line-${isDark}`" :data="lineData" :options="cartesianOptions" />
        <p v-else class="text-muted-foreground text-center text-sm">No data available.</p>
      </div>
    </CardContent>
  </Card>

  <Card class="flex flex-col">
    <CardHeader><CardTitle>Listening over time (hours)</CardTitle></CardHeader>
    <CardContent class="relative flex-1">
      <div class="h-72 p-4 pt-0">
        <Line v-if="lineDataHours" :key="`line-hours-${isDark}`" :data="lineDataHours" :options="cartesianOptions" />
        <p v-else class="text-muted-foreground text-center text-sm">No data available.</p>
      </div>
    </CardContent>
  </Card>
</div>
</div>
</template>
