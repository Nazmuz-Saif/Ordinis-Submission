import { personName } from '../../utils/people'
// Where a leave request is in its approval chain: the step it waits on, and every decision with its comment.
function ApprovalProgress({ approval }) {
  if (!approval) return <span className="text-xs text-[#71717A]">No approval</span>
  const { status, current_step: step, total_steps: total, current_step_role_name: role, actions } = approval
  return (
    <div data-testid="leave-approval" className="text-xs text-[#71717A] space-y-1 min-w-48 max-w-xs">
      {status === 'pending' && (
        <p data-testid="leave-approval-waiting" className="font-medium text-[#B45309]">
          Step {step} of {total} · waiting for {role}
        </p>
      )}
      {actions.map((a) => (
        <p key={`${a.step_order}-${a.created_at}`} data-testid="leave-approval-action">
          <span className={a.decision === 'approved' ? 'text-[#15803D]' : 'text-[#B91C1C]'}>
            Step {a.step_order} {a.decision}
          </span>{' '}
          by {personName(a.actor_name, a.actor_email)}
          {a.comment && <span data-testid="leave-approval-comment" className="block text-[#14142B] mt-0.5">“{a.comment}”</span>}
        </p>
      ))}
    </div>
  )
}

export default ApprovalProgress
