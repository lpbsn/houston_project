import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'app.spore',
  appName: 'Spore',
  webDir: 'dist-native',
  android: {
    allowMixedContent: false,
  },
  experimental: {
    ios: {
      spm: {
        packageOptions: {
          '@capacitor-firebase/messaging': {
            symlink: true,
          },
        },
      },
    },
  },
}

export default config
