<script setup lang="ts">
import { computed } from 'vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useDataStore } from '@/stores/data'
import { fileTypes } from '@/lib/fileTypes'

const dataStore = useDataStore()

const completionPercentage = computed(() => {
  const requiredTypes = fileTypes.filter((ft) => !ft.optional)
  const done = requiredTypes.filter((ft) => dataStore.fileTypeStatus[ft.key]).length
  return Math.round((done / requiredTypes.length) * 100)
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
          <li v-for="ft in fileTypes" :key="ft.key">
            {{ ft.label }}: {{ dataStore.fileTypeStatus[ft.key] ? 'loaded' : 'missing' }}
          </li>
        </ul>
      </template>
      <p v-else class="text-muted-foreground text-sm">No data loaded yet.</p>
    </CardContent>
  </Card>
</template>
