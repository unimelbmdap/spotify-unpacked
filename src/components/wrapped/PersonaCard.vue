<template>
  <div class="wrapped-card">
    <div class="card-content animate-slide-up">
      <h2 class="pre-title">Your listening personality is...</h2>
      <div class="persona-box">
        <h1 class="main-title">{{ persona }}</h1>
      </div>
      <p class="subtitle">Your emotional diversity score was {{ entropy.toFixed(2) }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDataStore } from '@/stores/data'

const dataStore = useDataStore()
const metrics = computed(() => dataStore.wrappedMetrics)

const persona = computed(() => metrics.value.persona)
const entropy = computed(() => metrics.value.entropy)
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
.pre-title { font-size: 1.5rem; font-weight: 500; opacity: 0.9; margin-bottom: 2rem; }
.persona-box {
  background: linear-gradient(135deg, rgba(255,255,255,0.2), rgba(255,255,255,0.05));
  padding: 3rem;
  border-radius: 2rem;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.1);
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
}
.main-title { font-size: 4rem; font-weight: 900; letter-spacing: -0.05em; margin: 0; line-height: 1.1; }
.subtitle { font-size: 1.25rem; font-weight: 400; opacity: 0.8; margin-top: 2rem; }
.animate-slide-up { animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; transform: translateY(40px); }
@keyframes slideUp { to { opacity: 1; transform: translateY(0); } }
</style>
