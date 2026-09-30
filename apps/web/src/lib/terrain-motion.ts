import type { Transition } from 'framer-motion'

import type { TerrainTransitionKind } from '@/app/terrain-back-path'

/** Terrain page transition duration (seconds). Target band: 120–220 ms. */
export const TERRAIN_PAGE_DURATION = 0.18

export const TERRAIN_PAGE_EASE = 'easeOut' as const

export const TERRAIN_PAGE_TRANSITION: Transition = {
  duration: TERRAIN_PAGE_DURATION,
  ease: TERRAIN_PAGE_EASE,
}

export const TERRAIN_TAP_SCALE = 0.97

const HIERARCHICAL_SHIFT = 16

type ReducedMotionFlag = boolean | null

export function terrainPageMotionProps(
  shouldReduceMotion: ReducedMotionFlag,
  kind: TerrainTransitionKind = 'fade',
  desktop = false,
) {
  if (shouldReduceMotion) {
    return {}
  }

  const directional = !desktop && (kind === 'forward' || kind === 'back')

  return {
    custom: kind,
    variants: {
      enter: (value: TerrainTransitionKind) => {
        if (!directional) {
          return { opacity: 0 }
        }
        return { opacity: 0, x: value === 'back' ? -HIERARCHICAL_SHIFT : HIERARCHICAL_SHIFT }
      },
      center: { opacity: 1, x: 0 },
      exit: (value: TerrainTransitionKind) => {
        if (desktop || value === 'fade') {
          return { opacity: 0 }
        }
        return { opacity: 0, x: value === 'back' ? HIERARCHICAL_SHIFT : -HIERARCHICAL_SHIFT }
      },
    },
    initial: 'enter' as const,
    animate: 'center' as const,
    exit: 'exit' as const,
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
