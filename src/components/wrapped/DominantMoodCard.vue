<template>
  <div class="wrapped-card">
    <div class="card-content animate-slide-up">
      <h2 class="pre-title">This year, you were mostly...</h2>
      
      <div class="split-view">
        <div class="lens-box ekman">
          <div class="lens-title">The Ekman Lens</div>
          <h1 class="main-title">{{ ekmanName }}</h1>
          <p class="subtitle">You spent {{ ekmanPercent }}% of your time here.</p>
        </div>
        
        <div class="lens-box thayer">
          <div class="lens-title">The Thayer Lens</div>
          <h1 class="main-title">{{ thayerName }}</h1>
          <p class="subtitle">You spent {{ thayerPercent }}% of your time here.</p>
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

const ekmanName = computed(() => metrics.value.ekman.topEmotion.charAt(0).toUpperCase() + metrics.value.ekman.topEmotion.slice(1))
const ekmanPercent = computed(() => ((metrics.value.ekman.emotionShare[metrics.value.ekman.topEmotion] || 0) * 100).toFixed(0))

const thayerName = computed(() => metrics.value.thayer.topEmotion.charAt(0).toUpperCase() + metrics.value.thayer.topEmotion.slice(1))
const thayerPercent = computed(() => ((metrics.value.thayer.emotionShare[metrics.value.thayer.topEmotion] || 0) * 100).toFixed(0))
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
  width: 100%;
}
.pre-title { font-size: 1.5rem; font-weight: 500; opacity: 0.9; margin-bottom: 3rem; }
.split-view {
  display: flex;
  gap: 2rem;
  width: 100%;
  justify-content: center;
}
.lens-box {
  flex: 1;
  background: rgba(255,255,255,0.1);
  padding: 2rem;
  border-radius: 1rem;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.05);
}
.lens-title { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.7; margin-bottom: 1rem; font-weight: bold; }
.main-title { font-size: 3rem; font-weight: 900; letter-spacing: -0.05em; text-transform: uppercase; margin: 0; line-height: 1; text-shadow: 0 4px 20px rgba(0,0,0,0.2); }
.subtitle { font-size: 1rem; font-weight: 400; opacity: 0.8; margin-top: 1rem; }
.animate-slide-up { animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; transform: translateY(40px); width: 100%; max-width: 800px; }
@keyframes slideUp { to { opacity: 1; transform: translateY(0); } }
</style>
