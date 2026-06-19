import { apiClient, withAuthRetry } from '@/api/client'

import type { OperationalRealtimeWsTicketResponse } from './types'

function getAuthHeaders(accessToken: string | null) {
  return accessToken
    ? {
        Authorization: `Bearer ${accessToken}`,
      }
    : undefined
}

function realtimePathParams(establishmentId: string) {
  return {
    path: {
      establishment_id: establishmentId,
    },
  }
}

function assertRealtimeTicketData(result: {
  response: Response
  data?: OperationalRealtimeWsTicketResponse
  error?: unknown
}): OperationalRealtimeWsTicketResponse {
  if (result.response.ok && result.data !== undefined) {
    return result.data
  }

  throw new Error('Failed to issue operational realtime WebSocket ticket.')
}

export async function issueOperationalRealtimeWsTicket(
  establishmentId: string,
): Promise<OperationalRealtimeWsTicketResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/realtime/ws-ticket/', {
        params: realtimePathParams(establishmentId),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertRealtimeTicketData(result)
}
