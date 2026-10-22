// How a person is shown everywhere: the full name first, the email (or code) only as small text.
// Old rows have no name: the email is shown instead, so a page is never blank.

export function personName(name, email) {
  return (name && name.trim()) || email || '—'
}

export function personInitials(name, email) {
  const clean = (name || '').trim()
  if (clean) {
    const parts = clean.split(/\s+/)
    return (parts.length > 1 ? parts[0][0] + parts[parts.length - 1][0] : clean.slice(0, 2)).toUpperCase()
  }
  return (email || '?').split('@')[0].slice(0, 2).toUpperCase()
}
