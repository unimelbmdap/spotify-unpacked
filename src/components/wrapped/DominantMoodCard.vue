<template>
  <div class="wrapped-card">
    <div class="card-content animate-slide-up">
      <h2 class="pre-title">This year, you were mostly...</h2>
      <h1 class="main-title">{{ emotionName }}</h1>
      <p class="subtitle">You spent {{ percent }}% of your listening time feeling this way.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDataStore } from '@/stores/data'

const dataStore = useDataStore()
const metrics = computed(() => dataStore.wrappedMetrics)

const emotionName = computed(() => metrics.value.topEmotion.charAt(0).toUpperCase() + metrics.value.topEmotion.slice(1))
const percent = computed(() => {
  const share = metrics.value.emotionShare[metrics.value.topEmotion] || 0
  return (share * 100).toFixed(0)
})
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
.pre-title { font-size: 1.5rem; font-weight: 500; opacity: 0.9; margin-bottom: 1rem; }
.main-title { font-size: 5rem; font-weight: 900; letter-spacing: -0.05em; text-transform: uppercase; margin: 0; line-height: 1; text-shadow: 0 4px 20px rgba(0,0,0,0.2); }
.subtitle { font-size: 1.25rem; font-weight: 400; opacity: 0.8; margin-top: 1.5rem; }
.animate-slide-up { animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; transform: translateY(40px); }
@keyframes slideUp { to { opacity: 1; transform: translateY(0); } }
</style>
