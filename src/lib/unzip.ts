import jszip from 'jszip'

export async function unzipFile(file: File): Promise<File[]> {
  const zipContent = await jszip.loadAsync(file)
  const files: File[] = []

  for (const [path, entry] of Object.entries(zipContent.files)) {
    if (entry.dir || !path.endsWith('.json')) continue
    const content = await entry.async('string')
    const filename = path.split('/').pop()!
    files.push(new File([content], filename, { type: 'application/json' }))
  }

  return files
}
