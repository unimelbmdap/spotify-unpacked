<script setup lang="ts">
import { ref } from 'vue'
import FileCard from '@/components/FileCard.vue';
import BanCard from '@/components/BanCard.vue';
import { useDataStore } from '@/stores/data';
import { fileTypes } from '@/lib/fileTypes';
import { useFileDrop } from '@/composables/useFileDrop'
import { unzipFile } from '@/lib/unzip'
import { LoaderCircle } from 'lucide-vue-next'

const datastore = useDataStore();
const fileInput = ref<HTMLInputElement | null>(null)

const { isDragOver, isProcessing, onDragOver, onDragLeave, onDrop } = useFileDrop(
  (files) => datastore.loadFiles(files),
)

function onClickBrowse() {
  fileInput.value?.click()
}

async function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const rawFiles = Array.from(input.files ?? [])
  const files: File[] = []
  for (const file of rawFiles) {
    if (file.name.endsWith('.zip')) {
      files.push(...(await unzipFile(file)))
    } else {
      files.push(file)
    }
  }
  if (files.length > 0) datastore.loadFiles(files)
  input.value = ''
}
</script>

<template>

  <div class="flex flex-col flex-1 gap-4 p-4">

    <!-- BAN row -->
    <div class="grid grid-cols-3 gap-4">
      <BanCard label="Listening time in 2025" :value="datastore.listeningTimeHours.toLocaleString()" unit="hours" />
      <BanCard label="Unique songs" :value="datastore.uniqueTrackCount.toLocaleString()" />
      <BanCard label="Favourite time of day" :value="datastore.favouriteHour ?? '-'"/>
    </div>

    <div class="relative grid grid-cols-1 gap-4">
      <div v-if="isProcessing" class="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 rounded-lg bg-background/80">
        <LoaderCircle class="text-primary h-6 w-6 animate-spin" />
        <p class="text-muted-foreground text-sm">Reading files...</p>
      </div>

      <FileCard
        v-for="ft in fileTypes"
        :key="ft.key"
        :label="ft.label"
        :satisfied="datastore.fileTypeStatus[ft.key]"
        :what="ft.what"
        :file="ft.file"
        :why="ft.why"
        :class="isDragOver
            ? 'border-primary bg-primary/5'
            : 'border-muted-foreground/25 hover:border-muted-foreground/50'
        "
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
        @click="onClickBrowse"
      />
    </div>

  </div>

  <input
    ref="fileInput"
    type="file"
    multiple
    accept=".json,.zip"
    class="hidden"
    @change="onFileSelected"
  />

</template>

