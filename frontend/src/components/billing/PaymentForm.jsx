import { useState } from 'react'
import { submitPayment } from '../../services/billingService'
import { fieldText, readError } from '../../utils/apiError'
import { formatMoney } from '../../features/payroll/payslipFormat'

const inputClass =
  'w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition'

// The form that reports a payment made outside the system. Used when a new company pays for the first time and,
// later, to renew. The amount shown is the server's quote and cannot be edited.
//   quote         the answer of GET /billing/quote/ for this plan and number of months
//   instructions  the answer of GET /billing/payment-instructions/
//   initial       values to start with (after a rejection: the previous method and payer)
//   invoiceId     the open renewal invoice being paid; the server then uses the invoice's plan, months and amount
function PaymentForm({ quote, instructions, initial = {}, invoiceId = '', submitLabel = 'Submit payment', onSubmitted, onAlreadyPending }) {
  const methods = instructions?.methods || []
  const [method, setMethod] = useState(initial.method || methods[0]?.method || 'bkash')
  const [payerName, setPayerName] = useState(initial.payer_name || '')
  const [payerNumber, setPayerNumber] = useState(initial.payer_number || '')
  const [transactionId, setTransactionId] = useState('')
  const [fields, setFields] = useState({})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const chosen = methods.find((m) => m.method === method)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setFields({})
    setBusy(true)
    try {
      const payment = await submitPayment({
        plan: quote.plan.name,
        months: quote.months,
        method,
        payer_name: payerName,
        payer_number: payerNumber,
        transaction_id: transactionId,
        amount: quote.amount,
        ...(invoiceId ? { invoice: invoiceId } : {}),
      })
      onSubmitted(payment)
    } catch (err) {
      const info = readError(err, 'The payment could not be sent. Please try again.')
      if (info.code === 'PAYMENT_ALREADY_PENDING' && onAlreadyPending) {
        onAlreadyPending()
        return
      }
      setFields(info.fields)
      setError(info.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} data-testid="payment-form" className="space-y-5">
      <div>
        <p className="text-sm font-medium text-[#14142B] mb-2">How did you pay?</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2" role="radiogroup" aria-label="Payment method">
          {methods.map((m) => (
            <button
              type="button"
              key={m.method}
              role="radio"
              aria-checked={method === m.method}
              data-testid={`payment-method-${m.method}`}
              onClick={() => setMethod(m.method)}
              className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${method === m.method ? 'border-[#6C31D6] bg-[#EDE9FE] text-[#6C31D6]' : 'border-[#EEEEF2] bg-white text-[#14142B] hover:border-[#A78BFA]'}`}
            >
              {m.label}
            </button>
          ))}
        </div>
        {fieldText(fields, 'method') && <p className="text-xs text-[#DC2626] mt-1">{fieldText(fields, 'method')}</p>}
        {chosen && (
          <div data-testid="payment-instructions" className="mt-3 rounded-lg bg-[#F1EEFB] text-sm text-[#14142B] px-4 py-3">
            <p className="font-medium">{chosen.label}</p>
            <p className="mt-1">{chosen.instructions}</p>
            {instructions?.note && <p className="mt-2 text-xs text-[#71717A]">{instructions.note}</p>}
          </div>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="payer-name" className="block text-sm text-[#14142B] mb-1">Name of the person who paid</label>
          <input id="payer-name" data-testid="payer-name" value={payerName} onChange={(e) => setPayerName(e.target.value)} className={inputClass} required />
          {fieldText(fields, 'payer_name') && <p className="text-xs text-[#DC2626] mt-1">{fieldText(fields, 'payer_name')}</p>}
        </div>
        <div>
          <label htmlFor="payer-number" className="block text-sm text-[#14142B] mb-1">Number the payment came from</label>
          <input id="payer-number" data-testid="payer-number" value={payerNumber} onChange={(e) => setPayerNumber(e.target.value)} placeholder="01XXXXXXXXX" className={inputClass} required />
          {fieldText(fields, 'payer_number') && <p className="text-xs text-[#DC2626] mt-1">{fieldText(fields, 'payer_number')}</p>}
        </div>
        <div>
          <label htmlFor="transaction-id" className="block text-sm text-[#14142B] mb-1">Transaction id</label>
          <input id="transaction-id" data-testid="transaction-id" value={transactionId} onChange={(e) => setTransactionId(e.target.value)} className={inputClass} required />
          <p className="text-xs text-[#71717A] mt-1">Exactly as your payment receipt shows it.</p>
          {fieldText(fields, 'transaction_id') && <p className="text-xs text-[#DC2626] mt-1">{fieldText(fields, 'transaction_id')}</p>}
        </div>
        <div>
          <label htmlFor="payment-amount" className="block text-sm text-[#14142B] mb-1">Amount to pay</label>
          <input id="payment-amount" data-testid="payment-amount" value={formatMoney(quote.amount, quote.currency)} readOnly className={`${inputClass} bg-[#FAFAFA] font-semibold`} />
          <p className="text-xs text-[#71717A] mt-1">Worked out by the server. It cannot be changed.</p>
        </div>
      </div>

      {error && (
        <p role="alert" data-testid="payment-error" className="rounded-lg bg-[#DC2626]/10 text-[#B91C1C] text-sm px-4 py-3">{error}</p>
      )}

      <button
        type="submit"
        disabled={busy}
        data-testid="payment-submit"
        className="bg-[#6C31D6] hover:bg-[#5A28B0] disabled:opacity-60 text-white rounded-lg px-5 py-2 text-sm font-medium transition"
      >
        {busy ? 'Sending...' : submitLabel}
      </button>
    </form>
  )
}

export default PaymentForm
