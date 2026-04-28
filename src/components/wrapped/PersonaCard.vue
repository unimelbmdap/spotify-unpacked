<template>
  <div class="wrapped-card">
    <div class="card-content animate-slide-up">
      <h2 class="pre-title">Your listening personality is...</h2>
      
      <div class="split-view">
        <div class="lens-box ekman">
          <div class="lens-title">The Ekman Lens</div>
          <div class="persona-box">
            <h1 class="main-title">{{ ePersona }}</h1>
          </div>
          <p class="subtitle">Diversity score: {{ eEntropy.toFixed(2) }}</p>
        </div>
        
        <div class="lens-box thayer">
          <div class="lens-title">The Thayer Lens</div>
          <div class="persona-box">
            <h1 class="main-title">{{ tPersona }}</h1>
          </div>
          <p class="subtitle">Diversity score: {{ tEntropy.toFixed(2) }}</p>
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

const ePersona = computed(() => metrics.value.ekman.persona)
const eEntropy = computed(() => metrics.value.ekman.entropy)

const tPersona = computed(() => metrics.value.thayer.persona)
const tEntropy = computed(() => metrics.value.thayer.entropy)
</script>

<style scoped>
.wrapped-card { height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: white; padding: 2rem; width: 100%; }
.pre-title { font-size: 1.5rem; font-weight: 500; opacity: 0.9; margin-bottom: 3rem; }
.split-view { display: flex; gap: 2rem; width: 100%; justify-content: center; }
.lens-box { flex: 1; display: flex; flex-direction: column; align-items: center; }
.lens-title { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.7; margin-bottom: 2rem; font-weight: bold; }
.persona-box { background: linear-gradient(135deg, rgba(255,255,255,0.2), rgba(255,255,255,0.05)); padding: 2rem; border-radius: 2rem; backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 10px 40px rgba(0,0,0,0.2); width: 100%; display: flex; align-items: center; justify-content: center; flex: 1; }
.main-title { font-size: 2.5rem; font-weight: 900; letter-spacing: -0.05em; margin: 0; line-height: 1.1; }
.subtitle { font-size: 1rem; font-weight: 400; opacity: 0.8; margin-top: 1.5rem; }
.animate-slide-up { animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; transform: translateY(40px); width: 100%; max-width: 900px; }
@keyframes slideUp { to { opacity: 1; transform: translateY(0); } }
</style>
