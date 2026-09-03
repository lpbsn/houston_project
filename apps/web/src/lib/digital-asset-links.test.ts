import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

import { assertProductionAssetLinks, parseAssetLinksJson } from '@/lib/digital-asset-links'

const validFingerprint =
  '14:6D:E9:83:C5:73:06:50:D8:EE:B9:95:2F:34:FC:64:16:A0:83:42:E6:1D:BE:A8:8A:04:96:B2:3F:CF:44:E5'

function statement(fingerprints: string[]) {
  return JSON.stringify([
    {
      relation: ['delegate_permission/common.handle_all_urls'],
      target: {
        namespace: 'android_app',
        package_name: 'app.spore',
        sha256_cert_fingerprints: fingerprints,
      },
    },
  ])
}

describe('digital asset links statements', () => {
  it('accepts one or more real Play-style SHA-256 fingerprints', () => {
    const second =
      'AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99'
    expect(() => assertProductionAssetLinks(statement([validFingerprint, second]))).not.toThrow()
    expect(parseAssetLinksJson(statement([validFingerprint]))).toHaveLength(1)
  })

  it('rejects placeholders, lowercase fingerprints, and the wrong package', () => {
    const allZero =
      '00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00'
    expect(() => assertProductionAssetLinks(statement(['YOUR_SHA256']))).toThrow(/placeholder|uppercase/i)
    expect(() => assertProductionAssetLinks(statement([allZero]))).toThrow(/placeholder/)
    expect(() =>
      assertProductionAssetLinks(statement([validFingerprint.toLowerCase()])),
    ).toThrow(/uppercase/)
    const wrongPackage = statement([validFingerprint]).replace('app.spore', 'com.example')
    expect(() => assertProductionAssetLinks(wrongPackage)).toThrow(/package_name/)
  })
})

describe('committed association files', () => {
  it('does not publish assetlinks.json or AASA until store identities exist', () => {
    const wellKnown = resolve(process.cwd(), 'public/.well-known')
    expect(() => readFileSync(resolve(wellKnown, 'assetlinks.json'), 'utf8')).toThrow()
    expect(() =>
      readFileSync(resolve(wellKnown, 'apple-app-site-association'), 'utf8'),
    ).toThrow()
  })
})
