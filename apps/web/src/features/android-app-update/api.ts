import { apiClient } from '@/api/client'

export async function fetchAndroidMinSupportedVersionCode(): Promise<number | null> {
  try {
    const { data, error, response } = await apiClient.GET('/api/v1/client-requirements/')
    if (error || !response.ok || data == null) {
      return null
    }
    const value = data.android_min_supported_version_code
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) {
      return null
    }
    return value
  } catch {
    return null
  }
}
