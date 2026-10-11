import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Printer } from 'lucide-react'
import { getPayslip } from '../../services/payrollService'
import EmptyState from '../../components/common/EmptyState'
import { formatMoney } from './payslipFormat'

// When printing, show only the payslip: hide the menu, the top bar and the buttons.
const PRINT_CSS = `@media print {
  body * { visibility: hidden; }
  #payslip-doc, #payslip-doc * { visibility: visible; }
  #payslip-doc { position: absolute; left: 0; top: 0; width: 100%; border: none; box-shadow: none; }
}`

function PayslipViewPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [payslip, setPayslip] = useState(null)
  const [state, setState] = useState('loading') // loading | ready | missing | error

  useEffect(() => {
    let active = true
    getPayslip(id)
      .then((data) => {
        if (!active) return
        setPayslip(data)
        setState('ready')
      })
      .catch((err) => {
        if (active) setState(err.response?.status === 404 ? 'missing' : 'error')
      })
    return () => {
      active = false
    }
  }, [id])

  if (state === 'loading') return <div className="skeleton h-64 w-full max-w-2xl rounded-xl" />
  if (state === 'missing') return <div data-testid="payslip-missing"><EmptyState title="Payslip not found" description="It does not exist, or it is not yours to open." /></div>
  if (state === 'error') return <div role="alert" className="rounded-lg bg-[#DC2626]/10 text-[#B91C1C] px-4 py-3 text-sm max-w-2xl">Failed to load the payslip.</div>

  const money = (v) => formatMoney(v, payslip.currency)
  const allowances = Object.entries(payslip.allowances || {})

  return (
    <div className="space-y-4 max-w-2xl">
      <style>{PRINT_CSS}</style>
      <div className="flex items-center justify-between">
        <button type="button" onClick={() => navigate(-1)} className="flex items-center gap-1.5 text-sm text-[#71717A] hover:text-[#14142B]">
          <ArrowLeft size={16} /> Back
        </button>
        <button type="button" data-testid="print-payslip" onClick={() => window.print()} className="flex items-center gap-1.5 border border-[#EEEEF2] bg-white hover:bg-[#FAFAFA] rounded-lg px-3 py-2 text-sm font-medium text-[#14142B]">
          <Printer size={16} /> Print
        </button>
      </div>

      <article id="payslip-doc" data-testid="payslip-doc" className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-6 space-y-5">
        <header className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-[#14142B]">Payslip</h1>
            <p data-testid="payslip-month-label" className="text-sm text-[#71717A]">{payslip.month_label}</p>
          </div>
          <div className="text-right text-sm">
            <p data-testid="payslip-employee-email" className="font-medium text-[#14142B]">{payslip.employee_email}</p>
            <p className="text-[#71717A]">{payslip.employee_code}</p>
          </div>
        </header>

        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[#71717A] border-b border-[#EEEEF2]"><th className="py-2 font-medium">Earnings</th><th className="py-2 font-medium text-right">Amount</th></tr>
          </thead>
          <tbody className="divide-y divide-[#EEEEF2]">
            <tr><td className="py-2">Base salary</td><td className="py-2 text-right">{money(payslip.base_salary)}</td></tr>
            {allowances.map(([name, amount]) => (
              <tr key={name} data-testid="payslip-allowance"><td className="py-2">{name}</td><td className="py-2 text-right">{money(amount)}</td></tr>
            ))}
            <tr className="font-semibold"><td className="py-2">Gross</td><td data-testid="payslip-gross" className="py-2 text-right">{money(payslip.gross_amount)}</td></tr>
            <tr>
              <td className="py-2">Deductions{payslip.deduction_note ? <span className="block text-xs text-[#71717A]">{payslip.deduction_note}</span> : null}</td>
              <td data-testid="payslip-deductions" className="py-2 text-right">- {money(payslip.deductions)}</td>
            </tr>
            <tr className="font-bold text-[#14142B]"><td className="py-3 text-base">Net pay</td><td data-testid="payslip-net" className="py-3 text-right text-base">{money(payslip.net_amount)}</td></tr>
          </tbody>
        </table>

        <footer className="text-xs text-[#71717A]">
          Generated {new Date(payslip.created_at).toLocaleDateString()} by {payslip.generated_by_email || 'finance'}.
        </footer>
      </article>
    </div>
  )
}

export default PayslipViewPage
