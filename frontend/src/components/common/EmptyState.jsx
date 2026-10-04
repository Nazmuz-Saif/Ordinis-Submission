import { Inbox, Layers } from 'lucide-react'

// variant="empty"        -> there is no data yet (give the user an action when possible)
// variant="coming-soon"  -> the module itself is not built yet
function EmptyState({ title, description, actionLabel, onAction, icon: Icon, variant = 'empty' }) {
  const DefaultIcon = variant === 'coming-soon' ? Layers : Inbox
  const ShownIcon = Icon || DefaultIcon
  return (
    <div
      data-testid="empty-state"
      className="bg-white rounded-xl border border-dashed border-[#EEEEF2] py-12 px-6 flex flex-col items-center text-center"
    >
      <div className="w-12 h-12 rounded-xl bg-[#EDE9FE] text-[#6C31D6] flex items-center justify-center mb-4">
        <ShownIcon size={22} aria-hidden="true" />
      </div>
      <h3 className="text-base font-semibold text-[#14142B]">{title}</h3>
      {description && <p className="text-sm text-[#71717A] mt-1 max-w-sm">{description}</p>}
      {actionLabel && onAction && variant === 'empty' && (
        <button
          onClick={onAction}
          data-testid="empty-state-action"
          className="mt-5 bg-[#6C31D6] hover:bg-[#5A28B0] active:scale-[0.98] text-white rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150"
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}

export default EmptyState
