import { useCallback, useEffect, useState } from 'react'
import { getSubscriptionsPage } from '../../services/adminService'
import StatusPill from '../../components/common/StatusPill'
import { formatDate as formatDay, monthsText } from '../subscribe/subscribeFormat'
import { DataTable, Notice, PageHeader } from './shared'
import { daysLeftCell } from './subscriptionFormat'
import { usePagedList } from './usePagedList'

const FILTERS = [
  { key: '', label: 'All' },
  { key: 'expiring', label: 'Expiring in 7 days' },
  { key: 'restricted', label: 'Expired or restricted' },
]
const STATE_PILL = {
  active: ['success', 'Active'],
  grace: ['warning', 'Grace period'],
  expired: ['failed', 'Expired'],
  pending_payment: ['info', 'Waiting for payment'],
  cancelled: ['neutral', 'Cancelled'],
}
const TONES = { red: 'text-[#B91C1C] font-semibold', amber: 'text-[#B45309] font-semibold', normal: 'text-[#14142B]', none: 'text-[#71717A]' }


function SubscriptionsPage() {
  const [filter, setFilter] = useState('')
  const [search, setSearch] = useState('')
  const [q, setQ] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => setQ(search.trim()), 300)
    return () => clearTimeout(timer)
  }, [search])

  const load = useCallback((page) => getSubscriptionsPage(page, { filter, q }), [filter, q])
  const list = usePagedList(load, `${filter}|${q}`)

  const columns = [
    {
      key: 'company', label: 'Company',
      render: (s) => (
        <>
          <p className="font-medium whitespace-nowrap">{s.company_name}</p>
          <p className="text-xs text-[#71717A]">{s.company_subdomain}{s.company_suspended ? ' · suspended' : ''}</p>
        </>
      ),
    },
    { key: 'plan', label: 'Plan', render: (s) => s.plan_name },
    {
      key: 'status', label: 'Status',
      render: (s) => {
        const [variant, label] = STATE_PILL[s.status] || STATE_PILL.cancelled
        return <StatusPill status={variant} label={label} />
      },
    },
    { key: 'length', label: 'Last paid length', render: (s) => (s.status === 'pending_payment' ? '-' : monthsText(s.billing_months)) },
    { key: 'ends', label: 'Ends', render: (s) => (s.status === 'pending_payment' ? '-' : <span className="whitespace-nowrap">{formatDay(s.period_end)}</span>) },
    {
      key: 'days', label: 'Days left',
      render: (s) => {
        const cell = daysLeftCell(s)
        return <span data-testid="days-left" data-tone={cell.tone} className={`whitespace-nowrap ${TONES[cell.tone]}`}>{cell.text}</span>
      },
    },
  ]

  return (
    <div className="space-y-5">
      <PageHeader title="Subscriptions" subtitle="Every company's plan and how many days it has left, soonest to end first." />
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#EEEEF2]">
        <div className="flex gap-1">
          {FILTERS.map((f) => (
            <button
              key={f.key || 'all'} type="button" data-testid={`filter-${f.key || 'all'}`} onClick={() => setFilter(f.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors duration-150 ${filter === f.key ? 'border-[#6C31D6] text-[#6C31D6]' : 'border-transparent text-[#71717A] hover:text-[#14142B]'}`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <input
          type="search" aria-label="Search companies" data-testid="subscriptions-search" placeholder="Company name"
          value={search} onChange={(e) => setSearch(e.target.value)}
          className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] bg-white w-64 mb-2"
        />
      </div>
      {list.error && <Notice>{list.error}</Notice>}
      <DataTable
        testId="subscriptions-table" rowTestId="subscription-row" columns={columns} rows={list.data?.items ?? []}
        list={list} page={list.page} onPage={list.setPage} emptyTitle="No companies" emptyText="Nothing to show for this filter."
      />
    </div>
  )
}

export default SubscriptionsPage
