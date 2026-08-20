import type { CapacitorConfig } from '@capacitor/cli'
import { KeyboardResize } from '@capacitor/keyboard'

const config: CapacitorConfig = {
  appId: 'app.spore',
  appName: 'Spore',
  webDir: 'dist-native',
  android: {
    allowMixedContent: false,
  },
  plugins: {
    Keyboard: {
      resize: KeyboardResize.Native,
    },
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
