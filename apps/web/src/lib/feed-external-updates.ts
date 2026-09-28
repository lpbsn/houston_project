type FeedReadingSession = {
  matches: (queryKey: readonly unknown[]) => boolean
  atTop: () => boolean
  interacting: () => boolean
  onDefer: () => void
  onRemove: (entityId: string) => void
}

const sessions = new Set<FeedReadingSession>()

export function registerFeedReadingSession(session: FeedReadingSession): () => void {
  sessions.add(session)
  return () => {
    sessions.delete(session)
  }
}

export function queryKeyMatchesPrefix(
  queryKey: readonly unknown[],
  prefix: readonly unknown[],
): boolean {
  if (queryKey.length < prefix.length) {
    return false
  }
  return prefix.every((part, index) => queryKey[index] === part)
}

/**
 * Content invalidation while a scrolled reading is in progress defers list refetch.
 * No mounted session means the list should refresh.
 */
export function deferFeedListInvalidation(queryKey: readonly unknown[]): boolean {
  let deferred = false
  for (const session of sessions) {
    if (!session.matches(queryKey)) {
      continue
    }
    if (session.atTop() && !session.interacting()) {
      continue
    }
    session.onDefer()
    deferred = true
  }
  return deferred
}

export function removeHydratedFeedEntity(queryKey: readonly unknown[], entityId: string): void {
  for (const session of sessions) {
    if (session.matches(queryKey)) {
      session.onRemove(entityId)
    }
  }
}

export function resetFeedReadingSessionsForTests(): void {
  sessions.clear()
}
