export const SPA_NAVIGATION_DENYLIST = [/^\/api/, /^\/ws/]

export function shouldBypassSpaNavigation(pathname: string): boolean {
  return SPA_NAVIGATION_DENYLIST.some((pattern) => pattern.test(pathname))
}
