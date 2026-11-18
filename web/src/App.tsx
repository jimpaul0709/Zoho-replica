import { useEffect, useState } from 'react'
import { get, post, token, type S } from './api'
import { initials, useHash } from './ui'
import Login from './pages/Login'
import Password from './pages/Password'
import Week from './pages/Week'
import Approvals from './pages/Approvals'
import Leave from './pages/Leave'
import Payslips from './pages/Payslips'
import Hr from './pages/Hr'

const ICONS: Record<string, string> = {
  week: 'M3 8a3 3 0 013-3h12a3 3 0 013 3v10a3 3 0 01-3 3H6a3 3 0 01-3-3zM8 3v4M16 3v4M3 10h18',
  leave: 'M4 20c0-7 5-13 16-14-1 9-7 14-14 14M4 20L14 10',
  payslips: 'M6 6h12a3 3 0 013 3v6a3 3 0 01-3 3H6a3 3 0 01-3-3V9a3 3 0 013-3zM12 9.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5',
  approvals: 'M5 12l4 4L19 6',
  hr: 'M9 4.5a3.5 3.5 0 100 7 3.5 3.5 0 000-7M2.5 20c0-4 3-6 6.5-6s6.5 2 6.5 6M17 11a3 3 0 100-6M21.5 19c0-3-1.5-4.5-3.5-5',
}
// Role-based access comes later: every signed-in person sees every screen for now.
const NAV = [
  { group: 'Me', items: [['week', 'Week'], ['leave', 'Leave'], ['payslips', 'Payslips']] },
  { group: 'Manager', items: [['approvals', 'Approvals']] },
  { group: 'HR', items: [['hr', 'HR admin']] },
]
const PAGES: Record<string, () => React.ReactNode> = {
  week: () => <Week />,
  leave: () => <Leave />,
  payslips: () => <Payslips />,
  approvals: () => <Approvals />,
  hr: () => <Hr />,
  password: () => <Password />,
}

export default function App() {
  const [me, setMe] = useState<S['MeOut'] | null>(null)
  const [ready, setReady] = useState(!token.get())
  const route = useHash() || 'week'

  useEffect(() => {
    if (token.get()) get<S['MeOut']>('/auth/me').then(setMe, () => token.clear()).finally(() => setReady(true))
    const out = () => setMe(null)
    window.addEventListener('workhub-signed-out', out)
    return () => window.removeEventListener('workhub-signed-out', out)
  }, [])

  if (!ready) return <div className="center">Loading…</div>
  if (!me) return <Login onSignedIn={setMe} />

  const signOut = async () => {
    await post('/auth/logout').catch(() => {}) // the token is dropped locally either way
    token.clear()
    setMe(null)
  }
  const page = (PAGES[route] ?? PAGES.week)()

  return (
    <div className="app">
      <header className="topbar">
        <div className="logo"><i />WorkHub</div>
        <span className="spacer" />
        <div className="who">
          <span className="avatar">{initials(me.name)}</span>
          <span>{me.name}<br /><span className="hint">{me.roles.join(', ')}</span></span>
          <a className="btn sm" href="#password">Change password</a>
          <button type="button" className="btn sm" onClick={signOut}>Sign out</button>
        </div>
      </header>
      <div className="body">
        <nav className="nav" aria-label="Main">
          {NAV.map((g) => (
            <div key={g.group} style={{ display: 'contents' }}>
              <div className="grp">{g.group}</div>
              {g.items.map(([id, label]) => (
                <a key={id} href={'#' + id} aria-current={route === id ? 'page' : undefined}>
                  <svg className="i" viewBox="0 0 24 24" aria-hidden="true"><path d={ICONS[id]} /></svg>
                  <span className="t">{label}</span>
                </a>
              ))}
            </div>
          ))}
        </nav>
        <main>{page}</main>
      </div>
    </div>
  )
}
