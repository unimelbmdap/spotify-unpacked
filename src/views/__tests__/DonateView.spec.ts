import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('@/lib/api', () => {
  class ApiError extends Error {
    status: number
    constructor(status: number, message: string) {
      super(message)
      this.status = status
    }
  }
  return {
    ApiError,
    checkCode: vi.fn(),
    getConsent: vi.fn(),
    donate: vi.fn(),
  }
})

import DonateView from '../DonateView.vue'
import * as api from '@/lib/api'

const mountView = () => mount(DonateView, { global: { stubs: { RouterLink: true } } })

async function advanceToFormStep(wrapper: ReturnType<typeof mountView>) {
  await wrapper.find('[data-test="code-input"]').setValue('MDAP-2026-001')
  await wrapper.find('[data-test="check-code"]').trigger('click')
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getConsent).mockResolvedValue({ version: 'v1.0', text: 'CONSENT TEXT' })
})

describe('DonateView', () => {
  it('advances to the consent + files step when the code is valid', async () => {
    vi.mocked(api.checkCode).mockResolvedValue({ valid: true })
    const wrapper = mountView()

    await advanceToFormStep(wrapper)

    expect(api.checkCode).toHaveBeenCalledWith('MDAP-2026-001')
    expect(wrapper.text()).toContain('CONSENT TEXT')
  })

  it('shows an error and stays on the code step for an invalid code', async () => {
    vi.mocked(api.checkCode).mockResolvedValue({ valid: false })
    const wrapper = mountView()

    await advanceToFormStep(wrapper)

    expect(wrapper.text()).toContain('not recognised')
    expect(wrapper.text()).not.toContain('CONSENT TEXT')
  })

  it('shows a success message with the donation id after a successful submit', async () => {
    vi.mocked(api.checkCode).mockResolvedValue({ valid: true })
    vi.mocked(api.donate).mockResolvedValue({ donation_id: 42, results: [] })
    const wrapper = mountView()

    await advanceToFormStep(wrapper)
    wrapper.vm.onFiles([new File(['{}'], 'StreamingHistory.json', { type: 'application/json' })])
    await wrapper.find('[data-test="consent-checkbox"]').setValue(true)
    await wrapper.find('[data-test="submit-donation"]').trigger('click')
    await flushPromises()

    expect(api.donate).toHaveBeenCalled()
    expect(wrapper.text()).toContain('42')
  })

  it('returns to the code step when the submit is rejected as 401', async () => {
    vi.mocked(api.checkCode).mockResolvedValue({ valid: true })
    vi.mocked(api.donate).mockRejectedValue(new api.ApiError(401, 'invalid'))
    const wrapper = mountView()

    await advanceToFormStep(wrapper)
    wrapper.vm.onFiles([new File(['{}'], 'StreamingHistory.json', { type: 'application/json' })])
    await wrapper.find('[data-test="consent-checkbox"]').setValue(true)
    await wrapper.find('[data-test="submit-donation"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="code-input"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('invalid or already used')
  })
})
