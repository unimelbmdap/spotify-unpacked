<template>
  <div class="wrapped-container" style="background: linear-gradient(135deg, #1a1a2e 0%, #3a0ca3 100%)">
    
    <!-- No Data State -->
    <div v-if="!store.isLoaded" class="no-data">
      <h1>Loading your Wrapped...</h1>
    </div>
    <div v-else-if="cards.length === 0" class="no-data">
      <h1>We need your data first!</h1>
      <p>Please return to the dashboard and select a participant.</p>
      <button class="go-back-btn" @click="goHome">Go to Directory</button>
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
        <GenericWrappedCard v-if="cards[currentIndex]" :card="cards[currentIndex]!" :key="currentIndex" />
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePresentationStore } from '@/stores/presentation'
import GenericWrappedCard from '@/components/wrapped/GenericWrappedCard.vue'

const router = useRouter()
const store = usePresentationStore()

const cards = computed(() => store.selectedCards)

const currentIndex = ref(0)
const progress = ref(0)
let timer: number | null = null

const DURATION = 10000 // 10 seconds per card

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
    // Optionally redirect to profile overview at the end
    setTimeout(() => {
      goHome()
    }, 1000)
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
  const query = store.selectedUserId ? { user: store.selectedUserId } : {}
  router.push({ path: '/', query })
}

onMounted(() => {
  if (cards.value.length > 0) {
    startTimer()
  } else if (!store.isLoaded) {
    store.loadData().then(() => {
      if (cards.value.length > 0) startTimer()
    })
  }
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.wrapped-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  position: fixed;
  top: 0;
  left: 0;
  z-index: 9999;
}

.wrapped-content {
  width: 100%;
  height: 100%;
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
