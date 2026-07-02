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

const store = useVisualisationStore()

const chartTypes = [
  { value: 'bar', label: 'Bar' },
  { value: 'line', label: 'Line' },
  { value: 'pie', label: 'Pie' },
  { value: 'doughnut', label: 'Doughnut' },
  { value: 'radar', label: 'Radar' },
  { value: 'polarArea', label: 'Polar Area' },
  { value: 'bubble', label: 'Bubble' },
  { value: 'scatter', label: 'Scatter' },
]
</script>

<template>
  <ScrollArea class="h-full">
    <div class="flex flex-col gap-4 p-4">
      <Card>
        <CardHeader>
          <CardTitle>Controls That Are Not Currently Usable</CardTitle>
          <CardDescription>Configure your visualisation</CardDescription>
        </CardHeader>
        <CardContent>
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
