import { Input } from '@/components/ui/input'
import {
  PASSWORD_CREATION_HINTS,
  evaluatePasswordCreation,
} from '@/features/auth/lib/password-creation'
import { cn } from '@/lib/utils'

type PasswordCreationFieldsProps = {
  password: string
  confirmation: string
  onPasswordChange: (value: string) => void
  onConfirmationChange: (value: string) => void
  passwordId?: string
  confirmationId?: string
  disabled?: boolean
}

export function PasswordCreationFields({
  password,
  confirmation,
  onPasswordChange,
  onConfirmationChange,
  passwordId = 'password',
  confirmationId = 'password_confirmation',
  disabled = false,
}: PasswordCreationFieldsProps) {
  const issues = evaluatePasswordCreation(password, confirmation)

  return (
    <div className="space-y-3">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block space-y-1.5" htmlFor={passwordId}>
          <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
            Mot de passe
          </span>
          <Input
            id={passwordId}
            type="password"
            autoComplete="new-password"
            value={password}
            disabled={disabled}
            onChange={(event) => onPasswordChange(event.target.value)}
            className="h-11 rounded-xl border-spore-forest/15"
          />
        </label>
        <label className="block space-y-1.5" htmlFor={confirmationId}>
          <span className="text-[11px] font-semibold uppercase tracking-wide text-spore-muted">
            Confirmer le mot de passe
          </span>
          <Input
            id={confirmationId}
            type="password"
            autoComplete="new-password"
            value={confirmation}
            disabled={disabled}
            onChange={(event) => onConfirmationChange(event.target.value)}
            className="h-11 rounded-xl border-spore-forest/15"
          />
        </label>
      </div>
      <ul className="space-y-1 text-xs text-spore-muted">
        <li className={cn(issues.tooShort && 'text-destructive')}>
          {PASSWORD_CREATION_HINTS.minLength}
        </li>
        <li className={cn(issues.numericOnly && 'text-destructive')}>
          {PASSWORD_CREATION_HINTS.notNumericOnly}
        </li>
        <li className={cn(issues.mismatch && 'text-destructive')}>
          {PASSWORD_CREATION_HINTS.confirmationMatch}
        </li>
      </ul>
    </div>
  )
}
