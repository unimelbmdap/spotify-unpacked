import { describe, it, expect } from 'vitest'

import { mount } from '@vue/test-utils'
import router from '@/router'
import App from '../App.vue'

describe('App', () => {
  it('mounts without error', async () => {
    // AppHeader uses RouterLink + $route, so a real router is needed; RouterView
    // is stubbed so we don't render the heavy dashboard/charts in jsdom.
    router.push('/')
    await router.isReady()
    const wrapper = mount(App, {
      global: { plugins: [router], stubs: { RouterView: true } },
    })
    expect(wrapper.exists()).toBe(true)
  })
})
