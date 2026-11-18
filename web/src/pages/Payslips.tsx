import { Banner } from '../ui'

// Payslips need a backend (upload, match by employee code, publish). Screen comes with that milestone.
export default function Payslips() {
  return (
    <section style={{ display: 'grid', gap: 18 }}>
      <h2>Payslips</h2>
      <Banner>Payslips are not available yet. HR will publish them here once the payslip service is built.</Banner>
    </section>
  )
}
