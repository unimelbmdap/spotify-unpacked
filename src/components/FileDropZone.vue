<script setup lang="ts">
import { ref } from 'vue'
import { Upload, FileCheck, LoaderCircle } from 'lucide-vue-next'
import { useDataStore } from '@/stores/data'
import { useFileDrop } from '@/composables/useFileDrop'
import JSZip from 'jszip'

const emit = defineEmits<{
  filesDropped: [files: File[]]
}>()

const dataStore = useDataStore()
const fileInput = ref<HTMLInputElement | null>(null)

const { isDragOver, isProcessing, onDragOver, onDragLeave, onDrop } = useFileDrop(
  (files) => emit('filesDropped', files),
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
      const zip = await JSZip.loadAsync(file)
      for (const [path, entry] of Object.entries(zip.files)) {
        if (entry.dir || !path.endsWith('.json')) continue
        const content = await entry.async('string')
        const filename = path.split('/').pop()!
        files.push(new File([content], filename, { type: 'application/json' }))
      }
    } else {
      files.push(file)
    }
  }
  if (files.length > 0) emit('filesDropped', files)
  input.value = ''
}

function reset() {
  isProcessing.value = false
}

defineExpose({ reset })
</script>

<template>
  <div
    class="flex h-32 cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed transition-colors"
    :class="
      isDragOver
        ? 'border-primary bg-primary/5'
        : 'border-muted-foreground/25 hover:border-muted-foreground/50'
    "
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
    @click="onClickBrowse"
  >
    <template v-if="isProcessing">
      <LoaderCircle class="text-primary h-6 w-6 animate-spin" />
      <p class="text-muted-foreground text-sm">Reading files...</p>
    </template>
    <template v-else-if="dataStore.fileCount > 0 && !isDragOver">
      <FileCheck class="text-primary h-6 w-6" />
      <p class="text-muted-foreground text-sm">
        Uploaded {{ dataStore.fileCount }} {{ dataStore.fileCount === 1 ? 'file' : 'files' }}
      </p>
    </template>
    <template v-else>
      <Upload class="text-muted-foreground h-6 w-6" :class="{ 'text-primary': isDragOver }" />
      <p class="text-muted-foreground text-sm">
        {{ isDragOver ? 'Drop files to upload' : 'Drop files here or click to browse' }}
      </p>
    </template>
    <input
      ref="fileInput"
      type="file"
      multiple
      accept=".json,.zip"
      class="hidden"
      @change="onFileSelected"
    />
  </div>
</template>
