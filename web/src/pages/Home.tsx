import { get, addDays, fmtDay, iso, mondayOf, toHours, type S } from '../api'
import { CountUp, Empty, useLoad } from '../ui'

const EXPECTED_HOURS = 40
const hello = () => { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening' }

export default function Home({ name }: { name: string }) {
  const start = mondayOf(new Date())
  const week = useLoad(() => get<S['WeekOut']>('/time/week?on=' + start), [])
  const balances = useLoad(() => get<S['BalanceOut'][]>('/leave/balances?year=' + new Date().getFullYear()), [])
  const inbox = useLoad(() => get<unknown[]>('/approvals/inbox').catch(() => []), [])
  const entries = week.data?.entries ?? []
  const days = [0, 1, 2, 3, 4, 5, 6].map((i) => addDays(start, i))
  const perDay = days.map((d) => toHours(entries.filter((e) => e.work_date === d).reduce((s, e) => s + e.minutes, 0)))
  const logged = Math.round(perDay.reduce((a, b) => a + b, 0) * 100) / 100
  const today = iso(new Date())
  const waiting = inbox.data?.length ?? 0

  return (
    <section className="home">
      <div className="hero">
        <div>
          <h2>{hello()}, {name.split(' ')[0]}</h2>
          <p className="hint">{new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}{week.data ? ' · this week is ' + week.data.status.replace(/_/g, ' ') : ''}</p>
          <div className="actions">
            <a className="btn primary" href="#week">Log time</a>
            <a className="btn" href="#leave">Request leave</a>
          </div>
        </div>
        <div className="hero-stat">
          <span className="hint">Logged this week</span>
          <span className="big"><CountUp value={logged} /> <small>of {EXPECTED_HOURS} h</small></span>
          <div className="meter"><i style={{ width: Math.min(100, (logged / EXPECTED_HOURS) * 100) + '%' }} /></div>
        </div>
      </div>

      <div className="week-strip card">
        {days.map((d, i) => (
          <div key={d} className={'wk-day' + (d === today ? ' today' : '') + (i > 4 ? ' off' : '')} style={{ ['--i' as string]: i }}>
            <span className="hint">{fmtDay(d, { weekday: 'short' })}</span>
            <b>{fmtDay(d, { day: 'numeric' })}</b>
            <span className="wk-h">{perDay[i] ? perDay[i] + ' h' : '–'}</span>
          </div>
        ))}
      </div>

      <div className="grid2">
        <div className="card">
          <div className="head"><h3>Leave balance</h3><span className="spacer" /><a className="hint" href="#leave">Open</a></div>
          {(balances.data ?? []).slice(0, 4).map((b) => {
            const total = b.opening + b.accrued + b.adjusted
            return (
              <div key={b.leave_type_id} className="bal-mini">
                <span>{b.leave_type}</span>
                <div className="meter"><i style={{ width: (total > 0 ? Math.max(0, (b.available / total) * 100) : 0) + '%' }} /></div>
                <span className="hint"><b>{b.available}</b> h left</span>
              </div>
            )
          })}
          {balances.data?.length === 0 && <Empty title="No leave balances yet" hint="HR sets your opening balance." />}
        </div>
        <div className="card">
          <div className="head"><h3>Waiting for your approval</h3><span className="spacer" /><a className="hint" href="#approvals">Open</a></div>
          {waiting > 0
            ? <div className="stat-big"><span className="big"><CountUp value={waiting} /></span><span className="hint">timesheets and leave requests</span></div>
            : <Empty title="Nothing waiting" hint="Good job. New requests from your team show up here." />}
        </div>
      </div>
    </section>
  )
}
