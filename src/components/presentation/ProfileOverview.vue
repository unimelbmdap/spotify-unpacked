<script setup lang="ts">
import { usePresentationStore } from '@/stores/presentation'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import { ArrowRight, ArrowLeft } from 'lucide-vue-next'

const store = usePresentationStore()
const router = useRouter()

const profile = computed(() => store.selectedProfile)

const confidence = computed(() => {
  if (!profile.value) return null
  const z = profile.value.profile_conf
  if (z < 0.15) return { label: 'Low Confidence', variant: 'destructive', desc: 'Slight data footprint. Treat as preliminary.' }
  if (z < 0.50) return { label: 'Moderate Confidence', variant: 'secondary', desc: 'Moderate data footprint. Reliable but may shift.' }
  return { label: 'High Confidence', variant: 'default', desc: 'Strong data footprint. Stable classification.' }
})

function goBack() {
  store.setSelectedUser(null)
  router.push({ query: {} })
}

function startWrapped() {
  router.push('/wrapped')
}
</script>

<template>
  <div v-if="profile" class="max-w-4xl mx-auto space-y-6 py-8">
    <button @click="goBack" class="flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors">
      <ArrowLeft class="w-4 h-4 mr-1" />
      Back to Directory
    </button>

    <Card class="border-2 shadow-sm">
      <CardHeader class="pb-4">
        <div class="flex justify-between items-start mb-2">
          <Badge 
            v-if="profile.profile_label === 'Provisional Profile'" 
            variant="outline" 
            class="text-amber-500 border-amber-500 mb-2"
          >
            Provisional Profile
          </Badge>
          <div v-else></div> <!-- Spacer -->
          
          <!-- Confidence Badge -->
          <div class="flex flex-col items-end group relative cursor-help">
            <Badge :variant="confidence?.variant as any">
              {{ confidence?.label }}
            </Badge>
            <div class="absolute top-full mt-2 right-0 w-48 p-2 bg-popover text-popover-foreground text-xs rounded shadow-lg border opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
              <span class="font-semibold block mb-1">Actuarial Weight (Z = {{ profile.profile_conf.toFixed(2) }})</span>
              {{ confidence?.desc }}
            </div>
          </div>
        </div>

        <CardTitle class="text-4xl md:text-5xl font-bold tracking-tight mb-2">
          {{ profile.profile_label }}
        </CardTitle>
      </CardHeader>
      
      <CardContent class="space-y-8">
        <p class="text-lg text-muted-foreground leading-relaxed">
          {{ profile.profile_description }}
        </p>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="bg-muted/50 p-4 rounded-lg">
            <div class="text-sm text-muted-foreground mb-1 uppercase tracking-wider font-semibold">Intentionality</div>
            <div class="text-xl font-medium">{{ profile.intentionality_band }}</div>
          </div>
          <div class="bg-muted/50 p-4 rounded-lg">
            <div class="text-sm text-muted-foreground mb-1 uppercase tracking-wider font-semibold">Emotional Range</div>
            <div class="text-xl font-medium">{{ profile.emotional_range_band }}</div>
          </div>
          <div class="bg-muted/50 p-4 rounded-lg">
            <div class="text-sm text-muted-foreground mb-1 uppercase tracking-wider font-semibold">Pressure Signal</div>
            <div class="text-xl font-medium">{{ profile.pressure_signal_band }}</div>
          </div>
        </div>
      </CardContent>

      <CardFooter class="flex flex-col items-start bg-muted/30 pt-6 mt-4">
        <p class="text-xs text-muted-foreground italic max-w-2xl">
          {{ profile.disclaimer }}
        </p>
        <div class="w-full flex justify-end mt-4">
          <Button @click="startWrapped" class="group">
            View Story
            <ArrowRight class="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
          </Button>
        </div>
      </CardFooter>
    </Card>

  </div>
</template>
