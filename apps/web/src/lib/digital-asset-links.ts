const SHA256_FINGERPRINT = /^[0-9A-F]{2}(:[0-9A-F]{2}){31}$/
const PLACEHOLDER_FINGERPRINT = /YOUR_|PLACEHOLDER|TEAMID|^00(:00){31}$/i
const HANDLE_ALL_URLS = 'delegate_permission/common.handle_all_urls'
const PACKAGE_NAME = 'app.spore'

type AndroidAppTarget = {
  namespace?: unknown
  package_name?: unknown
  sha256_cert_fingerprints?: unknown
}

type AssetLinkStatement = {
  relation?: unknown
  target?: AndroidAppTarget
}

export function parseAssetLinksJson(raw: string): AssetLinkStatement[] {
  const parsed: unknown = JSON.parse(raw)
  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error('assetlinks.json must be a non-empty JSON array')
  }
  return parsed as AssetLinkStatement[]
}

export function assertProductionAssetLinks(raw: string): void {
  const statements = parseAssetLinksJson(raw)
  for (const statement of statements) {
    const relations = statement.relation
    if (!Array.isArray(relations) || !relations.includes(HANDLE_ALL_URLS)) {
      throw new Error(`assetlinks.json relation must include ${HANDLE_ALL_URLS}`)
    }
    const target = statement.target
    if (!target || target.namespace !== 'android_app') {
      throw new Error('assetlinks.json target.namespace must be android_app')
    }
    if (target.package_name !== PACKAGE_NAME) {
      throw new Error(`assetlinks.json package_name must be ${PACKAGE_NAME}`)
    }
    const fingerprints = target.sha256_cert_fingerprints
    if (!Array.isArray(fingerprints) || fingerprints.length === 0) {
      throw new Error('assetlinks.json must list at least one SHA-256 fingerprint')
    }
    for (const fingerprint of fingerprints) {
      if (typeof fingerprint !== 'string' || !SHA256_FINGERPRINT.test(fingerprint)) {
        throw new Error('assetlinks.json fingerprints must be uppercase colon-separated SHA-256')
      }
      if (PLACEHOLDER_FINGERPRINT.test(fingerprint)) {
        throw new Error('assetlinks.json must not contain placeholder fingerprints')
      }
    }
  }
}
