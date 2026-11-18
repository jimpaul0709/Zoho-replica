import { ThemeToggle } from '../ui'

const FEATURES = [
  {
    id: 'time', tag: 'Time', img: 'day', alt: 'The day view with hours for one task and the weekly totals above',
    title: 'Log the week in one grid',
    body: 'Hours per task and charge code, day totals, and a running count of what is still to log. Submit when the week is done; it locks once approved.',
    points: ['Grid and day views', 'Edit requests after approval', 'Every correction kept in an audit log'],
  },
  {
    id: 'leave', tag: 'Leave', img: 'leave', alt: 'Leave balance and the apply-for-leave form',
    title: 'Ask for leave, see what is left',
    body: 'Your balance sits above the request form, so you know before you apply. Requests go straight to your manager.',
    points: ['Balances accrue monthly', 'Carry-forward handled for you', 'Holidays and teams set up by HR'],
  },
  {
    id: 'approvals', tag: 'Approvals', img: 'approvals', alt: 'A manager approving several timesheets at once',
    title: 'Managers approve in one pass',
    body: 'Timesheets and leave waiting on you in one list. Tick several, approve, or open one to review. Going away? Delegate to someone else for those dates.',
    points: ['Bulk approve', 'Delegation while away', 'Payslips published to each person by HR'],
  },
]

// Hash routes drive the app, so in-page scrolling uses scrollIntoView, not #anchors.
const go = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })

export default function Landing() {
  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="logo"><i />WorkHub</div>
        <span className="spacer" />
        <ThemeToggle />
        <button type="button" className="btn lp-link" onClick={() => go('features')}>Features</button>
        <a className="btn primary" href="#login">Sign in</a>
      </header>

      <section className="lp-hero">
        <h1>Time, leave and payslips, in one place.</h1>
        <p>Log your week, ask for leave and open your payslip without switching between three tools.</p>
        <div className="actions">
          <a className="btn primary lg" href="#login">Sign in</a>
          <button type="button" className="btn lg" onClick={() => go('features')}>See how it works</button>
        </div>
        <span className="hint">No account? HR creates accounts and resets passwords.</span>
        <figure className="lp-shot lp-hero-shot">
          <img src="/landing/week.png" alt="The WorkHub week grid with hours logged per task" />
        </figure>
      </section>

      <section id="features" className="lp-features">
        {FEATURES.map((f, i) => (
          <article key={f.id} className={'lp-row' + (i % 2 ? ' flip' : '')}>
            <div className="lp-copy">
              <span className="chip info">{f.tag}</span>
              <h2>{f.title}</h2>
              <p>{f.body}</p>
              <ul>{f.points.map((p) => <li key={p}>{p}</li>)}</ul>
            </div>
            <figure className="lp-shot">
              <img src={`/landing/${f.img}.png`} alt={f.alt} loading="lazy" />
            </figure>
          </article>
        ))}
      </section>

      <section className="lp-cta">
        <h2>Ready when you are.</h2>
        <a className="btn primary lg" href="#login">Sign in to WorkHub</a>
      </section>

      <footer className="lp-foot hint">WorkHub · Ampera</footer>
    </div>
  )
}
