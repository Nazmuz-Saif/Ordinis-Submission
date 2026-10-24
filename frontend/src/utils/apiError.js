// What the server said went wrong: { message, code, fields } from the standard error envelope.
export function readError(err, fallback = 'Something went wrong. Please try again.') {
  const e = err?.response?.data?.error
  return { message: e?.message || fallback, code: e?.code || '', fields: e?.field_errors || {} }
}

export function fieldText(fields, name) {
  const value = fields?.[name]
  return value ? (Array.isArray(value) ? value.join(' ') : String(value)) : ''
}
