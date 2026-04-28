<template>
  <div class="wrapped-card">
    <div class="card-content animate-slide-up">
      <h2 class="pre-title">Your days had a rhythm...</h2>
      
      <div class="times-grid">
        <div class="time-slot">
          <div class="time-label">Morning</div>
          <div class="mood-val">{{ morning }}</div>
        </div>
        <div class="time-slot">
          <div class="time-label">Afternoon</div>
          <div class="mood-val">{{ afternoon }}</div>
        </div>
        <div class="time-slot">
          <div class="time-label">Night</div>
          <div class="mood-val">{{ night }}</div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDataStore } from '@/stores/data'

const dataStore = useDataStore()
const metrics = computed(() => dataStore.wrappedMetrics)

const morning = computed(() => metrics.value.timeOfDay.morning)
const afternoon = computed(() => metrics.value.timeOfDay.afternoon)
const night = computed(() => metrics.value.timeOfDay.night)
</script>

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
.times-grid { display: flex; flex-direction: column; gap: 2rem; width: 100%; max-width: 400px; }
.time-slot { background: rgba(255,255,255,0.1); padding: 1.5rem; border-radius: 1rem; backdrop-filter: blur(10px); display: flex; justify-content: space-between; align-items: center; }
.time-label { font-size: 1.25rem; font-weight: 600; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.05em; }
.mood-val { font-size: 1.5rem; font-weight: 800; text-transform: capitalize; }
.animate-slide-up { animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; transform: translateY(40px); }
@keyframes slideUp { to { opacity: 1; transform: translateY(0); } }
</style>
