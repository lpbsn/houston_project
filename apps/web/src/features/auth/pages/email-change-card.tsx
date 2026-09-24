import { useState } from 'react'

import { AuthApiError, fetchBootstrap, requestEmailChange } from '@/features/auth/api'
import { cn } from '@/lib/utils'

type EmailChangeCardProps = {
  email: string | null
  pendingEmail: string | null
  disabled?: boolean
}

export function EmailChangeCard({
  email,
  pendingEmail,
  disabled = false,
}: EmailChangeCardProps) {
  const [open, setOpen] = useState(false)
  const [password, setPassword] = useState('')
  const [newEmail, setNewEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successPending, setSuccessPending] = useState<string | null>(pendingEmail)

  const displayedPending = successPending ?? pendingEmail

  async function submit() {
    setError(null)
    setIsSubmitting(true)
    try {
      const result = await requestEmailChange({
        password,
        new_email: newEmail,
      })
      setSuccessPending(result.pending_email)
      setPassword('')
      setNewEmail('')
      setOpen(false)
      await fetchBootstrap()
    } catch (caught) {
      if (caught instanceof AuthApiError) {
        if (caught.code === 'invalid_credentials') {
          setError('Mot de passe incorrect.')
        } else if (caught.code === 'email_change_duplicate') {
          setError('Un compte existe déjà pour cette adresse.')
        } else if (caught.code === 'email_change_unavailable') {
          setError('Le changement d’e-mail est indisponible pour le moment.')
        } else if (caught.code === 'email_change_unchanged') {
          setError('C’est déjà votre adresse e-mail.')
        } else {
          setError(caught.message)
        }
      } else {
        setError('La demande n’a pas pu être envoyée.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return open ? (
        <div className="space-y-3 p-4">
          <p className="text-sm font-medium text-[#1a1a1a]">Changer d’e-mail</p>
          <p className="text-sm text-[#5c5a54]">
            Un lien de confirmation sera envoyé à la nouvelle adresse. L’e-mail de connexion ne
            change qu’après confirmation.
          </p>
          <p className="text-sm text-[#5c5a54]">Adresse actuelle : {email || '—'}</p>
          <input
            type="password"
            autoComplete="current-password"
            placeholder="Mot de passe actuel"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="min-h-11 w-full rounded-md border border-[#E8E6DF] px-3 text-sm"
          />
          <input
            type="email"
            autoComplete="email"
            placeholder="Nouvelle adresse e-mail"
            value={newEmail}
            onChange={(event) => setNewEmail(event.target.value)}
            className="min-h-11 w-full rounded-md border border-[#E8E6DF] px-3 text-sm"
          />
          {error ? <p className="text-sm text-[#E24B4A]">{error}</p> : null}
          <div className="flex gap-2">
            <button
              type="button"
              className="min-h-11 flex-1 text-sm text-[#5c5a54]"
              disabled={isSubmitting}
              onClick={() => {
                setOpen(false)
                setPassword('')
                setNewEmail('')
                setError(null)
              }}
            >
              Annuler
            </button>
            <button
              type="button"
              className={cn(
                'min-h-11 flex-1 text-sm font-medium text-[#1a1a1a]',
                (!password || !newEmail || isSubmitting) && 'opacity-60',
              )}
              disabled={!password || !newEmail || isSubmitting}
              onClick={() => {
                void submit()
              }}
            >
              {isSubmitting ? 'Envoi...' : 'Envoyer le lien'}
            </button>
          </div>
        </div>
  ) : (
    <div>
      {displayedPending ? (
        <p className="px-4 pt-3 text-sm text-[#5c5a54]">
          Confirmation en attente pour {displayedPending}.
        </p>
      ) : null}
      <button
        type="button"
        className={cn(
          'flex min-h-11 w-full items-center px-4 text-left text-sm font-medium text-[#1a1a1a]',
          disabled && 'opacity-60',
        )}
        disabled={disabled}
        onClick={() => {
          setError(null)
          setOpen(true)
        }}
      >
        Changer d’e-mail
      </button>
    </div>
  )
}
