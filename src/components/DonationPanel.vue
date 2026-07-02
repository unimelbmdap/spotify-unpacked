<script setup lang="ts">
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Gift } from 'lucide-vue-next'


</script>

<template>
  <ScrollArea class="h-full">
    <div class="flex flex-col gap-4 p-4">
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
