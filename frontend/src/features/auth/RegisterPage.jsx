import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { registerCompany } from '../../services/authService'
import { useAuth } from '../../store/AuthContext'

const inputClass =
  'w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition'

function slugify(value) {
  return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
}

function RegisterPage() {
  const [form, setForm] = useState({
    company_name: '',
    subdomain: '',
    industry: '',
    ceo_email: '',
    ceo_password: '',
  })
  const [subdomainTouched, setSubdomainTouched] = useState(false)
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { refreshMe } = useAuth()

  function handleChange(e) {
    const { name, value } = e.target
    setForm((prev) => {
      const next = { ...prev, [name]: value }
      // Suggest a subdomain from the company name until the user edits it themselves.
      if (name === 'company_name' && !subdomainTouched) next.subdomain = slugify(value)
      return next
    })
    if (name === 'subdomain') setSubdomainTouched(true)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setFieldErrors({})
    setLoading(true)
    try {
      await registerCompany({
        company_name: form.company_name,
        subdomain: form.subdomain,
        industry: form.industry,
        ceo_email: form.ceo_email,
        ceo_password: form.ceo_password,
      })
      await refreshMe()
      navigate('/organization')
    } catch (err) {
      const data = err.response?.data?.error
      setFieldErrors(data?.field_errors || {})
      setError(data?.message ? 'Please fix the highlighted fields.' : 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  function fieldError(name) {
    const e = fieldErrors[name]
    return e ? <p className="text-xs text-[#DC2626] mt-1">{Array.isArray(e) ? e.join(' ') : String(e)}</p> : null
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center px-4 py-10">
      <div className="bg-white/70 backdrop-blur-xl border border-white/30 shadow-lg rounded-xl p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-[#14142B] mb-1">Create your company</h1>
        <p className="text-sm text-[#71717A] mb-6">
          Set up your Ordinis workspace. You will be its CEO.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-[#14142B] mb-1">Company name</label>
            <input name="company_name" value={form.company_name} onChange={handleChange} className={inputClass} required />
            {fieldError('company_name')}
          </div>

          <div>
            <label className="block text-sm text-[#14142B] mb-1">Subdomain</label>
            <input name="subdomain" value={form.subdomain} onChange={handleChange} placeholder="acme" className={inputClass} required />
            <p className="text-xs text-[#71717A] mt-1">Letters, numbers, and hyphens only.</p>
            {fieldError('subdomain')}
          </div>

          <div>
            <label className="block text-sm text-[#14142B] mb-1">Industry (optional)</label>
            <input name="industry" value={form.industry} onChange={handleChange} className={inputClass} />
            {fieldError('industry')}
          </div>

          <div>
            <label className="block text-sm text-[#14142B] mb-1">Your email</label>
            <input type="email" name="ceo_email" value={form.ceo_email} onChange={handleChange} className={inputClass} required />
            {fieldError('ceo_email')}
          </div>

          <div>
            <label className="block text-sm text-[#14142B] mb-1">Password</label>
            <input type="password" name="ceo_password" value={form.ceo_password} onChange={handleChange} minLength={8} className={inputClass} required />
            <p className="text-xs text-[#71717A] mt-1">At least 8 characters.</p>
            {fieldError('ceo_password')}
          </div>

          {error && <p className="text-sm text-[#DC2626]">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#6C31D6] hover:bg-[#5A28B0] disabled:opacity-60 text-white rounded-lg py-2 text-sm font-medium transition"
          >
            {loading ? 'Creating...' : 'Create company'}
          </button>
        </form>

        <p className="text-sm text-[#71717A] mt-6 text-center">
          Already registered?{' '}
          <Link to="/login" className="text-[#6C31D6] hover:underline font-medium">
            Login
          </Link>
        </p>
      </div>
    </div>
  )
}

export default RegisterPage
