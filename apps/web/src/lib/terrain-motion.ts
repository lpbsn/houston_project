import type { Transition, Variant } from 'framer-motion'

/** Terrain page transition duration (seconds). Target band: 120–220 ms. */
export const TERRAIN_PAGE_DURATION = 0.18

export const TERRAIN_PAGE_EASE = 'easeOut' as const

export const TERRAIN_PAGE_TRANSITION: Transition = {
  duration: TERRAIN_PAGE_DURATION,
  ease: TERRAIN_PAGE_EASE,
}

export const TERRAIN_TAP_SCALE = 0.97

type ReducedMotionFlag = boolean | null

export function terrainPageMotionProps(shouldReduceMotion: ReducedMotionFlag) {
  if (shouldReduceMotion) {
    return {}
  }

  return {
    initial: { opacity: 0, y: 6 } satisfies Variant,
    animate: { opacity: 1, y: 0 } satisfies Variant,
    exit: { opacity: 0, y: -4 } satisfies Variant,
    transition: TERRAIN_PAGE_TRANSITION,
  }
}

export function terrainTapProps(shouldReduceMotion: ReducedMotionFlag) {
  if (shouldReduceMotion) {
    return {}
  }

  return {
    whileTap: { scale: TERRAIN_TAP_SCALE },
  }
}
