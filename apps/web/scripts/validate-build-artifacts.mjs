import { existsSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'

export function assertNoPwaBuildArtifacts(distRoot, html, fail) {
  if (existsSync(resolve(distRoot, 'sw.js'))) {
    fail('sw.js must not be emitted')
  }
  if (existsSync(resolve(distRoot, 'manifest.webmanifest'))) {
    fail('manifest.webmanifest must not be emitted')
  }
  if (html.includes('apple-mobile-web-app-capable')) {
    fail('index.html must not include apple-mobile-web-app-capable')
  }
  if (html.includes('rel="manifest"') || html.includes('manifest.webmanifest')) {
    fail('index.html must not reference a web app manifest')
  }

  const workboxFiles = readdirSync(distRoot).filter((file) => /^workbox-.*\.js$/.test(file))
  if (workboxFiles.length > 0) {
    fail(`workbox runtime must not be emitted (${workboxFiles.join(', ')})`)
  }
}
