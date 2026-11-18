import { useState } from 'react'
import { get, post, api, addDays, mondayOf, type S } from '../api'
import { Banner, Loading, useLoad } from '../ui'

type Msg = { kind: 'ok' | 'bad'; text: string } | undefined

// Runs an API call and reports the result in one place.
function useAction() {
  const [msg, setMsg] = useState<Msg>()
  const run = async (fn: () => Promise<unknown>, done: string) => {
    try {
      await fn()
      setMsg({ kind: 'ok', text: done })
      return true
    } catch (e) {
      setMsg({ kind: 'bad', text: (e as Error).message })
      return false
    }
  }
  return { msg, run }
}

export default function Hr() {
  const [tab, setTab] = useState<'time' | 'leave' | 'pay'>('time')
  return (
    <section style={{ display: 'grid', gap: 18 }}>
      <div className="head"><h2>HR admin</h2></div>
      <div className="tabs" role="tablist">
        {([['time', 'Time corrections'], ['leave', 'Leave setup'], ['pay', 'Payslip batch']] as const).map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)}>{label}</button>
        ))}
      </div>
      {tab === 'time' && <TimeCorrections />}
      {tab === 'leave' && <LeaveSetup />}
      {tab === 'pay' && <Banner>Payslip upload and publish are not built yet.</Banner>}
    </section>
  )
}

function TimeCorrections() {
  const { msg, run } = useAction()
  const [userId, setUserId] = useState('')
  const [week, setWeek] = useState(mondayOf(new Date(Date.now() - 7 * 864e5)))
  const [reason, setReason] = useState('')
  const [entryId, setEntryId] = useState('')
  const [minutes, setMinutes] = useState('')
  const ready = userId && reason.trim()
  const url = '/hr/users/' + userId + '/weeks/' + week

  return (
    <div className="card">
      {msg && <Banner kind={msg.kind}>{msg.text}</Banner>}
      <div className="grid3">
        <label className="field"><span>Employee (user id)</span><input id="hr-user" type="text" inputMode="numeric" value={userId} onChange={(e) => setUserId(e.target.value)} /></label>
        <label className="field"><span>Week starting (Monday)</span><input id="hr-week" type="date" value={week} onChange={(e) => setWeek(mondayOf(new Date(e.target.value + 'T00:00')))} /></label>
      </div>
      <label className="field"><span>Reason (kept in the audit log, the employee sees it)</span><textarea id="hr-reason" value={reason} onChange={(e) => setReason(e.target.value)} /></label>
      <div className="grid3">
        <label className="field"><span>Entry id to change</span><input id="hr-entry" type="text" inputMode="numeric" value={entryId} onChange={(e) => setEntryId(e.target.value)} /></label>
        <label className="field"><span>New hours (0 removes it)</span><input id="hr-hours" type="text" inputMode="decimal" value={minutes} onChange={(e) => setMinutes(e.target.value)} /></label>
      </div>
      <div className="actions">
        <button type="button" className="btn primary" disabled={!ready || !entryId || minutes === ''}
          onClick={() => run(() => {
            const m = Math.round(Number(minutes) * 60)
            const change = m === 0 ? { op: 'delete', entry_id: Number(entryId) } : { op: 'update', entry_id: Number(entryId), minutes: m }
            return post(url + '/corrections', { reason, changes: [change] })
          }, 'Correction saved')}>Save correction</button>
        <button type="button" className="btn danger" disabled={!ready}
          onClick={() => run(() => post(url + '/send-back', { reason }), 'Week sent back to ' + week)}>Send week back to employee</button>
      </div>
      <div className="hint">Find entry ids in the employee's week. Adding new entries is not on this screen yet.</div>
    </div>
  )
}

function LeaveSetup() {
  const { msg, run } = useAction()
  const year = new Date().getFullYear()
  const types = useLoad(() => get<S['TypeOut'][]>('/leave/types'), [])
  const targets = useLoad(() => get<S['TargetsOut']>('/time/targets'), [])
  const blackout = useLoad(() => get<S['BlackoutOut'][]>('/leave/blackout-days'), [])
  const [t, setT] = useState({ name: '', paid: true, charge_code_id: '', accrual: '', cap: '' })
  const [b, setB] = useState({ user_id: '', leave_type_id: '', opening: '' })
  const [day, setDay] = useState({ on_date: '', note: '' })

  return (
    <div className="grid2">
      {msg && <div style={{ gridColumn: '1 / -1' }}><Banner kind={msg.kind}>{msg.text}</Banner></div>}
      <Loading error={types.error || targets.error || blackout.error} loading={false} />
      <div className="card">
        <h3>Leave types</h3>
        {(types.data ?? []).map((x) => <div key={x.id}>{x.name}{x.paid === false ? ' (unpaid)' : ''}</div>)}
        <label className="field"><span>Name</span><input id="lt-name" type="text" value={t.name} onChange={(e) => setT({ ...t, name: e.target.value })} /></label>
        <label className="field"><span>Charge code for this leave</span>
          <select id="lt-code" value={t.charge_code_id} onChange={(e) => setT({ ...t, charge_code_id: e.target.value })}>
            <option value="">Choose…</option>
            {(targets.data?.charge_codes ?? []).map((c) => <option key={c.id} value={c.id}>{c.code} · {c.name}</option>)}
          </select></label>
        <div className="grid3">
          <label className="field"><span>Days added per month</span><input id="lt-accrual" type="text" inputMode="decimal" value={t.accrual} onChange={(e) => setT({ ...t, accrual: e.target.value })} /></label>
          <label className="field"><span>Carry forward cap (days)</span><input id="lt-cap" type="text" inputMode="decimal" value={t.cap} onChange={(e) => setT({ ...t, cap: e.target.value })} /></label>
        </div>
        <label className="row"><input type="checkbox" checked={t.paid} onChange={(e) => setT({ ...t, paid: e.target.checked })} /> Paid leave</label>
        <div><button type="button" className="btn primary" disabled={!t.name || !t.charge_code_id}
          onClick={() => run(async () => {
            await post('/leave/types', { name: t.name, paid: t.paid, charge_code_id: Number(t.charge_code_id), accrual_per_month: Number(t.accrual || 0), carry_forward_cap: Number(t.cap || 0) })
            types.reload()
          }, 'Leave type added')}>Add leave type</button></div>
      </div>

      <div className="card">
        <h3>Opening balance ({year})</h3>
        <label className="field"><span>Employee (user id)</span><input id="bal-user" type="text" inputMode="numeric" value={b.user_id} onChange={(e) => setB({ ...b, user_id: e.target.value })} /></label>
        <label className="field"><span>Leave type</span>
          <select id="bal-type" value={b.leave_type_id} onChange={(e) => setB({ ...b, leave_type_id: e.target.value })}>
            <option value="">Choose…</option>
            {(types.data ?? []).map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
          </select></label>
        <label className="field"><span>Opening days</span><input id="bal-days" type="text" inputMode="decimal" value={b.opening} onChange={(e) => setB({ ...b, opening: e.target.value })} /></label>
        <div><button type="button" className="btn primary" disabled={!b.user_id || !b.leave_type_id || b.opening === ''}
          onClick={() => run(() => api('PUT', '/leave/balances', { user_id: Number(b.user_id), leave_type_id: Number(b.leave_type_id), leave_year: year, opening: Number(b.opening) }), 'Balance saved')}>Save balance</button></div>
      </div>

      <div className="card">
        <h3>Blackout days</h3>
        {(blackout.data ?? []).map((x) => <div key={x.id}>{x.on_date} · {x.note}</div>)}
        <div className="grid3">
          <label className="field"><span>Date</span><input id="bo-date" type="date" value={day.on_date} min={addDays(mondayOf(new Date()), 0)} onChange={(e) => setDay({ ...day, on_date: e.target.value })} /></label>
          <label className="field"><span>Note</span><input id="bo-note" type="text" value={day.note} onChange={(e) => setDay({ ...day, note: e.target.value })} /></label>
        </div>
        <div><button type="button" className="btn primary" disabled={!day.on_date || !day.note}
          onClick={() => run(async () => { await post('/leave/blackout-days', day); setDay({ on_date: '', note: '' }); blackout.reload() }, 'Blackout day added')}>Add blackout day</button></div>
      </div>
    </div>
  )
}
