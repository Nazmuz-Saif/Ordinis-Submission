import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { groupByModule, moduleLabel } from '../../features/roles/roleFormat'

// Permissions in collapsible module sections: name, one-line description,
// "Select all" per section and a counter of how many are chosen.
function PermissionPicker({ permissions, selected, onChange }) {
  const [collapsed, setCollapsed] = useState({})
  const groups = groupByModule(permissions)

  function toggle(id) {
    onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id])
  }

  function toggleSection(perms) {
    const ids = perms.map((p) => p.id)
    const allChosen = ids.every((id) => selected.includes(id))
    onChange(allChosen ? selected.filter((id) => !ids.includes(id)) : [...new Set([...selected, ...ids])])
  }

  return (
    <div>
      <p className="text-xs text-[#71717A] mb-2" data-testid="perm-counter">
        {selected.length} of {permissions.length} selected
      </p>
      <div className="space-y-2">
        {groups.map(([module, perms]) => {
          const chosen = perms.filter((p) => selected.includes(p.id)).length
          const isOpen = !collapsed[module]
          return (
            <div key={module} className="border border-[#EEEEF2] rounded-lg">
              <div className="flex items-center justify-between px-3 py-2 bg-[#FAFAFA] rounded-t-lg">
                <button
                  type="button"
                  onClick={() => setCollapsed((c) => ({ ...c, [module]: isOpen }))}
                  className="flex items-center gap-1.5 text-sm font-semibold text-[#14142B]"
                  aria-expanded={isOpen}
                >
                  <ChevronDown size={14} className={`transition-transform duration-200 ${isOpen ? '' : '-rotate-90'}`} />
                  {moduleLabel(module)}
                  <span className="text-xs font-normal text-[#71717A]">({chosen}/{perms.length})</span>
                </button>
                <button
                  type="button"
                  onClick={() => toggleSection(perms)}
                  className="text-xs text-[#6C31D6] hover:underline"
                >
                  {chosen === perms.length ? 'Clear all' : 'Select all'}
                </button>
              </div>
              {isOpen && (
                <div className="p-3 grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-3">
                  {perms.map((perm) => (
                    <label key={perm.id} className="flex items-start gap-2.5 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={selected.includes(perm.id)}
                        onChange={() => toggle(perm.id)}
                        className="mt-0.5 rounded border-[#D1D5DB] text-[#6C31D6] focus:ring-[#6C31D6] w-4 h-4"
                      />
                      <span>
                        <span className="block text-sm font-medium text-[#14142B]">{perm.name}</span>
                        <span className="block text-xs text-[#71717A]">{perm.description}</span>
                      </span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default PermissionPicker
