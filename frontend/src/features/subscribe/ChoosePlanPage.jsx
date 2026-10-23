import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check } from 'lucide-react'
import { getPlans, getQuote } from '../../services/billingService'
import { MAX_MONTHS, MIN_MONTHS, MONTH_CHOICES, validMonths } from '../../utils/subscription'
import { readError } from '../../utils/apiError'
import { formatMoney } from '../payroll/payslipFormat'
import SubscribeShell from './SubscribeShell'
import { formatDate, monthsText } from './subscribeFormat'

function ChoosePlanPage() {
  const navigate = useNavigate()
  const [plans, setPlans] = useState(null)
  const [plan, setPlan] = useState('')
  const [preset, setPreset] = useState(12)        // 1, 3, 6, 12 or null while a custom number is typed
  const [custom, setCustom] = useState('')
  const [result, setResult] = useState(null)     // { key, quote } or { key, error } for the last answer of the server
  const [loadError, setLoadError] = useState('')

  const months = preset ?? Number(custom)
  const monthsOk = validMonths(months)
  const key = `${plan}|${months}`
  // Only an answer for the plan and months on screen counts; an older answer is shown dimmed until the new one arrives.
  const fresh = result?.key === key ? result : null
  const quote = fresh?.quote ?? result?.quote ?? null
  const quoteError = fresh?.error || ''
  const quoting = monthsOk && Boolean(plan) && !fresh

  useEffect(() => {
    getPlans()
      .then((list) => {
        setPlans(list)
        setPlan((current) => current || list[0]?.name || '')
      })
      .catch(() => setLoadError('Could not load the plans. Please reload the page.'))
  }, [])

  // The live total always comes from the server, so the screen and the server never disagree.
  useEffect(() => {
    if (!plan || !monthsOk) return undefined
    let stale = false
    const timer = setTimeout(() => {
      getQuote(plan, months)
        .then((q) => {
          if (!stale) setResult({ key: `${plan}|${months}`, quote: q })
        })
        .catch((err) => {
          if (!stale) setResult({ key: `${plan}|${months}`, error: readError(err).message })
        })
    }, 200)
    return () => {
      stale = true
      clearTimeout(timer)
    }
  }, [plan, months, monthsOk])

  function pickPreset(n) {
    setPreset(n)
    setCustom('')
  }

  function typeCustom(value) {
    setCustom(value)
    setPreset(null)
  }

  const ready = Boolean(plan) && monthsOk && Boolean(fresh?.quote)

  return (
    <SubscribeShell
      step="plan"
      title="Choose your plan"
      subtitle="Pick a plan and how long you want to pay for. 12 months cost the price of 10. Your company starts as soon as the platform team approves your payment."
    >
      {loadError && <p role="alert" className="rounded-lg bg-[#DC2626]/10 text-[#B91C1C] text-sm px-4 py-3 mb-4">{loadError}</p>}

      <div className="grid gap-4 md:grid-cols-3" role="radiogroup" aria-label="Plan">
        {plans === null && !loadError && [0, 1, 2].map((n) => <div key={n} className="skeleton h-44 rounded-xl" />)}
        {plans?.map((p) => {
          const selected = plan === p.name
          return (
            <button
              type="button"
              key={p.id}
              role="radio"
              aria-checked={selected}
              data-testid={`plan-card-${p.name.toLowerCase()}`}
              onClick={() => setPlan(p.name)}
              className={`text-left bg-white rounded-xl border p-5 shadow-sm transition ${selected ? 'border-[#6C31D6] ring-2 ring-[#6C31D6]/20' : 'border-[#EEEEF2] hover:border-[#A78BFA]'}`}
            >
              <div className="flex items-center justify-between">
                <p className="text-lg font-bold text-[#14142B]">{p.name}</p>
                {selected && <Check size={18} className="text-[#6C31D6]" aria-label="Selected" />}
              </div>
              <p className="mt-3 text-2xl font-bold text-[#14142B]">{formatMoney(p.price_monthly, p.currency)}</p>
              <p className="text-xs text-[#71717A]">per month</p>
              <p className="mt-3 text-sm text-[#14142B]">{p.unlimited ? 'No employee limit' : `Up to ${p.max_employees} employees`}</p>
            </button>
          )
        })}
      </div>

      <div className="mt-8">
        <p className="text-sm font-medium text-[#14142B] mb-2">For how long?</p>
        <div className="flex flex-wrap items-center gap-2" role="radiogroup" aria-label="Months">
          {MONTH_CHOICES.map((n) => (
            <button
              type="button"
              key={n}
              role="radio"
              aria-checked={preset === n}
              data-testid={`months-option-${n}`}
              onClick={() => pickPreset(n)}
              className={`rounded-lg border px-4 py-2 text-sm font-medium transition ${preset === n ? 'border-[#6C31D6] bg-[#EDE9FE] text-[#6C31D6]' : 'border-[#EEEEF2] bg-white text-[#14142B] hover:border-[#A78BFA]'}`}
            >
              {monthsText(n)}
            </button>
          ))}
          <label className="flex items-center gap-2 text-sm text-[#71717A] ml-2">
            or
            <input
              type="number"
              min={MIN_MONTHS}
              max={MAX_MONTHS}
              step="1"
              inputMode="numeric"
              data-testid="months-custom"
              aria-label="Custom number of months"
              value={custom}
              onChange={(e) => typeCustom(e.target.value)}
              placeholder="1 to 36"
              className={`w-24 border rounded-lg px-3 py-2 text-sm outline-none transition ${preset === null ? 'border-[#6C31D6] ring-2 ring-[#6C31D6]/15' : 'border-[#EEEEF2]'}`}
            />
            months
          </label>
        </div>
        {preset === null && !monthsOk && (
          <p data-testid="months-hint" className="text-xs text-[#DC2626] mt-2">Enter a whole number of months from {MIN_MONTHS} to {MAX_MONTHS}.</p>
        )}
      </div>

      <div data-testid="quote-card" className="mt-8 bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5 max-w-xl">
        <p className="text-sm text-[#71717A]">Total to pay</p>
        {quote && monthsOk && !quoteError ? (
          <div className={quoting ? 'opacity-60 transition' : 'transition'}>
            <p data-testid="quote-total" className="text-3xl font-bold text-[#14142B] mt-1">{formatMoney(quote.amount, quote.currency)}</p>
            <p data-testid="quote-summary" className="text-sm text-[#14142B] mt-2">
              {quote.plan.name} for {monthsText(quote.months)} at {formatMoney(quote.monthly_price, quote.currency)} per month
            </p>
            {Number(quote.discount) > 0 && (
              <p data-testid="quote-discount" className="text-sm text-[#15803D] mt-1">
                You save {formatMoney(quote.discount, quote.currency)} ({quote.free_months} months free)
              </p>
            )}
            <p className="text-xs text-[#71717A] mt-2">
              Starts {formatDate(quote.period_start)} and ends {formatDate(quote.period_end)} once your payment is approved.
            </p>
          </div>
        ) : (
          <p className="text-sm text-[#71717A] mt-2">{monthsOk ? (quoteError ? '' : 'Working out the price...') : 'Choose how many months to see the price.'}</p>
        )}
        {quoteError && monthsOk && <p role="alert" data-testid="quote-error" className="text-sm text-[#B91C1C] mt-2">{quoteError}</p>}
      </div>

      <div className="mt-6">
        <button
          type="button"
          data-testid="plan-next"
          disabled={!ready}
          onClick={() => navigate(`/subscribe/pay?plan=${encodeURIComponent(plan)}&months=${months}`)}
          className="bg-[#6C31D6] hover:bg-[#5A28B0] disabled:opacity-50 text-white rounded-lg px-6 py-2 text-sm font-medium transition"
        >
          Next: pay
        </button>
      </div>
    </SubscribeShell>
  )
}

export default ChoosePlanPage
