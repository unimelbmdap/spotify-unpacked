<script setup lang="ts">
import { computed } from 'vue'
import type { BehavioralProfile } from '@/composables/useAuditSummary'

const props = defineProps<{
  profile: BehavioralProfile
}>()

// Label color mapping
const primaryColor = computed(() => {
  const label = props.profile.behavioral_label_primary
  if (label.includes('Receptive')) return 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-200 dark:border-blue-800'
  if (label.includes('Responsive')) return 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-200 dark:border-emerald-800'
  if (label.includes('Deliberate')) return 'bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/30 dark:text-purple-200 dark:border-purple-800'
  if (label.includes('Mixed')) return 'bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-700'
  if (label.includes('Insufficient')) return 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-200 dark:border-red-800'
  return 'bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-700'
})

// Confidence color mapping
const confidenceColor = (conf: string) => {
  switch (conf) {
    case 'High': return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
    case 'Medium': return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
    case 'Low': return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300'
    case 'Baseline': return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
    case 'None': return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
    default: return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300'
  }
}

// Band color mapping
const bandColor = (level: string) => {
  switch (level) {
    case 'Low': return 'text-emerald-600 bg-emerald-50 border-emerald-100 dark:text-emerald-400 dark:bg-emerald-900/20 dark:border-emerald-800'
    case 'Medium': return 'text-amber-600 bg-amber-50 border-amber-100 dark:text-amber-400 dark:bg-amber-900/20 dark:border-amber-800'
    case 'High': return 'text-rose-600 bg-rose-50 border-rose-100 dark:text-rose-400 dark:bg-rose-900/20 dark:border-rose-800'
    default: return 'text-gray-400 bg-gray-50 border-gray-100 dark:text-gray-500 dark:bg-gray-900/20 dark:border-gray-800'
  }
}

const formatPercent = (val: number) => `${(val * 100).toFixed(1)}%`
</script>

<template>
  <div class="rounded-xl border border-border bg-card p-6 shadow-sm max-w-2xl text-card-foreground">
    <!-- Header -->
    <div class="flex flex-wrap items-start justify-between gap-4 mb-8">
      <div>
        <h3 class="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-3">Behavioral Profile</h3>
        <div class="flex items-center gap-3">
          <span :class="['px-3 py-1.5 rounded-lg text-lg font-bold border shadow-sm', primaryColor]">
            {{ profile.behavioral_label_primary }}
          </span>
          <span :class="['px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-tight', confidenceColor(profile.classification_confidence)]">
            {{ profile.classification_confidence }} Confidence
          </span>
        </div>
      </div>
      
      <div class="text-right">
        <span class="text-[10px] font-bold text-muted-foreground uppercase tracking-widest block mb-1">Platform Context</span>
        <span class="px-2 py-1 rounded bg-slate-800 text-white text-xs font-mono dark:bg-slate-200 dark:text-slate-900">
          {{ profile.platform_mode }}
        </span>
      </div>
    </div>

    <!-- Signal Bands Grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
      <div v-for="signal in [
        { label: 'Skip Rate', val: profile.skip_rate, level: profile.skip_level },
        { label: 'Shuffle Rate', val: profile.shuffle_rate, level: profile.shuffle_level },
        { label: 'Selection', val: profile.active_selection_score, level: profile.deliberate_level }
      ]" :key="signal.label" class="p-3 rounded-lg border border-border bg-muted/50">
        <span class="text-[10px] font-semibold text-muted-foreground uppercase block mb-1">{{ signal.label }}</span>
        <div class="flex items-end justify-between">
          <span class="text-xl font-bold text-foreground">{{ formatPercent(signal.val) }}</span>
          <span :class="['px-1.5 py-0.5 rounded text-[10px] font-bold border', bandColor(signal.level)]">
            {{ signal.level }}
          </span>
        </div>
      </div>
    </div>

    <!-- Explanation Note -->
    <div class="text-sm text-muted-foreground bg-muted rounded-xl p-4 border border-border">
      <div class="flex gap-3">
        <div class="mt-0.5">
          <svg class="w-5 h-5 text-muted-foreground/60" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
        </div>
        <div>
          <p class="leading-relaxed font-medium text-foreground/80">{{ profile.behavioral_basis_note }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
