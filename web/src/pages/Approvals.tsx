import { useState } from 'react'
import { api, get, post, fmtDay, fmtRange, addDays, toHours, type S } from '../api'
import { Banner, Chip, DateField, Empty, Loading, UserSelect, initials, useLoad } from '../ui'

type Item = S['InboxItem']
const isTime = (i: Item) => i.subject_type !== 'leave'

export default function Approvals() {
  const inbox = useLoad(() => get<Item[]>('/approvals/inbox'), [])
  const [tab, setTab] = useState<'time' | 'leave'>('time')
  const [openId, setOpenId] = useState<number>()
  const [picked, setPicked] = useState<number[]>([])
  const [back, setBack] = useState<{ date?: string; text: string }>()
  const [msg, setMsg] = useState<{ kind: 'ok' | 'bad'; text: string }>()

  const items = (inbox.data ?? []).filter((i) => (tab === 'leave' ? !isTime(i) : isTime(i)))
  const open = inbox.data?.find((i) => i.approval_id === openId)

  async function act(fn: () => Promise<unknown>, done: string, close = false) {
    try {
      await fn()
      setMsg({ kind: 'ok', text: done })
      setBack(undefined)
      if (close) setOpenId(undefined)
      inbox.reload()
    } catch (e) {
      setMsg({ kind: 'bad', text: (e as Error).message })
    }
  }
  const base = (i: Item) => '/approvals/' + i.approval_id
  const bulk = () =>
    act(async () => {
      const r = await post<S['BulkResult']>('/approvals/bulk-approve', { approval_ids: picked })
      setPicked([])
      if (r.skipped.length) throw new Error(r.skipped.length + ' skipped: ' + r.skipped.map((s) => s.reason).join('; '))
    }, 'Approved')

  const sendBack = (i: Item) => {
    const text = (back?.text ?? '').trim()
    if (!text) return setMsg({ kind: 'bad', text: 'Add a reason before sending back.' })
    return back?.date
      ? act(() => post(base(i) + '/days/' + back.date + '/send-back', { reason: text }), 'Day sent back')
      : act(() => post(base(i) + '/send-back', { reason: text }), 'Sent back', true)
  }

  return (
    <section style={{ display: 'grid', gap: 18 }}>
      <div className="head"><h2>Approvals</h2></div>
      <div className="tabs" role="tablist">
        {(['time', 'leave'] as const).map((t) => (
          <button key={t} type="button" role="tab" aria-selected={tab === t} onClick={() => { setTab(t); setOpenId(undefined) }}>
            {t === 'time' ? 'Timesheets' : 'Leave'} <span className="count">{(inbox.data ?? []).filter((i) => (t === 'leave') === !isTime(i)).length}</span>
          </button>
        ))}
      </div>
      <Loading error={inbox.error} loading={inbox.loading && !inbox.data} />
      {msg && <Banner kind={msg.kind}>{msg.text}</Banner>}

      {!open && inbox.data && (
        <div className="card scroll">
          {tab === 'time' && (
            <div className="row">
              <button type="button" className="btn primary sm" disabled={!picked.length} onClick={bulk}>Approve selected ({picked.length})</button>
            </div>
          )}
          {items.length === 0 ? (
            <Empty title="Nothing waiting for you" hint="Weeks and leave requests from your team show up here once they are submitted." />
          ) : (
            <table>
              <thead><tr>{tab === 'time' && <th><input type="checkbox" aria-label="Select all" checked={picked.length === items.length} onChange={(e) => setPicked(e.target.checked ? items.map((i) => i.approval_id) : [])} /></th>}<th>Employee</th><th>{tab === 'time' ? 'Week' : 'Dates'}</th><th className="num">Hours</th><th>Submitted</th><th /></tr></thead>
              <tbody>
                {items.map((i) => (
                  <tr key={i.approval_id}>
                    {tab === 'time' && (
                      <td><input type="checkbox" aria-label={'Select ' + i.requester_name} checked={picked.includes(i.approval_id)}
                        onChange={(e) => setPicked(e.target.checked ? [...picked, i.approval_id] : picked.filter((x) => x !== i.approval_id))} /></td>
                    )}
                    <td><span className="who2"><i className="av c1">{initials(i.requester_name)}</i>{i.requester_name}</span></td>
                    <td>{i.leave ? fmtRange(i.leave.from_date, i.leave.to_date) : i.week_start ? fmtRange(i.week_start, addDays(i.week_start, 6)) : ''}</td>
                    <td className="num"><span className="hcell"><i style={{ width: Math.min(100, ((i.leave ? i.leave.hours : toHours(i.total_minutes)) / 40) * 100) + '%' }} />{i.leave ? i.leave.hours : toHours(i.total_minutes)}</span></td>
                    <td>{new Date(i.requested_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })} {i.overdue && <span className="chip bad">overdue</span>}</td>
                    <td><button type="button" className="btn sm" onClick={() => { setOpenId(i.approval_id); setMsg(undefined) }}>Review</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {open && (
        <>
          <div className="head">
            <button type="button" className="btn sm" onClick={() => { setOpenId(undefined); setBack(undefined) }}>‹ Back to inbox</button>
            <h3>{open.requester_name}{open.week_start ? ' · ' + fmtRange(open.week_start, addDays(open.week_start, 6)) : ''}</h3>
          </div>
          {open.leave ? (
            <div className="card">
              <div><b>{open.leave.leave_type}</b> · {fmtRange(open.leave.from_date, open.leave.to_date)} · {open.leave.hours} h</div>
              {open.leave.reason && <div>{open.leave.reason}</div>}
              {open.leave.applied_after_dates && <Banner kind="warn">Applied after the leave dates.</Banner>}
            </div>
          ) : (
            <div className="card scroll">
              <table>
                <thead><tr><th>Day</th><th className="num">Hours</th><th>Decision</th><th /></tr></thead>
                <tbody>
                  {open.days.map((d) => (
                    <tr key={d.work_date}>
                      <td>{fmtDay(d.work_date)}</td>
                      <td className="num">{toHours(d.minutes)}</td>
                      <td><Chip status={d.status} />{d.reason && <span className="hint"> {d.reason}</span>}</td>
                      <td className="actions">
                        <button type="button" className="btn sm" onClick={() => act(() => post(base(open) + '/days/' + d.work_date + '/approve'), 'Day approved')}>Approve</button>
                        <button type="button" className="btn sm" onClick={() => setBack({ date: d.work_date, text: '' })}>Send back</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {back && (
            <div className="card flat">
              <label className="field"><span>Reason for sending back {back.date ? fmtDay(back.date) : 'the whole request'} (required, the employee sees this)</span>
                <textarea id="reason" value={back.text} onChange={(e) => setBack({ ...back, text: e.target.value })} placeholder="What should they change?" /></label>
              <div className="actions"><button type="button" className="btn danger" onClick={() => sendBack(open)}>Send back</button><button type="button" className="btn" onClick={() => setBack(undefined)}>Cancel</button></div>
            </div>
          )}
          <div className="actions">
            <button type="button" className="btn danger" onClick={() => setBack({ text: '' })}>Send back</button>
            <button type="button" className="btn primary" onClick={() => act(() => post(base(open) + '/approve'), 'Approved', true)}>Approve</button>
          </div>
          {open.timeline.length > 0 && (
            <div className="card flat"><h3>History</h3>
              {open.timeline.map((s, n) => <div key={n} className="hint">{new Date(s.at).toLocaleString('en-GB')} · {s.actor_name} {s.action}{s.comment ? ': ' + s.comment : ''}</div>)}
            </div>
          )}
        </>
      )}
      <Delegations />
    </section>
  )
}

function Delegations() {
  const list = useLoad(() => get<S['DelegationOut'][]>('/delegations'), [])
  const [to, setTo] = useState('')
  const [from, setFrom] = useState('')
  const [until, setUntil] = useState('')
  const [err, setErr] = useState('')

  async function add() {
    try {
      setErr('')
      await post('/delegations', { to_user_id: Number(to), starts_on: from, ends_on: until })
      setTo(''); setFrom(''); setUntil('')
      list.reload()
    } catch (e) {
      setErr((e as Error).message)
    }
  }
  return (
    <div className="card">
      <h3>Delegate while I am away</h3>
      {err && <Banner kind="bad">{err}</Banner>}
      {(list.data ?? []).map((d) => (
        <div className="row" key={d.id}>
          <span>User #{d.to_user_id} · {fmtRange(d.starts_on, d.ends_on)}</span>
          <button type="button" className="btn sm" onClick={() => api('DELETE', '/delegations/' + d.id).then(list.reload)}>Remove</button>
        </div>
      ))}
      <div className="grid3">
        <UserSelect id="deleg-to" label="Delegate to" value={to} onChange={setTo} />
        <DateField id="deleg-from" label="From" value={from} onChange={(v) => { setFrom(v); if (until && until < v) setUntil('') }} />
        <DateField id="deleg-until" label="Until" value={until} min={from} rangeFrom={from} onChange={setUntil} />
      </div>
      <div><button type="button" className="btn primary" disabled={!to || !from || !until} onClick={add}>Save delegation</button></div>
    </div>
  )
}
