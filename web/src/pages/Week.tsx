import { useState } from 'react'
import { api, get, post, addDays, fmtDay, fmtRange, iso, mondayOf, toHours, toMinutes, type S } from '../api'
import { Banner, Chip, Loading, useLoad } from '../ui'

type Entry = S['EntryOut']
const DAYS = [0, 1, 2, 3, 4, 5, 6]
const keyOf = (e: Entry) => (e.task_id ? 't:' + e.task_id : 'c:' + e.charge_code_id)
// shortcut: expected hours are 8 per weekday; read the real figure from org settings when it is exposed.
const EXPECTED_HOURS = 40

function Cell(props: { entries: Entry[]; label: string; disabled: boolean; rev: number; onCommit: (text: string) => void }) {
  const { entries, label, disabled, rev, onCommit } = props
  const total = entries.reduce((s, e) => s + e.minutes, 0)
  // Several entries in one cell, or leave/holiday time, are shown as a total and not edited here.
  const fixed = entries.length > 1 || entries.some((e) => e.source === 'leave' || e.source === 'holiday')
  return (
    <input
      key={total + ':' + rev}
      className="hrs"
      type="text"
      inputMode="decimal"
      aria-label={label}
      placeholder="0"
      defaultValue={total ? String(toHours(total)) : ''}
      disabled={disabled || fixed}
      onBlur={(e) => onCommit(e.target.value)}
      onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
    />
  )
}

export default function Week() {
  const [weekStart, setWeekStart] = useState(mondayOf(new Date()))
  const [extra, setExtra] = useState<string[]>([])
  const [view, setView] = useState<'grid' | 'day'>(window.innerWidth < 760 ? 'day' : 'grid')
  const [dayIdx, setDayIdx] = useState((new Date().getDay() + 6) % 7)
  const [err, setErr] = useState('')
  const [pick, setPick] = useState('')
  const [rev, setRev] = useState(0)
  const week = useLoad(() => get<S['WeekOut']>('/time/week?on=' + weekStart), [weekStart])
  const targets = useLoad(() => get<S['TargetsOut']>('/time/targets'), [])

  const wk = week.data?.week_start === weekStart ? week.data : undefined
  const entries = wk?.entries ?? []
  const rows = [...new Set([...entries.map(keyOf), ...extra])]
  const today = iso(new Date())
  const dates = DAYS.map((i) => addDays(weekStart, i))
  const locked = !!wk && (wk.locked || wk.status === 'approved')
  const cellEntries = (key: string, date: string) => entries.filter((e) => keyOf(e) === key && e.work_date === date)
  const dayTotal = (date: string) => entries.filter((e) => e.work_date === date).reduce((s, e) => s + e.minutes, 0)
  const logged = toHours(entries.reduce((s, e) => s + e.minutes, 0))

  function label(key: string): [string, string] {
    const [kind, id] = key.split(':')
    if (kind === 't') {
      const t = targets.data?.tasks.find((x) => x.id === Number(id))
      return t ? [t.key + ' · ' + t.title, t.project_name] : ['Task #' + id, '']
    }
    const c = targets.data?.charge_codes.find((x) => x.id === Number(id))
    return [c ? c.code + ' · ' + c.name : 'Charge code #' + id, 'Charge code']
  }

  async function commit(key: string, date: string, text: string) {
    const hours = text.trim() === '' ? 0 : Number(text)
    if (!Number.isFinite(hours) || hours < 0 || hours > 24) return setErr('Enter hours between 0 and 24, for example 4.5.')
    const [one] = cellEntries(key, date)
    const minutes = toMinutes(hours)
    try {
      setErr('')
      if (one && minutes === 0) await api('DELETE', '/time/entries/' + one.id)
      else if (one && minutes !== one.minutes) await api('PATCH', '/time/entries/' + one.id, { minutes })
      else if (!one && minutes > 0) {
        const [kind, id] = key.split(':')
        await post('/time/entries', { work_date: date, minutes, [kind === 't' ? 'task_id' : 'charge_code_id']: Number(id) })
      } else return
    } catch (e) {
      setErr((e as Error).message)
    }
    setRev((r) => r + 1)
    week.reload()
  }

  async function submit() {
    try {
      setErr('')
      await post('/time/weeks/' + weekStart + '/submit')
      week.reload()
    } catch (e) {
      setErr((e as Error).message)
    }
  }

  const go = (start: string) => { setWeekStart(start); setExtra([]); setErr('') }
  const cell = (key: string, date: string) => (
    <Cell
      entries={cellEntries(key, date)}
      label={label(key)[0] + ' on ' + fmtDay(date)}
      disabled={locked || date > today}
      rev={rev}
      onCommit={(t) => commit(key, date, t)}
    />
  )
  const options = [
    ...(targets.data?.tasks ?? []).map((t) => ['t:' + t.id, t.key + ' · ' + t.title + ' (' + t.project_name + ')']),
    ...(targets.data?.charge_codes ?? []).map((c) => ['c:' + c.id, 'Charge code: ' + c.code + ' · ' + c.name]),
  ].filter(([k]) => !rows.includes(k))

  return (
    <section style={{ display: 'grid', gap: 18 }}>
      <div className="head">
        <h2>My week</h2>
        <span className="row">
          <button type="button" className="btn sm" aria-label="Previous week" onClick={() => go(addDays(weekStart, -7))}>‹</button>
          <b>{fmtRange(weekStart, addDays(weekStart, 6))}</b>
          <button type="button" className="btn sm" aria-label="Next week" onClick={() => go(addDays(weekStart, 7))}>›</button>
          <button type="button" className="btn sm" onClick={() => go(mondayOf(new Date()))}>This week</button>
        </span>
        <span className="spacer" />
        <span className="seg" aria-label="Week view">
          <button type="button" aria-pressed={view === 'grid'} onClick={() => setView('grid')}>Grid</button>
          <button type="button" aria-pressed={view === 'day'} onClick={() => setView('day')}>Day</button>
        </span>
        {wk && <Chip status={wk.status} />}
      </div>
      <Loading error={week.error || targets.error} loading={week.loading && !wk} />
      {err && <Banner kind="bad">{err}</Banner>}
      {wk && (
        <>
          {Object.keys(wk.day_reasons).length > 0 && (
            <Banner kind="bad">
              <div>
                <b>Your manager sent time back for changes.</b>
                {Object.entries(wk.day_reasons).map(([d, r]) => <div key={d}>{fmtDay(d)}: {r}</div>)}
              </div>
            </Banner>
          )}
          {wk.status === 'submitted' && <Banner>Submitted. Waiting for approval. You can still change entries until it is approved.</Banner>}
          {locked && <Banner kind="ok">Approved. This week is locked; ask HR for a correction if something is wrong.</Banner>}

          <div className="strip">
            <div><span className="hint">Logged this week</span><span className="big">{logged} h</span><span className="hint">of {EXPECTED_HOURS} h expected</span></div>
            <div><span className="hint">Still to log</span><span className="big">{Math.max(0, EXPECTED_HOURS - logged)} h</span><span className="hint">to reach {EXPECTED_HOURS} h</span></div>
            <div>
              <span className="hint">Hours per day (dashed line = 8 h)</span>
              <div className="bars">
                {dates.map((d, i) => {
                  const h = toHours(dayTotal(d))
                  return (
                    <div className="bcol" key={d}>
                      <div className={'bfill' + (i < 5 && d <= today && h < 8 ? ' low' : '')} style={{ height: Math.min(100, (h / 8) * 100) + '%' }} />
                      <span>{'MTWTFSS'[i]}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {view === 'grid' ? (
            <div className="card scroll">
              <table id="grid">
                <thead>
                  <tr>
                    <th>Task or charge code</th>
                    {dates.map((d, i) => <th key={d} className={'num' + (i > 4 ? ' weekend' : '')}>{fmtDay(d)}</th>)}
                    <th className="num">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.length === 0 && <tr><td colSpan={9} className="hint">No time yet. Add a task or charge code below.</td></tr>}
                  {rows.map((key) => {
                    const [name, sub] = label(key)
                    const total = entries.filter((e) => keyOf(e) === key).reduce((s, e) => s + e.minutes, 0)
                    return (
                      <tr key={key}>
                        <td>{name}<br /><span className="hint">{sub}</span></td>
                        {dates.map((d, i) => <td key={d} className={'num' + (i > 4 ? ' weekend' : '')}>{cell(key, d)}</td>)}
                        <td className="num">{toHours(total)}</td>
                      </tr>
                    )
                  })}
                </tbody>
                <tfoot>
                  <tr className="total">
                    <td>Day total</td>
                    {dates.map((d, i) => <td key={d} className={'num' + (i < 5 && d <= today && dayTotal(d) < 480 ? ' short' : '')}>{toHours(dayTotal(d))}</td>)}
                    <td className="num">{logged}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          ) : (
            <div className="card flat">
              <div className="row">
                <button type="button" className="btn sm" aria-label="Previous day" disabled={dayIdx === 0} onClick={() => setDayIdx(dayIdx - 1)}>‹</button>
                <b>{fmtDay(dates[dayIdx], { weekday: 'long', day: 'numeric', month: 'short' })}</b>
                <button type="button" className="btn sm" aria-label="Next day" disabled={dayIdx === 6} onClick={() => setDayIdx(dayIdx + 1)}>›</button>
                <span className="spacer" />
                <span className="hint">Day total {toHours(dayTotal(dates[dayIdx]))} h</span>
              </div>
              {rows.map((key) => (
                <label className="field" key={key}><span>{label(key)[0]} (hours)</span>{cell(key, dates[dayIdx])}</label>
              ))}
            </div>
          )}

          <div className="actions">
            <select aria-label="Add a task or charge code" value={pick} onChange={(e) => setPick(e.target.value)} style={{ width: 'auto', maxWidth: 360 }}>
              <option value="">+ Add task or charge code…</option>
              {options.map(([k, text]) => <option key={k} value={k}>{text}</option>)}
            </select>
            <button type="button" className="btn" disabled={!pick} onClick={() => { setExtra([...extra, pick]); setPick('') }}>Add row</button>
            <span className="spacer" />
            {(wk.status === 'draft' || wk.status === 'sent_back') && (
              <button type="button" className="btn primary" disabled={entries.length === 0} onClick={submit}>Submit week for approval</button>
            )}
          </div>
        </>
      )}
    </section>
  )
}
