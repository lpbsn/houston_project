export const iosAppStoreUrl = 'https://apps.apple.com/fr/app/spore/id6810116036'

export type AndroidDistribution = 'closed' | 'public'

/** Closed testing until this constant is changed and deployed. */
export const androidDistribution: AndroidDistribution = 'closed'

/** Ignored while androidDistribution is closed. */
export const androidPlayStoreUrl = ''

export type AndroidChoice =
  | { kind: 'request' }
  | { kind: 'store'; href: string }
  | { kind: 'unavailable' }

export function resolveAndroidChoice(
  distribution: AndroidDistribution,
  playStoreUrl: string,
): AndroidChoice {
  if (distribution === 'closed') {
    return { kind: 'request' }
  }
  const href = playStoreUrl.trim()
  if (!href) {
    return { kind: 'unavailable' }
  }
  return { kind: 'store', href }
}
