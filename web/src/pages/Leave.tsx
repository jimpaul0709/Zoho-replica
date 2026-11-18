import { useState, type FormEvent } from 'react'
import { get, post, fmtRange, type S } from '../api'
import { Banner, Chip, CountUp, DateField, Empty, Loading, Select, useLoad } from '../ui'

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
      <div className="bal-cards">
        {(balances.data ?? []).map((b, i) => {
          const total = b.opening + b.accrued + b.adjusted
          return (
            <div className="card bal-card" key={b.leave_type_id} style={{ ['--i' as string]: i }}>
              <span className="hint">{b.leave_type}</span>
              <span className="big"><CountUp value={b.available} /> <small>h left</small></span>
              <div className="meter"><i style={{ width: (total > 0 ? Math.max(0, (b.available / total) * 100) : 0) + '%' }} /></div>
              <span className="hint">of {total} h (8 h = 1 day){b.pending ? ', ' + b.pending + ' pending' : ''}</span>
            </div>
          )
        })}
        {balances.data?.length === 0 && <Empty title="No leave balances yet" hint="HR sets your opening balance under HR admin, Leave setup." />}
      </div>

      <div className="grid2">
        <form className="card" onSubmit={apply}>
          <h3>Apply for leave</h3>
          {msg && <Banner kind={msg.kind}>{msg.text}</Banner>}
          <Select id="leave-type" label="Leave type" value={typeId} onChange={setTypeId} required
            options={(types.data ?? []).map((t) => ({ value: String(t.id), label: t.name }))} />
          <div className="grid2" style={{ gap: 10 }}>
            <DateField id="leave-from" label="From" value={from} onChange={(v) => { setFrom(v); if (to && to < v) setTo('') }} required />
            <DateField id="leave-to" label="To (optional)" value={to} min={from} rangeFrom={from} onChange={setTo} />
          </div>
          <label className="field"><span>Reason (optional)</span><textarea id="leave-reason" value={reason} onChange={(e) => setReason(e.target.value)} /></label>
          {hitsBlackout.length > 0 && <Banner kind="warn">{hitsBlackout.map((b) => fmtRange(b.on_date, b.on_date) + ' is a blackout day (' + b.note + ')').join('; ')}</Banner>}
          <div><button className="btn primary" type="submit">Submit request</button></div>
        </form>

        <div className="card scroll">
          <h3>My requests</h3>
          {requests.data?.length === 0 && <Empty title="No leave requests yet" hint="Use the form to ask for time off." />}
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
                    {r.status === 'applied' &&<button type="button" className="btn sm" onClick={() => change(r.id, 'withdraw')}>Withdraw</button>}
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
