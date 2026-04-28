<script setup lang="ts">
import { computed } from 'vue'
import { useDataStore } from '@/stores/data'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip } from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip)

const dataStore = useDataStore()

const chartData = computed(() => {
  const dates = dataStore.baseTimeline.dates
  const pos = dataStore.baseTimeline.tugPos
  const neg = dataStore.baseTimeline.tugNeg
  const valence = pos.map((p, i) => p + (neg[i] || 0))

  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const labels = dates.map(d => {
    const parts = d.split('-')
    if (parts.length === 3) {
      return monthNames[parseInt(parts[1]) - 1]
    }
    return d
  })

  return {
    labels: labels,
    datasets: [{
      label: 'Combined Mood Arc',
      data: valence,
      borderColor: 'white',
      borderWidth: 3,
      pointRadius: 0,
      tension: 0.4
    }]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false }
  },
  scales: {
    x: { 
      display: true,
      grid: { display: false },
      ticks: {
        color: 'rgba(255,255,255,0.7)',
        maxRotation: 0,
        autoSkip: true,
        maxTicksLimit: 12
      }
    },
    y: { display: false }
  },
  layout: { padding: 0 }
}
</script>

<template>
  <div class="wrapped-card">
    <div class="card-content animate-slide-up">
      <h2 class="pre-title">Your combined emotional arc</h2>
      
      <div class="chart-container">
        <Line :data="chartData" :options="chartOptions" />
      </div>

    </div>
  </div>
</template>

<style scoped>
.wrapped-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  color: white;
  width: 100%;
}
.card-content {
  width: 100vw;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.pre-title { font-size: 1.5rem; font-weight: 500; opacity: 0.9; margin-bottom: 3rem; }
.chart-container {
  width: 100vw;
  height: 400px;
  background: rgba(255,255,255,0.02);
  padding-top: 1rem;
}
.animate-slide-up { animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; transform: translateY(40px); }
@keyframes slideUp { to { opacity: 1; transform: translateY(0); } }
</style>
