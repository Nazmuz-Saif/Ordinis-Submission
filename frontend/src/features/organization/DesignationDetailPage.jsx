import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, IdCard, Users } from 'lucide-react'
import EmptyState from '../../components/common/EmptyState'
import { getDesignationOverview } from '../../services/organizationService'
import { MembersTable } from './orgDetailParts'

function DesignationDetailPage() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    getDesignationOverview(id)
      .then((res) => { if (!cancelled) setData(res) })
      .catch((err) => { if (!cancelled) setError(err.response?.status === 404 ? 'This designation was not found.' : 'Failed to load this designation.') })
    return () => { cancelled = true }
  }, [id])

  const back = (
    <Link to="/organization/designations" className="inline-flex items-center gap-1 text-sm text-[#71717A] hover:text-[#6C31D6] mb-4">
      <ArrowLeft size={14} /> Designations
    </Link>
  )

  if (error) return <div>{back}<p className="text-sm text-[#DC2626]" data-testid="detail-error">{error}</p></div>
  if (!data) return <div>{back}<p className="text-sm text-[#71717A]">Loading...</p></div>

  return (
    <div>
      {back}
      <div className="flex items-start gap-3 mb-6">
        <div className="w-11 h-11 rounded-xl bg-[#6C31D6]/10 text-[#6C31D6] flex items-center justify-center shrink-0">
          <IdCard size={22} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[#14142B]" data-testid="designation-title">{data.title}</h1>
          <p className="text-sm text-[#71717A] mt-1" data-testid="designation-count-line">
            {data.employee_count} {data.employee_count === 1 ? 'person holds' : 'people hold'} this designation
          </p>
        </div>
      </div>
      {data.employees.length === 0
        ? <EmptyState icon={Users} title="Nobody holds this designation" description="Give it to an employee from the Employees page." />
        : <MembersTable members={data.employees} showDepartment showDesignation={false} />}
    </div>
  )
}

export default DesignationDetailPage
