// Shared helpers for the Roles screens. Permission names, modules and descriptions come only from the server.

export function moduleLabel(module) {
  return (module || 'other').replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())
}

export function groupByModule(perms) {
  const groups = {}
  perms.forEach((p) => {
    const key = p.module || 'other'
    if (!groups[key]) groups[key] = []
    groups[key].push(p)
  })
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
}

export function errorMessage(err, fallback) {
  return err.response?.data?.error?.message || err.response?.data?.detail || fallback
}
