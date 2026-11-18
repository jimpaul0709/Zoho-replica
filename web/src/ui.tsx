import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type ReactNode, type RefObject } from 'react'
import { get, iso, parseDate, fmtDay, type S } from './api'

// Load data from the API; `reload()` refetches after a change.
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T>()
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fn, deps)
  const reload = useCallback(() => {
    setLoading(true)
    run().then((d) => { setData(d); setError('') }, (e: Error) => setError(e.message)).finally(() => setLoading(false))
  }, [run])
  useEffect(reload, [reload])
  return { data, error, loading, reload }
}

export function useHash() {
  const [hash, setHash] = useState(location.hash.slice(1))
  useEffect(() => {
    const on = () => setHash(location.hash.slice(1))
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return hash
}

export function Banner({ kind = 'info', children }: { kind?: 'info' | 'ok' | 'warn' | 'bad'; children: ReactNode }) {
  return <div className={`banner ${kind}`} role={kind === 'bad' ? 'alert' : 'status'}>{children}</div>
}

const TONE: Record<string, string> = {
  approved: 'ok', published: 'ok', active: 'ok',
  submitted: 'warn', pending: 'warn', waiting: 'warn', requested: 'warn', applied: 'warn',
  sent_back: 'bad', rejected: 'bad', declined: 'bad', cancelled: 'bad', withdrawn: 'bad',
}
export function Chip({ status }: { status: string }) {
  return <span className={`chip ${TONE[status] ?? ''}`}>{status.replace(/_/g, ' ')}</span>
}

export function Loading({ error, loading }: { error: string; loading: boolean }) {
  if (error) return <Banner kind="bad">{error}</Banner>
  return loading ? <div className="skeleton" aria-busy="true" aria-label="Loading"><i /><i /><i /></div> : null
}

export function Empty({ title, hint }: { title: string; hint: string }) {
  return <div className="empty"><b>{title}</b><span className="hint">{hint}</span></div>
}

export const initials = (name: string) => name.split(/\s+/).map((w) => w[0]).join('').slice(0, 2).toUpperCase()

// Run `close` on a click outside `ref` while `open`.
export function useDismiss(ref: RefObject<HTMLElement | null>, open: boolean, close: () => void) {
  useEffect(() => {
    if (!open) return
    const on = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) close() }
    document.addEventListener('mousedown', on)
    return () => document.removeEventListener('mousedown', on)
  }, [ref, open, close])
}

export type Opt = { value: string; label: string; sub?: string }

// Dropdown that replaces the native <select>: styled list, type-to-search past 7 options, arrow keys, Enter, Escape.
export function Select({ id, label, ariaLabel, value, onChange, options, placeholder = 'Choose…', required, className = '' }: {
  id: string; label?: string; ariaLabel?: string; value: string; onChange: (v: string) => void
  options: Opt[]; placeholder?: string; required?: boolean; className?: string
}) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [active, setActive] = useState(0)
  const root = useRef<HTMLDivElement>(null)
  const btn = useRef<HTMLButtonElement>(null)
  const list = useRef<HTMLUListElement>(null)
  const searchable = options.length > 7
  const shown = options.filter((o) => (o.label + ' ' + (o.sub ?? '')).toLowerCase().includes(q.trim().toLowerCase()))
  const cur = options.find((o) => o.value === value)
  const close = useCallback(() => { setOpen(false); setQ('') }, [])
  useDismiss(root, open, close)
  useEffect(() => { if (open && !searchable) list.current?.focus() }, [open, searchable])

  const show = () => { setActive(Math.max(0, shown.findIndex((o) => o.value === value))); setOpen(true) }
  const pick = (o?: Opt) => { if (o) onChange(o.value); close(); btn.current?.focus() }
  const key = (e: KeyboardEvent) => {
    if (!open) { if (e.key === 'ArrowDown') { e.preventDefault(); show() } return }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => Math.min(Math.max(a + (e.key === 'ArrowDown' ? 1 : -1), 0), shown.length - 1))
    } else if (e.key === 'Enter') { e.preventDefault(); pick(shown[active]) }
    else if (e.key === 'Escape') { e.preventDefault(); close(); btn.current?.focus() }
  }
  useEffect(() => { document.getElementById(`${id}-o${active}`)?.scrollIntoView({ block: 'nearest' }) }, [id, active, open])

  return (
    <div className={`field sel ${className}`} ref={root} onKeyDown={key}>
      {label && <span id={`${id}-l`}>{label}</span>}
      <button type="button" id={id} ref={btn} className="sel-btn" aria-haspopup="listbox" aria-expanded={open} aria-label={ariaLabel}
        aria-labelledby={label ? `${id}-l ${id}` : undefined} onClick={() => (open ? close() : show())}>
        <span className={cur ? 'sel-val' : 'sel-ph'}>{cur ? cur.label : placeholder}</span>
        <svg className="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
      </button>
      {required && <input className="sel-req" tabIndex={-1} aria-hidden="true" value={value} onChange={() => {}} required />}
      {open && (
        <div className="sel-pop">
          {searchable && <input className="sel-q" type="text" placeholder="Search…" aria-label="Search options" autoFocus value={q}
            onChange={(e) => { setQ(e.target.value); setActive(0) }} />}
          <ul role="listbox" ref={list} tabIndex={-1} aria-label={label ?? ariaLabel} aria-activedescendant={shown[active] ? `${id}-o${active}` : undefined}>
            {shown.map((o, i) => (
              <li key={o.value} id={`${id}-o${i}`} role="option" aria-selected={o.value === value} className={i === active ? 'on' : ''}
                onMouseEnter={() => setActive(i)} onClick={() => pick(o)}>
                <span>{o.label}</span>{o.sub && <span className="hint">{o.sub}</span>}
              </li>
            ))}
            {shown.length === 0 && <li className="sel-none" role="presentation">No matches</li>}
          </ul>
        </div>
      )}
    </div>
  )
}

// Name dropdown over active users; `value` is the user id as text ('' = none chosen).
export function UserSelect({ id, label, value, onChange }: { id: string; label: string; value: string; onChange: (v: string) => void }) {
  const users = useLoad(() => get<S['UserPick'][]>('/users'), [])
  return (
    <Select id={id} label={label} value={value} onChange={onChange}
      placeholder={users.error ? 'Could not load users' : users.loading ? 'Loading…' : 'Choose…'}
      options={(users.data ?? []).map((u) => ({ value: String(u.id), label: u.name, sub: u.email }))} />
  )
}

// Date picker that replaces <input type="date">. Values are yyyy-mm-dd. `rangeFrom` shades the days between it and the value.
export function DateField({ id, label, value, onChange, min, rangeFrom, required }: {
  id: string; label: string; value: string; onChange: (v: string) => void; min?: string; rangeFrom?: string; required?: boolean
}) {
  const [open, setOpen] = useState(false)
  const first = (s: string) => { const d = parseDate(s || min || iso(new Date())); d.setDate(1); return d }
  const [view, setView] = useState(() => first(value))
  const root = useRef<HTMLDivElement>(null)
  const close = useCallback(() => setOpen(false), [])
  useDismiss(root, open, close)
  const today = iso(new Date())
  const lead = (view.getDay() + 6) % 7
  const cells = Array.from({ length: 42 }, (_, i) => { const d = new Date(view); d.setDate(1 - lead + i); return iso(d) })
  const step = (n: number) => setView(new Date(view.getFullYear(), view.getMonth() + n, 1))
  const pick = (d: string) => { onChange(d); setOpen(false) }
  return (
    <div className="field sel" ref={root} onKeyDown={(e) => { if (e.key === 'Escape') setOpen(false) }}>
      <span id={`${id}-l`}>{label}</span>
      <button type="button" id={id} className="sel-btn" aria-haspopup="dialog" aria-expanded={open} aria-labelledby={`${id}-l ${id}`}
        onClick={() => { setView(first(value)); setOpen(!open) }}>
        <span className={value ? 'sel-val' : 'sel-ph'}>{value ? fmtDay(value, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }) : 'Pick a date'}</span>
        <svg className="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 8a3 3 0 013-3h12a3 3 0 013 3v10a3 3 0 01-3 3H6a3 3 0 01-3-3zM8 3v4M16 3v4M3 10h18" /></svg>
      </button>
      {required && <input className="sel-req" tabIndex={-1} aria-hidden="true" value={value} onChange={() => {}} required />}
      {open && (
        <div className="sel-pop cal-pop" role="dialog" aria-label={label}>
          <div className="cal-head">
            <button type="button" className="btn sm" aria-label="Previous month" onClick={() => step(-1)}>‹</button>
            <b>{view.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })}</b>
            <button type="button" className="btn sm" aria-label="Next month" onClick={() => step(1)}>›</button>
          </div>
          <div className="cal-grid">
            {'MTWTFSS'.split('').map((w, i) => <span key={i} className="hint cal-w">{w}</span>)}
            {cells.map((d) => {
              const off = d.slice(0, 7) !== iso(view).slice(0, 7)
              const lo = rangeFrom && value ? (rangeFrom < value ? rangeFrom : value) : ''
              const hi = rangeFrom && value ? (rangeFrom < value ? value : rangeFrom) : ''
              const cls = (off ? ' off' : '') + (d === value ? ' sel' : '') + (d === today ? ' today' : '') + (lo && d >= lo && d <= hi && d !== value ? ' mid' : '')
              return <button key={d} type="button" className={'cal-d' + cls} disabled={!!min && d < min} aria-pressed={d === value} aria-label={fmtDay(d, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })} onClick={() => pick(d)}>{Number(d.slice(8))}</button>
            })}
          </div>
          <div className="cal-foot">
            <button type="button" className="btn sm" onClick={() => pick(today)} disabled={!!min && today < min}>Today</button>
            {!required && value && <button type="button" className="btn sm" onClick={() => pick('')}>Clear</button>}
          </div>
        </div>
      )}
    </div>
  )
}

const THEME_KEY = 'wh-theme'
try { const s = localStorage.getItem(THEME_KEY); if (s) document.documentElement.dataset.theme = s } catch { /* storage blocked: follow the system */ }

// Sun/moon button. No saved choice means the page follows the system theme.
export function ThemeToggle() {
  const now = () => document.documentElement.dataset.theme ?? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  const [dark, setDark] = useState(() => now() === 'dark')
  const flip = () => {
    const next = dark ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    try { localStorage.setItem(THEME_KEY, next) } catch { /* storage blocked: applies for this visit only */ }
    setDark(!dark)
  }
  const label = dark ? 'Switch to light theme' : 'Switch to dark theme'
  return (
    <button type="button" className="icon-btn" aria-label={label} title={label} onClick={flip}>
      <svg className="i" viewBox="0 0 24 24" aria-hidden="true">
        <path d={dark ? 'M12 8a4 4 0 100 8 4 4 0 000-8M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4' : 'M20 14.5A8 8 0 019.5 4 8 8 0 1020 14.5z'} />
      </svg>
    </button>
  )
}
