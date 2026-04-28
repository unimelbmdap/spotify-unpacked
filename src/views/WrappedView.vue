<template>
  <div class="wrapped-container" :style="{ background: currentBgColor }">
    
    <!-- No Data State -->
    <div v-if="!dataStore.hasData" class="no-data">
      <h1>We need your data first!</h1>
      <p>Please return to the dashboard and upload your streaming history to see your Wrapped.</p>
      <button class="go-back-btn" @click="goHome">Go to Dashboard</button>
    </div>

    <!-- Wrapped Story -->
    <div v-else class="wrapped-content">
      <!-- Progress Bar -->
      <div class="progress-container">
        <div 
          v-for="(_, index) in cards" 
          :key="index" 
          class="progress-bar-bg"
        >
          <div 
            class="progress-bar-fill" 
            :style="{ 
              width: currentIndex > index ? '100%' : currentIndex === index ? progress + '%' : '0%',
              transition: currentIndex === index ? 'width 0.1s linear' : 'none'
            }"
          ></div>
        </div>
      </div>

      <!-- Current Card -->
      <transition name="fade" mode="out-in">
        <component :is="cards[currentIndex].component" :key="currentIndex" />
      </transition>

      <!-- Navigation Overlays -->
      <div class="nav-left" @click="prevCard"></div>
      <div class="nav-right" @click="nextCard"></div>
      
      <!-- Close Button -->
      <button class="close-btn" @click="goHome">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores/data'

import DominantMoodCard from '@/components/wrapped/DominantMoodCard.vue'
import EmotionalArcCard from '@/components/wrapped/EmotionalArcCard.vue'
import TimeOfDayCard from '@/components/wrapped/TimeOfDayCard.vue'
import TopEmotionArtistsCard from '@/components/wrapped/TopEmotionArtistsCard.vue'
import PersonaCard from '@/components/wrapped/PersonaCard.vue'

const router = useRouter()
const dataStore = useDataStore()

const cards = shallowRef([
  { component: DominantMoodCard },
  { component: EmotionalArcCard },
  { component: TimeOfDayCard },
  { component: TopEmotionArtistsCard },
  { component: PersonaCard },
])

const currentIndex = ref(0)
const progress = ref(0)
let timer: number | null = null

const DURATION = 10000 // 10 seconds per card

const baseCMap = dataStore.baseTimeline.cMap || {}
const metrics = computed(() => dataStore.wrappedMetrics)

const currentBgColor = computed(() => {
  const eDom = metrics.value.ekman.topEmotion
  const tDom = metrics.value.thayer.topEmotion
  
  let eHex = baseCMap[eDom] || '#1a1a1a'
  let tHex = baseCMap[tDom] || '#1a1a1a'
  
  eHex = darkenHex(eHex, 0.6)
  tHex = darkenHex(tHex, 0.6)
  
  if (currentIndex.value === 4) {
    eHex = darkenHex(eHex, 0.8)
    tHex = darkenHex(tHex, 0.8)
  }
  
  return `linear-gradient(135deg, ${eHex} 0%, ${tHex} 100%)`
})

function darkenHex(hex: string, factor: number) {
  if (!hex.startsWith('#')) return '#1a1a1a'
  let r = parseInt(hex.slice(1,3), 16)
  let g = parseInt(hex.slice(3,5), 16)
  let b = parseInt(hex.slice(5,7), 16)
  
  r = Math.floor(r * (1 - factor))
  g = Math.floor(g * (1 - factor))
  b = Math.floor(b * (1 - factor))
  
  return `rgb(${r},${g},${b})`
}

function startTimer() {
  progress.value = 0
  if (timer) clearInterval(timer)
  
  const step = 50 // 50ms interval
  timer = setInterval(() => {
    progress.value += (step / DURATION) * 100
    if (progress.value >= 100) {
      nextCard()
    }
  }, step) as any
}

function nextCard() {
  if (currentIndex.value < cards.value.length - 1) {
    currentIndex.value++
    startTimer()
  } else {
    // End of wrapped
    if (timer) clearInterval(timer)
    progress.value = 100
  }
}

function prevCard() {
  if (currentIndex.value > 0) {
    currentIndex.value--
    startTimer()
  } else {
    progress.value = 0
  }
}

function goHome() {
  router.push('/')
}

onMounted(() => {
  startTimer()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.wrapped-container {
  width: 100vw;
  height: 100vh;
  transition: background-color 1s ease;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 9999;
}

.wrapped-content {
  width: 100%;
  height: 100%;
  max-height: 900px;
  position: relative;
  display: flex;
  flex-direction: column;
}

.progress-container {
  position: absolute;
  top: 20px;
  left: 20px;
  right: 20px;
  display: flex;
  gap: 8px;
  z-index: 10;
}

.progress-bar-bg {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: white;
  width: 0%;
}

.nav-left {
  position: absolute;
  top: 0; left: 0; bottom: 0;
  width: 40%;
  z-index: 5;
  cursor: pointer;
}

.nav-right {
  position: absolute;
  top: 0; right: 0; bottom: 0;
  width: 60%;
  z-index: 5;
  cursor: pointer;
}

.close-btn {
  position: absolute;
  top: 40px;
  right: 20px;
  background: rgba(0,0,0,0.3);
  border: none;
  color: white;
  width: 40px; height: 40px;
  border-radius: 50%;
  display: flex; justify-content: center; align-items: center;
  z-index: 20;
  cursor: pointer;
  backdrop-filter: blur(5px);
  transition: background 0.2s;
}
.close-btn:hover {
  background: rgba(0,0,0,0.5);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.no-data {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: white;
  padding: 2rem;
  gap: 1.5rem;
}
.no-data h1 { font-size: 2.5rem; font-weight: bold; }
.no-data p { font-size: 1.25rem; opacity: 0.8; max-width: 400px; }
.go-back-btn {
  padding: 1rem 2rem;
  background: white;
  color: black;
  border-radius: 9999px;
  font-weight: bold;
  cursor: pointer;
  border: none;
  transition: transform 0.2s;
}
.go-back-btn:hover { transform: scale(1.05); }
</style>
