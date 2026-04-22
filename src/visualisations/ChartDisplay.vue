<script setup lang="ts">
import { computed, ref, onUnmounted } from 'vue'
import { useDark } from '@vueuse/core'
import { useVisualisationStore } from '@/stores/visualisation'
import { useDataStore } from '@/stores/data'
import {
  Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale, PointElement, LineElement, RadialLinearScale, Filler, ArcElement, TimeScale
} from 'chart.js'
import 'chartjs-adapter-date-fns'
import annotationPlugin from 'chartjs-plugin-annotation'
import { Bar, Line, PolarArea } from 'vue-chartjs'
import type { Chart } from 'chart.js'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'

const emojiMap: Record<string, string> = {
  'joy': '😊', 'love': '😍', 'surprise': '😲', 'sadness': '😢', 'anger': '😡', 'fear': '😨',
  'happy': '😄', 'energetic': '⚡', 'sad': '😔', 'calm': '😌'
}

// Chart.js Plugin: Scaling emojis in Polar Area slices
const radarEmojiPlugin = {
  id: 'radarEmoji',
  afterDraw: (chart: any) => {
    const { ctx } = chart
    const meta = chart.getDatasetMeta(0)
    if (!meta || !meta.data) return

    ctx.save()
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    meta.data.forEach((segment: any, i: number) => {
      const dataValue = chart.data.datasets[0].data[i]
      const label = chart.data.labels[i]
      const emoji = emojiMap[label] || ''
      if (!emoji || dataValue < 5) return 

      const { x, y, startAngle, endAngle, outerRadius } = segment
      const midAngle = (startAngle + endAngle) / 2
      const distance = outerRadius * 0.6
      const emojiX = x + Math.cos(midAngle) * distance
      const emojiY = y + Math.sin(midAngle) * distance

      const fontSize = Math.max(12, Math.min(32, (dataValue / 100) * 80))
      ctx.font = `${fontSize}px Arial`
      ctx.fillText(emoji, emojiX, emojiY)
    })
    ctx.restore()
  }
}

// Chart.js Plugin: Emojis for weekly peaks on Line charts
const weeklyPeakPlugin = {
  id: 'weeklyPeak',
  afterDraw: (chart: any) => {
    const { ctx } = chart
    const datasets = chart.data.datasets
    const labels = chart.data.labels
    if (!labels || labels.length < 7) return

    ctx.save()
    ctx.font = '16px Arial'
    ctx.textAlign = 'center'

    for (let i = 0; i < labels.length; i += 7) {
      const end = Math.min(i + 7, labels.length)
      let maxVal = -1
      let maxIdx = -1
      let maxLabel = ''

      datasets.forEach((ds: any) => {
        for (let j = i; j < end; j++) {
          if (ds.data[j] > maxVal) {
            maxVal = ds.data[j]
            maxIdx = j
            maxLabel = ds.label
          }
        }
      })

      if (maxVal > 20 && maxIdx !== -1) {
        const dsIdx = chart.data.datasets.findIndex((ds:any) => ds.label === maxLabel)
        const meta = chart.getDatasetMeta(dsIdx)
        if (meta && meta.data[maxIdx]) {
           const point = meta.data[maxIdx]
           const emoji = emojiMap[maxLabel] || ''
           if (emoji) {
              ctx.fillText(emoji, point.x, point.y - 12)
           }
        }
      }
    }
    ctx.restore()
  }
}

// Chart.js Plugin: Per-chart needle segment via Scale API
const needlePlugin = {
  id: 'needle',
  afterDraw: (chart: Chart) => {
    const labels = chart.data.labels as string[] | undefined
    if (!labels || !labels.length) return

    const index = activeIndex.value
    if (index < 0 || index >= labels.length) return

    const xScale = chart.scales.x
    if (!xScale) return

    // Use index for pixel lookup (most reliable for CategoryScale)
    const x = xScale.getPixelForValue(index)
    const { top, bottom } = chart.chartArea
    const ctx = chart.ctx

    ctx.save()
    ctx.strokeStyle = isDark.value ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.15)'
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.moveTo(x, top)
    ctx.lineTo(x, bottom)
    ctx.stroke()
    ctx.restore()
  }
}

ChartJS.register(
  Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale, PointElement, LineElement, RadialLinearScale, Filler, ArcElement, TimeScale, annotationPlugin
)

const visStore = useVisualisationStore()
const dataStore = useDataStore()
const isDark = useDark({ storageKey: 'spotify-unpacked-colour-mode' })

const masterChartRef = ref<any>(null)
const activeIndex = ref(0)
const labels500k = computed(() => dataStore.liveChartData.line500k?.labels ?? [])

const scrollContainer = ref<HTMLElement | null>(null)
let scrollInterval: number | null = null

const startStepping = (direction: number) => {
  if (scrollInterval) return
  step(direction)
  scrollInterval = window.setInterval(() => {
    step(direction)
  }, 50)
}

const stopStepping = () => {
  if (scrollInterval) {
    window.clearInterval(scrollInterval)
    scrollInterval = null
  }
}

const step = (direction: number) => {
  if (scrollContainer.value) {
    scrollContainer.value.scrollLeft += direction * 8 // 1 day = 8px
  }
}

onUnmounted(() => stopStepping())

const baseOptions = computed(() => {
  const textColour = isDark.value ? 'rgba(255,255,255,0.85)' : 'rgba(0,0,0,0.8)'
  const gridColour = isDark.value ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'
  return { textColour, gridColour }
})

const academicAnnotations = computed(() => {
  const swotvacColor = isDark.value ? 'rgba(255, 249, 196, 0.1)' : '#FFF9C4'
  const examColor = isDark.value ? 'rgba(255, 235, 238, 0.3)' : '#FFEBEE'

  const dates = dataStore.liveChartData.line500k?.labels as string[] | undefined
  if (!dates || dates.length === 0) return {}

  const activeYears = new Set<number>()
  dates.forEach(d => activeYears.add(new Date(d).getFullYear()))

  const annotations: any = {}
  let annId = 0
  activeYears.forEach(y => {
      const s1 = `${y}-05-25`, e1 = `${y}-06-30`
      const s2 = `${y}-10-25`, e2 = `${y}-11-30`
      const hasFirstSem = dates.some(d => d >= s1 && d <= e1)
      const hasSecondSem = dates.some(d => d >= s2 && d <= e2)

      if (hasFirstSem) {
        annotations[`box${annId++}`] = { type: 'box', xMin: `${y}-05-25`, xMax: `${y}-06-01`, backgroundColor: swotvacColor, borderWidth: 0, drawTime: 'beforeDatasetsDraw' }
        annotations[`box${annId++}`] = { type: 'box', xMin: `${y}-06-01`, xMax: `${y}-06-30`, backgroundColor: examColor, borderWidth: 0, drawTime: 'beforeDatasetsDraw' }
      }
      if (hasSecondSem) {
        annotations[`box${annId++}`] = { type: 'box', xMin: `${y}-10-25`, xMax: `${y}-11-01`, backgroundColor: swotvacColor, borderWidth: 0, drawTime: 'beforeDatasetsDraw' }
        annotations[`box${annId++}`] = { type: 'box', xMin: `${y}-11-01`, xMax: `${y}-11-30`, backgroundColor: examColor, borderWidth: 0, drawTime: 'beforeDatasetsDraw' }
      }
  })
  return annotations
})

const radialOptions500k = computed(() => {
  const { textColour, gridColour } = baseOptions.value
  return {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        startAngle: -30, // Mathematical center for 6-wedge JOY at Top (0°)
        min: 0,
        max: 100,
        ticks: { display: false },
        grid: { color: gridColour },
        angleLines: { color: gridColour },
        pointLabels: { 
          display: true,
          color: (ctx: any) => dataStore.baseTimeline.cMap[ctx.label] || textColour, 
          font: { size: 10, weight: 'bold' as const },
          padding: 20,
          centerPointLabels: true, // Align labels with slice centers per Chart.js 4
          callback: (label: string, index: number) => {
             const radarData = dataStore.radarChartData.radar500k.datasets[0].data
             const val = radarData[index] ?? 0
             return [label.toUpperCase(), Math.round(val) + '%']
          }
        },
      },
    },
    layout: { padding: 40 },
    plugins: { 
      legend: { display: false },
      radarEmoji: true,
      tooltip: { enabled: true }
    }
  }
})

const radialOptions278k = computed(() => {
  const { textColour, gridColour } = baseOptions.value
  return {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        startAngle: -45, // Mathematical center for 4-wedge HAPPY at Top (0°)
        min: 0,
        max: 100,
        ticks: { display: false },
        grid: { color: gridColour },
        angleLines: { color: gridColour },
        pointLabels: { 
          display: true,
          color: (ctx: any) => dataStore.baseTimeline.cMap[ctx.label] || textColour, 
          font: { size: 10, weight: 'bold' as const },
          padding: 20,
          centerPointLabels: true,
          callback: (label: string, index: number) => {
             const radarData = dataStore.radarChartData.radar278k.datasets[0].data
             const val = radarData[index] ?? 0
             return [label.toUpperCase(), Math.round(val) + '%']
          }
        },
      },
    },
    layout: { padding: 40 },
    plugins: { 
      legend: { display: false },
      radarEmoji: true,
      tooltip: { enabled: true }
    }
  }
})

const lineXAxis = computed(() => {
  const { textColour } = baseOptions.value
  return { 
    type: 'category' as const,
    offset: false,
    ticks: { 
      color: textColour,
      maxRotation: 45,
      minRotation: 45,
      autoSkip: true,
      autoSkipPadding: 50,
      align: 'center' as const
    }, 
    grid: { display: false } 
  }
})

const barXAxis = computed(() => {
  const { textColour } = baseOptions.value
  return { 
    type: 'category' as const,
    offset: true,
    ticks: { 
      color: textColour,
      maxRotation: 45,
      minRotation: 45,
      autoSkip: true,
      autoSkipPadding: 50,
      align: 'center' as const
    }, 
    grid: { display: false } 
  }
})

const timelineOptions = computed(() => {
  const { textColour, gridColour } = baseOptions.value
  return {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: lineXAxis.value,
      y: { 
        min: 0, 
        max: 100, 
        ticks: { color: textColour }, 
        grid: { color: gridColour },
        afterFit: (axis: any) => { axis.width = 40 }
      },
    },
    plugins: {
      legend: { display: false },
      weeklyPeak: true,
      needle: true,
      annotation: { annotations: academicAnnotations.value }
    },
    layout: { 
      padding: { top: 40, left: 0, right: 0 },
      autoPadding: false
    },
    interaction: { mode: 'index' as const, intersect: false },
    elements: { point: { radius: 0, hitRadius: 10 } }
  }
})

const tugOfWarOptions = computed(() => {
  const { textColour, gridColour } = baseOptions.value
  return {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { ...barXAxis.value, stacked: true },
      y: { 
        min: -100, 
        max: 100, 
        stacked: true,
        ticks: { color: textColour }, 
        grid: { color: gridColour },
        afterFit: (axis: any) => { axis.width = 40 }
      },
    },
    plugins: {
      legend: { display: false },
      needle: true,
      annotation: { annotations: academicAnnotations.value }
    },
    layout: { 
      padding: { top: 40, left: 0, right: 0 },
      autoPadding: false
    }
  }
})

const coverageOptions = computed(() => {
  const { textColour, gridColour } = baseOptions.value
  return {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { ...barXAxis.value, stacked: true },
      y: { 
        min: 0, 
        stacked: true, 
        ticks: { color: textColour }, 
        grid: { color: gridColour },
        afterFit: (axis: any) => { axis.width = 40 }
      },
    },
    plugins: {
      legend: { display: false },
      needle: true,
      annotation: { annotations: academicAnnotations.value }
    },
    layout: { 
      padding: { top: 40, left: 0, right: 0 },
      autoPadding: false
    }
  }
})

const timelineWidth = computed(() => {
  const dates = dataStore.liveChartData.line500k?.labels?.length || 0
  return Math.max(800, dates * 8) 
})

const handleScroll = (e: Event) => {
  const target = e.target as HTMLElement
  const scrollRange = target.scrollWidth - target.clientWidth
  const scrollLeft = target.scrollLeft

  const n = labels500k.value.length
  if (!n || scrollRange <= 0) return

  const fraction = Math.min(1, Math.max(0, scrollLeft / scrollRange))
  activeIndex.value = Math.round(fraction * (n - 1))
  visStore.scrollWindow = [activeIndex.value, activeIndex.value + 1]
}

const needleLeft = computed(() => {
  const vueComp = masterChartRef.value
  const chart = vueComp?.chart
  const labels = labels500k.value

  if (!chart || !labels.length) return '50%'

  const xScale = chart.scales.x
  const label = labels[activeIndex.value]
  const x = xScale.getPixelForValue(label, activeIndex.value)

  // Convert canvas x -> container CSS left
  const rect = chart.canvas.getBoundingClientRect()
  const containerRect = scrollContainer.value?.getBoundingClientRect()
  if (!containerRect) return '50%'

  // x is relative to canvas left. Rect.left is screen-relative. 
  // containerRect.left is screen-relative.
  const cssX = x + (rect.left - containerRect.left)
  return `${cssX}px`
})
</script>

<template>
  <div v-if="dataStore.hasData && dataStore.liveChartData.line500k?.labels?.length" class="flex flex-col h-full overflow-y-auto bg-background p-6 gap-8">
     
     <div class="grid grid-cols-1 md:grid-cols-2 gap-8 shrink-0">
        <div class="flex flex-col items-center justify-center p-6 border rounded-xl shadow-sm bg-card aspect-square max-h-[400px]">
           <h3 class="font-bold text-center mb-2 tracking-widest text-muted-foreground text-xs uppercase">LYRICS (%) - <span class="text-primary">{{ dataStore.radarChartData.radarDate }}</span></h3>
           <div class="flex-1 w-full relative">
              <PolarArea :data="dataStore.radarChartData.radar500k" :options="radialOptions500k" :plugins="[radarEmojiPlugin]" />
           </div>
        </div>
        <div class="flex flex-col items-center justify-center p-6 border rounded-xl shadow-sm bg-card aspect-square max-h-[400px]">
           <h3 class="font-bold text-center mb-2 tracking-widest text-muted-foreground text-xs uppercase">AUDIO (%) - <span class="text-primary">{{ dataStore.radarChartData.radarDate }}</span></h3>
           <div class="flex-1 w-full relative">
              <PolarArea :data="dataStore.radarChartData.radar278k" :options="radialOptions278k" :plugins="[radarEmojiPlugin]" />
           </div>
        </div>
     </div>

     <div class="w-full flex flex-col gap-2 relative text-foreground">
          <div class="flex items-baseline gap-3">
            <h3 class="font-bold text-lg">Temporal Trends & Coverage</h3>
            <span class="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold opacity-70">
              Measure: Temporal Occupancy
            </span>
          </div>
          <p class="text-xs text-muted-foreground max-w-2xl leading-relaxed mb-2">
            Percentages show how much listening time was occupied by each state.
            Totals may fall below 100% because silence, niche/unmapped listening, and 7-day smoothing are preserved rather than normalized away.
          </p>
         
          <div class="relative w-full group">
            <div 
              class="absolute inset-y-0 z-30 pointer-events-none flex flex-col items-center"
              :style="{ left: needleLeft }"
            >
                <div class="w-[1.5px] h-full bg-primary/20 relative flex flex-col items-center">
                    <!-- Top Arrow head -->
                    <div class="absolute -top-[1px] w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[8px] border-t-primary/70"></div>
                    
                    <!-- Bottom Arrow head -->
                    <div class="absolute bottom-[16px] w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-b-[8px] border-b-primary/70"></div>
                </div>
            </div>

            <div class="absolute left-0 inset-y-0 z-40 flex items-center p-2">
                <Button variant="secondary" size="icon" class="opacity-0 group-hover:opacity-100 transition-opacity shadow-lg rounded-full" @mousedown="startStepping(-1)" @mouseup="stopStepping" @mouseleave="stopStepping">
                    <ChevronLeft class="size-4" />
                </Button>
            </div>
            <div class="absolute right-0 inset-y-0 z-40 flex items-center p-2">
                <Button variant="secondary" size="icon" class="opacity-0 group-hover:opacity-100 transition-opacity shadow-lg rounded-full" @mousedown="startStepping(1)" @mouseup="stopStepping" @mouseleave="stopStepping">
                    <ChevronRight class="size-4" />
                </Button>
            </div>

            <div ref="scrollContainer" class="w-full overflow-x-auto border rounded-xl shadow-sm bg-card custom-scrollbar" @scroll="handleScroll">
                <div class="flex items-start">
                    <div class="w-1/2 shrink-0 h-1"></div>
                    <div :style="`width: ${timelineWidth}px;`" class="flex flex-col shrink-0 divide-y divide-border relative">
                        
                        <div class="h-[300px] w-full py-4 shrink-0 relative flex flex-col">
                            <div class="sticky left-6 z-20 bg-background/90 backdrop-blur-sm px-3 py-1.5 rounded-lg border shadow-sm w-fit pointer-events-none mb-1 flex items-center gap-4">
                                <span class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Emotion (500k)</span>
                                <span class="text-xs font-mono text-primary font-bold">{{ dataStore.radarChartData.radarDate }}</span>
                            </div>
                            <div class="absolute inset-0 pt-12 pb-16">
                               <Line ref="masterChartRef" :data="dataStore.liveChartData.line500k" :options="timelineOptions" :plugins="[weeklyPeakPlugin, needlePlugin]" />
                            </div>
                        </div>
                        
                        <div class="h-[300px] w-full py-4 shrink-0 relative flex flex-col">
                            <div class="sticky left-6 z-20 bg-background/90 backdrop-blur-sm px-3 py-1.5 rounded-lg border shadow-sm w-fit pointer-events-none mb-1 flex items-center gap-4">
                                <span class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Emotion (278k)</span>
                                <span class="text-xs font-mono text-primary font-bold">{{ dataStore.radarChartData.radarDate }}</span>
                            </div>
                            <div class="absolute inset-0 pt-12 pb-16">
                               <Line :data="dataStore.liveChartData.line278k" :options="timelineOptions" :plugins="[weeklyPeakPlugin, needlePlugin]" />
                            </div>
                        </div>
                        
                        <div class="h-[300px] w-full py-4 shrink-0 relative flex flex-col">
                            <div class="sticky left-6 z-20 bg-background/90 backdrop-blur-sm px-3 py-1.5 rounded-lg border shadow-sm w-fit pointer-events-none mb-1 flex items-center gap-4">
                                <span class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Sentiment Deviation</span>
                                <span class="text-xs font-mono text-primary font-bold">{{ dataStore.radarChartData.radarDate }}</span>
                                <div class="flex items-center gap-3 border-l pl-4">
                                   <div class="flex items-center gap-1.5">
                                     <div class="size-2 rounded-full bg-[#32CD32]"></div>
                                     <span class="text-[10px] opacity-80">Positive</span>
                                   </div>
                                   <div class="flex items-center gap-1.5">
                                     <div class="size-2 rounded-full bg-[#DC143C]"></div>
                                     <span class="text-[10px] opacity-80">Negative</span>
                                   </div>
                                </div>
                            </div>
                            <div class="absolute inset-0 pt-12 pb-16">
                               <Bar :data="dataStore.liveChartData.tugOfWar" :options="tugOfWarOptions" :plugins="[needlePlugin]" />
                            </div>
                        </div>
                        
                        <div class="h-[300px] w-full py-4 shrink-0 relative flex flex-col">
                            <div class="sticky left-6 z-20 bg-background/90 backdrop-blur-sm px-3 py-1.5 rounded-lg border shadow-sm w-fit pointer-events-none mb-1 flex items-center gap-4">
                                <span class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Match Coverage</span>
                                <span class="text-xs font-mono text-primary font-bold">{{ dataStore.radarChartData.radarDate }}</span>
                                <div class="flex items-center gap-3 border-l pl-4">
                                   <div class="flex items-center gap-1.5">
                                     <div class="size-2 rounded bg-[#4682B4]"></div>
                                     <span class="text-[10px] opacity-80">Observed Match</span>
                                   </div>
                                   <div class="flex items-center gap-1.5">
                                     <div class="size-2 rounded bg-[#F0B35A]"></div>
                                     <span class="text-[10px] opacity-80">Imputed Mood</span>
                                   </div>
                                   <div class="flex items-center gap-1.5">
                                     <div class="size-2 rounded bg-[#D3D3D3]"></div>
                                     <span class="text-[10px] opacity-80">Niche Selection</span>
                                   </div>
                                </div>
                            </div>
                            <div class="absolute inset-0 pt-12 pb-16">
                               <Bar :data="dataStore.liveChartData.matchCoverage" :options="coverageOptions" :plugins="[needlePlugin]" />
                            </div>
                        </div>
                    </div>
                    <div class="w-1/2 shrink-0 h-1"></div>
                </div>
            </div>
         </div>
     </div>
  </div>
  
  <div v-else class="flex items-center justify-center h-full p-12">
    <div class="max-w-md text-center space-y-4">
      <div v-if="dataStore.fileCount > 0" class="space-y-2">
        <p class="text-foreground font-semibold">Data loaded partially</p>
        <p class="text-muted-foreground text-sm"> Streaming History detected. Upload <code class="bg-muted px-1 rounded">Streaming_History_Audio_*.json</code>. </p>
      </div>
      <div v-else class="animate-pulse">
        <p class="text-muted-foreground text-sm"> Awaiting data mappings... </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { height: 12px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; border-radius: 8px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(150, 150, 150, 0.3); border-radius: 8px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(150, 150, 150, 0.5); }
</style>
