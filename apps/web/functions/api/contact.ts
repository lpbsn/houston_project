import { validContact, type ContactResponse } from '../../shared/contact'

type Env = {
  RESEND_API_KEY?: string
  CONTACT_TO_EMAIL?: string
  CONTACT_FROM_EMAIL?: string
  TURNSTILE_SECRET_KEY?: string
}
type Context = { request: Request; env: Env }
const json = (body: ContactResponse, status = 200) => Response.json(body, {
  status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' },
})

// Same-origin, public marketing form. No application session or tenant access.
export async function onRequest({ request, env }: Context): Promise<Response> {
  if (request.method !== 'POST') return json({ ok: false, code: 'method_not_allowed' }, 405)
  const url = new URL(request.url)
  if (request.headers.get('Origin') !== url.origin) {
    return json({ ok: false, code: 'invalid_origin' }, 403)
  }
  if (!request.headers.get('Content-Type')?.startsWith('application/json')) {
    return json({ ok: false, code: 'invalid_request' }, 415)
  }
  if (!env.RESEND_API_KEY || !env.CONTACT_TO_EMAIL || !env.CONTACT_FROM_EMAIL ||
      !env.TURNSTILE_SECRET_KEY) return json({ ok: false, code: 'unavailable' }, 503)

  // Bound the body while streaming; do not trust Content-Length supplied by the caller.
  const reader = request.body?.getReader()
  if (!reader) return json({ ok: false, code: 'invalid_request' }, 400)
  let size = 0
  let raw = ''
  const decoder = new TextDecoder()
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      size += value.byteLength
      if (size > 32768) {
        await reader.cancel()
        return json({ ok: false, code: 'too_large' }, 413)
      }
      raw += decoder.decode(value, { stream: true })
    }
    raw += decoder.decode()
  } catch { return json({ ok: false, code: 'invalid_request' }, 400) }
  let data: unknown
  try { data = JSON.parse(raw) } catch { return json({ ok: false, code: 'invalid_request' }, 400) }
  if (!validContact(data) || data.website) return json({ ok: false, code: 'invalid_request' }, 400)

  try {
    const verification = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method: 'POST', signal: AbortSignal.timeout(8000),
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ secret: env.TURNSTILE_SECRET_KEY, response: data.token,
        remoteip: request.headers.get('CF-Connecting-IP') || undefined }),
    })
    if (!verification.ok) return json({ ok: false, code: 'unavailable' }, 503)
    const challenge = await verification.json() as { success?: boolean; hostname?: string; action?: string }
    if (!challenge.success || challenge.hostname !== url.hostname || challenge.action !== 'contact') {
      return json({ ok: false, code: 'verification_failed' }, 400)
    }
    // Stable key across retries; include the content hash so edited messages are distinct.
    const text = [
      'Nouvelle demande depuis la landing Spore',
      `Nom : ${data.name.trim()}`, `E-mail : ${data.email.trim()}`,
      `Établissement / groupe : ${data.organization.trim()}`,
      `Téléphone : ${data.phone.trim() || 'Non renseigné'}`, '', data.message.trim(),
    ].join('\n')
    const payload = { from: env.CONTACT_FROM_EMAIL, to: [env.CONTACT_TO_EMAIL],
      reply_to: data.email.trim(), subject: 'Spore — nouvelle demande de contact', text }
    const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(payload)))
    const digest = Array.from(new Uint8Array(hash), n => n.toString(16).padStart(2, '0')).join('')
    const sent = await fetch('https://api.resend.com/emails', {
      method: 'POST', signal: AbortSignal.timeout(10000),
      headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, 'Content-Type': 'application/json',
        'Idempotency-Key': `landing-${data.requestId}-${digest}` },
      body: JSON.stringify(payload),
    })
    if (!sent.ok) return json({ ok: false, code: 'send_failed' }, 503)
    const result = await sent.json() as { id?: string }
    if (!result.id) return json({ ok: false, code: 'send_failed' }, 503)
    return json({ ok: true })
  } catch {
    // Never return or log provider payloads, personal data or secrets.
    return json({ ok: false, code: 'unavailable' }, 503)
  }
}
