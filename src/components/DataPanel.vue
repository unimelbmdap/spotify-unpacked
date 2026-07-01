<script setup lang="ts">
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { computed, ref } from 'vue'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { CircleHelp } from 'lucide-vue-next'
import FileDropZone from '@/components/FileDropZone.vue'
import StatsCard from '@/components/StatsCard.vue'
import { useDataStore } from '@/stores/data'
import DownloadHelp from './DownloadHelp.vue'

const dataStore = useDataStore()
const dropZone = ref<InstanceType<typeof FileDropZone> | null>(null)

function onFilesDropped(files: File[]) {
  dataStore.loadFiles(files)
}

function onClear() {
  dataStore.clear()
  dropZone.value?.reset()
}

const duplicateSummary = computed(() => {
  const parts: string[] = []
  if (dataStore.skippedFiles.length > 0) {
    parts.push(`${dataStore.skippedFiles.length} duplicate ${dataStore.skippedFiles.length === 1 ? 'file' : 'files'}`)
  }
  if (dataStore.skippedEntryCount > 0) {
    parts.push(`${dataStore.skippedEntryCount.toLocaleString()} duplicate ${dataStore.skippedEntryCount === 1 ? 'play' : 'plays'} already in your data`)
  }
  return parts.length > 0 ? `Skipped ${parts.join(' and ')}.` : ''
})
</script>

<template>
  <ScrollArea class="h-full">
    <div class="flex flex-col gap-4 p-4">
      <Card>
        <CardHeader>
          <div class="flex items-center justify-between">
            <div>
              <CardTitle>Data</CardTitle>
              <CardDescription>Upload your Spotify data export</CardDescription>
            </div>
            <Popover>
              <PopoverTrigger as-child>
                <Button variant="ghost" size="icon" class="h-8 w-8">
                  <CircleHelp class="h-4 w-4" />
                </Button>
              </PopoverTrigger>
              <PopoverContent class="w-80">
                <div class="space-y-2">
                  <h4 class="font-medium leading-none">How to use</h4>
                  <p class="text-sm text-muted-foreground">
                    Upload your Spotify data files by dragging and dropping them into the zone below, or click to browse. You can upload files one at a time or multiple files together.
                  </p>
                  <p class="text-sm text-muted-foreground">
                    We are looking for three files. The streaming file will be in your Spotify Extended Streaming History folder, the playlist and library files will be in your Spotify Account Data.
                  </p>
                  <p class="text-sm text-muted-foreground">
                    Supported file types: JSON files (.json) from your Spotify data downloads.
                  </p>
                </div>
              </PopoverContent>
            </Popover>
          </div>
        </CardHeader>
        <CardContent>
          <FileDropZone ref="dropZone" @files-dropped="onFilesDropped" />
          <p v-if="duplicateSummary" class="text-muted-foreground mt-2 text-xs">
            {{ duplicateSummary }}
          </p>
        </CardContent>
      </Card>

      <Button v-if="dataStore.hasData" variant="outline" size="sm" class="w-full" @click="onClear">
        Clear data
      </Button>

      <StatsCard />
      <DownloadHelp />
    </div>
    
  </ScrollArea>
</template>
