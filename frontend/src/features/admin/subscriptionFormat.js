// What the "days left" cell says and how loudly: expired is red, 7 days or fewer is amber.
export function daysLeftCell(row) {
  const left = row.days_left
  if (left === null || left === undefined) return { tone: 'none', text: '-' }
  if (row.status === 'expired') return { tone: 'red', text: left < 0 ? `Expired ${-left} ${-left === 1 ? 'day' : 'days'} ago` : 'Expired' }
  if (left < 0) return { tone: 'amber', text: `Ended ${-left} ${-left === 1 ? 'day' : 'days'} ago` }
  if (left === 0) return { tone: 'amber', text: 'Ends today' }
  return { tone: left <= 7 ? 'amber' : 'normal', text: `${left} ${left === 1 ? 'day' : 'days'}` }
}
