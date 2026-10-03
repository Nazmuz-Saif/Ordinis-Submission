// Shows the company's subscription plan. Renders nothing unless the server sends a plan name.
function PlanBadge({ name }) {
  if (!name) return null
  return (
    <span
      data-testid="plan-badge"
      className="rounded-full bg-[#EDE9FE] text-[#6C31D6] text-[11px] font-semibold px-2 py-0.5"
    >
      {name}
    </span>
  )
}

export default PlanBadge
