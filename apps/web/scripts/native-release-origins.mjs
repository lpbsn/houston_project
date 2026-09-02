export const NATIVE_RELEASE_ORIGIN = 'https://app.spore-os.com'

const FORBIDDEN_BAKED_URL_MARKERS = [
  'http://localhost',
  'https://localhost',
  'http://127.0.0.1',
  'https://127.0.0.1',
  'http://10.0.2.2',
  'https://10.0.2.2',
  'ws://localhost',
  'ws://127.0.0.1',
  'ws://10.0.2.2',
]

function trimTrailingSlash(value) {
  return value.replace(/\/+$/, '')
}

export function assertNativeReleaseOrigin(value, label) {
  const trimmed = trimTrailingSlash((value ?? '').trim())
  if (trimmed !== NATIVE_RELEASE_ORIGIN) {
    throw new Error(
      `${label} must be ${NATIVE_RELEASE_ORIGIN} for a Native store build (got ${JSON.stringify(value)}).`,
    )
  }
}

export function findForbiddenNativeReleaseHosts(text) {
  return FORBIDDEN_BAKED_URL_MARKERS.filter((marker) => text.includes(marker))
}

export function assertNativeReleaseEnv(env = process.env) {
  assertNativeReleaseOrigin(env.VITE_API_BASE_URL, 'VITE_API_BASE_URL')
  assertNativeReleaseOrigin(env.VITE_PUBLIC_APP_URL, 'VITE_PUBLIC_APP_URL')
}

export function assertNativeReleaseBundleText(bundleText) {
  const forbidden = findForbiddenNativeReleaseHosts(bundleText)
  if (forbidden.length > 0) {
    throw new Error(
      `Native store bundle must not contain local/test hosts (${forbidden.join(', ')}).`,
    )
  }
  if (!bundleText.includes(NATIVE_RELEASE_ORIGIN)) {
    throw new Error(
      `Native store bundle must embed ${NATIVE_RELEASE_ORIGIN}.`,
    )
  }
}
