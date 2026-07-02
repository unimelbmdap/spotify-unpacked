<script setup lang="ts">
import { Card, CardContent } from '@/components/ui/card'

defineProps<{
  label: string
  value: string | number
  unit?: string
  caption?: string
}>()

</script>

<template>
<Card class="ban">
  <CardContent class="flex flex-col gap-1 pt-6">
    <p class="text-sm font-bold text-muted-foreground">{{ label }}</p>
    <div class="flex items-baseline gap-1.5">
      <span class="text-3xl font-bold tracking-tight">{{ value }}</span>
      <span v-if="unit" class="text-sm text-muted-foreground">{{ unit }}</span>
    </div>
    <p v-if="caption" class="text-xs font-light italic text-muted-foreground mt-2">{{ caption }}</p>
  </CardContent>
</Card>
</template>
