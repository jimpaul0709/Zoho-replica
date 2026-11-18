import type { components } from './api-types'

export type S = components['schemas']

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const KEY = 'workhub_token'

export const token = {
  get: () => localStorage.getItem(KEY),
  set: (t: string) => localStorage.setItem(KEY, t),
  clear: () => localStorage.removeItem(KEY),
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// FastAPI sends {detail: "text"} or, for validation errors, {detail: [{msg, loc}]}.
function messageOf(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d?.msg ?? '').filter(Boolean).join('; ') || fallback
  return fallback
}

// A FormData body is sent as multipart (the browser sets the boundary); anything else as JSON.
async function raw(method: string, path: string, body?: unknown): Promise<Response> {
  const t = token.get()
  const form = body instanceof FormData
  const res = await fetch(BASE + path, {
    method,
    headers: {
      ...(body !== undefined && !form ? { 'Content-Type': 'application/json' } : {}),
      ...(t ? { Authorization: `Bearer ${t}` } : {}),
    },
    body: body === undefined ? undefined : form ? body : JSON.stringify(body),
  }).catch(() => {
    throw new ApiError(0, 'Cannot reach the server. Check that the API is running.')
  })
  if (res.status === 401 && path !== '/auth/login') {
    token.clear()
    window.dispatchEvent(new Event('workhub-signed-out'))
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new ApiError(res.status, messageOf(data.detail, res.statusText))
  }
  return res
}

export async function api<T = unknown>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await raw(method, path, body)
  return (res.status === 204 ? undefined : await res.json()) as T
}

// Fetch a protected file (needs the Bearer token, so a plain link will not work) and save it.
export async function saveFile(path: string, filename: string) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(await (await raw('GET', path)).blob())
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}

export const get = <T,>(path: string) => api<T>('GET', path)
export const post = <T,>(path: string, body?: unknown) => api<T>('POST', path, body)

// The API counts minutes; the screens show decimal hours (4.5).
export const toHours = (minutes: number) => Math.round((minutes / 60) * 100) / 100
export const toMinutes = (hours: number) => Math.round(hours * 60)

// Local-date helpers (toISOString would shift the day for people east of UTC).
export const iso = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
export const parseDate = (s: string) => {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}
export const addDays = (s: string, n: number) => {
  const d = parseDate(s)
  d.setDate(d.getDate() + n)
  return iso(d)
}
export const mondayOf = (d: Date) => {
  const x = new Date(d)
  x.setDate(x.getDate() - ((x.getDay() + 6) % 7))
  return iso(x)
}
export const fmtDay = (s: string, opts: Intl.DateTimeFormatOptions = { weekday: 'short', day: 'numeric' }) =>
  parseDate(s).toLocaleDateString('en-GB', opts)
export const fmtRange = (a: string, b: string) =>
  `${fmtDay(a, { day: 'numeric', month: 'short' })} – ${fmtDay(b, { day: 'numeric', month: 'short', year: 'numeric' })}`
