import { personName } from '../../utils/people'

// A person in a table cell or a list: the full name first, then a small line.
// `sub` defaults to the email when the person has a name (so nothing is lost), and to nothing otherwise.
function Person({ name, email, sub }) {
  const hasName = Boolean(name && name.trim())
  const small = sub !== undefined ? sub : hasName ? email : null
  return (
    <span className="block min-w-0">
      <span className="block font-medium text-[#14142B] truncate">{personName(name, email)}</span>
      {small ? <span className="block text-xs text-[#71717A] truncate">{small}</span> : null}
    </span>
  )
}

export default Person
