// Thin client for the donation backend. Base URL comes from VITE_API_BASE_URL
// (set per environment); in dev it defaults to the local FastAPI server.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export interface CodeCheck {
  valid: boolean
}

export interface Consent {
  version: string
  text: string
}

export interface DonateResult {
  filename: string
  asset_id: string | null
  status: string
  detail?: string
}

export interface DonationResponse {
  donation_id: number
  results: DonateResult[]
}

/** Error carrying the HTTP status so callers can map it to a message. */
export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function detailOf(res: Response): Promise<string> {
  try {
    const body = await res.json()
    return typeof body?.detail === 'string' ? body.detail : res.statusText
  } catch {
    return res.statusText
  }
}

/** Up-front, read-only check that a participant code can currently be used. */
export async function checkCode(code: string): Promise<CodeCheck> {
  const res = await fetch(`${BASE_URL}/api/codes/${encodeURIComponent(code)}`)
  if (!res.ok) {
    throw new ApiError(res.status, await detailOf(res))
  }
  return res.json()
}

/** Fetch the current consent text and version to display before donating. */
export async function getConsent(): Promise<Consent> {
  const res = await fetch(`${BASE_URL}/api/consent`)
  if (!res.ok) {
    throw new ApiError(res.status, await detailOf(res))
  }
  return res.json()
}

/**
 * Submit a donation. Uses XMLHttpRequest (not fetch) so we can report upload
 * progress for potentially large exports. Rejects with an ApiError carrying
 * the HTTP status on any non-2xx response.
 */
export function donate(
  form: FormData,
  onProgress?: (percent: number) => void,
): Promise<DonationResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${BASE_URL}/api/donate`)

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    }

    xhr.onload = () => {
      let body: unknown = null
      try {
        body = JSON.parse(xhr.responseText)
      } catch {
        body = null
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(body as DonationResponse)
      } else {
        const detail =
          body && typeof body === 'object' && 'detail' in body
            ? String((body as { detail: unknown }).detail)
            : 'Donation failed'
        reject(new ApiError(xhr.status, detail))
      }
    }

    xhr.onerror = () => reject(new ApiError(0, 'Network error'))
    xhr.send(form)
  })
}
