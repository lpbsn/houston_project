const STORAGE_KEY = 'houston.onboarding.registration.v1'

export type RegistrationSessionSnapshot = {
  invite_code: string
  first_name: string
  last_name: string
  email: string
  organization_name: string
}

const EMPTY: RegistrationSessionSnapshot = {
  invite_code: '',
  first_name: '',
  last_name: '',
  email: '',
  organization_name: '',
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string'
}

function parseSnapshot(raw: unknown): RegistrationSessionSnapshot | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return null
  }

  const record = raw as Record<string, unknown>
  if (
    !isNonEmptyString(record.invite_code) ||
    !isNonEmptyString(record.first_name) ||
    !isNonEmptyString(record.last_name) ||
    !isNonEmptyString(record.email) ||
    !isNonEmptyString(record.organization_name)
  ) {
    return null
  }

  // Reject unexpected secret keys if a corrupted/malicious payload appears.
  if ('password' in record || 'password_confirmation' in record) {
    return null
  }

  return {
    invite_code: record.invite_code,
    first_name: record.first_name,
    last_name: record.last_name,
    email: record.email,
    organization_name: record.organization_name,
  }
}

export function loadRegistrationSessionSnapshot(): RegistrationSessionSnapshot {
  if (typeof window === 'undefined') {
    return { ...EMPTY }
  }

  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return { ...EMPTY }
    }
    const parsed = parseSnapshot(JSON.parse(raw))
    return parsed ? parsed : { ...EMPTY }
  } catch {
    return { ...EMPTY }
  }
}

export function saveRegistrationSessionSnapshot(
  snapshot: RegistrationSessionSnapshot,
): void {
  if (typeof window === 'undefined') {
    return
  }

  try {
    const payload: RegistrationSessionSnapshot = {
      invite_code: snapshot.invite_code,
      first_name: snapshot.first_name,
      last_name: snapshot.last_name,
      email: snapshot.email,
      organization_name: snapshot.organization_name,
    }
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  } catch {
    // Best-effort only; quota / private mode must not break registration.
  }
}

export function clearRegistrationSessionSnapshot(): void {
  if (typeof window === 'undefined') {
    return
  }

  try {
    window.sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}

export const REGISTRATION_SESSION_STORAGE_KEY = STORAGE_KEY
