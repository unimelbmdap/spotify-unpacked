<template>
  <div class="wrapped-card">
    <div class="card-content animate-slide-up">
      <h2 class="pre-title">The architects of your {{ emotionName }} era...</h2>
      
      <div class="artists-list">
        <div v-for="(artist, index) in topArtists" :key="index" class="artist-row">
          <div class="rank">#{{ index + 1 }}</div>
          <div class="artist-info">
            <div class="artist-name">{{ artist.name }}</div>
            <div class="artist-time">{{ Math.round(artist.minutes) }} mins</div>
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

const emotionName = computed(() => metrics.value.topEmotion)
const topArtists = computed(() => metrics.value.topArtists)
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
.pre-title { font-size: 1.5rem; font-weight: 500; opacity: 0.9; margin-bottom: 3rem; text-transform: capitalize; }
.artists-list { display: flex; flex-direction: column; gap: 1.5rem; width: 100%; max-width: 500px; }
.artist-row { 
  background: rgba(255,255,255,0.1); 
  padding: 1.5rem; 
  border-radius: 1rem; 
  backdrop-filter: blur(10px); 
  display: flex; 
  align-items: center;
  gap: 1.5rem;
  text-align: left;
}
.rank { font-size: 2rem; font-weight: 900; opacity: 0.5; }
.artist-info { flex: 1; }
.artist-name { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.25rem; }
.artist-time { font-size: 1rem; opacity: 0.8; }

.animate-slide-up { animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; transform: translateY(40px); }
@keyframes slideUp { to { opacity: 1; transform: translateY(0); } }
</style>
