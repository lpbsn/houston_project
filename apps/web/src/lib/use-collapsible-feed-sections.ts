import { useCallback, useMemo, useState } from 'react'

type UseCollapsibleFeedSectionsOptions = {
  defaultCollapsedKeys?: readonly string[]
  resetToken?: unknown
}

const EMPTY_DEFAULT_COLLAPSED_KEYS: readonly string[] = []

function buildExpansionState(
  sectionKeys: readonly string[],
  defaultCollapsedSet: ReadonlySet<string>,
): Record<string, boolean> {
  return Object.fromEntries(
    sectionKeys.map((key) => [key, !defaultCollapsedSet.has(key)]),
  )
}

function mergeExpansionState(
  previous: Record<string, boolean>,
  sectionKeys: readonly string[],
  defaultCollapsedSet: ReadonlySet<string>,
): Record<string, boolean> {
  const next: Record<string, boolean> = {}

  for (const key of sectionKeys) {
    next[key] = key in previous ? previous[key]! : !defaultCollapsedSet.has(key)
  }

  return next
}

export function useCollapsibleFeedSections(
  sectionKeys: readonly string[],
  options?: UseCollapsibleFeedSectionsOptions,
) {
  const defaultCollapsedKeys = options?.defaultCollapsedKeys ?? EMPTY_DEFAULT_COLLAPSED_KEYS
  const defaultCollapsedSet = useMemo(
    () => new Set(defaultCollapsedKeys),
    [defaultCollapsedKeys],
  )
  const resetToken = options?.resetToken
  const sectionKeysKey = sectionKeys.join('\0')

  const [state, setState] = useState(() => ({
    resetToken,
    sectionKeysKey,
    expandedByKey: buildExpansionState(sectionKeys, defaultCollapsedSet),
  }))

  if (state.resetToken !== resetToken) {
    setState({
      resetToken,
      sectionKeysKey,
      expandedByKey: buildExpansionState(sectionKeys, defaultCollapsedSet),
    })
  } else if (state.sectionKeysKey !== sectionKeysKey) {
    setState({
      resetToken,
      sectionKeysKey,
      expandedByKey: mergeExpansionState(state.expandedByKey, sectionKeys, defaultCollapsedSet),
    })
  }

  const isExpanded = useCallback(
    (key: string) => state.expandedByKey[key] ?? !defaultCollapsedSet.has(key),
    [state.expandedByKey, defaultCollapsedSet],
  )

  const toggle = useCallback(
    (key: string) => {
      setState((current) => ({
        ...current,
        expandedByKey: {
          ...current.expandedByKey,
          [key]: !(current.expandedByKey[key] ?? !defaultCollapsedSet.has(key)),
        },
      }))
    },
    [defaultCollapsedSet],
  )

  return { isExpanded, toggle }
}
