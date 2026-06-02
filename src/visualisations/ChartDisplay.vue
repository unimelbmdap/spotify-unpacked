<script setup lang="ts">
import { computed } from 'vue'
import { useVisualisationStore } from '@/stores/visualisation'
import { useDataStore } from '@/stores/data'
import {useChartOptions} from '@/composables/useChartOptions'
import { Bar, Bubble, Doughnut, Line, Pie, PolarArea, Radar, Scatter } from 'vue-chartjs'

const visStore = useVisualisationStore()
const dataStore = useDataStore()
const { cartesianOptions, radialOptions, simpleOptions, isDark } = useChartOptions()

// Each vue-chartjs component expects its specific ChartData variant (e.g. ChartData<"bar">),
// but data is selected dynamically at runtime. The v-if guards in the template ensure correctness.
const currentData = computed(() => dataStore.getChartData(visStore.selectedChart) as any)


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
