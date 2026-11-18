import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type ReactNode, type RefObject } from 'react'
import { get, type S } from './api'

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
