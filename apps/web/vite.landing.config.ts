import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const webRoot = fileURLToPath(new URL('.', import.meta.url))
const landingRoot = fileURLToPath(new URL('./landing', import.meta.url))

// Public marketing site — no service worker plugin, no app entry.
export default defineConfig({
  root: landingRoot,
  base: '/',
  publicDir: fileURLToPath(new URL('./public-landing', import.meta.url)),
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@contracts': fileURLToPath(new URL('../../contracts', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    fs: {
      allow: [webRoot],
    },
  },
  build: {
    outDir: fileURLToPath(new URL('./dist-landing', import.meta.url)),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: fileURLToPath(new URL('./landing/index.html', import.meta.url)),
        mentionsLegales: fileURLToPath(
          new URL('./landing/mentions-legales/index.html', import.meta.url),
        ),
      },
    },
  },
})
