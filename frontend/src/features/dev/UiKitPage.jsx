import { useState } from 'react'
import { Briefcase, Users } from 'lucide-react'
import StatusPill from '../../components/common/StatusPill'
import MetricCard from '../../components/common/MetricCard'
import EmptyState from '../../components/common/EmptyState'
import ChartCard from '../../components/common/ChartCard'

const BARS = [
  { label: 'Jan', value: 40 },
  { label: 'Feb', value: 65 },
  { label: 'Mar', value: 52 },
  { label: 'Apr', value: 80 },
  { label: 'May', value: 70 },
]

function SimpleBars() {
  return (
    <div className="flex items-end gap-3 h-48">
      {BARS.map((b) => (
        <div key={b.label} className="flex-1 flex flex-col items-center gap-1">
          <div className="w-full rounded-t-md bg-[#6C31D6]" style={{ height: `${b.value * 1.6}px` }} />
          <span className="text-xs text-[#71717A]">{b.label}</span>
        </div>
      ))}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <section className="mb-10">
      <h2 className="text-lg font-semibold text-[#14142B] mb-3">{title}</h2>
      {children}
    </section>
  )
}

// Development-only showcase of the shared UI components. Route: /dev/ui-kit
function UiKitPage() {
  const [loading, setLoading] = useState(false)
  const [clicks, setClicks] = useState(0)

  return (
    <div className="min-h-screen bg-[#FAFAFA] p-6">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold text-[#14142B]">UI Kit</h1>
        <p className="text-sm text-[#71717A] mt-1 mb-6">Shared components from the Ordinis design system.</p>

        <label className="flex items-center gap-2 text-sm text-[#14142B] mb-8">
          <input type="checkbox" checked={loading} onChange={(e) => setLoading(e.target.checked)} />
          Show loading states
        </label>

        <Section title="StatusPill">
          <div className="flex flex-wrap gap-3">
            <StatusPill status="success" />
            <StatusPill status="warning" />
            <StatusPill status="failed" />
            <StatusPill status="info" />
            <StatusPill status="neutral" />
            <StatusPill status="approved" label="Approved" />
            <StatusPill status="pending" label="Pending" />
            <StatusPill status="rejected" label="Rejected" />
          </div>
        </Section>

        <Section title="MetricCard">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <MetricCard label="Total Employees" value="124" delta="+8 this month" deltaTone="positive" icon={Users} loading={loading} />
            <MetricCard label="Attendance Rate" value="94.2%" delta="-1.2% vs last month" deltaTone="negative" loading={loading} />
            <MetricCard label="Active Projects" value="12" delta="No change" icon={Briefcase} loading={loading} />
          </div>
        </Section>

        <Section title="EmptyState">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <EmptyState
                title="No employees yet"
                description="Add your first employee to get started."
                actionLabel="Add Employee"
                onAction={() => setClicks((c) => c + 1)}
              />
              <p data-testid="empty-state-clicks" className="text-xs text-[#71717A] mt-2">Action clicked: {clicks}</p>
            </div>
            <EmptyState variant="coming-soon" title="Analytics" description="This module is coming soon." />
          </div>
        </Section>

        <Section title="ChartCard">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ChartCard title="Employee Growth" subtitle="Last 5 months" loading={loading}>
              <SimpleBars />
            </ChartCard>
            <ChartCard title="Leave by Department" subtitle="This quarter" empty emptyText="No leave data yet." />
          </div>
        </Section>
      </div>
    </div>
  )
}

export default UiKitPage
