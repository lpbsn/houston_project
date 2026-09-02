import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const distRoot = resolve(webRoot, 'dist-landing')

const requiredFiles = [
  'index.html',
  'mentions-legales/index.html',
  'supprimer-compte/index.html',
  'politique-de-confidentialite/index.html',
  'conditions-d-utilisation/index.html',
  'robots.txt',
  'sitemap.xml',
  '_redirects',
]

const expectedCanonicals = {
  'index.html': 'https://spore-os.com/',
  'mentions-legales/index.html': 'https://spore-os.com/mentions-legales/',
  'supprimer-compte/index.html': 'https://spore-os.com/supprimer-compte/',
  'politique-de-confidentialite/index.html':
    'https://spore-os.com/politique-de-confidentialite/',
  'conditions-d-utilisation/index.html': 'https://spore-os.com/conditions-d-utilisation/',
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

const redirects = readFileSync(resolve(distRoot, '_redirects'), 'utf8')
const requiredRedirects = [
  '/mentions-legales /mentions-legales/index.html 200',
  '/mentions-legales/ /mentions-legales/index.html 200',
  '/supprimer-compte /supprimer-compte/index.html 200',
  '/supprimer-compte/ /supprimer-compte/index.html 200',
  '/politique-de-confidentialite /politique-de-confidentialite/index.html 200',
  '/politique-de-confidentialite/ /politique-de-confidentialite/index.html 200',
  '/conditions-d-utilisation /conditions-d-utilisation/index.html 200',
  '/conditions-d-utilisation/ /conditions-d-utilisation/index.html 200',
]
for (const rule of requiredRedirects) {
  if (!redirects.includes(rule)) {
    fail(`_redirects missing ${rule}`)
  }
}
if (redirects.includes('/* /index.html 200')) {
  fail('_redirects must not SPA-fallback all routes to index.html')
}

console.log('landing build validation ok')
