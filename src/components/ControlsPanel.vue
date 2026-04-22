<script setup lang="ts">
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Gift } from 'lucide-vue-next'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useVisualisationStore } from '@/stores/visualisation'
import { useDataStore } from '@/stores/data'
import { computed } from 'vue'

const store = useVisualisationStore()
const dataStore = useDataStore()

const chartTypes = [
  { value: 'temporal', label: 'Temporal Dashboard' },
  { value: 'bar', label: 'Bar' },
  { value: 'line', label: 'Line' },
  { value: 'pie', label: 'Pie' },
  { value: 'doughnut', label: 'Doughnut' },
  { value: 'radar', label: 'Radar' },
  { value: 'polarArea', label: 'Polar Area' },
  { value: 'bubble', label: 'Bubble' },
  { value: 'scatter', label: 'Scatter' },
]

const sourceOrigins = [
  { value: 'All', label: 'All Sources' },
  { value: 'Library', label: 'In Library' },
  { value: 'Playlist', label: 'In Playlist' },
]

</script>

<template>
  <ScrollArea class="h-full">
    <div class="flex flex-col gap-4 p-4">
      <Card>
        <CardHeader>
          <CardTitle>Controls</CardTitle>
          <CardDescription>Configure your visualisation</CardDescription>
        </CardHeader>
        <CardContent>
          <div class="flex flex-col gap-4">
            <div class="flex flex-col gap-2">
              <label class="text-sm font-medium">Chart Type</label>
              <Select v-model="store.selectedChart">
                <SelectTrigger>
                  <SelectValue placeholder="Select a chart type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="chart in chartTypes" :key="chart.value" :value="chart.value">
                    {{ chart.label }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div class="flex flex-col gap-2">
              <label class="text-sm font-medium">Source Origin</label>
              <Select v-model="store.sourceOrigin">
                <SelectTrigger>
                  <SelectValue placeholder="Select origin filter" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="origin in sourceOrigins" :key="origin.value" :value="origin.value">
                    {{ origin.label }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div class="flex flex-col gap-2">
              <label class="text-sm font-medium">Year Filter</label>
              <Select v-model="store.year">
                <SelectTrigger>
                  <SelectValue placeholder="Select year" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="y in dataStore.availableYears" :key="y" :value="y">
                    {{ y }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div class="flex flex-col gap-2">
              <label class="text-sm font-medium">Date Range</label>
              <div class="flex items-center gap-2">
                <input 
                  type="date" 
                  v-model="store.dateRange.start" 
                  class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                />
                <span class="text-sm text-muted-foreground">to</span>
                <input 
                  type="date" 
                  v-model="store.dateRange.end" 
                  class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                />
              </div>
            </div>

            <div class="flex items-center gap-2">
              <input 
                type="checkbox" 
                id="aiGhostToggle" 
                v-model="store.aiGhostToggle"
                class="size-4 rounded border-input text-primary focus:ring-primary"
              />
              <label for="aiGhostToggle" class="text-sm font-medium">Flag AI/Ghost Contexts</label>
            </div>

            <div class="flex items-center gap-2">
              <input 
                type="checkbox" 
                id="allowImputation" 
                v-model="store.allowImputation"
                class="size-4 rounded border-input text-primary focus:ring-primary"
              />
              <label for="allowImputation" class="text-sm font-medium">Mood Persistence (Imputation)</label>
            </div>
            <div class="flex items-center gap-2">
              <input 
                type="checkbox" 
                id="useRollingAverage" 
                v-model="store.useRollingAverage"
                class="size-4 rounded border-input text-primary focus:ring-primary"
              />
              <label for="useRollingAverage" class="text-sm font-medium">7-Day Rolling Average</label>
            </div>
          </div>
        </CardContent>
      </Card>

      <RouterLink to="/donate">
        <Card class="transition-colors hover:border-primary/50">
          <CardHeader>
            <CardTitle class="flex items-center gap-2">
              <Gift class="size-4" />
              Donate Your Data
            </CardTitle>
            <CardDescription>
              Help improve our research by contributing listening data. Click for details.
            </CardDescription>
          </CardHeader>
        </Card>
      </RouterLink>
    </div>
  </ScrollArea>
</template>
