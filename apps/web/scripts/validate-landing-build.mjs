import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const distRoot = resolve(webRoot, 'dist-landing')

const requiredFiles = [
  'index.html',
  'mentions-legales/index.html',
  'robots.txt',
  'sitemap.xml',
]

const expectedCanonicals = {
  'index.html': 'https://spore-os.com/',
  'mentions-legales/index.html': 'https://spore-os.com/mentions-legales/',
}

function fail(message) {
  console.error(`landing build validation failed: ${message}`)
  process.exit(1)
}

for (const relativePath of requiredFiles) {
  const absolutePath = resolve(distRoot, relativePath)
  if (!existsSync(absolutePath)) {
    fail(`missing ${relativePath}`)
  }
}

const assetsDir = resolve(distRoot, 'assets')
if (!existsSync(assetsDir)) {
  fail('missing assets/')
}

for (const [relativePath, canonical] of Object.entries(expectedCanonicals)) {
  const html = readFileSync(resolve(distRoot, relativePath), 'utf8')
  const needle = `href="${canonical}"`
  if (!html.includes('rel="canonical"') || !html.includes(needle)) {
    fail(`${relativePath} missing canonical ${canonical}`)
  }
}

console.log('landing build validation ok')
