<template>
  <div class="wrapped-card">
    <div class="card-content animate-slide-up">
      <h2 class="pre-title">The architects of your moods...</h2>
      
      <div class="split-view">
        <div class="lens-box ekman">
          <div class="lens-title">Top for {{ eMood }} (Ekman)</div>
          <div class="artists-list">
            <div v-for="(artist, index) in eArtists" :key="index" class="artist-row">
              <div class="rank">#{{ index + 1 }}</div>
              <div class="artist-info">
                <div class="artist-name">{{ artist.name }}</div>
                <div class="artist-time">{{ Math.round(artist.minutes) }} mins</div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="lens-box thayer">
          <div class="lens-title">Top for {{ tMood }} (Thayer)</div>
          <div class="artists-list">
            <div v-for="(artist, index) in tArtists" :key="index" class="artist-row">
              <div class="rank">#{{ index + 1 }}</div>
              <div class="artist-info">
                <div class="artist-name">{{ artist.name }}</div>
                <div class="artist-time">{{ Math.round(artist.minutes) }} mins</div>
              </div>
            </div>
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

const eMood = computed(() => metrics.value.ekman.topEmotion)
const eArtists = computed(() => metrics.value.ekman.topArtists)

const tMood = computed(() => metrics.value.thayer.topEmotion)
const tArtists = computed(() => metrics.value.thayer.topArtists)
</script>

<style scoped>
.wrapped-card { height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: white; padding: 2rem; width: 100%; }
.pre-title { font-size: 1.5rem; font-weight: 500; opacity: 0.9; margin-bottom: 3rem; }
.split-view { display: flex; gap: 2rem; width: 100%; justify-content: center; }
.lens-box { flex: 1; background: rgba(255,255,255,0.1); padding: 2rem; border-radius: 1rem; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.05); }
.lens-title { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.7; margin-bottom: 2rem; font-weight: bold; }
.artists-list { display: flex; flex-direction: column; gap: 1rem; width: 100%; }
.artist-row { background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 0.5rem; display: flex; align-items: center; gap: 1rem; text-align: left; }
.rank { font-size: 1.5rem; font-weight: 900; opacity: 0.5; }
.artist-info { flex: 1; overflow: hidden; }
.artist-name { font-size: 1rem; font-weight: 700; margin-bottom: 0.25rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.artist-time { font-size: 0.8rem; opacity: 0.8; }
.animate-slide-up { animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; transform: translateY(40px); width: 100%; max-width: 900px; }
@keyframes slideUp { to { opacity: 1; transform: translateY(0); } }
</style>
