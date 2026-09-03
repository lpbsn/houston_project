import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

import { assertProductionAssetLinks } from '@/lib/digital-asset-links'

const repoRoot = resolve(process.cwd(), '../..')
const webRoot = process.cwd()

function nginxWellKnownLocations(conf: string) {
  expect(conf).toContain('location = /.well-known/apple-app-site-association')
  expect(conf).toContain('location = /.well-known/assetlinks.json')
  expect(conf).toContain('try_files $uri =404')
  expect(conf).toContain('default_type application/json')
}

describe('app links association serving path', () => {
  it('keeps dedicated nginx 404s for association files on local and Railway web', () => {
    nginxWellKnownLocations(
      readFileSync(resolve(repoRoot, 'infra/docker/web/nginx.conf'), 'utf8'),
    )
    nginxWellKnownLocations(
      readFileSync(resolve(repoRoot, 'infra/docker/railway/nginx.conf'), 'utf8'),
    )
  })

  it('reserves Vite public/.well-known without serving store association files', () => {
    const wellKnown = resolve(webRoot, 'public/.well-known')
    expect(existsSync(resolve(wellKnown, '.gitkeep'))).toBe(true)
    expect(existsSync(resolve(wellKnown, 'assetlinks.json'))).toBe(false)
    expect(existsSync(resolve(wellKnown, 'apple-app-site-association'))).toBe(false)
  })

  it('validates assetlinks.json only when a real file is committed', () => {
    const assetlinksPath = resolve(webRoot, 'public/.well-known/assetlinks.json')
    if (!existsSync(assetlinksPath)) {
      return
    }
    assertProductionAssetLinks(readFileSync(assetlinksPath, 'utf8'))
  })

  it('keeps Android App Links host and iOS Associated Domains on app.spore-os.com', () => {
    const manifest = readFileSync(
      resolve(webRoot, 'android/app/src/main/AndroidManifest.xml'),
      'utf8',
    )
    const entitlements = readFileSync(resolve(webRoot, 'ios/App/App/App.entitlements'), 'utf8')
    expect(manifest).toContain('android:autoVerify="true"')
    expect(manifest).toContain('android:scheme="https"')
    expect(manifest).toContain('android:host="app.spore-os.com"')
    expect(entitlements).toContain('applinks:app.spore-os.com')
  })
})
