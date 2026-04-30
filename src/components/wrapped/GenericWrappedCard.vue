<script setup lang="ts">
import type { WrappedCard } from '@/stores/presentation'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'

defineProps<{
  card: WrappedCard
}>()
</script>

<template>
  <div class="h-full w-full flex flex-col justify-center items-center p-8 text-center text-white">
    <div class="max-w-3xl w-full">
      <h2 class="text-4xl md:text-6xl font-bold mb-6 drop-shadow-lg leading-tight">{{ card.headline }}</h2>
      <p class="text-xl md:text-2xl opacity-90 mb-12 drop-shadow">{{ card.subheadline }}</p>
      
      <!-- Visual Placeholder based on card.visual_type -->
      <div v-if="card.visual_type === 'big-number'" class="text-7xl font-extrabold drop-shadow-xl animate-pulse">
        #{{ card.card_order }}
      </div>
      <div v-else-if="card.visual_type === 'badge'" class="inline-block px-8 py-4 bg-white/20 backdrop-blur-md rounded-full text-2xl font-semibold shadow-xl border border-white/30">
        Highlight
      </div>
      <div v-else-if="card.visual_type === 'meter'" class="w-full h-8 bg-black/30 rounded-full overflow-hidden shadow-inner border border-white/10">
        <div class="w-2/3 h-full bg-gradient-to-r from-blue-400 to-purple-500"></div>
      </div>
      <div v-else class="h-32 flex items-center justify-center border-2 border-dashed border-white/50 rounded-xl backdrop-blur-sm bg-black/10">
        Visual: {{ card.visual_type }}
      </div>

      <div v-if="card.confidence_note" class="mt-16 text-sm opacity-60 italic tracking-wider">
        {{ card.confidence_note }}
      </div>
    </div>
  </div>
</template>
