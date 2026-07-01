<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Button } from '@/components/ui/button'
import { ApiError, checkCode, donate, getConsent, type Consent, type DonationResponse } from '@/lib/api'

// Client-side mirrors of the backend limits, for early feedback only. The
// backend re-enforces them authoritatively.
const MAX_FILES = 10
const MAX_BYTES_PER_FILE = 50 * 1024 * 1024
const MAX_BYTES_PER_REQUEST = 200 * 1024 * 1024

const appVersion = typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : 'dev'

type Step = 'code' | 'form' | 'done'

const step = ref<Step>('code')

// Step 1: code.
const code = ref('')
const checking = ref(false)
const codeError = ref('')

// Step 2: consent + files.
const consent = ref<Consent | null>(null)
const consentAccepted = ref(false)
const files = ref<File[]>([])
const fileError = ref('')

// Submit.
const submitting = ref(false)
const progress = ref(0)
const submitError = ref('')
const result = ref<DonationResponse | null>(null)

async function onCheckCode() {
  const value = code.value.trim()
  codeError.value = ''
  if (!value) {
    codeError.value = 'Please enter your participant code.'
    return
  }
  checking.value = true
  try {
    const { valid } = await checkCode(value)
    if (!valid) {
      codeError.value = 'Code not recognised or already used.'
      return
    }
    consent.value = await getConsent()
    step.value = 'form'
  } catch (err) {
    codeError.value =
      err instanceof ApiError && err.status === 429
        ? 'Too many attempts. Please wait a moment and try again.'
        : 'Could not check your code. Please try again.'
  } finally {
    checking.value = false
  }
}

function onFiles(selected: File[]) {
  fileError.value = ''
  const jsonFiles = selected.filter((f) => f.name.toLowerCase().endsWith('.json'))
  if (jsonFiles.length !== selected.length) {
    fileError.value = 'Only .json files from your Spotify export are accepted.'
  }

  // Merge with anything already chosen, de-duplicating by name.
  const byName = new Map(files.value.map((f) => [f.name, f]))
  for (const f of jsonFiles) byName.set(f.name, f)
  const merged = [...byName.values()]

  if (merged.length > MAX_FILES) {
    fileError.value = `Please select at most ${MAX_FILES} files.`
    return
  }
  if (merged.some((f) => f.size > MAX_BYTES_PER_FILE)) {
    fileError.value = 'One of your files is larger than 50 MB.'
    return
  }
  if (merged.reduce((sum, f) => sum + f.size, 0) > MAX_BYTES_PER_REQUEST) {
    fileError.value = 'Your files total more than 200 MB.'
    return
  }
  files.value = merged
}

function onFileInput(event: Event) {
  const input = event.target as HTMLInputElement
  onFiles(Array.from(input.files ?? []))
  input.value = ''
}

function removeFile(name: string) {
  files.value = files.value.filter((f) => f.name !== name)
}

const canSubmit = computed(
  () => consentAccepted.value && files.value.length > 0 && !submitting.value,
)

async function onSubmit() {
  if (!canSubmit.value || !consent.value) return
  submitError.value = ''
  submitting.value = true
  progress.value = 0

  const form = new FormData()
  form.append('participant_code', code.value.trim())
  form.append('consent_version', consent.value.version)
  form.append('consent_accepted', 'true')
  form.append('app_version', appVersion)
  for (const f of files.value) form.append('files', f, f.name)

  try {
    result.value = await donate(form, (p) => (progress.value = p))
    step.value = 'done'
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      step.value = 'code'
      codeError.value = 'Your code is invalid or already used. Please re-enter it.'
    } else if (err instanceof ApiError && err.status === 409) {
      submitError.value = 'The consent form has been updated. Please reload and try again.'
    } else if (err instanceof ApiError && err.status === 413) {
      submitError.value = 'Your files are too large. Please check the size limits.'
    } else {
      submitError.value = 'Sorry, we could not receive your donation. Please try again.'
    }
  } finally {
    submitting.value = false
  }
}

defineExpose({ onFiles })
</script>

<template>
  <div class="mx-auto flex h-full w-full max-w-xl flex-col gap-6 p-8">
    <header class="flex items-center justify-between">
      <h1 class="text-lg font-semibold">Donate your Spotify data</h1>
      <RouterLink to="/">
        <Button variant="outline" size="sm">Back to Dashboard</Button>
      </RouterLink>
    </header>

    <!-- Step 1: participant code -->
    <section v-if="step === 'code'" class="flex flex-col gap-3">
      <label for="participant-code" class="text-sm font-medium">Participant code</label>
      <input
        id="participant-code"
        data-test="code-input"
        v-model="code"
        type="text"
        placeholder="e.g. MDAP-2026-001"
        class="border-input rounded-md border px-3 py-2 text-sm"
        @keyup.enter="onCheckCode"
      />
      <p v-if="codeError" data-test="code-error" class="text-destructive text-sm">
        {{ codeError }}
      </p>
      <Button data-test="check-code" :disabled="checking" @click="onCheckCode">
        {{ checking ? 'Checking…' : 'Continue' }}
      </Button>
    </section>

    <!-- Step 2: consent + files -->
    <section v-else-if="step === 'form'" class="flex flex-col gap-4">
      <div
        class="bg-muted/40 max-h-48 overflow-y-auto rounded-md border p-3 text-sm whitespace-pre-line"
      >
        {{ consent?.text }}
      </div>

      <label class="flex items-center gap-2 text-sm">
        <input data-test="consent-checkbox" v-model="consentAccepted" type="checkbox" />
        I have read and accept the consent terms.
      </label>

      <div class="flex flex-col gap-2">
        <input type="file" accept=".json" multiple @change="onFileInput" />
        <p v-if="fileError" data-test="file-error" class="text-destructive text-sm">
          {{ fileError }}
        </p>
        <ul v-if="files.length" class="text-muted-foreground text-sm">
          <li v-for="f in files" :key="f.name" class="flex items-center justify-between">
            <span>{{ f.name }}</span>
            <button type="button" class="text-destructive" @click="removeFile(f.name)">
              remove
            </button>
          </li>
        </ul>
      </div>

      <p v-if="submitting" class="text-muted-foreground text-sm">Uploading… {{ progress }}%</p>
      <p v-if="submitError" data-test="submit-error" class="text-destructive text-sm">
        {{ submitError }}
      </p>

      <Button data-test="submit-donation" :disabled="!canSubmit" @click="onSubmit">
        {{ submitting ? 'Submitting…' : 'Submit donation' }}
      </Button>
    </section>

    <!-- Step 3: done -->
    <section v-else class="flex flex-col gap-3">
      <p class="text-sm font-medium">Thank you — your data has been received.</p>
      <p class="text-muted-foreground text-sm">Reference number: {{ result?.donation_id }}</p>
      <RouterLink to="/">
        <Button variant="outline" size="sm">Back to Dashboard</Button>
      </RouterLink>
    </section>
  </div>
</template>
