import { serializeScopedTerrainPath } from '@/app/scoped-terrain'

export function buildOperationalConfigPath(establishmentId: string): string {
  return serializeScopedTerrainPath(
    { type: 'establishment', establishmentId },
    'operational-config',
  )
}

export function buildOperationalConfigFallbackPath(establishmentId: string): string {
  return serializeScopedTerrainPath({ type: 'establishment', establishmentId }, 'reporting')
}
