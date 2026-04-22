import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useVisualisationStore = defineStore('visualisation', () => {
  const selectedChart = ref('temporal')
  const dateRange = ref({ start: '', end: '' })
  const year = ref('All')
  const sourceOrigin = ref('All') // 'All', 'Library', 'Playlist'
  const aiGhostToggle = ref(false)
  const allowImputation = ref(true)
  const useRollingAverage = ref(true)
  const scrollWindow = ref<[number, number] | null>(null) // Array slice indices

  return { selectedChart, dateRange, year, sourceOrigin, aiGhostToggle, allowImputation, useRollingAverage, scrollWindow }
})
