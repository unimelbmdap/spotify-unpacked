<script setup lang="ts">
import { useDataStore } from '@/stores/data'
import { computed, ref, watch } from 'vue'
import {useChartOptions} from '@/composables/useChartOptions'
import {Card, CardContent, CardHeader, CardTitle} from '@/components/ui/card'
import { Slider } from '@/components/ui/slider'
import { Button } from '@/components/ui/button'
import { Line, PolarArea } from 'vue-chartjs'
import type { TooltipItem } from 'chart.js'
import BanCard from '@/components/BanCard.vue'
import { topTrack, topArtist } from '@/lib/monthlyStats'
import { formatMinutes, formatDateWithDayofWeek  } from '@/lib/utils'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { WINDOW_LABEL_CAPITALISED } from '@/lib/dateWindow'

const datastore = useDataStore()
const {cartesianOptions, radialOptions, isDark} = useChartOptions()

const selectedMonthIndex = ref(0)
watch(() => datastore.monthLabels.length, (length) => {
  if (length > 0) selectedMonthIndex.value = length - 1
}, { immediate: true })

const selectedMonthLabel = computed(() => datastore.monthLabels[selectedMonthIndex.value] ?? null)

function stepMonth(delta: number) {
  const max = datastore.monthLabels.length - 1
  selectedMonthIndex.value = Math.min(max, Math.max(0, selectedMonthIndex.value + delta))
}


const stackedAreaData = computed(() => {
  const daily = datastore.listeningTimeByDate
  const labels = Object.keys(daily)
  if (labels.length === 0) return null
  const selectedLabel = selectedMonthLabel.value
  const dateMonthLabels = datastore.dateMonthLabels
  return {
    labels,
    datasets: [
      {
        label: 'All listening',
        backgroundColor: 'hsla(141, 72%, 42%, 0.35)',
        borderColor: 'hsla(141, 72%, 42%, 1)',
        fill: true,
        tension: 0.4,
        pointRadius: labels.map((_, i) => dateMonthLabels[i] === selectedLabel ? 3 : 0),
        pointHoverRadius: 5,
        pointBackgroundColor: 'hsla(141, 72%, 42%, 1)',
        pointBorderColor: 'white',
        pointBorderWidth: 2,
        data: labels.map(l => daily[l] ?? 0),
      },
    ],
  }
})

const stackedAreaOptions = computed(() => {
  const base = cartesianOptions.value
  return {
    ...base,
    interaction: { mode: 'index' as const, intersect: false },
    plugins: {
      ...base.plugins,
      tooltip: {
        callbacks: {
          title: (context: TooltipItem<'line'>[]) => {
            const date = new Date(context[0]?.label ?? '')
            return formatDateWithDayofWeek(date)
          },
          label: (context: TooltipItem<'line'>) => `Listening time: ${formatMinutes(context.parsed.y ?? 0)}`,
        },
      },
    },
  }
})

const monthEntries = computed(() => selectedMonthLabel.value ? datastore.entriesForMonth(selectedMonthLabel.value) : [])
const topTrackForMonth = computed(() => topTrack(monthEntries.value))
const topArtistForMonth = computed(() => topArtist(monthEntries.value))
const listeningHoursForSelectedMonth = computed(() => selectedMonthLabel.value ? datastore.listeningHoursForMonth(selectedMonthLabel.value) : 0)
const songsPlayedForSelectedMonth = computed(() => monthEntries.value.length)
const favouriteHourForSelectedMonth = computed(() => selectedMonthLabel.value ? datastore.favouriteHourForMonth(selectedMonthLabel.value) : null)

const hourLabelsAll = Array.from({ length: 24 }, (_, i) => {
  if (i === 0) return '12am'
  if (i < 12) return `${i}am`
  if (i === 12) return '12pm'
  return `${i - 12}pm`
})
const hourLabels = hourLabelsAll.map((label, i) => [0, 6, 12, 18].includes(i) ? label : '')
const hourColorsLibrary = Array.from({length: 24}, (_, i) => `hsla(141, 62%, ${30 + Math.round((i / 23) * 32)}%, 0.8)`)

function makePolarHourData(hours: number[], colors: string[]) {
  if (hours.every(v => v === 0)) return null
  return { labels: hourLabels, datasets: [{ backgroundColor: colors, data: hours }] }
}

const monthlyPolarData = computed(() => {
  if (!selectedMonthLabel.value) return null
  return makePolarHourData(datastore.hourlyForMonth(selectedMonthLabel.value), hourColorsLibrary)
})

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
</script>

<template>
  <div class="h-full overflow-y-auto p-4">
    <div class="grid grid-cols-3 gap-4 mb-6" v-if="datastore.hasLibraryData">
      <BanCard label="Listening time" :value="listeningHoursForSelectedMonth.toLocaleString()" unit="hours" :caption="`In ${selectedMonthLabel}`" />
      <BanCard label="Songs played" :value="songsPlayedForSelectedMonth.toLocaleString()" :caption="`In ${selectedMonthLabel}`" />
      <BanCard label="Most popular time of day" :value="favouriteHourForSelectedMonth ?? '-'" :caption="`In ${selectedMonthLabel}`" />
    </div>
    <div class="grid grid-cols-2 gap-4 mb-6" v-else>
      <BanCard label="Total listening time" :value="datastore.listeningTimeHours.toLocaleString()" unit="hours" :caption="WINDOW_LABEL_CAPITALISED" />
      <BanCard label="Favourite time of day" :value="datastore.favouriteHour ?? '-'"/>
    </div>

    <template v-if="datastore.hasLibraryData">
      <div class="grid flex-1 grid-cols-1 gap-4 mb-4">
        <Card class="flex flex-col">
          <CardHeader><CardTitle>Listening over time — {{ selectedMonthLabel }}</CardTitle></CardHeader>
          <CardContent class="relative flex-1">
            <div class="h-72 p-4 pt-0">
              <Line v-if="stackedAreaData" :key="`stacked-area-${isDark}`" :data="stackedAreaData" :options="stackedAreaOptions" />
              <p v-else class="text-muted-foreground text-center text-sm">No data available.</p>
            </div>
            <div v-if="datastore.monthLabels.length > 0" class="flex items-center gap-3 px-4 pb-4">
              <Button variant="outline" size="icon" :disabled="selectedMonthIndex === 0" @click="stepMonth(-1)">
                <ChevronLeft class="size-4" />
              </Button>
              <Slider
                class="flex-1 **:data-[slot=slider-range]:bg-muted"
                :model-value="[selectedMonthIndex]"
                @update:model-value="(v) => selectedMonthIndex = v?.[0] ?? selectedMonthIndex"
                :min="0"
                :max="datastore.monthLabels.length-1"
                :step="1"
              />
              <Button variant="outline" size="icon" :disabled="selectedMonthIndex === datastore.monthLabels.length - 1" @click="stepMonth(1)">
                <ChevronRight class="size-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <div class="grid flex-1 grid-cols-2 gap-4 mb-4">
        <BanCard label="Most played song" :value="topTrackForMonth?.name ?? '-'" :caption="topTrackForMonth ? `${topTrackForMonth.playCount} plays in ${selectedMonthLabel}` : `No plays in ${selectedMonthLabel}`" />
        <BanCard label="Most played artist" :value="topArtistForMonth?.name ?? '-'" :caption="topArtistForMonth ? `${topArtistForMonth.playCount} plays in ${selectedMonthLabel}` : `No plays in ${selectedMonthLabel}`" />
      </div>

      <div class="grid flex-1 grid-cols-1 gap-4 mb-4">
        <Card class="flex flex-col">
          <CardHeader><CardTitle>Time of day — {{ selectedMonthLabel }}</CardTitle></CardHeader>
          <CardContent class="relative flex-1">
            <div class="h-72 p-4 pt-0">
              <PolarArea v-if="monthlyPolarData" :key="`monthly-polar-${isDark}-${selectedMonthLabel}`" :data="monthlyPolarData" :options="hourlyPolarOptions" />
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
