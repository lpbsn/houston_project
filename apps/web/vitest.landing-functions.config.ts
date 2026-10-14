import { defineConfig } from 'vitest/config'
export default defineConfig({ test: { include: ['tests/landing/**/*.test.ts'], environment: 'node' } })
