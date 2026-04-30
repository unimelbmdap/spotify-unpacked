<script setup lang="ts">
import { usePresentationStore } from '@/stores/presentation'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { computed } from 'vue'

const store = usePresentationStore()

const profile = computed(() => store.selectedProfile)

interface ActuarialComparison {
  label: string
  raw: number
  cred: number
  isPercent: boolean
  desc: string
}

const comparisons = computed<ActuarialComparison[]>(() => {
  if (!profile.value) return []
  const p = profile.value
  return [
    {
      label: 'Heavy Listening',
      raw: p.heavy_share_raw,
      cred: p.heavy_share_cred,
      isPercent: true,
      desc: 'Observed heavy emotion share vs cohort-adjusted baseline.'
    },
    {
      label: 'Upbeat Listening',
      raw: p.upbeat_share_raw,
      cred: p.upbeat_share_cred,
      isPercent: true,
      desc: 'Observed upbeat emotion share vs cohort-adjusted baseline.'
    },
    {
      label: 'Exam Period Spike',
      raw: p.exam_peak_share_raw,
      cred: p.exam_tail_ratio, // Note: cred is actually a ratio, so we handle it below
      isPercent: false, // The cred is a ratio, raw is a percent. 
      desc: 'Raw month share vs ratio of exam to non-exam exposure.'
    }
  ]
})

function formatValue(val: number, isPercent: boolean, isRatio = false) {
  if (isRatio) return val.toFixed(2) + 'x'
  return isPercent ? (val * 100).toFixed(1) + '%' : val.toFixed(2)
}
</script>

<template>
  <div v-if="profile" class="max-w-4xl mx-auto mt-8">
    <Card>
      <CardHeader>
        <CardTitle class="text-xl">Actuarial Explanation</CardTitle>
        <p class="text-sm text-muted-foreground">
          Why you got this profile. We shrink observed signals toward the cohort average when data is sparse.
        </p>
      </CardHeader>
      <CardContent>
        <div class="space-y-6">
          <div v-for="comp in comparisons" :key="comp.label" class="flex flex-col gap-2">
            <div class="flex justify-between items-end">
              <span class="font-medium">{{ comp.label }}</span>
              <span class="text-xs text-muted-foreground">{{ comp.desc }}</span>
            </div>
            
            <div class="grid grid-cols-2 gap-4">
              <!-- Raw Bar -->
              <div class="space-y-1">
                <div class="flex justify-between text-xs text-muted-foreground">
                  <span>Raw Observation</span>
                  <span>{{ comp.label === 'Exam Period Spike' ? formatValue(comp.raw, true) : formatValue(comp.raw, comp.isPercent) }}</span>
                </div>
                <div class="h-2 bg-secondary rounded overflow-hidden">
                  <div 
                    class="h-full bg-slate-400" 
                    :style="{ width: comp.label === 'Exam Period Spike' ? (comp.raw * 100) + '%' : (comp.raw * 100) + '%' }"
                  ></div>
                </div>
              </div>

              <!-- Adjusted Bar -->
              <div class="space-y-1">
                <div class="flex justify-between text-xs text-primary">
                  <span class="font-medium">Adjusted Signal</span>
                  <span class="font-medium">{{ comp.label === 'Exam Period Spike' ? formatValue(comp.cred, false, true) : formatValue(comp.cred, comp.isPercent) }}</span>
                </div>
                <div class="h-2 bg-secondary rounded overflow-hidden">
                  <div 
                    class="h-full bg-primary" 
                    :style="{ width: comp.label === 'Exam Period Spike' ? Math.min((comp.cred / 3) * 100, 100) + '%' : (comp.cred * 100) + '%' }"
                  ></div>
                </div>
              </div>
            </div>
          </div>

          <div class="bg-muted p-4 rounded-lg mt-6 text-sm text-muted-foreground border-l-4 border-primary">
            <strong>Diagnostic Note:</strong> {{ profile.profile_basis_note }}
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
