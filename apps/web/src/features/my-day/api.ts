import { apiClient, withAuthRetry } from '@/api/client'
import type { components } from '@/api/generated/types'
import { parseStandardApiError } from '@/lib/api-errors'

export type MyDayTask = components['schemas']['MyDayTask']
export type MyDayCard = components['schemas']['MyDayCard']
export type MyDayResponse = components['schemas']['MyDayResponse']
export type MyDaySectionKey = 'action' | 'follow' | 'upcoming'

export class MyDayRequestError extends Error {
  status: number

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'MyDayRequestError'
    this.status = status
  }
}

export const myDayQueryKey = (establishmentId: string | null) =>
  ['action-plans', 'my-day', establishmentId] as const

async function requestMyDay(
  establishmentId: string,
  query: { section?: MyDaySectionKey, cursor?: string },
): Promise<MyDayResponse> {
  const result = await withAuthRetry(
    (accessToken) => apiClient.GET('/api/v1/establishments/{establishment_id}/my-day/', {
      params: {
        path: { establishment_id: establishmentId },
        query,
      },
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
    }),
    { refreshable: true },
  )
  if (result.response.ok && result.data) return result.data
  const parsed = parseStandardApiError(result.response, result.error)
  throw new MyDayRequestError(parsed.status, parsed.detail)
}

export function fetchMyDay(establishmentId: string) {
  return requestMyDay(establishmentId, {})
}

export function fetchMyDaySection(
  establishmentId: string,
  section: MyDaySectionKey,
  cursor: string,
) {
  return requestMyDay(establishmentId, { section, cursor })
}
