/** Public contract for the landing-only Pages endpoint. Never contains server configuration. */
export type ContactRequest = {
  name: string
  email: string
  organization: string
  phone: string
  message: string
  website: string
  token: string
  requestId: string
}
export type ContactResponse = { ok: true } | { ok: false; code: string }

export function validContact(value: unknown): value is ContactRequest {
  if (!value || typeof value !== 'object') return false
  const v = value as Record<string, unknown>
  const field = (key: string, min: number, max: number) =>
    typeof v[key] === 'string' && v[key].trim().length >= min && v[key].length <= max
  return field('name', 1, 120) && field('organization', 1, 180) &&
    field('email', 3, 254) && /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(v.email as string) &&
    field('phone', 0, 40) && field('message', 1, 4000) && field('website', 0, 200) &&
    field('token', 1, 2048) && typeof v.requestId === 'string' &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v.requestId)
}
