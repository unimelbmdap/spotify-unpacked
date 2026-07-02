<script setup lang="ts">
import { ref } from 'vue'
import { Card, CardContent } from '@/components/ui/card'
import { CheckCircle2, Upload, ArrowUp, Info } from 'lucide-vue-next'

defineProps<{
  label: string
  satisfied: boolean
  what?: string
  file?: string
  why?: string
}>()

const showTooltip = ref(false)
</script>

<template>
<Card
  class="transition-colors duration-500"
  :class="satisfied ? 'border-green-500 bg-green-500/10' : ''"
>
  <CardContent class="flex items-center gap-3 pt-6">
    <CheckCircle2 v-if="satisfied" class="size-10 shrink-0 text-green-500 transition-colors duration-500" />
    <Upload v-else class="size-10 shrink-0 text-muted-foreground transition-colors duration-500" />
    <p class="text-sm font-medium">{{ label }}</p>

    <CheckCircle2 v-if="satisfied" class="ml-auto size-6 shrink-0 text-green-500 transition-colors duration-500" />
    <ArrowUp v-else class="ml-auto size-6 shrink-0 text-muted-foreground transition-colors duration-500" />
    <p v-if="satisfied" class="text-sm text-green-500 transition-colors duration-500">Uploaded</p>
    <p v-else class="text-sm text-muted-foreground transition-colors duration-500">Upload file please</p>

    <div
      v-if="what || why || file"
      class="relative"
      @mouseenter="showTooltip = true"
      @mouseleave="showTooltip = false"
    >
      <Info class="size-4 cursor-help text-muted-foreground hover:text-foreground transition-colors" />
      <div
        v-show="showTooltip"
        class="absolute right-0 bottom-full mb-2 w-lg rounded-md border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md z-50"
      >
        <p class="font-semibold mb-1">{{ label }}</p>
        <p>What we see: {{ what }}</p>
        <p>Why it matters: {{ why }}</p>
        <p>File: {{ file }}</p>
        <div class="absolute right-1.5 top-full border-4 border-transparent border-t-border" />
      </div>
    </div>
  </CardContent>
</Card>
</template>
