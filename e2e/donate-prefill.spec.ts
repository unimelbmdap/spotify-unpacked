import { test, expect } from '@playwright/test'

const streaming = JSON.stringify([
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
])

test('data loaded on the dashboard is offered for donation without re-selecting files', async ({ page }) => {
  // Mock the donation backend.
  await page.route('**/api/codes/validate', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ valid: true }) }),
  )
  await page.route('**/api/donate', (route) =>
    route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ donation_id: 7, results: [] }) }),
  )

  await page.goto('/')

  // Load a file on the dashboard via the first hidden file input (the dashboard
  // renders two: DataPanel's FileDropZone and UploadPanel).
  await page.locator('input[type="file"]').first().setInputFiles({
    name: 'Streaming_History_audio_2025.json',
    mimeType: 'application/json',
    buffer: Buffer.from(streaming),
  })

  // Go to donate; the loaded data should be pre-offered.
  // Navigate WITHIN the SPA via the in-app link (ControlsPanel's "Donate Your Data"
  // RouterLink). A full page.goto('/donate') would reload the app and wipe the
  // in-memory store, which is exactly the reload-fallback case, not this one.
  await page.getByRole('link', { name: 'Donate Your Data' }).click()
  await expect(page).toHaveURL(/\/donate$/)
  await page.fill('[data-test="code-input"]', 'MDAP-2026-001')
  await page.click('[data-test="check-code"]')
  await expect(page.locator('[data-test="donation-summary"]')).toContainText('1 plays')

  await page.check('[data-test="consent-checkbox"]')
  await page.click('[data-test="submit-donation"]')
  await expect(page.getByText('Reference number: 7')).toBeVisible()
})
