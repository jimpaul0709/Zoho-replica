import { useCallback, useEffect, useRef, useState } from 'react'
import { get, post, token, type S } from './api'
import { ThemeToggle, initials, useDismiss, useHash } from './ui'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Password from './pages/Password'
import Home from './pages/Home'
import Week from './pages/Week'
import Approvals from './pages/Approvals'
import Leave from './pages/Leave'
import Payslips from './pages/Payslips'
import Hr from './pages/Hr'

const ICONS: Record<string, string> = {
  home: 'M4 11l8-7 8 7v8a2 2 0 01-2 2h-3v-6H9v6H6a2 2 0 01-2-2z',
  week: 'M3 8a3 3 0 013-3h12a3 3 0 013 3v10a3 3 0 01-3 3H6a3 3 0 01-3-3zM8 3v4M16 3v4M3 10h18',
  leave: 'M4 20c0-7 5-13 16-14-1 9-7 14-14 14M4 20L14 10',
  payslips: 'M6 6h12a3 3 0 013 3v6a3 3 0 01-3 3H6a3 3 0 01-3-3V9a3 3 0 013-3zM12 9.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5',
  approvals: 'M5 12l4 4L19 6',
  hr: 'M9 4.5a3.5 3.5 0 100 7 3.5 3.5 0 000-7M2.5 20c0-4 3-6 6.5-6s6.5 2 6.5 6M17 11a3 3 0 100-6M21.5 19c0-3-1.5-4.5-3.5-5',
}
// Role-based access comes later: every signed-in person sees every screen for now.
const NAV = [
  { group: 'Me', items: [['home', 'Home'], ['week', 'Week'], ['leave', 'Leave'], ['payslips', 'Payslips']] },
  { group: 'Manager', items: [['approvals', 'Approvals']] },
  { group: 'HR', items: [['hr', 'HR admin']] },
]
const PAGES: Record<string, (me: S['MeOut']) => React.ReactNode> = {
  home: (me) => <Home name={me.name} />,
  week: () => <Week />,
  leave: () => <Leave />,
  payslips: () => <Payslips />,
  approvals: () => <Approvals />,
  hr: () => <Hr />,
  password: () => <Password />,
}

// Avatar button that opens account actions (replaces two loose buttons in the top bar).
function AccountMenu({ name, roles, onSignOut }: { name: string; roles: string[]; onSignOut: () => void }) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const close = useCallback(() => setOpen(false), [])
  useDismiss(root, open, close)
  return (
    <div className="acct" ref={root} onKeyDown={(e) => { if (e.key === 'Escape') setOpen(false) }}>
      <button type="button" className="acct-btn" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className="avatar">{initials(name)}</span>
        <span className="acct-name">{name}</span>
        <svg className="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
      </button>
      {open && (
        <div className="menu-pop" role="menu">
          <div className="menu-head"><b>{name}</b><span className="hint">{roles.join(', ')}</span></div>
          <a role="menuitem" href="#password" onClick={close}>Change password</a>
          <button type="button" role="menuitem" onClick={onSignOut}>Sign out</button>
        </div>
      )}
    </div>
  )
}

export default function App() {
  const [me, setMe] = useState<S['MeOut'] | null>(null)
  const [ready, setReady] = useState(!token.get())
  const hash = useHash()
  const route = hash || 'home'

  useEffect(() => {
    if (token.get()) get<S['MeOut']>('/auth/me').then(setMe, () => token.clear()).finally(() => setReady(true))
    const out = () => setMe(null)
    window.addEventListener('workhub-signed-out', out)
    return () => window.removeEventListener('workhub-signed-out', out)
  }, [])

  if (!ready) return <div className="center">Loading…</div>
  if (!me) return hash ? <Login onSignedIn={setMe} /> : <Landing />

  const signOut = async () => {
    await post('/auth/logout').catch(() => {}) // the token is dropped locally either way
    token.clear()
    setMe(null)
    location.hash = '' // back to the landing page
  }
  const page = (PAGES[route] ?? PAGES.home)(me)
  const found = NAV.flatMap((g) => g.items.map(([id, l]) => [id, l, g.group] as const)).find(([id]) => id === route)

  return (
    <div className="app">
      <nav className="nav" aria-label="Main">
        <div className="logo"><i />WorkHub</div>
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
      <div className="col">
        <header className="topbar">
          <span className="crumb"><span className="hint">{found ? found[2] + " /" : ""}</span> {found?.[1] ?? "Account"}</span>
          <span className="spacer" />
          <ThemeToggle />
          <AccountMenu name={me.name} roles={me.roles} onSignOut={signOut} />
        </header>
        <main>{page}</main>
      </div>
    </div>
  )
}
