import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const repoRoot = resolve(process.cwd(), '../..')

function readNginx(relativePath: string) {
  return readFileSync(resolve(repoRoot, relativePath), 'utf8')
}

function expectUnknownPathGuards(conf: string) {
  expect(conf).toContain('location ^~ /assets/')
  expect(conf).toContain('location ~ /\\.')
  expect(conf).toContain('return 404;')
  expect(conf).toContain('location ~* \\.[a-z0-9]+$')
  expect(conf).toContain('try_files $uri =404;')
  expect(conf).toContain('try_files $uri $uri/ /index.html;')
  expect(conf).toContain('location = /.well-known/apple-app-site-association')
  expect(conf).toContain('location = /.well-known/assetlinks.json')
}

describe('nginx unknown and sensitive paths', () => {
  it('404s hidden and missing static paths without removing the SPA fallback', () => {
    expectUnknownPathGuards(readNginx('infra/docker/web/nginx.conf'))
    expectUnknownPathGuards(readNginx('infra/docker/railway/nginx.conf'))
  })

  it('keeps Railway API and WebSocket prefixes ahead of the static regexes', () => {
    const conf = readNginx('infra/docker/railway/nginx.conf')
    expect(conf).toContain('location ^~ /api/')
    expect(conf).toContain('location ^~ /ws/')
  })
})
