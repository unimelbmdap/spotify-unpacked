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

  return {
    labels: dates,
    datasets: [{
      label: 'Mood Arc',
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
    x: { display: false },
    y: { display: false }
  }
}
</script>

<template>
  <div class="wrapped-card">
    <div class="card-content animate-slide-up">
      <h2 class="pre-title">Your emotional arc over time</h2>
      
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
  padding: 2rem;
}
.pre-title { font-size: 1.5rem; font-weight: 500; opacity: 0.9; margin-bottom: 3rem; }
.chart-container {
  width: 100%;
  max-width: 600px;
  height: 300px;
  background: rgba(255,255,255,0.05);
  border-radius: 1rem;
  padding: 1rem;
}
.animate-slide-up { animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; transform: translateY(40px); }
@keyframes slideUp { to { opacity: 1; transform: translateY(0); } }
</style>
