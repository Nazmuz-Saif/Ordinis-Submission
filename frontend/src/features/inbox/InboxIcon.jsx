import { Bell, CheckSquare, ClipboardCheck, FileCheck2 } from 'lucide-react'

const ICONS = { approval: FileCheck2, task_review: ClipboardCheck, task: CheckSquare, notification: Bell }

export default function InboxIcon({ kind, size = 18 }) {
  const Icon = ICONS[kind] || Bell
  return <Icon size={size} aria-hidden="true" />
}
