import { apiClient } from '@/api/client'

const CSRF_COOKIE_NAME = 'csrftoken'

function readCookie(name: string) {
  const escapedName = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = document.cookie.match(new RegExp(`(?:^|; )${escapedName}=([^;]*)`))

  return match ? decodeURIComponent(match[1]) : null
}

export function getCsrfToken() {
  return readCookie(CSRF_COOKIE_NAME)
}

export async function ensureCsrfToken() {
  const currentToken = getCsrfToken()

  if (currentToken) {
    return currentToken
  }

  const { error } = await apiClient.GET('/api/v1/auth/csrf/', {
    credentials: 'include',
  })

  if (error) {
    throw new Error('Unable to initialize CSRF protection.')
  }

  const refreshedToken = getCsrfToken()

  if (!refreshedToken) {
    throw new Error('The CSRF cookie was not set by the backend.')
  }

  return refreshedToken
}
