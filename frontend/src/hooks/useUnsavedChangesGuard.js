import { useEffect } from 'react'

// Warns before the person leaves a page with unsaved changes: closing or reloading the tab,
// and clicking any link inside the app (the app uses BrowserRouter, which has no route blocker).
export default function useUnsavedChangesGuard(dirty, message = 'You have unsaved changes. Leave this page and lose them?') {
  useEffect(() => {
    if (!dirty) return undefined

    function onBeforeUnload(e) {
      e.preventDefault()
      e.returnValue = ''
    }

    function onClick(e) {
      const link = e.target.closest?.('a[href]')
      if (!link || link.target === '_blank') return
      const url = new URL(link.href, window.location.href)
      if (url.origin !== window.location.origin) return
      if (url.pathname === window.location.pathname) return
      if (!window.confirm(message)) {
        e.preventDefault()
        e.stopPropagation()
      }
    }

    window.addEventListener('beforeunload', onBeforeUnload)
    document.addEventListener('click', onClick, true)   // capture: runs before the router sees the click
    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload)
      document.removeEventListener('click', onClick, true)
    }
  }, [dirty, message])
}
