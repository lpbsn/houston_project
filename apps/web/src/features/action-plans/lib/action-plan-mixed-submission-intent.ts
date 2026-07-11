const STORAGE_PREFIX = 'houston:mixed-submission:'

export type MixedSubmissionIntent = {
  submissionId: string
  payloadHash: string
}

export function buildMixedSubmissionStorageKey(
  establishmentId: string,
  actionPlanId: string,
): string {
  return `${STORAGE_PREFIX}${establishmentId}:${actionPlanId}`
}

export function readMixedSubmissionIntent(
  establishmentId: string,
  actionPlanId: string,
): MixedSubmissionIntent | null {
  if (typeof window === 'undefined') {
    return null
  }

  const raw = window.sessionStorage.getItem(
    buildMixedSubmissionStorageKey(establishmentId, actionPlanId),
  )
  if (!raw) {
    return null
  }

  try {
    const parsed = JSON.parse(raw) as Partial<MixedSubmissionIntent>
    if (
      typeof parsed.submissionId === 'string' &&
      parsed.submissionId.length > 0 &&
      typeof parsed.payloadHash === 'string' &&
      parsed.payloadHash.length > 0
    ) {
      return {
        submissionId: parsed.submissionId,
        payloadHash: parsed.payloadHash,
      }
    }
  } catch {
    return null
  }

  return null
}

export function writeMixedSubmissionIntent(
  establishmentId: string,
  actionPlanId: string,
  intent: MixedSubmissionIntent,
): void {
  if (typeof window === 'undefined') {
    return
  }

  window.sessionStorage.setItem(
    buildMixedSubmissionStorageKey(establishmentId, actionPlanId),
    JSON.stringify(intent),
  )
}

export function clearMixedSubmissionIntent(
  establishmentId: string,
  actionPlanId: string,
): void {
  if (typeof window === 'undefined') {
    return
  }

  window.sessionStorage.removeItem(
    buildMixedSubmissionStorageKey(establishmentId, actionPlanId),
  )
}

export function clearAllMixedSubmissionIntents(): void {
  if (typeof window === 'undefined') {
    return
  }

  const keysToRemove: string[] = []
  for (let index = 0; index < window.sessionStorage.length; index += 1) {
    const key = window.sessionStorage.key(index)
    if (key?.startsWith(STORAGE_PREFIX)) {
      keysToRemove.push(key)
    }
  }

  for (const key of keysToRemove) {
    window.sessionStorage.removeItem(key)
  }
}

async function digestPayloadHash(payload: string): Promise<string> {
  if (typeof window !== 'undefined' && window.crypto?.subtle) {
    const encoded = new TextEncoder().encode(payload)
    const digest = await window.crypto.subtle.digest('SHA-256', encoded)
    return Array.from(new Uint8Array(digest))
      .map((byte) => byte.toString(16).padStart(2, '0'))
      .join('')
  }

  let hash = 0
  for (let index = 0; index < payload.length; index += 1) {
    hash = (hash * 31 + payload.charCodeAt(index)) >>> 0
  }
  return hash.toString(16).padStart(16, '0')
}

function sortAssignees<T extends { membership_id?: string; business_unit_id?: string }>(
  assignees: T[],
): T[] {
  return [...assignees].sort((left, right) => {
    const leftKey = `${left.membership_id ?? ''}:${left.business_unit_id ?? ''}`
    const rightKey = `${right.membership_id ?? ''}:${right.business_unit_id ?? ''}`
    return leftKey.localeCompare(rightKey)
  })
}

function canonicalizeMixedBodies(scheduleBody: unknown, useBody: unknown): string {
  const schedule =
    typeof scheduleBody === 'object' && scheduleBody !== null
      ? (scheduleBody as Record<string, unknown>)
      : {}
  const use =
    typeof useBody === 'object' && useBody !== null ? (useBody as Record<string, unknown>) : {}

  const canonical = {
    schedule: {
      ...schedule,
      assignees: Array.isArray(schedule.assignees)
        ? sortAssignees(schedule.assignees as Array<Record<string, unknown>>)
        : [],
      recurrence_days: Array.isArray(schedule.recurrence_days)
        ? [...schedule.recurrence_days].map(String).sort()
        : [],
    },
    use: {
      ...use,
      assignees: Array.isArray(use.assignees)
        ? sortAssignees(use.assignees as Array<Record<string, unknown>>)
        : [],
    },
  }

  return JSON.stringify(canonical)
}

export async function computeMixedPayloadHash(
  scheduleBody: unknown,
  useBody: unknown,
): Promise<string> {
  return digestPayloadHash(canonicalizeMixedBodies(scheduleBody, useBody))
}

export async function resolveMixedSubmissionIntent(options: {
  establishmentId: string
  actionPlanId: string
  scheduleBody: unknown
  useBody: unknown
}): Promise<MixedSubmissionIntent> {
  const payloadHash = await computeMixedPayloadHash(options.scheduleBody, options.useBody)
  const existing = readMixedSubmissionIntent(options.establishmentId, options.actionPlanId)

  if (existing?.payloadHash === payloadHash) {
    return existing
  }

  const nextIntent = {
    submissionId: crypto.randomUUID(),
    payloadHash,
  }
  writeMixedSubmissionIntent(options.establishmentId, options.actionPlanId, nextIntent)
  return nextIntent
}
