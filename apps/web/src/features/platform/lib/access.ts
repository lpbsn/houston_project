import type { BootstrapResponse } from '@/features/auth/types'

export function isPlatformOperatorActive(
  bootstrap: BootstrapResponse | null | undefined,
): boolean {
  return bootstrap?.permission_hints?.platform_operator_active === true
}
