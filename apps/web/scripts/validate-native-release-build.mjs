import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  assertNativeReleaseBundleText,
  assertNativeReleaseEnv,
} from './native-release-origins.mjs'

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const distRoot = resolve(webRoot, 'dist-native')

function fail(message) {
  console.error(`native release validation failed: ${message}`)
  process.exit(1)
}

function collectTextFiles(dir, acc = []) {
  if (!existsSync(dir)) {
    return acc
  }
  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry)
    const stat = statSync(fullPath)
    if (stat.isDirectory()) {
      collectTextFiles(fullPath, acc)
      continue
    }
    if (/\.(html|js|css|json|txt|map)$/i.test(entry)) {
      acc.push(readFileSync(fullPath, 'utf8'))
    }
  }
  return acc
}

try {
  assertNativeReleaseEnv()
} catch (error) {
  fail(error instanceof Error ? error.message : String(error))
}

if (!existsSync(distRoot)) {
  fail('missing dist-native/')
}

const bundleText = collectTextFiles(distRoot).join('\n')
try {
  assertNativeReleaseBundleText(bundleText)
} catch (error) {
  fail(error instanceof Error ? error.message : String(error))
}

console.log('native release validation ok')
