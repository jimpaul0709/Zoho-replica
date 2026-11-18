import { useState, type FormEvent } from 'react'
import { post } from '../api'
import { Banner } from '../ui'

export default function Password() {
  const [cur, setCur] = useState('')
  const [next, setNext] = useState('')
  const [again, setAgain] = useState('')
  const [msg, setMsg] = useState<{ kind: 'ok' | 'bad'; text: string }>()

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (next !== again) return setMsg({ kind: 'bad', text: 'The new passwords do not match.' })
    try {
      await post('/auth/password', { current_password: cur, new_password: next })
      setCur(''); setNext(''); setAgain('')
      setMsg({ kind: 'ok', text: 'Password changed. Your other browsers were signed out.' })
    } catch (err) {
      setMsg({ kind: 'bad', text: (err as Error).message })
    }
  }

  return (
    <section style={{ display: 'grid', gap: 18 }}>
      <h2>Change password</h2>
      <form className="card" style={{ maxWidth: 420 }} onSubmit={submit}>
        {msg && <Banner kind={msg.kind}>{msg.text}</Banner>}
        <label className="field"><span>Current password</span><input id="cur" type="password" value={cur} onChange={(e) => setCur(e.target.value)} required /></label>
        <label className="field"><span>New password</span><input id="next" type="password" value={next} onChange={(e) => setNext(e.target.value)} minLength={8} required /><span className="hint">At least 8 characters.</span></label>
        <label className="field"><span>Repeat new password</span><input id="again" type="password" value={again} onChange={(e) => setAgain(e.target.value)} required /></label>
        <div className="actions"><button className="btn primary" type="submit">Save password</button><a className="btn" href="#week">Cancel</a></div>
      </form>
    </section>
  )
}
