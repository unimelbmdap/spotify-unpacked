<script setup lang="ts">
import { usePresentationStore } from '@/stores/presentation'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { computed } from 'vue'

const store = usePresentationStore()

const profile = computed(() => store.selectedProfile)
const measures = computed(() => store.selectedMeasures)

const tableRows = computed(() => {
  return measures.value.map(m => ({
    metric: m.metric_name,
    raw: m.metric_value_num,
    layer: m.metric_layer,
    group: m.metric_group,
    source: m.source_table
  }))
})
</script>

<template>
  <div v-if="profile && store.isResearchMode" class="max-w-6xl mx-auto mt-8">
    <Card class="border-destructive shadow-sm">
      <CardHeader class="bg-destructive/10">
        <CardTitle class="text-xl text-destructive">Research Mode: Actuarial Debug Table</CardTitle>
        <p class="text-sm text-muted-foreground">
          Internal audit view showing all explicitly exported metrics for the current participant.
        </p>
      </CardHeader>
      <CardContent class="pt-6">
        <div class="overflow-x-auto">
          <table class="w-full text-sm text-left">
            <thead class="text-xs uppercase bg-muted text-muted-foreground">
              <tr>
                <th class="px-4 py-3 rounded-tl-lg">Metric Name</th>
                <th class="px-4 py-3">Value</th>
                <th class="px-4 py-3">Layer</th>
                <th class="px-4 py-3">Group</th>
                <th class="px-4 py-3 rounded-tr-lg">Source</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in tableRows" :key="row.metric" class="border-b last:border-0 hover:bg-muted/50">
                <td class="px-4 py-3 font-medium">{{ row.metric }}</td>
                <td class="px-4 py-3">{{ row.raw.toFixed(4) }}</td>
                <td class="px-4 py-3">
                  <span class="px-2 py-1 rounded text-xs font-semibold"
                        :class="{
                          'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300': row.layer === 'raw',
                          'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300': row.layer === 'cred',
                          'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300': row.layer === 'conf',
                          'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-300': row.layer === 'tail',
                          'bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-300': row.layer === 'exp'
                        }">
                    {{ row.layer }}
                  </span>
                </td>
                <td class="px-4 py-3">{{ row.group }}</td>
                <td class="px-4 py-3 text-xs text-muted-foreground">{{ row.source }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
