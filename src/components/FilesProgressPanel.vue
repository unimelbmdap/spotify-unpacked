<script setup lang="ts">
import { computed } from 'vue'
import { useDataStore } from '@/stores/data'

const dataStore = useDataStore()

const fileCounts = computed(() => {
  const counts = {
    streaming: 0,
    streaming2025: 0,
    library: 0,
    playlist: 0,
    unrecognised: 0,
  }

  dataStore.files.forEach((file) => {
    const nameLower = file.name.toLowerCase()
    if (nameLower.includes('streaming')) {
      counts.streaming++
      if (nameLower.includes('2025')) {
        counts.streaming2025++
      }
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

const completionSteps = computed(() => [
  { label: 'Streaming file with 2025 data', done: fileCounts.value.streaming2025 >= 1 },
  { label: 'Library file', done: fileCounts.value.library >= 1 },
  { label: 'Playlist file', done: fileCounts.value.playlist >= 1 },
])

const completionPercentage = computed(() => {
  const done = completionSteps.value.filter((s) => s.done).length
  return Math.round((done / completionSteps.value.length) * 100)
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
        <div class="flex justify-between text-sm mb-1">
          <span class="text-muted-foreground">Dataset completeness</span>
          <span class="font-medium">{{ completionPercentage }}%</span>
        </div>
        <div class="w-full bg-muted rounded-full h-2.5">
          <div
            class="bg-green-500 h-2.5 rounded-full transition-all duration-500"
            :style="{ width: completionPercentage + '%' }"
          />
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
          </li></ul>
          <ul class="text-xs space-y-1 mt-2">
          <li v-if="fileCounts.unrecognised > 0">
            {{ fileCounts.unrecognised }} {{ fileCounts.unrecognised === 1 ? 'non-essential file' : 'non-essential files' }} loaded (these will be ignored)
          </li>
        </ul>
      </template>
      <p v-else class="text-muted-foreground text-sm">No data loaded yet.</p>
    </CardContent>
  </Card>
</template>
