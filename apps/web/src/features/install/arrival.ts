import type { BootstrapResponse } from '@/features/auth/types'

export type AccessArrivalKind = 'activated' | 'joined'

export type AccessArrival = {
  userId: string
  arrival: AccessArrivalKind
  establishmentId: string
}

const STORAGE_KEY = 'spore.access-arrival'

let held: AccessArrival | null = null
let holdGeneration = 0

function readStorage(): AccessArrival | null {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return null
    }
    return parseArrival(JSON.parse(raw))
  } catch {
    return null
  }
}

function parseArrival(value: unknown): AccessArrival | null {
  if (!value || typeof value !== 'object') {
    return null
  }
  const record = value as Record<string, unknown>
  if (typeof record.userId !== 'string' || record.userId.length === 0) {
    return null
  }
  if (record.arrival !== 'activated' && record.arrival !== 'joined') {
    return null
  }
  if (typeof record.establishmentId !== 'string' || record.establishmentId.length === 0) {
    return null
  }
  return {
    userId: record.userId,
    arrival: record.arrival,
    establishmentId: record.establishmentId,
  }
}

export function rememberAccessArrival(value: AccessArrival): void {
  held = value
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value))
  } catch {
    held = value
  }
}

export function readAccessArrivalForDisplay(): AccessArrival | null {
  const stored = readStorage()
  if (stored) {
    held = stored
    return stored
  }
  return held
}

export function releaseDisplayedAccessArrival(): void {
  const generation = ++holdGeneration
  try {
    window.sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // The in-memory copy still covers this render.
  }
  queueMicrotask(() => {
    if (holdGeneration === generation) {
      held = null
    }
  })
}

export function clearAccessArrival(): void {
  holdGeneration += 1
  held = null
  try {
    window.sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // Nothing else keeps the arrival once the session ends.
  }
}

function establishmentName(bootstrap: BootstrapResponse, establishmentId: string): string | null {
  const pending = bootstrap.pending_onboarding_memberships.find(
    (membership) => membership.establishment_id === establishmentId,
  )
  if (pending?.establishment_name) {
    return pending.establishment_name
  }
  const membership = bootstrap.memberships.find(
    (item) => item.establishment_id === establishmentId,
  )
  if (membership?.establishment_name) {
    return membership.establishment_name
  }
  if (bootstrap.active_membership?.establishment_id === establishmentId) {
    return bootstrap.active_membership.establishment_name || null
  }
  return null
}

function knowsEstablishment(bootstrap: BootstrapResponse, establishmentId: string): boolean {
  return (
    bootstrap.memberships.some((membership) => membership.establishment_id === establishmentId) ||
    bootstrap.pending_onboarding_memberships.some(
      (membership) => membership.establishment_id === establishmentId,
    )
  )
}

function hasOperationalMembership(bootstrap: BootstrapResponse): boolean {
  return bootstrap.memberships.some((membership) => membership.status === 'active')
}

export function resolveAccessCopy(
  bootstrap: BootstrapResponse | null | undefined,
  arrival: AccessArrival | null,
): {
  lines: string[]
  question: string
  spaceReady: boolean
  establishmentId: string | null
} {
  const question = 'Où souhaitez-vous utiliser SPORE ?'
  if (!bootstrap) {
    return { lines: [], question, spaceReady: false, establishmentId: null }
  }

  const arrivalMatches =
    arrival !== null &&
    arrival.userId === bootstrap.user.id &&
    knowsEstablishment(bootstrap, arrival.establishmentId)
  const concernedId = arrivalMatches ? arrival.establishmentId : null
  const concernedPending = concernedId
    ? bootstrap.pending_onboarding_memberships.some(
        (membership) => membership.establishment_id === concernedId,
      )
    : bootstrap.pending_onboarding_memberships.length > 0 && !hasOperationalMembership(bootstrap)
  const spaceReady = concernedId
    ? !concernedPending
    : hasOperationalMembership(bootstrap)

  const lines: string[] = []
  if (concernedPending) {
    lines.push('Votre compte est activé. Votre établissement est encore en préparation.')
    if (
      concernedId &&
      bootstrap.memberships.some(
        (membership) =>
          membership.status === 'active' && membership.establishment_id !== concernedId,
      )
    ) {
      lines.push('Vos autres établissements restent accessibles.')
    }
  } else if (arrivalMatches && arrival) {
    if (arrival.arrival === 'joined') {
      const name = establishmentName(bootstrap, arrival.establishmentId)
      lines.push(name ? `Vous avez rejoint ${name}.` : 'Vous avez rejoint votre établissement.')
    } else {
      lines.push('Votre compte SPORE est activé.')
    }
  }

  return { lines, question, spaceReady, establishmentId: concernedId }
}

export function playRequestEstablishmentId(
  bootstrap: BootstrapResponse | null | undefined,
  arrival: AccessArrival | null,
): string | undefined {
  const copy = resolveAccessCopy(bootstrap, arrival)
  if (copy.establishmentId) {
    return copy.establishmentId
  }
  const active = bootstrap?.active_membership
  if (active?.establishment_id) {
    return active.establishment_id
  }
  const pending = bootstrap?.pending_onboarding_memberships ?? []
  if (pending.length === 1) {
    return pending[0]?.establishment_id
  }
  return undefined
}
