import { useEffect, useState } from 'react'
import { Check, UserRound } from 'lucide-react'
import { getProfile, updateProfile } from '../../services/authService'
import { useAuth } from '../../store/AuthContext'
import useUnsavedChangesGuard from '../../hooks/useUnsavedChangesGuard'

const EDITABLE = ['full_name', 'phone', 'address', 'emergency_contact_name', 'emergency_contact_phone']
const EMPLOYEE_ONLY = ['phone', 'address', 'emergency_contact_name', 'emergency_contact_phone']

const inputClass =
  'border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition w-full'

function toForm(profile) {
  const form = {}
  EDITABLE.forEach((key) => { form[key] = profile[key] || '' })
  return form
}

function ReadOnly({ label, value, testId }) {
  return (
    <div>
      <p className="text-xs text-[#71717A] mb-1">{label}</p>
      <p className="text-sm text-[#14142B] bg-[#FAFAFA] border border-[#EEEEF2] rounded-lg px-3 py-2 min-h-[38px]" data-testid={testId}>
        {value || '—'}
      </p>
    </div>
  )
}

function MyProfilePage() {
  const { refreshMe } = useAuth()
  const [profile, setProfile] = useState(null)
  const [form, setForm] = useState(null)
  const [saved, setSaved] = useState(null)      // the values as last loaded or saved, to detect changes
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [success, setSuccess] = useState('')

  useEffect(() => {
    getProfile()
      .then((data) => {
        setProfile(data)
        setForm(toForm(data))
        setSaved(toForm(data))
      })
      .catch(() => setError('Could not load your profile. Please reload the page.'))
      .finally(() => setLoading(false))
  }, [])

  const dirty = Boolean(form && saved && EDITABLE.some((key) => form[key] !== saved[key]))
  useUnsavedChangesGuard(dirty)

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
    setSuccess('')
    setFieldErrors((errs) => ({ ...errs, [e.target.name]: undefined }))
  }

  async function handleSave(e) {
    e.preventDefault()
    setError('')
    setSuccess('')
    setFieldErrors({})
    const isEmployee = Boolean(profile.employee_id)
    const keys = EDITABLE.filter((key) => isEmployee || !EMPLOYEE_ONLY.includes(key))
    const values = {}
    keys.forEach((key) => { values[key] = form[key].trim() })
    setSaving(true)
    try {
      const data = await updateProfile(values)
      setProfile(data)
      setForm(toForm(data))
      setSaved(toForm(data))
      setSuccess('Your profile was saved.')
      refreshMe()          // so the name in the top bar updates at once
    } catch (err) {
      const body = err.response?.data?.error
      setFieldErrors(body?.field_errors || {})
      setError(body?.message || 'Could not save your profile.')
    } finally {
      setSaving(false)
    }
  }

  function field(name, label, props = {}) {
    return (
      <div>
        <label htmlFor={`profile-${name}`} className="block text-xs text-[#71717A] mb-1">{label}</label>
        <input
          id={`profile-${name}`}
          name={name}
          value={form[name]}
          onChange={handleChange}
          className={`${inputClass} ${fieldErrors[name] ? 'border-red-400' : ''}`}
          {...props}
        />
        {fieldErrors[name] && (
          <p className="text-xs text-red-600 mt-1" data-testid={`error-${name}`}>{fieldErrors[name]}</p>
        )}
      </div>
    )
  }

  if (loading) return <p className="text-sm text-[#71717A]">Loading…</p>
  if (!profile) return <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-sm">{error}</div>

  const isEmployee = Boolean(profile.employee_id)

  return (
    <div className="pb-12 max-w-3xl">
      <div className="flex items-center gap-2 mb-1">
        <UserRound size={22} className="text-[#6C31D6]" />
        <h1 className="text-2xl font-bold text-[#14142B]">My Profile</h1>
      </div>
      <p className="text-sm text-[#71717A] mb-6">Your own details. You can update your name and contact information; the rest is set by your company.</p>

      {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-sm" data-testid="profile-error">{error}</div>}
      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm flex items-center gap-2" data-testid="profile-success">
          <Check size={14} /> {success}
        </div>
      )}

      <form onSubmit={handleSave} noValidate>
        <div className="bg-white rounded-xl border border-[#EEEEF2] p-6 mb-6">
          <h2 className="text-base font-semibold text-[#14142B] mb-4">Account</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {field('full_name', 'Full name', { maxLength: 150, required: true })}
            <ReadOnly label="Email (used to log in — cannot be changed here)" value={profile.email} testId="profile-email" />
            {isEmployee && (
              <>
                <ReadOnly label="Employee code" value={profile.employee_code} />
                <ReadOnly label="Designation" value={profile.designation_title} />
                <ReadOnly label="Department" value={profile.department_name} />
                <ReadOnly label="Reports to" value={profile.manager_name} />
                <ReadOnly label="Company" value={profile.company_name} testId="profile-company" />
                <ReadOnly label="Joined on" value={profile.joined_on} />
              </>
            )}
          </div>
        </div>

        {isEmployee && (
          <div className="bg-white rounded-xl border border-[#EEEEF2] p-6 mb-6">
            <h2 className="text-base font-semibold text-[#14142B] mb-4">Contact details</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {field('phone', 'Phone', { maxLength: 30, placeholder: '+880 1700-000000', inputMode: 'tel' })}
              {field('address', 'Address', { maxLength: 255 })}
              {field('emergency_contact_name', 'Emergency contact name', { maxLength: 100 })}
              {field('emergency_contact_phone', 'Emergency contact phone', { maxLength: 30, inputMode: 'tel' })}
            </div>
          </div>
        )}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={saving || !dirty}
            data-testid="profile-save"
            className="bg-[#6C31D6] hover:bg-[#5A28B0] disabled:opacity-50 text-white rounded-lg px-5 py-2 text-sm font-medium transition"
          >
            {saving ? 'Saving…' : 'Save changes'}
          </button>
          {dirty && <span className="text-xs text-[#71717A]">You have unsaved changes.</span>}
        </div>
      </form>
    </div>
  )
}

export default MyProfilePage
