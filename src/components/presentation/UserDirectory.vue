<script setup lang="ts">
import { usePresentationStore } from '@/stores/presentation'
import { useRouter } from 'vue-router'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

const store = usePresentationStore()
const router = useRouter()

function selectUser(userId: string) {
  router.push({ query: { user: userId } })
  store.setSelectedUser(userId)
}

function getConfidenceBand(conf: number) {
  if (conf < 0.15) return { label: 'Low Confidence', variant: 'destructive' }
  if (conf < 0.50) return { label: 'Moderate Confidence', variant: 'secondary' }
  return { label: 'High Confidence', variant: 'default' }
}
</script>

<template>
  <div class="space-y-6 max-w-5xl mx-auto py-8">
    <div>
      <h1 class="text-3xl font-bold tracking-tight">Participant Directory</h1>
      <p class="text-muted-foreground mt-2">
        Select a participant to view their Emotion Regulation Profile.
      </p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <Card 
        v-for="profile in Object.values(store.profilesByUser)" 
        :key="profile.person_id"
        class="cursor-pointer hover:border-primary transition-colors duration-200"
        @click="selectUser(profile.person_id)"
      >
        <CardHeader class="pb-3">
          <div class="flex justify-between items-start">
            <CardTitle class="text-xl">Participant {{ profile.person_id }}</CardTitle>
            <Badge 
              v-if="profile.profile_label === 'Provisional Profile'" 
              variant="outline" 
              class="text-amber-500 border-amber-500"
            >
              Provisional
            </Badge>
          </div>
          <CardDescription class="text-base font-medium mt-1 text-foreground">
            {{ profile.profile_label }}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div class="flex items-center gap-2 mt-2">
            <Badge :variant="getConfidenceBand(profile.profile_conf).variant as any">
              {{ getConfidenceBand(profile.profile_conf).label }}
            </Badge>
            <span class="text-xs text-muted-foreground">Z = {{ profile.profile_conf.toFixed(2) }}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
