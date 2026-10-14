type FastAPIError = { response?: { data?: { detail?: unknown } } }

export function parseApiError(ex: unknown): string {
  const detail = (ex as FastAPIError)?.response?.data?.detail

  if (!detail) return 'Request failed. Is the backend running?'

  // FastAPI validation errors come as an array of {msg, loc} objects
  if (Array.isArray(detail)) {
    return detail.map((e: { msg?: string }) => e.msg ?? String(e)).join(' · ')
  }

  if (typeof detail === 'string') return detail

  return JSON.stringify(detail)
}
