// "Created Department" / "Updated Task" / "Refused" ... one readable line per row.
export function actionText(row) {
  if (row.action === 'denied') return 'Refused request'
  if (row.action === 'export') return 'Exported the audit log'
  if (row.action === 'read') return `Break-Glass read: ${row.object_repr}`
  return `${row.action_label} ${row.model_name}`.trim()
}

export function formatWhen(iso) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function moduleLabel(module) {
  return (module || '').replace(/_/g, ' ')
}
