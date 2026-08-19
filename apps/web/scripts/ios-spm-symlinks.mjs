import {
  existsSync,
  lstatSync,
  mkdirSync,
  readlinkSync,
  realpathSync,
  symlinkSync,
  unlinkSync,
} from 'node:fs'
import { dirname, isAbsolute, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

export const CAPACITOR_FIREBASE_MESSAGING_LINK_NAME = 'CapacitorFirebaseMessaging'
export const CAPACITOR_FIREBASE_MESSAGING_RELATIVE_TARGET =
  '../../../../node_modules/@capacitor-firebase/messaging'

export function capacitorFirebaseMessagingPaths(webRoot) {
  const symlinkDir = resolve(webRoot, 'ios/App/CapApp-SPM/symlinks')
  return {
    symlinkDir,
    linkPath: join(symlinkDir, CAPACITOR_FIREBASE_MESSAGING_LINK_NAME),
    packagePath: resolve(webRoot, 'node_modules/@capacitor-firebase/messaging'),
  }
}

export function rewriteCapacitorFirebaseMessagingSymlink(webRoot) {
  const { symlinkDir, linkPath, packagePath } = capacitorFirebaseMessagingPaths(webRoot)
  if (!existsSync(packagePath)) {
    throw new Error('missing node_modules/@capacitor-firebase/messaging')
  }

  mkdirSync(symlinkDir, { recursive: true })
  try {
    unlinkSync(linkPath)
  } catch (error) {
    if (error.code !== 'ENOENT') {
      throw error
    }
  }
  symlinkSync(CAPACITOR_FIREBASE_MESSAGING_RELATIVE_TARGET, linkPath)
}

export function assertCapacitorFirebaseMessagingSymlink(webRoot, fail) {
  const { linkPath, packagePath } = capacitorFirebaseMessagingPaths(webRoot)

  let stat
  try {
    stat = lstatSync(linkPath)
  } catch {
    fail(
      'missing CapApp-SPM symlink CapacitorFirebaseMessaging; use npm run cap:sync, not npx cap sync',
    )
    return
  }

  if (!stat.isSymbolicLink()) {
    fail('CapApp-SPM CapacitorFirebaseMessaging must be a symlink')
    return
  }

  const target = readlinkSync(linkPath)
  if (isAbsolute(target)) {
    fail(
      `CapApp-SPM CapacitorFirebaseMessaging must be a relative symlink (got ${target}); use npm run cap:sync, not npx cap sync`,
    )
    return
  }

  if (!existsSync(packagePath)) {
    fail('missing node_modules/@capacitor-firebase/messaging')
    return
  }

  const resolvedTarget = resolve(dirname(linkPath), target)
  if (realpathSync(resolvedTarget) !== realpathSync(packagePath)) {
    fail(
      `CapApp-SPM CapacitorFirebaseMessaging must resolve to node_modules/@capacitor-firebase/messaging (got ${target})`,
    )
  }
}

function fail(message) {
  console.error(`ios SPM symlink failed: ${message}`)
  process.exit(1)
}

const invokedDirectly =
  Boolean(process.argv[1]) && resolve(process.argv[1]) === fileURLToPath(import.meta.url)

if (invokedDirectly) {
  const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
  try {
    rewriteCapacitorFirebaseMessagingSymlink(webRoot)
  } catch (error) {
    fail(error instanceof Error ? error.message : String(error))
  }
  assertCapacitorFirebaseMessagingSymlink(webRoot, fail)
}
