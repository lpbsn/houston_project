import type { ContactRequest, ContactResponse } from '../../../shared/contact'

export async function sendContact(data: ContactRequest): Promise<void> {
  const response = await fetch('/api/contact', {
    method: 'POST', credentials: 'omit', signal: AbortSignal.timeout(25000),
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
  const result = await response.json() as ContactResponse
  if (!response.ok || result.ok !== true) throw new Error('contact_failed')
}
