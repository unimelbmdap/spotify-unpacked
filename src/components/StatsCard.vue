<script setup lang="ts">
import { computed } from 'vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useDataStore } from '@/stores/data'

const essentialFilesTarget = 3
const dataStore = useDataStore()

const fileCounts = computed(() => {
  const counts = {
    streaming: 0,
    library: 0,
    playlist: 0,
    unrecognised: 0,
  }

  dataStore.files.forEach((file) => {
    const nameLower = file.name.toLowerCase()
    if (
          nameLower.includes('streaming_history_audio') &&
          nameLower.includes('2025')) {
      counts.streaming++
    } else if (nameLower.includes('library')) {
      counts.library++
    } else if (nameLower.includes('playlist')) {
      counts.playlist++
    } else {
      counts.unrecognised++
    }
  })

  return counts
})

const essentialFilesLoaded = computed(
  () => fileCounts.value.streaming + fileCounts.value.library + fileCounts.value.playlist
)

const completionPercent = computed(() => {
  if (essentialFilesTarget <= 0) return 0
  return Math.min(100, Math.round((essentialFilesLoaded.value / essentialFilesTarget) * 100))
})
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>Statistics</CardTitle>
      <CardDescription>Summary of your loaded dataset</CardDescription>
    </CardHeader>
    <CardContent>
      <div class="mb-4">
      <div class="text-xs text-muted-foreground">{{ essentialFilesLoaded }}/{{ essentialFilesTarget }} essential files loaded {{ completionPercent }}%</div>
        <div class="h-4 w-full rounded-full bg-secondary overflow-hidden">
    <div class="h-full bg-primary transition-all duration-300" :style="{ width: `${completionPercent}%` }" />
  </div>
    </div>
      <template v-if="dataStore.hasData">
        <ul class="text-sm space-y-1">
          <li>
            {{ fileCounts.streaming }} {{ fileCounts.streaming === 1 ? 'streaming file' : 'streaming files' }} loaded
          </li>
          <li>
            {{ fileCounts.library }} {{ fileCounts.library === 1 ? 'library file' : 'library files' }} loaded
          </li>
          <li>
            {{ fileCounts.playlist }} {{ fileCounts.playlist === 1 ? 'playlist file' : 'playlist files' }} loaded
          </li>
          <li v-if="fileCounts.unrecognised > 0">
            {{ fileCounts.unrecognised }} {{ fileCounts.unrecognised === 1 ? 'nonessential file' : 'nonessential files' }} ignored
          </li>
        </ul>
      </template>
      <p v-else class="text-muted-foreground text-sm">No data loaded yet.</p>
    </CardContent>
  </Card>
</template>
