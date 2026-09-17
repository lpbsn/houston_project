/** Matches Django `MinimumLengthValidator` `min_length` in AUTH_PASSWORD_VALIDATORS. */
export const PASSWORD_MIN_LENGTH = 12

export const PASSWORD_CREATION_HINTS = {
  minLength: `Au moins ${PASSWORD_MIN_LENGTH} caractères`,
  notNumericOnly: 'Ne doit pas être uniquement composé de chiffres',
  confirmationMatch: 'Les deux champs doivent correspondre',
} as const

export const PASSWORD_CREATION_ERRORS = {
  tooShort: `Le mot de passe doit contenir au moins ${PASSWORD_MIN_LENGTH} caractères.`,
  numericOnly: 'Le mot de passe ne peut pas être uniquement composé de chiffres.',
  mismatch: 'Les mots de passe ne correspondent pas.',
} as const

export type PasswordCreationIssues = {
  empty: boolean
  tooShort: boolean
  numericOnly: boolean
  mismatch: boolean
}

export function evaluatePasswordCreation(
  password: string,
  confirmation: string,
): PasswordCreationIssues {
  const empty = password.length === 0 || confirmation.length === 0
  return {
    empty,
    tooShort: password.length > 0 && password.length < PASSWORD_MIN_LENGTH,
    numericOnly: password.length > 0 && /^\d+$/.test(password),
    mismatch: password.length > 0 && confirmation.length > 0 && password !== confirmation,
  }
}

export function canSubmitPasswordCreation(password: string, confirmation: string): boolean {
  const issues = evaluatePasswordCreation(password, confirmation)
  return !issues.empty && !issues.tooShort && !issues.numericOnly && !issues.mismatch
}

export function passwordCreationBlockerMessage(
  issues: PasswordCreationIssues,
): string | null {
  if (issues.tooShort) {
    return PASSWORD_CREATION_ERRORS.tooShort
  }
  if (issues.numericOnly) {
    return PASSWORD_CREATION_ERRORS.numericOnly
  }
  if (issues.mismatch) {
    return PASSWORD_CREATION_ERRORS.mismatch
  }
  return null
}
