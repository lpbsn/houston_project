import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('app and landing build isolation', () => {
  it('keeps the app Vite config free of PWA plugins', () => {
    const config = readFileSync(resolve(process.cwd(), 'vite.config.ts'), 'utf8')
    expect(config).not.toMatch(/from ['"]vite-plugin-pwa['"]/)
    expect(config).not.toMatch(/\bVitePWA\s*\(/)
    expect(config).toContain("outDir: isNativeBuild ? 'dist-native' : 'dist'")
    expect(config).toContain("base: isNativeBuild ? './' : '/'")
  })

  it('defines an independent landing Vite config without PWA', () => {
    const config = readFileSync(resolve(process.cwd(), 'vite.landing.config.ts'), 'utf8')
    expect(config).toContain("outDir:")
    expect(config).toContain('dist-landing')
    expect(config).toContain("publicDir:")
    expect(config).toContain('public-landing')
    expect(config).toContain("base: '/'")
    expect(config).toContain('emptyOutDir: true')
    expect(config).not.toMatch(/from ['"]vite-plugin-pwa['"]/)
    expect(config).not.toMatch(/\bVitePWA\s*\(/)
  })

  it('pins VITE_APP_RUNTIME on the Vite process and keeps tsc -b in full builds', () => {
    const pkg = JSON.parse(readFileSync(resolve(process.cwd(), 'package.json'), 'utf8')) as {
      scripts: Record<string, string>
    }
    expect(pkg.scripts.build).toBe(
      'tsc -b && VITE_APP_RUNTIME=web vite build && node scripts/validate-web-build.mjs',
    )
    expect(pkg.scripts['build:bundle']).toBe(
      'VITE_APP_RUNTIME=web vite build && node scripts/validate-web-build.mjs',
    )
    expect(pkg.scripts['build:native']).toBe(
      'tsc -b && VITE_APP_RUNTIME=native vite build && node scripts/validate-native-build.mjs',
    )
    expect(pkg.scripts['dev:native']).toBe('VITE_APP_RUNTIME=native vite')
    expect(pkg.scripts['build:landing']).toContain('vite.landing.config.ts')
    expect(pkg.scripts['build:landing']).toContain('validate-landing-build')
    expect(pkg.scripts['dev:landing']).toContain('vite.landing.config.ts')
  })
})
