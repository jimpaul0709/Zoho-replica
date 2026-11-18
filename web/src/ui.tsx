import { useCallback, useEffect, useState, type ReactNode } from 'react'
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

// Name dropdown over active users; `value` is the user id as text ('' = none chosen).
export function UserSelect({ id, label, value, onChange }: { id: string; label: string; value: string; onChange: (v: string) => void }) {
  const users = useLoad(() => get<S['UserPick'][]>('/users'), [])
  return (
    <label className="field"><span>{label}</span>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{users.error ? 'Could not load users' : users.loading ? 'Loading…' : 'Choose…'}</option>
        {(users.data ?? []).map((u) => <option key={u.id} value={u.id}>{u.name} · {u.email}</option>)}
      </select>
    </label>
  )
}
