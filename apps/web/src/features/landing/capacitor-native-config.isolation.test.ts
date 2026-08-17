import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('capacitor native config isolation', () => {
  it('keeps mixed content and cleartext out of the committed Capacitor config', () => {
    const config = readFileSync(resolve(process.cwd(), 'capacitor.config.ts'), 'utf8')
    expect(config).toContain("webDir: 'dist-native'")
    expect(config).toContain('allowMixedContent: false')
    expect(config).not.toMatch(/cleartext\s*:/)
    expect(config).not.toMatch(/server\s*:/)
  })

  it('enables Android mixed content only in the debug Gradle source set', () => {
    const debugConfig = JSON.parse(
      readFileSync(
        resolve(process.cwd(), 'android/app/src/debug/assets/capacitor.config.json'),
        'utf8',
      ),
    ) as { appId?: string; webDir?: string; android?: { allowMixedContent?: boolean } }
    const mainManifest = readFileSync(
      resolve(process.cwd(), 'android/app/src/main/AndroidManifest.xml'),
      'utf8',
    )
    const debugManifest = readFileSync(
      resolve(process.cwd(), 'android/app/src/debug/AndroidManifest.xml'),
      'utf8',
    )
    const debugNetwork = readFileSync(
      resolve(
        process.cwd(),
        'android/app/src/debug/res/xml/network_security_config.xml',
      ),
      'utf8',
    )

    expect(debugConfig.appId).toBe('app.spore')
    expect(debugConfig.webDir).toBe('dist-native')
    expect(debugConfig.android?.allowMixedContent).toBe(true)
    expect(mainManifest).not.toMatch(/usesCleartextTraffic/)
    expect(mainManifest).not.toMatch(/networkSecurityConfig/)
    expect(debugManifest).toContain('networkSecurityConfig')
    expect(debugNetwork).toContain('10.0.2.2')
    expect(debugNetwork).toContain('cleartextTrafficPermitted="true"')
  })
})
