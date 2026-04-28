<template>
  <div class="wrapped-card">
    <div class="card-content animate-slide-up">
      <h2 class="pre-title">Your days had a rhythm...</h2>
      
      <div class="split-view">
        <div class="lens-box ekman">
          <div class="lens-title">The Ekman Lens</div>
          <div class="times-grid">
            <div class="time-slot"><span class="time-label">Morn</span><span class="mood-val">{{ eMorn }}</span></div>
            <div class="time-slot"><span class="time-label">Aft</span><span class="mood-val">{{ eAft }}</span></div>
            <div class="time-slot"><span class="time-label">Night</span><span class="mood-val">{{ eNight }}</span></div>
          </div>
        </div>
        
        <div class="lens-box thayer">
          <div class="lens-title">The Thayer Lens</div>
          <div class="times-grid">
            <div class="time-slot"><span class="time-label">Morn</span><span class="mood-val">{{ tMorn }}</span></div>
            <div class="time-slot"><span class="time-label">Aft</span><span class="mood-val">{{ tAft }}</span></div>
            <div class="time-slot"><span class="time-label">Night</span><span class="mood-val">{{ tNight }}</span></div>
          </div>
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

const eMorn = computed(() => metrics.value.ekman.timeOfDay.morning)
const eAft = computed(() => metrics.value.ekman.timeOfDay.afternoon)
const eNight = computed(() => metrics.value.ekman.timeOfDay.night)

const tMorn = computed(() => metrics.value.thayer.timeOfDay.morning)
const tAft = computed(() => metrics.value.thayer.timeOfDay.afternoon)
const tNight = computed(() => metrics.value.thayer.timeOfDay.night)
</script>

<style scoped>
.wrapped-card { height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: white; padding: 2rem; width: 100%; }
.pre-title { font-size: 1.5rem; font-weight: 500; opacity: 0.9; margin-bottom: 3rem; }
.split-view { display: flex; gap: 2rem; width: 100%; justify-content: center; }
.lens-box { flex: 1; background: rgba(255,255,255,0.1); padding: 2rem; border-radius: 1rem; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.05); }
.lens-title { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.7; margin-bottom: 2rem; font-weight: bold; }
.times-grid { display: flex; flex-direction: column; gap: 1rem; width: 100%; }
.time-slot { background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 0.5rem; display: flex; justify-content: space-between; align-items: center; }
.time-label { font-size: 1rem; font-weight: 600; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.05em; }
.mood-val { font-size: 1.25rem; font-weight: 800; text-transform: capitalize; }
.animate-slide-up { animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; transform: translateY(40px); width: 100%; max-width: 800px; }
@keyframes slideUp { to { opacity: 1; transform: translateY(0); } }
</style>
