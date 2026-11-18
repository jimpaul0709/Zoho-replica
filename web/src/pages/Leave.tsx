import { useState, type FormEvent } from 'react'
import { get, post, fmtRange, type S } from '../api'
import { Banner, Chip, Loading, useLoad } from '../ui'

export default function Leave() {
  const year = new Date().getFullYear()
  const balances = useLoad(() => get<S['BalanceOut'][]>('/leave/balances?year=' + year), [])
  const types = useLoad(() => get<S['TypeOut'][]>('/leave/types'), [])
  const requests = useLoad(() => get<S['LeaveOut'][]>('/leave/requests'), [])
  const blackout = useLoad(() => get<S['BlackoutOut'][]>('/leave/blackout-days'), [])
  const [typeId, setTypeId] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [reason, setReason] = useState('')
  const [msg, setMsg] = useState<{ kind: 'ok' | 'bad'; text: string }>()

  const typeName = (id: number) => types.data?.find((t) => t.id === id)?.name ?? 'Leave'
  const hitsBlackout = (blackout.data ?? []).filter((b) => from && b.on_date >= from && b.on_date <= (to || from))

  async function apply(e: FormEvent) {
    e.preventDefault()
    try {
      await post('/leave/requests', { leave_type_id: Number(typeId), from_date: from, to_date: to || from, reason: reason || null })
      setMsg({ kind: 'ok', text: 'Leave request sent to your manager.' })
      setFrom(''); setTo(''); setReason('')
      requests.reload(); balances.reload()
    } catch (err) {
      setMsg({ kind: 'bad', text: (err as Error).message })
    }
  }
  const change = async (id: number, action: 'withdraw' | 'cancel') => {
    try {
      await post('/leave/requests/' + id + '/' + action)
      requests.reload(); balances.reload()
    } catch (err) {
      setMsg({ kind: 'bad', text: (err as Error).message })
    }
  }

  return (
    <section style={{ display: 'grid', gap: 18 }}>
      <div className="head"><h2>Leave</h2></div>
      <Loading error={balances.error || types.error || requests.error} loading={balances.loading && !balances.data} />
      <div className="grid4">
        {(balances.data ?? []).map((b) => {
          const total = b.opening + b.accrued + b.adjusted
          return (
            <div className="card" key={b.leave_type_id}>
              <span className="hint">{b.leave_type}</span>
              <div className="ringrow">
                <div className="ring" style={{ ['--p' as string]: total > 0 ? Math.max(0, (b.available / total) * 100) : 0 }}><b>{b.available}</b></div>
                <span className="hint">days left<br />{b.used} used{b.pending ? ', ' + b.pending + ' pending' : ''}</span>
              </div>
            </div>
          )
        })}
        {balances.data?.length === 0 && <div className="hint">No balances yet. HR sets opening balances.</div>}
      </div>

      <div className="grid2">
        <form className="card" onSubmit={apply}>
          <h3>Apply for leave</h3>
          {msg && <Banner kind={msg.kind}>{msg.text}</Banner>}
          <label className="field"><span>Leave type</span>
            <select id="leave-type" value={typeId} onChange={(e) => setTypeId(e.target.value)} required>
              <option value="">Choose…</option>
              {(types.data ?? []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select></label>
          <div className="grid2" style={{ gap: 10 }}>
            <label className="field"><span>From</span><input id="leave-from" type="date" value={from} onChange={(e) => setFrom(e.target.value)} required /></label>
            <label className="field"><span>To</span><input id="leave-to" type="date" value={to} min={from} onChange={(e) => setTo(e.target.value)} /></label>
          </div>
          <label className="field"><span>Reason (optional)</span><textarea id="leave-reason" value={reason} onChange={(e) => setReason(e.target.value)} /></label>
          {hitsBlackout.length > 0 && <Banner kind="warn">{hitsBlackout.map((b) => fmtRange(b.on_date, b.on_date) + ' is a blackout day (' + b.note + ')').join('; ')}</Banner>}
          <div><button className="btn primary" type="submit">Submit request</button></div>
        </form>

        <div className="card scroll">
          <h3>My requests</h3>
          {requests.data?.length === 0 && <div className="hint">No leave requests yet.</div>}
          <table>
            <thead><tr><th>Type</th><th>Dates</th><th className="num">Hours</th><th>Status</th><th /></tr></thead>
            <tbody>
              {(requests.data ?? []).map((r) => (
                <tr key={r.id}>
                  <td>{typeName(r.leave_type_id)}</td>
                  <td>{fmtRange(r.from_date, r.to_date)}</td>
                  <td className="num">{r.hours}</td>
                  <td><Chip status={r.status} /></td>
                  <td>
                    {r.status === 'pending' && <button type="button" className="btn sm" onClick={() => change(r.id, 'withdraw')}>Withdraw</button>}
                    {r.status === 'approved' && <button type="button" className="btn sm" onClick={() => change(r.id, 'cancel')}>Cancel</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
