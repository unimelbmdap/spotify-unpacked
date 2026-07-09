import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/lib/api', () => {
  class ApiError extends Error {
    status: number
    constructor(status: number, message: string) {
      super(message)
      this.status = status
    }
  }
  return { ApiError, checkCode: vi.fn(), getConsent: vi.fn(), donate: vi.fn() }
})

import DonateView from '../DonateView.vue'
import * as api from '@/lib/api'
import { useDataStore } from '@/stores/data'

const mountView = () => mount(DonateView, { global: { stubs: { RouterLink: true } } })

async function advanceToFormStep(wrapper: ReturnType<typeof mountView>) {
  await wrapper.find('[data-test="code-input"]').setValue('MDAP-2026-001')
  await wrapper.find('[data-test="check-code"]').trigger('click')
  await flushPromises()
}

const streamingFile = () =>
  new File(
    [
      JSON.stringify([
        {
          ts: '2025-07-01T10:00:00Z',
          platform: 'ios',
          ms_played: 1000,
          master_metadata_track_name: 'Song',
          master_metadata_album_artist_name: 'Artist',
          master_metadata_album_album_name: 'Album',
          spotify_track_uri: 'spotify:track:1',
          reason_start: 'trackdone',
          reason_end: 'trackdone',
          shuffle: false,
          skipped: false,
        },
      ]),
    ],
    'Streaming_History_audio_2025.json',
    { type: 'application/json' },
  )

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  vi.mocked(api.getConsent).mockResolvedValue({ version: 'v1.0', text: 'CONSENT TEXT' })
})

describe('DonateView', () => {
  it('advances to the consent step when the code is valid', async () => {
    vi.mocked(api.checkCode).mockResolvedValue({ valid: true })
    const wrapper = mountView()
    await advanceToFormStep(wrapper)
    expect(wrapper.text()).toContain('CONSENT TEXT')
  })

  it('cannot submit when the store has no donatable data', async () => {
    vi.mocked(api.checkCode).mockResolvedValue({ valid: true })
    const wrapper = mountView()
    await advanceToFormStep(wrapper)
    await wrapper.find('[data-test="consent-checkbox"]').setValue(true)
    expect(wrapper.find('[data-test="submit-donation"]').attributes('disabled')).toBeDefined()
  })

  it('donates only reconstructed files built from the store', async () => {
    vi.mocked(api.checkCode).mockResolvedValue({ valid: true })
    vi.mocked(api.donate).mockResolvedValue({ donation_id: 42, results: [] })
    const store = useDataStore()
    await store.loadFiles([streamingFile()])

    const wrapper = mountView()
    await advanceToFormStep(wrapper)
    await wrapper.find('[data-test="consent-checkbox"]').setValue(true)
    await wrapper.find('[data-test="submit-donation"]').trigger('click')
    await flushPromises()

    expect(api.donate).toHaveBeenCalled()
    const form = vi.mocked(api.donate).mock.calls[0]?.[0] as FormData
    const donated = form.getAll('files') as File[]
    expect(donated.map((f) => f.name)).toEqual(['streaming_history.json'])
    expect(wrapper.text()).toContain('42')
  })

  it('prompts to load data on the dashboard when the store has no data', async () => {
    vi.mocked(api.checkCode).mockResolvedValue({ valid: true })
    const wrapper = mountView()
    await advanceToFormStep(wrapper)
    // No store data: prompt back to the dashboard, no file picker, no summary, submit disabled.
    expect(wrapper.find('[data-test="donation-summary"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="no-data"]').exists()).toBe(true)
    expect(wrapper.find('input[type="file"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="submit-donation"]').attributes('disabled')).toBeDefined()
  })
})
