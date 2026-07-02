import { ref } from 'vue'
import JSZip from 'jszip'

async function readDirectoryEntries(directory: FileSystemDirectoryEntry): Promise<File[]> {
  const reader = directory.createReader()
  const files: File[] = []
  let batch: FileSystemEntry[] = []
  do {
    batch = await new Promise((resolve, reject) => reader.readEntries(resolve, reject))
    for (const entry of batch) {
      if (entry.isFile) {
        const file = await new Promise<File>((resolve, reject) =>
          (entry as FileSystemFileEntry).file(resolve, reject),
        )
        files.push(file)
      } else if (entry.isDirectory) {
        files.push(...(await readDirectoryEntries(entry as FileSystemDirectoryEntry)))
      }
    }
  } while (batch.length > 0)
  return files
}

async function collectFiles(event: DragEvent): Promise<File[]> {
  const items = Array.from(event.dataTransfer?.items ?? [])
  const entries = items.map(item => item.webkitGetAsEntry?.() ?? null) // all sync, before any await
  const files: File[] = []

  for (const entry of entries) {
    if (!entry) continue
    if (entry.isDirectory) {
      files.push(...(await readDirectoryEntries(entry as FileSystemDirectoryEntry)))
    } else if (entry.isFile) {
      const file = await new Promise<File>((resolve, reject) =>
        (entry as FileSystemFileEntry).file(resolve, reject),
      )
      files.push(file)
    }
  }

  return files
}

export function useFileDrop(onFiles: (files: File[]) => void) {
  const isDragOver = ref(false)
  const isProcessing = ref(false)

  function onDragOver(event: DragEvent) {
    event.preventDefault()
    isDragOver.value = true
  }

  function onDragLeave() {
    isDragOver.value = false
  }

  async function onDrop(event: DragEvent) {
    event.preventDefault()
    isDragOver.value = false
    isProcessing.value = true
    try {
      const rawFiles = await collectFiles(event)
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
      if (files.length > 0) onFiles(files)
    } finally {
      isProcessing.value = false
    }
  }

  return { isDragOver, isProcessing, onDragOver, onDragLeave, onDrop }
}
