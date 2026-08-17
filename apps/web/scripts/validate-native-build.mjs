import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { assertNoPwaBuildArtifacts } from './validate-build-artifacts.mjs'

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const distRoot = resolve(webRoot, 'dist-native')

function fail(message) {
  console.error(`native build validation failed: ${message}`)
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
if (html.includes('src="/assets/') || html.includes("src='/assets/")) {
  fail('index.html should not use origin-absolute /assets/ URLs')
}
if (!html.includes('src="./assets/') && !html.includes('src="assets/')) {
  fail('index.html should reference relative asset URLs')
}

assertNoPwaBuildArtifacts(distRoot, html, fail)

console.log('native build validation ok')
