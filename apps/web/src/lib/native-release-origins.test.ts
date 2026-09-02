import { describe, expect, it } from 'vitest'

import {
  NATIVE_RELEASE_ORIGIN,
  assertNativeReleaseBundleText,
  assertNativeReleaseEnv,
  assertNativeReleaseOrigin,
  findForbiddenNativeReleaseHosts,
} from '../../scripts/native-release-origins.mjs'

describe('native release origins', () => {
  it('accepts the pinned production origin', () => {
    expect(() => assertNativeReleaseOrigin(NATIVE_RELEASE_ORIGIN, 'VITE_API_BASE_URL')).not.toThrow()
    expect(() =>
      assertNativeReleaseOrigin(`${NATIVE_RELEASE_ORIGIN}/`, 'VITE_PUBLIC_APP_URL'),
    ).not.toThrow()
  })

  it('rejects loopback, http, and other hosts', () => {
    expect(() => assertNativeReleaseOrigin('http://localhost:8000', 'VITE_API_BASE_URL')).toThrow(
      /must be https:\/\/app\.spore-os\.com/,
    )
    expect(() => assertNativeReleaseOrigin('https://api.example.test', 'VITE_API_BASE_URL')).toThrow(
      /must be https:\/\/app\.spore-os\.com/,
    )
    expect(() => assertNativeReleaseOrigin('https://app.spore-os.com/login', 'VITE_PUBLIC_APP_URL')).toThrow(
      /must be https:\/\/app\.spore-os\.com/,
    )
  })

  it('requires both env vars for a store bake', () => {
    expect(() =>
      assertNativeReleaseEnv({
        VITE_API_BASE_URL: NATIVE_RELEASE_ORIGIN,
        VITE_PUBLIC_APP_URL: NATIVE_RELEASE_ORIGIN,
      }),
    ).not.toThrow()
    expect(() =>
      assertNativeReleaseEnv({
        VITE_API_BASE_URL: 'http://10.0.2.2:8000',
        VITE_PUBLIC_APP_URL: NATIVE_RELEASE_ORIGIN,
      }),
    ).toThrow(/VITE_API_BASE_URL/)
  })

  it('rejects baked loopback hosts and requires the production origin in the bundle', () => {
    expect(findForbiddenNativeReleaseHosts('api at http://localhost:8000')).toEqual([
      'http://localhost',
    ])
    expect(findForbiddenNativeReleaseHosts('const loopbacks=["localhost","127.0.0.1"]')).toEqual([])
    expect(() =>
      assertNativeReleaseBundleText(`const api=${JSON.stringify(NATIVE_RELEASE_ORIGIN)}`),
    ).not.toThrow()
    expect(() =>
      assertNativeReleaseBundleText(
        `const api=${JSON.stringify(NATIVE_RELEASE_ORIGIN)};const bad="http://localhost:8000"`,
      ),
    ).toThrow(/http:\/\/localhost/)
    expect(() => assertNativeReleaseBundleText('no origin here')).toThrow(/must embed/)
  })
})
