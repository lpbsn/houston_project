import { apiClient, withAuthRetry } from '@/api/client'
import type { components } from '@/api/generated/types'
import { parseStandardApiError } from '@/lib/api-errors'

export type MyDayTask = components['schemas']['MyDayTask']
export const myDayQueryKey = (establishmentId: string | null) =>
  ['action-plans', 'my-day', establishmentId] as const

export async function fetchMyDay(establishmentId: string, offset: number) {
  const result = await withAuthRetry(
    (accessToken) => apiClient.GET('/api/v1/establishments/{establishment_id}/my-day/', {
      params: { path: { establishment_id: establishmentId }, query: { offset } },
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
    }),
    { refreshable: true },
  )
  if (result.response.ok && result.data) return result.data
  throw new Error(parseStandardApiError(result.response, result.error).detail)
}
