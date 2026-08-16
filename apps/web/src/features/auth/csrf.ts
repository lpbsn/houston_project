import { apiClient } from '@/api/client'

let cachedCsrfToken: string | null = null

export function clearCsrfTokenCache() {
  cachedCsrfToken = null
}

export async function ensureCsrfToken() {
  if (cachedCsrfToken) {
    return cachedCsrfToken
  }

  const { data, error } = await apiClient.GET('/api/v1/auth/csrf/', {
    credentials: 'include',
  })

  if (error || !data?.csrf_token) {
    throw new Error('Unable to initialize CSRF protection.')
  }

  cachedCsrfToken = data.csrf_token
  return cachedCsrfToken
}
