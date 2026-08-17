import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'app.spore',
  appName: 'Spore',
  webDir: 'dist-native',
  android: {
    allowMixedContent: false,
  },
}

export default config
