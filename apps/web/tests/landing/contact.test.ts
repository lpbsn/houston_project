import { afterEach, describe, expect, it, vi } from 'vitest'
import { onRequest } from '../../functions/api/contact'
const env = { RESEND_API_KEY: 'secret', CONTACT_TO_EMAIL: 'inbox@example.com', CONTACT_FROM_EMAIL: 'Spore <contact@example.com>', TURNSTILE_SECRET_KEY: 'secret-turnstile' }
const data = { name: 'Camille', email: 'camille@example.com', organization: 'Boutique', phone: '', message: 'Une démonstration.', website: '', token: 'valid-token', requestId: '5e7634e3-99c0-4abf-9234-cc3e20715abc' }
const request = (body: unknown = data, origin = 'https://spore-os.com') => new Request('https://spore-os.com/api/contact', { method: 'POST', headers: { Origin: origin, 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
const challenge = { success: true, hostname: 'spore-os.com', action: 'contact' }
afterEach(() => vi.unstubAllGlobals())
describe('landing contact endpoint', () => {
  it('uses only the configured recipient and the visitor as reply-to', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(challenge)).mockResolvedValueOnce(Response.json({ id: 'mail-id' }))
    vi.stubGlobal('fetch', fetcher)
    expect(await (await onRequest({ request: request({ ...data, to: 'attacker@example.com' }), env })).json()).toEqual({ ok: true })
    const email = JSON.parse(fetcher.mock.calls[1][1].body)
    expect(email.to).toEqual(['inbox@example.com']); expect(email.reply_to).toBe(data.email)
    expect(email.html).toBeUndefined(); expect(email.text).toContain(data.message)
  })
  it('fails closed when delivery is not configured', async () => {
    const fetcher = vi.fn(); vi.stubGlobal('fetch', fetcher)
    expect((await onRequest({ request: request(), env: {} })).status).toBe(503)
    expect(fetcher).not.toHaveBeenCalled()
  })
  it.each(['https://other.example', 'null', ''])('rejects another origin: %s', async origin => {
    expect((await onRequest({ request: request(data, origin), env })).status).toBe(403)
  })
  it.each([{ ...data, email: 'invalid' }, { ...data, message: ' ' }, { ...data, website: 'spam' }, { ...data, token: '' }, { ...data, message: 'x'.repeat(4001) }])('rejects invalid input', async payload => {
    const fetcher = vi.fn(); vi.stubGlobal('fetch', fetcher)
    expect((await onRequest({ request: request(payload), env })).status).toBe(400)
    expect(fetcher).not.toHaveBeenCalled()
  })
  it('bounds streamed input size', async () => {
    expect((await onRequest({ request: request({ ...data, message: 'x'.repeat(40000) }), env })).status).toBe(413)
  })
  it.each([{ ...challenge, success: false }, { ...challenge, hostname: 'evil.example' }, { ...challenge, action: 'login' }])('requires challenge, hostname and action', async result => {
    const fetcher = vi.fn().mockResolvedValue(Response.json(result)); vi.stubGlobal('fetch', fetcher)
    expect((await onRequest({ request: request(), env })).status).toBe(400)
    expect(fetcher).toHaveBeenCalledTimes(1)
  })
  it('does not report success or expose provider payload when delivery fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(Response.json(challenge)).mockResolvedValueOnce(Response.json({ error: env.CONTACT_TO_EMAIL }, { status: 500 })))
    const response = await onRequest({ request: request(), env })
    expect(response.status).toBe(503); expect(await response.json()).toEqual({ ok: false, code: 'send_failed' })
  })
  it('handles network failures without exposing secrets', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error(env.RESEND_API_KEY)))
    expect(await (await onRequest({ request: request(), env })).json()).toEqual({ ok: false, code: 'unavailable' })
  })
  it('deduplicates retries but allows edited messages', async () => {
    const keys: string[] = []
    vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
      if (url.includes('siteverify')) return Response.json(challenge)
      keys.push((init.headers as Record<string, string>)['Idempotency-Key']); return Response.json({ id: 'mail-id' })
    }))
    await onRequest({ request: request(), env })
    await onRequest({ request: request({ ...data, token: 'new-token' }), env })
    await onRequest({ request: request({ ...data, message: 'Autre question.' }), env })
    expect(keys[0]).toBe(keys[1]); expect(keys[2]).not.toBe(keys[0])
  })
})
