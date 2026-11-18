import { useState, type FormEvent } from 'react'
import { get, post, token, type S } from '../api'
import { Banner } from '../ui'

export default function Login({ onSignedIn }: { onSignedIn: (me: S['MeOut']) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      token.set((await post<S['LoginOut']>('/auth/login', { email, password })).token)
      onSignedIn(await get<S['MeOut']>('/auth/me'))
      if (!location.hash) location.hash = 'week'
    } catch (err) {
      token.clear()
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-wrap" style={{ margin: 0 }}>
      <aside className="brand-pane">
        <h2>Time, leave and payslips in one place.</h2>
        <p>Log your week, ask for leave and open your payslip without switching between three tools.</p>
      </aside>
      <div className="login-side">
        <form className="card login" onSubmit={submit}>
          <div><h2>Sign in</h2><div className="hint">Use your Ampera email and password.</div></div>
          {error && <Banner kind="bad">{error}</Banner>}
          <label className="field"><span>Work email</span>
            <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" required autoFocus /></label>
          <label className="field"><span>Password</span>
            <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required /></label>
          <button className="btn primary" type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
          <div className="hint">No account or forgot your password? HR sets and resets passwords.</div>
        </form>
      </div>
    </div>
  )
}
