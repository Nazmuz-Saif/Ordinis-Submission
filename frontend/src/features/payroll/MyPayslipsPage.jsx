import { Link } from 'react-router-dom'
import { getPayslipsPage } from '../../services/payrollService'
import { DataTable, Notice, PageHeader } from '../admin/shared'
import { usePagedList } from '../admin/usePagedList'
import { formatMoney } from './payslipFormat'

const load = (page) => getPayslipsPage(page, { mine: true })

const columns = [
  { key: 'month', label: 'Month', render: (p) => <span className="font-medium whitespace-nowrap">{p.month_label}</span> },
  { key: 'gross', label: 'Gross', render: (p) => formatMoney(p.gross_amount, p.currency) },
  { key: 'deductions', label: 'Deductions', render: (p) => formatMoney(p.deductions, p.currency) },
  { key: 'net', label: 'Net pay', render: (p) => <span className="font-semibold">{formatMoney(p.net_amount, p.currency)}</span> },
  {
    key: 'action', label: 'Action', align: 'right',
    render: (p) => (
      <Link to={`/payroll/payslips/${p.id}`} data-testid="view-payslip" className="border border-[#EEEEF2] hover:bg-[#FAFAFA] rounded-lg px-3 py-1.5 text-sm font-medium text-[#14142B]">View</Link>
    ),
  },
]

function MyPayslipsPage() {
  const list = usePagedList(load)
  return (
    <div className="space-y-5">
      <PageHeader title="My payslips" subtitle="Your own payslips, newest first. Only you and the finance team can open them." />
      {list.error && <Notice>{list.error}</Notice>}
      <DataTable
        testId="my-payslips-table" rowTestId="payslip-row" columns={columns} rows={list.data?.items ?? []}
        list={list} page={list.page} onPage={list.setPage} emptyTitle="No payslips yet" emptyText="Your payslips appear here once the finance team generates them."
      />
    </div>
  )
}

export default MyPayslipsPage
