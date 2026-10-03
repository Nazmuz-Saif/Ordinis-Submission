import { useEffect } from 'react'

// Calls `onOutside` when the user clicks outside the element held by `ref`.
export default function useClickOutside(ref, onOutside, active = true) {
  useEffect(() => {
    if (!active) return undefined
    function handle(event) {
      if (ref.current && !ref.current.contains(event.target)) onOutside()
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [ref, onOutside, active])
}
