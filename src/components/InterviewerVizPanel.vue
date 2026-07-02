<script setup lang="ts">
import { useDataStore } from '@/stores/data'
import { computed } from 'vue'
import {useChartOptions} from '@/composables/useChartOptions'
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card'
import { Line, PolarArea, Radar } from 'vue-chartjs'
import type { TooltipItem } from 'chart.js'
import BanCard from '@/components/BanCard.vue'
import { archetypeConfig, bandScore } from '@/lib/archetypeConfig'
import { formatMinutes, formatDateWithDayofWeek } from '@/lib/utils'

const datastore = useDataStore()
const {cartesianOptions, radialOptions, isDark} = useChartOptions()

const stackedAreaData = computed(() => {
  const lib = datastore.listeningTimeByDateLibrary
  const other = datastore.listeningTimeByDateOther
  const labels = Object.keys(datastore.listeningTimeByDate)
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
        backgroundColor: 'hsla(28, 58%, 52%, 0.35)',
        borderColor: 'hsla(28, 58%, 52%, 1)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        data: labels.map(l => other[l] ?? 0),
      },
    ],
  }
})

const stackedAreaOptions = computed(() => {
  const base = cartesianOptions.value
  const lib = datastore.listeningTimeByDateLibrary
  const other = datastore.listeningTimeByDateOther
  return {
    ...base,
    scales: {
      x: { ...base.scales.x, stacked: true },
      y: { ...base.scales.y, stacked: true },
    },
    interaction: { mode: 'index' as const, intersect: false },
    plugins: {
      ...base.plugins,
      tooltip: {
        callbacks: {
          title: (context: TooltipItem<'line'>[]) => {
            const date = new Date(context[0].label ?? '')
            return formatDateWithDayofWeek(date)
          },
          label: (context: TooltipItem<'line'>) => {
            const date = context.label
            const value = context.parsed.y ?? 0
            const dayTotal = (lib[date] ?? 0) + (other[date] ?? 0)
            const percent = dayTotal > 0 ? Math.round((value / dayTotal) * 100) : 0
            return `${context.dataset.label}: ${formatMinutes(value)} (${percent}%)`
          },
        },
      },
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
const hourColorsOther = Array.from({length: 24}, (_, i) => `hsla(28, 55%, ${30 + Math.round((i / 23) * 32)}%, 0.8)`)

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

const archetypeRadarData = computed(() => {
  if (datastore.entries.length === 0) return null
  return {
    labels: [archetypeConfig.receptiveness.shortLabel, archetypeConfig.responsiveness.shortLabel, archetypeConfig.deliberate.shortLabel],
    datasets: [
      {
        label: 'Listening archetype',
        data: [
          Math.round(datastore.receptiveness * 100),
          Math.round(datastore.responsiveness * 100),
          Math.round(datastore.deliberate * 100),
        ],
        backgroundColor: 'hsla(205, 70%, 50%, 0.25)',
        borderColor: 'hsla(205, 70%, 50%, 1)',
        pointBackgroundColor: 'hsla(205, 70%, 50%, 1)',
      },
    ],
  }
})

const archetypeRadarOptions = computed(() => {
  const base = radialOptions.value
  return {
    ...base,
    scales: {
      r: {
        ...base.scales.r,
        min: 0,
        max: 100,
        ticks: {
          ...base.scales.r.ticks,
          stepSize: 25,
          callback: (value: string | number) => {
            if (value === 25) return 'Low'
            if (value === 100) return 'High'
            return ''
          },
        },
      },
    },
    plugins: {
      ...base.plugins,
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context: TooltipItem<'radar'>) => `${context.label}: ${context.formattedValue}%`,
        },
      },
    },
  }
})

function joinWithAnd(parts: string[]) {
  if (parts.length <= 1) return parts.join('')
  if (parts.length === 2) return parts.join(' and ')
  return `${parts.slice(0, -1).join(', ')}, and ${parts[parts.length - 1]}`
}

function showLevelAsText(score: number) {
  if (score < 0.33) return 'Low'
  if (score < 0.66) return 'Medium'
  return 'High'
}

const archetypeCaptions = computed(() => {
  const shufflePct = Math.round(datastore.shuffleRate * 100)
  const skipPct = Math.round(datastore.skipRate * 100)
  const reasonPct = Math.round(datastore.responsiveReasonRate * 100)

  const responsiveParts = []
  if (bandScore(datastore.shuffleRate, archetypeConfig.responsiveness.shuffle) > 0) responsiveParts.push(`shuffle use (${shufflePct}% of plays)`)
  if (bandScore(datastore.skipRate, archetypeConfig.responsiveness.skip) > 0) responsiveParts.push(`skips (${skipPct}% of plays)`)
  if (bandScore(datastore.responsiveReasonRate, archetypeConfig.responsiveness.reason) > 0) responsiveParts.push(`back/popup-driven track changes (${reasonPct}% of plays)`)

  const deliberateParts = []
  if (bandScore(datastore.shuffleRate, archetypeConfig.deliberate.shuffle) > 0) deliberateParts.push(`low shuffle use (${shufflePct}% of plays)`)
  if (bandScore(datastore.skipRate, archetypeConfig.deliberate.skip) > 0) deliberateParts.push(`skips above a baseline rate (${skipPct}% of plays)`)
  if (bandScore(datastore.responsiveReasonRate, archetypeConfig.deliberate.reason) > 0) deliberateParts.push(`few back/popup-driven track changes (${reasonPct}% of plays)`)
  if (bandScore(datastore.algorithmicRate, archetypeConfig.deliberate.algorithmic) > 0) deliberateParts.push(`low algorithm-driven listening (${datastore.listeningTimePercentOther}% of listening time)`)

  return [
    {
      label: archetypeConfig.receptiveness.label,
      displayValue: showLevelAsText(datastore.receptiveness),
      description: `This is based on your ${datastore.listeningTimePercentOther}% listening time coming from outside your library and playlists (algorithm & other). ${archetypeConfig.receptiveness.description}`,
    },
    {
      label: archetypeConfig.responsiveness.label,
      displayValue: showLevelAsText(datastore.responsiveness),
      description: responsiveParts.length
        ? `Based on ${joinWithAnd(responsiveParts)}. ${archetypeConfig.responsiveness.description}`
        : archetypeConfig.responsiveness.description,
    },
    {
      label: archetypeConfig.deliberate.label,
      displayValue: showLevelAsText(datastore.deliberate),
      description: deliberateParts.length
        ? `Based on ${joinWithAnd(deliberateParts)}. ${archetypeConfig.deliberate.description}`
        : archetypeConfig.deliberate.description,
    },
  ]
})

const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const dayColorsLibrary = Array.from({length: 7}, (_, i) => `hsla(141, 62%, ${33 + Math.round((i / 6) * 30)}%, 0.8)`)
const dayColorsOther = Array.from({length: 7}, (_, i) => `hsla(28, 55%, ${33 + Math.round((i / 6) * 30)}%, 0.8)`)

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
    <div class="grid grid-cols-3 gap-4 mb-6" v-if="datastore.hasLibraryData">
      <BanCard label="Library & playlists" :value="datastore.listeningTimeHoursLibrary.toLocaleString()" unit="hours" :caption="`${datastore.listeningTimePercentLibrary}% of listening time since July 2025`" />
      <BanCard label="Algorithm & other" :value="datastore.listeningTimeHoursOther.toLocaleString()" unit="hours" :caption="`${datastore.listeningTimePercentOther}% of listening time since July 2025`" />
      <BanCard label="Favourite time of day" :value="datastore.favouriteHour ?? '-'"/>
    </div>
    <div class="grid grid-cols-2 gap-4 mb-6" v-else>
      <BanCard label="Total listening time" :value="datastore.listeningTimeHours.toLocaleString()" unit="hours" caption="Since July 2025" />
      <BanCard label="Favourite time of day" :value="datastore.favouriteHour ?? '-'"/>
    </div>

    <template v-if="datastore.hasLibraryData">
      <div class="grid flex-1 grid-cols-1 gap-4 mb-4">
        <Card class="flex flex-col">
          <CardHeader><CardTitle>Listening over time</CardTitle></CardHeader>
          <CardContent class="relative flex-1">
            <div class="h-72 p-4 pt-0">
              <Line v-if="stackedAreaData" :key="`stacked-area-${isDark}`" :data="stackedAreaData" :options="stackedAreaOptions" />
              <p v-else class="text-muted-foreground text-center text-sm">No data available.</p>
            </div>
          </CardContent>
        </Card>
      </div>

    <div class="grid flex-1 grid-cols-1 gap-4 mb-6" v-if="datastore.hasLibraryData">
      <Card class="flex flex-col">
        <CardHeader><CardTitle>Listening archetype</CardTitle></CardHeader>
        <CardContent class="relative flex-1">
          <div class="h-72 p-4 pt-0">
            <Radar v-if="archetypeRadarData" :key="`archetype-radar-${isDark}`" :data="archetypeRadarData" :options="archetypeRadarOptions" />
            <p v-else class="text-muted-foreground text-center text-sm">No data available.</p>
          </div>
          <ul class="flex flex-col gap-2 px-4 pb-4 text-sm">
            <li v-for="archetype in archetypeCaptions" :key="archetype.label">
              <span class="font-bold">{{ archetype.label }} is at {{ archetype.displayValue }} - </span>
              <span class="text-muted-foreground"> {{ archetype.description }} </span>
            </li>
          </ul>
        </CardContent>
      </Card>
      </div>
    <div class="grid flex-1 grid-cols-1 gap-4 mb-6" v-else>
      <Card class="flex flex-col">
        <CardHeader><CardTitle>Listening archetype cannot be calculated without library and playlist files</CardTitle></CardHeader>
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
    </template>
    <template v-else>
      <p class="text-muted-foreground text-center text-sm mt-8">No library or playlist data was donated.</p>
    </template>
  </div>

</template>
