import { apiClient, withAuthRetry } from '@/api/client'

export type PlayStoreAccessStatus = 'none' | 'pending' | 'accepted'

export async function fetchPlayStoreAccess(): Promise<PlayStoreAccessStatus> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/auth/me/play-store-access/', {
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
      }),
    { refreshable: true },
  )
  if (result.error || !result.data) {
    return 'none'
  }
  return result.data.status
}

export async function submitPlayStoreAccess(input: {
  googlePlayEmail: string
  establishmentId?: string
}): Promise<void> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/auth/me/play-store-access/', {
        body: {
          google_play_email: input.googlePlayEmail,
          ...(input.establishmentId ? { establishment_id: input.establishmentId } : {}),
        },
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
      }),
    { refreshable: true },
  )
  if (result.error || result.data?.status !== 'accepted') {
    throw new Error('play_store_access_failed')
  }
}
