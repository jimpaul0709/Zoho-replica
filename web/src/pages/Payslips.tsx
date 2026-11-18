import { useState } from 'react'
import { get, saveFile, type S } from '../api'
import { Banner, Empty, Loading, useLoad } from '../ui'

const monthName = (m: string) => new Date(m + '-01T00:00').toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })

export default function Payslips() {
  const list = useLoad(() => get<S['PayslipRow'][]>('/payslips/mine'), [])
  const [err, setErr] = useState('')
  const open = (p: S['PayslipRow']) => saveFile('/payslips/' + p.id + '/file', 'payslip-' + p.month + '.pdf').then(() => setErr(''), (e: Error) => setErr(e.message))

  return (
    <section style={{ display: 'grid', gap: 18 }}>
      <div className="head"><h2>Payslips</h2></div>
      <Loading error={list.error} loading={list.loading && !list.data} />
      {err && <Banner kind="bad">{err}</Banner>}
      {list.data?.length === 0 && <Empty title="No payslips yet" hint="HR publishes payslips once a month's batch is checked. Only you can see yours." />}
      {(list.data ?? []).length > 0 && (
        <div className="card">
          {(list.data ?? []).map((p) => (
            <div className="row" key={p.id}>
              <b>{monthName(p.month)}</b>
              <span className="spacer" />
              <button type="button" className="btn sm" onClick={() => open(p)}>Download PDF</button>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
