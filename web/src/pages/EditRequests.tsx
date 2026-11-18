import { useState } from 'react'
import { get, post, fmtDay, toHours, toMinutes, type S } from '../api'
import { Banner, Chip, useLoad } from '../ui'

type Entry = S['EntryOut']

// Ask for changes to an approved (locked) week, and follow the requests already filed.
// shortcut: only update/delete of existing entries; adding new entries is not offered here.
export default function EditRequests({ weekStart, entries, nameOf }: { weekStart: string; entries: Entry[]; nameOf: (e: Entry) => string }) {
  const mine = useLoad(() => get<S['EditRequestOut'][]>('/time/edit-requests'), [])
  const [reason, setReason] = useState('')
  const [hours, setHours] = useState<Record<number, string>>({}) // entry id -> new hours ('' = unchanged, 0 = delete)
  const [err, setErr] = useState('')
  const editable = entries.filter((e) => e.source !== 'leave' && e.source !== 'holiday')
  const changes = editable.filter((e) => (hours[e.id] ?? '') !== '').map((e) => {
    const m = toMinutes(Number(hours[e.id]))
    return m === 0 ? { op: 'delete' as const, entry_id: e.id } : { op: 'update' as const, entry_id: e.id, minutes: m }
  })
  const bad = Object.values(hours).some((h) => h !== '' && !(Number(h) >= 0 && Number(h) <= 24))

  async function act(fn: () => Promise<unknown>) {
    try { setErr(''); await fn(); mine.reload() } catch (e) { setErr((e as Error).message) }
  }
  const send = () => act(async () => {
    await post('/time/weeks/' + weekStart + '/edit-requests', { reason, changes })
    setReason(''); setHours({})
  })

  return (
    <div className="card">
      <h3>Request a change to this week</h3>
      {err && <Banner kind="bad">{err}</Banner>}
      {editable.map((e) => (
        <label className="field" key={e.id}>
          <span>{fmtDay(e.work_date)} · {nameOf(e)} · now {toHours(e.minutes)} h. New hours (0 removes it)</span>
          <input type="text" inputMode="decimal" value={hours[e.id] ?? ''} onChange={(ev) => setHours({ ...hours, [e.id]: ev.target.value })} />
        </label>
      ))}
      <label className="field"><span>Reason</span><textarea value={reason} onChange={(e) => setReason(e.target.value)} /></label>
      <div><button type="button" className="btn primary" disabled={!reason.trim() || changes.length === 0 || bad} onClick={send}>Send edit request</button></div>

      {(mine.data ?? []).length > 0 && <h3>My edit requests</h3>}
      {(mine.data ?? []).map((r) => (
        <div className="row" key={r.id}>
          <span>Week of {fmtDay(r.week_start, { day: 'numeric', month: 'short' })} · {r.reason} · {r.changes.length} change{r.changes.length === 1 ? '' : 's'}</span>
          <Chip status={r.status} />
          {r.status === 'pending' && <button type="button" className="btn sm" onClick={() => act(() => post('/time/edit-requests/' + r.id + '/cancel'))}>Cancel</button>}
        </div>
      ))}
    </div>
  )
}
