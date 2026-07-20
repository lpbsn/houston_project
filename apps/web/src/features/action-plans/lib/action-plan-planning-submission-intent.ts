const STORAGE_PREFIX = 'houston:planning-submission:'

export type PlanningSubmissionIntent = {
  submissionId: string
  requestHash: string
  itemIds: string[]
}

export function buildPlanningSubmissionStorageKey(
  establishmentId: string,
  actionPlanId: string,
): string {
  return `${STORAGE_PREFIX}${establishmentId}:${actionPlanId}`
}

function isPlanningSubmissionIntent(value: unknown): value is PlanningSubmissionIntent {
  if (typeof value !== 'object' || value === null) {
    return false
  }
  const parsed = value as PlanningSubmissionIntent
  return (
    typeof parsed.submissionId === 'string' &&
    parsed.submissionId.length > 0 &&
    typeof parsed.requestHash === 'string' &&
    parsed.requestHash.length > 0 &&
    Array.isArray(parsed.itemIds) &&
    parsed.itemIds.every((itemId) => typeof itemId === 'string' && itemId.length > 0)
  )
}

export function readPlanningSubmissionIntent(
  establishmentId: string,
  actionPlanId: string,
): PlanningSubmissionIntent | null {
  try {
    const raw = sessionStorage.getItem(
      buildPlanningSubmissionStorageKey(establishmentId, actionPlanId),
    )
    if (!raw) {
      return null
    }
    const parsed = JSON.parse(raw) as unknown
    if (!isPlanningSubmissionIntent(parsed)) {
      return null
    }
    return parsed
  } catch {
    return null
  }
}

export function writePlanningSubmissionIntent(
  establishmentId: string,
  actionPlanId: string,
  intent: PlanningSubmissionIntent,
): void {
  sessionStorage.setItem(
    buildPlanningSubmissionStorageKey(establishmentId, actionPlanId),
    JSON.stringify(intent),
  )
}

export function clearPlanningSubmissionIntent(
  establishmentId: string,
  actionPlanId: string,
): void {
  sessionStorage.removeItem(buildPlanningSubmissionStorageKey(establishmentId, actionPlanId))
}

export function clearAllPlanningSubmissionIntents(): void {
  const keys: string[] = []
  for (let index = 0; index < sessionStorage.length; index += 1) {
    const key = sessionStorage.key(index)
    if (key?.startsWith(STORAGE_PREFIX)) {
      keys.push(key)
    }
  }
  for (const key of keys) {
    sessionStorage.removeItem(key)
  }
}

async function sha256Hex(value: string): Promise<string> {
  const data = new TextEncoder().encode(value)
  const digest = await crypto.subtle.digest('SHA-256', data)
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('')
}

/** Business fingerprint excluding submission_id and item_id (idempotence keys). */
export function buildPlanningBusinessFingerprint(body: {
  use_shared_chronology?: boolean
  items?: Array<Record<string, unknown>>
  submission_id?: string
}): string {
  const items = (body.items ?? []).map((item) => {
    const { item_id: _itemId, ...rest } = item
    return rest
  })
  return JSON.stringify({
    use_shared_chronology: body.use_shared_chronology ?? false,
    items,
  })
}

export function applyPlanningSubmissionIntent<
  TItem extends Record<string, unknown> & { item_id?: string },
>(
  body: { use_shared_chronology: boolean; items: TItem[] },
  intent: PlanningSubmissionIntent,
): {
  submission_id: string
  use_shared_chronology: boolean
  items: Array<TItem & { item_id: string }>
} {
  if (intent.itemIds.length !== body.items.length) {
    throw new Error('Planning submission intent item count mismatch.')
  }
  return {
    submission_id: intent.submissionId,
    use_shared_chronology: body.use_shared_chronology,
    items: body.items.map((item, index) => ({
      ...item,
      item_id: intent.itemIds[index]!,
    })),
  }
}

export async function resolvePlanningSubmissionIntent(options: {
  establishmentId: string
  actionPlanId: string
  body: {
    use_shared_chronology?: boolean
    items: Array<Record<string, unknown> & { item_id?: string }>
  }
}): Promise<PlanningSubmissionIntent> {
  const requestHash = await sha256Hex(buildPlanningBusinessFingerprint(options.body))
  const existing = readPlanningSubmissionIntent(options.establishmentId, options.actionPlanId)
  if (
    existing &&
    existing.requestHash === requestHash &&
    existing.itemIds.length === options.body.items.length
  ) {
    return existing
  }
  const intent: PlanningSubmissionIntent = {
    submissionId: crypto.randomUUID(),
    requestHash,
    itemIds: options.body.items.map(() => crypto.randomUUID()),
  }
  writePlanningSubmissionIntent(options.establishmentId, options.actionPlanId, intent)
  return intent
}
