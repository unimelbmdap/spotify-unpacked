<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useAuditSummary } from '@/composables/useAuditSummary'
import BehavioralProfileCard from '@/components/BehavioralProfileCard.vue'

const subjects = ['ama', 'angie', 'ken', 'p1', 'p2', 'aggregate']
const selectedSubject = ref('angie')
const { summary, loading, error, loadSummary } = useAuditSummary()

onMounted(() => loadSummary(selectedSubject.value))
watch(selectedSubject, (newVal) => loadSummary(newVal))
</script>

<template>
  <div class="p-8 max-w-4xl mx-auto overflow-y-auto h-full">
    <div class="mb-8 border-b pb-6">
      <h1 class="text-2xl font-bold mb-4">Behavioral Audit Sandbox</h1>
      <div class="flex flex-wrap gap-2">
        <button 
          v-for="s in subjects" :key="s"
          @click="selectedSubject = s"
          :class="[
            'px-4 py-2 rounded-md text-sm font-medium transition-colors',
            selectedSubject === s ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          ]"
        >
          {{ s.toUpperCase() }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="py-12 text-center text-slate-500 animate-pulse">Loading audit data...</div>
    <div v-else-if="error" class="py-12 text-center text-red-500 bg-red-50 rounded-lg border border-red-100">
      {{ error }}
      <p class="text-sm mt-2">Make sure the files exist in public/data/</p>
    </div>
    <div v-else-if="summary?.behavioral_profile">
      <BehavioralProfileCard :profile="summary.behavioral_profile" />
      
      <div class="mt-8 pt-8 border-t">
        <h4 class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-4">Audit Metadata</h4>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-slate-600">
          <div class="bg-slate-50 p-3 rounded-lg border border-slate-100">
            <span class="block text-xs text-slate-400 mb-1">Dataset Size</span>
            <span class="font-medium">{{ summary.dataset_shape?.rows.toLocaleString() }} plays recorded</span>
          </div>
          <div class="bg-slate-50 p-3 rounded-lg border border-slate-100">
            <span class="block text-xs text-slate-400 mb-1">Temporal Coverage</span>
            <span class="font-medium">Starts {{ new Date(summary.date_coverage?.start).toLocaleDateString() }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="py-12 text-center text-slate-400">
      No behavioral profile found in this audit summary.
    </div>
  </div>
</template>
