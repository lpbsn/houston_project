import { useEffect, useRef, useState } from 'react'

type Turnstile = {
  render: (el: HTMLElement, options: Record<string, unknown>) => string
  remove: (id: string) => void
}
declare global { interface Window { turnstile?: Turnstile } }
let loading: Promise<void> | undefined
function loadWidget(): Promise<void> {
  if (window.turnstile) return Promise.resolve()
  if (!loading) loading = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
    script.async = true
    const timeout = window.setTimeout(() => { script.remove(); loading = undefined; reject(new Error('timeout')) }, 15000)
    script.onload = () => { window.clearTimeout(timeout); resolve() }
    script.onerror = () => { window.clearTimeout(timeout); script.remove(); loading = undefined; reject(new Error('load_failed')) }
    document.head.appendChild(script)
  })
  return loading
}

export function ContactVerification({ onToken }: { onToken: (token: string) => void }) {
  const container = useRef<HTMLDivElement>(null)
  const [failed, setFailed] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const sitekey = import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined
  useEffect(() => {
    if (!sitekey) return
    let disposed = false
    let widget: string | undefined
    void loadWidget().then(() => {
      if (disposed || !container.current || !window.turnstile) return
      widget = window.turnstile.render(container.current, {
        sitekey, action: 'contact', theme: 'light', size: 'flexible',
        callback: onToken,
        'expired-callback': () => onToken(''),
        'error-callback': () => { onToken(''); setFailed(true) },
      })
    }).catch(() => { if (!disposed) setFailed(true) })
    return () => { disposed = true; if (widget) window.turnstile?.remove(widget) }
  }, [sitekey, onToken, attempt])
  if (!sitekey) return <p role="alert">Le formulaire est momentanément indisponible. Merci de revenir un peu plus tard.</p>
  return <div>
    <div ref={container} />
    {failed && <p role="alert">La vérification n’a pas pu aboutir. <button type="button" onClick={() => {
      onToken(''); setFailed(false); setAttempt(n => n + 1)
    }}>Réessayer la vérification</button></p>}
  </div>
}
