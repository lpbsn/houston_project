import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('landing build isolation', () => {
  it('keeps the app PWA start_url at /', () => {
    const config = readFileSync(resolve(process.cwd(), 'vite.config.ts'), 'utf8')
    expect(config).toContain("start_url: '/'")
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

  it('registers landing build scripts', () => {
    const pkg = JSON.parse(readFileSync(resolve(process.cwd(), 'package.json'), 'utf8')) as {
      scripts: Record<string, string>
    }
    expect(pkg.scripts['build:landing']).toContain('vite.landing.config.ts')
    expect(pkg.scripts['build:landing']).toContain('validate-landing-build')
    expect(pkg.scripts['dev:landing']).toContain('vite.landing.config.ts')
  })
})
