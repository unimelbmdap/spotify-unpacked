import { computed } from 'vue'
import { useDark } from '@vueuse/core'

export function useChartOptions() {
  const isDark = useDark({ storageKey: 'spotify-unpacked-colour-mode' })

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
      x: { ticks: { color: textColour }, grid: { color: gridColour } },
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
  return { cartesianOptions, radialOptions, simpleOptions, isDark }
}

