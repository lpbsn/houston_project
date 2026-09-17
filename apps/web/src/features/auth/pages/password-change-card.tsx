import { useState } from 'react'

import { AuthApiError, changePassword, fetchBootstrap } from '@/features/auth/api'
import { PasswordCreationFields } from '@/features/auth/components/password-creation-fields'
import {
  canSubmitPasswordCreation,
  evaluatePasswordCreation,
  passwordCreationBlockerMessage,
} from '@/features/auth/lib/password-creation'
import { TerrainCard } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

type PasswordChangeCardProps = {
  disabled?: boolean
}

export function PasswordChangeCard({ disabled = false }: PasswordChangeCardProps) {
  const [open, setOpen] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const canSubmit =
    Boolean(currentPassword) && canSubmitPasswordCreation(password, confirmation) && !isSubmitting

  async function submit() {
    const blocker = passwordCreationBlockerMessage(
      evaluatePasswordCreation(password, confirmation),
    )
    if (blocker) {
      setError(blocker)
      return
    }
    setError(null)
    setIsSubmitting(true)
    try {
      await changePassword({
        current_password: currentPassword,
        password,
        password_confirmation: confirmation,
      })
      setSuccess(true)
      setCurrentPassword('')
      setPassword('')
      setConfirmation('')
      setOpen(false)
      await fetchBootstrap()
    } catch (caught) {
      if (caught instanceof AuthApiError) {
        if (caught.code === 'invalid_credentials') {
          setError('Mot de passe actuel incorrect.')
        } else {
          setError(caught.message)
        }
      } else {
        setError('Le mot de passe n’a pas pu être modifié.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <TerrainCard padding="sm" className="space-y-3">
      {open ? (
        <div className="space-y-3">
          <p className="text-sm font-medium text-[#1a1a1a]">Changer le mot de passe</p>
          <p className="text-sm text-[#5c5a54]">
            Les autres sessions seront déconnectées. Celle-ci reste active.
          </p>
          <input
            type="password"
            autoComplete="current-password"
            placeholder="Mot de passe actuel"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            className="min-h-11 w-full rounded-md border border-[#E8E6DF] px-3 text-sm"
          />
          <PasswordCreationFields
            password={password}
            confirmation={confirmation}
            onPasswordChange={setPassword}
            onConfirmationChange={setConfirmation}
            disabled={isSubmitting}
          />
          {error ? <p className="text-sm text-[#E24B4A]">{error}</p> : null}
          <div className="flex gap-2">
            <button
              type="button"
              className="min-h-11 flex-1 text-sm text-[#5c5a54]"
              disabled={isSubmitting}
              onClick={() => {
                setOpen(false)
                setCurrentPassword('')
                setPassword('')
                setConfirmation('')
                setError(null)
              }}
            >
              Annuler
            </button>
            <button
              type="button"
              className={cn(
                'min-h-11 flex-1 text-sm font-medium text-[#1a1a1a]',
                !canSubmit && 'opacity-60',
              )}
              disabled={!canSubmit}
              onClick={() => {
                void submit()
              }}
            >
              {isSubmitting ? 'Enregistrement...' : 'Enregistrer'}
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {success ? (
            <p className="text-sm text-[#5c5a54]">Mot de passe mis à jour.</p>
          ) : null}
          <button
            type="button"
            className={cn(
              'flex min-h-11 w-full items-center justify-center text-sm font-medium text-[#1a1a1a]',
              disabled && 'opacity-60',
            )}
            disabled={disabled}
            onClick={() => {
              setError(null)
              setOpen(true)
            }}
          >
            Changer le mot de passe
          </button>
        </div>
      )}
    </TerrainCard>
  )
}
