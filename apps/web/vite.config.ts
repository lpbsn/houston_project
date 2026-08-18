import { availableParallelism } from 'node:os'
import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'

const envDir = fileURLToPath(new URL('../..', import.meta.url))

// Vitest 4.1.8 non-watch default: max(availableParallelism - 1, 1). Cap at 4 so
// local high-core machines do not oversubscribe jsdom; CI (~3) stays unchanged.
const defaultVitestWorkers = Math.max(availableParallelism() - 1, 1)

function isAbsoluteHttpOrigin(value: string): boolean {
  try {
    const parsed = new URL(value)
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return false
    }
    if (parsed.username || parsed.password) {
      return false
    }
    if (parsed.search || parsed.hash) {
      return false
    }
    return parsed.pathname === '' || parsed.pathname === '/'
  } catch {
    return false
  }
}

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, envDir, 'VITE_')
  const appRuntime = env.VITE_APP_RUNTIME === 'native' ? 'native' : 'web'
  const apiBaseUrl = (env.VITE_API_BASE_URL ?? '').trim()
  const publicAppUrl = (env.VITE_PUBLIC_APP_URL ?? '').trim()
  const isNativeBuild = command === 'build' && appRuntime === 'native'

  if (appRuntime === 'native' && !apiBaseUrl) {
    throw new Error('VITE_API_BASE_URL is required when VITE_APP_RUNTIME=native.')
  }
  if (appRuntime === 'native' && !isAbsoluteHttpOrigin(publicAppUrl)) {
    throw new Error(
      'VITE_PUBLIC_APP_URL must be an absolute http(s) origin when VITE_APP_RUNTIME=native.',
    )
  }

  return {
    envDir,
    base: isNativeBuild ? './' : '/',
    plugins: [react(), tailwindcss()],
    build: {
      outDir: isNativeBuild ? 'dist-native' : 'dist',
      emptyOutDir: true,
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        '@contracts': fileURLToPath(new URL('../../contracts', import.meta.url)),
      },
    },
    server: {
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000',
          // Preserve the browser host in local dev so Django sees a same-origin
          // request instead of an internal container host such as api:8000.
          changeOrigin: false,
        },
        '/ws': {
          target: process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000',
          changeOrigin: false,
          ws: true,
        },
      },
    },
    test: {
      environment: 'node',
      include: ['src/**/*.{test,spec}.{ts,tsx}'],
      maxWorkers: Math.min(defaultVitestWorkers, 4),
    },
  }
})
