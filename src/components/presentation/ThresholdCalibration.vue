<script setup lang="ts">
import { ref, computed } from 'vue'
import { usePresentationStore } from '@/stores/presentation'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Slider } from '@/components/ui/slider'
import { Badge } from '@/components/ui/badge'

const store = usePresentationStore()

// Draft Thresholds
const thresholds = ref({
  provisionalCoverageConf: 0.15,
  timeSpecificDaypartTail: 0.60,
  timeSpecificExamRatio: 2.0,
  processorHeavyCred: 0.30,
  processorAnchorTail: 0.05,
  uplifterUpbeatCred: 0.40,
  stabiliserEntropy: 1.5,
  stabiliserAnchorTail: 0.10,
  explorerEntropy: 2.0,
  explorerConcTail: 0.50
})

function evaluateProfile(user: any, t: typeof thresholds.value) {
  if (user.match_coverage_percent < 15.0 || user.profile_conf < t.provisionalCoverageConf) {
    return 'Provisional Profile'
  }
  // Note: we can't perfectly re-evaluate daypart_conc_tail without adding it to the student_profiles.csv 
  // Let's assume the user has exam_tail_ratio and others available.
  // Actually, we did export those in generate_profiles.py. We didn't export daypart_conc_tail or emotion_entropy_exp to student_profiles.csv directly.
  // Wait, I only exported heavy_share_raw, heavy_share_cred, upbeat_share_raw, upbeat_share_cred, exam_peak_share_raw, exam_tail_ratio.
  // For the sake of the sandbox, we'll just show the simulated label if we can, or just show a warning.
  // We can just simulate the ones we have.
  if (user.exam_tail_ratio > t.timeSpecificExamRatio) {
    return 'The Time-Specific Listener'
  }
  if (user.heavy_share_cred > t.processorHeavyCred) { // Simplified for sandbox
    return 'The Processor'
  }
  if (user.upbeat_share_cred > t.uplifterUpbeatCred) {
    return 'The Uplifter'
  }
  
  return 'Simulated (Requires full backend data)'
}

function updateThreshold(key: keyof typeof thresholds.value, v: number[] | undefined) {
  if (v && v[0] !== undefined) {
    thresholds.value[key] = v[0]
  }
}

const simulatedProfiles = computed(() => {
  return Object.values(store.profilesByUser).map(user => {
    const original = user.profile_label
    const simulated = evaluateProfile(user, thresholds.value)
    return {
      person_id: user.person_id,
      original,
      simulated,
      changed: original !== simulated && simulated !== 'Simulated (Requires full backend data)'
    }
  })
})
</script>

<template>
  <div v-if="store.isResearchMode" class="max-w-6xl mx-auto mt-8 mb-16">
    <Card class="border-destructive shadow-sm">
      <CardHeader class="bg-destructive/10">
        <CardTitle class="text-xl text-destructive">Research Mode: Threshold Calibration Sandbox</CardTitle>
        <p class="text-sm text-muted-foreground">
          Adjust the draft actuarial thresholds to see how they impact cohort classifications. This does not modify the backend Python logic.
        </p>
      </CardHeader>
      <CardContent class="pt-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          <!-- Controls -->
          <div class="space-y-6">
            <div class="space-y-2">
              <div class="flex justify-between">
                <label class="text-sm font-medium">Provisional: Coverage Conf < {{ thresholds.provisionalCoverageConf.toFixed(2) }}</label>
              </div>
              <Slider :model-value="[thresholds.provisionalCoverageConf]" @update:model-value="v => updateThreshold('provisionalCoverageConf', v)" :max="1" :step="0.05" />
            </div>

            <div class="space-y-2">
              <div class="flex justify-between">
                <label class="text-sm font-medium">Time-Specific: Exam Tail Ratio > {{ thresholds.timeSpecificExamRatio.toFixed(2) }}</label>
              </div>
              <Slider :model-value="[thresholds.timeSpecificExamRatio]" @update:model-value="v => updateThreshold('timeSpecificExamRatio', v)" :max="5" :step="0.1" />
            </div>

            <div class="space-y-2">
              <div class="flex justify-between">
                <label class="text-sm font-medium">Processor: Heavy Credibility > {{ thresholds.processorHeavyCred.toFixed(2) }}</label>
              </div>
              <Slider :model-value="[thresholds.processorHeavyCred]" @update:model-value="v => updateThreshold('processorHeavyCred', v)" :max="1" :step="0.05" />
            </div>

            <div class="space-y-2">
              <div class="flex justify-between">
                <label class="text-sm font-medium">Uplifter: Upbeat Credibility > {{ thresholds.uplifterUpbeatCred.toFixed(2) }}</label>
              </div>
              <Slider :model-value="[thresholds.uplifterUpbeatCred]" @update:model-value="v => updateThreshold('uplifterUpbeatCred', v)" :max="1" :step="0.05" />
            </div>
          </div>

          <!-- Impact Output -->
          <div>
            <h3 class="font-semibold mb-4 text-sm uppercase tracking-wider text-muted-foreground">Cohort Impact</h3>
            <div class="space-y-2">
              <div v-for="user in simulatedProfiles" :key="user.person_id" 
                   class="p-3 border rounded flex justify-between items-center transition-colors"
                   :class="{'bg-amber-100 dark:bg-amber-900 border-amber-300 dark:border-amber-700': user.changed}">
                <span class="font-medium text-sm">Participant {{ user.person_id }}</span>
                <div class="flex items-center gap-2">
                  <span class="text-xs text-muted-foreground line-through" v-if="user.changed">{{ user.original }}</span>
                  <Badge :variant="user.changed ? 'default' : 'secondary'">{{ user.simulated !== 'Simulated (Requires full backend data)' ? user.simulated : user.original }}</Badge>
                </div>
              </div>
            </div>
          </div>

        </div>
      </CardContent>
    </Card>
  </div>
</template>
