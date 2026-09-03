import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { assertNoPwaBuildArtifacts } from './validate-build-artifacts.mjs'

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const distRoot = resolve(webRoot, 'dist')

function fail(message) {
  console.error(`web build validation failed: ${message}`)
  process.exit(1)
}

const indexPath = resolve(distRoot, 'index.html')
if (!existsSync(indexPath)) {
  fail('missing index.html')
}

const assetsDir = resolve(distRoot, 'assets')
if (!existsSync(assetsDir)) {
  fail('missing assets/')
}

const hashedJs = readdirSync(assetsDir).filter((file) => /^.+-[A-Za-z0-9]+\.js$/.test(file))
if (hashedJs.length === 0) {
  fail('expected hashed JS assets')
}

const html = readFileSync(indexPath, 'utf8')
if (!html.includes('src="/assets/') && !html.includes("src='/assets/")) {
  fail('index.html should reference absolute /assets/ URLs')
}

assertNoPwaBuildArtifacts(distRoot, html, fail)

const publicWellKnown = resolve(webRoot, 'public/.well-known')
const distWellKnown = resolve(distRoot, '.well-known')
if (!existsSync(resolve(publicWellKnown, '.gitkeep'))) {
  fail('missing public/.well-known serving path')
}
if (!existsSync(resolve(distWellKnown, '.gitkeep'))) {
  fail('Vite did not copy public/.well-known into dist/')
}
if (
  existsSync(resolve(publicWellKnown, 'apple-app-site-association')) ||
  existsSync(resolve(distWellKnown, 'apple-app-site-association'))
) {
  fail('do not publish apple-app-site-association until the App Store Team ID exists')
}
const publicAssetLinks = resolve(publicWellKnown, 'assetlinks.json')
const distAssetLinks = resolve(distWellKnown, 'assetlinks.json')
if (existsSync(publicAssetLinks) !== existsSync(distAssetLinks)) {
  fail('assetlinks.json must copy from public/.well-known to dist/')
}

for (const file of hashedJs) {
  const source = readFileSync(resolve(assetsDir, file), 'utf8')
  if (source.includes('capacitor-secure-storage') || source.includes('@aparajita')) {
    fail('web dist must not include native Keychain/Keystore storage')
  }
  if (
    source.includes('@capacitor-firebase/messaging') ||
    source.includes('firebase-messaging-sw')
  ) {
    fail('web dist must not include native FCM or a Firebase messaging service worker')
  }
}

console.log('web build validation ok')
