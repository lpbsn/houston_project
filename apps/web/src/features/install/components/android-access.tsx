import { Info } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { fetchPlayStoreAccess, submitPlayStoreAccess } from '@/features/install/api'
import { AccessWebLink } from '@/features/install/components/access-web-link'
import type { AndroidChoice } from '@/features/install/distribution'

const primaryButtonClassName = 'h-12 w-full rounded-2xl bg-[#004d3b] text-white hover:bg-[#003b2d]'

const RECEIVED_MESSAGE =
  'Demande reçue. Elle a été transmise à l’équipe SPORE. L’autorisation Google Play n’est pas encore confirmée.'

type AndroidAccessProps = {
  choice: AndroidChoice
  establishmentId?: string
  onContinueWeb: () => void
}

export function AndroidAccess({
  choice,
  establishmentId,
  onContinueWeb,
}: AndroidAccessProps) {
  const [status, setStatus] = useState<'unknown' | 'none' | 'pending' | 'accepted'>('unknown')
  const [editing, setEditing] = useState(false)
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (choice.kind !== 'request') {
      return
    }
    let cancelled = false
    void fetchPlayStoreAccess()
      .then((next) => {
        if (!cancelled) {
          setStatus(next)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus('none')
        }
      })
    return () => {
      cancelled = true
    }
  }, [choice.kind])

  if (choice.kind === 'store') {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-[#172e27]">Télécharger sur Google Play</h1>
        <Button asChild className={primaryButtonClassName}>
          <a href={choice.href} target="_blank" rel="noopener noreferrer">
            Ouvrir Google Play
          </a>
        </Button>
        <AccessWebLink onClick={onContinueWeb} />
      </div>
    )
  }

  if (choice.kind === 'unavailable') {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-[#172e27]">Lien Android indisponible</h1>
        <p className="text-sm leading-6 text-[#40564d]">
          Le lien Google Play n’est pas disponible pour le moment. Vous pouvez continuer sur le Web.
        </p>
        <AccessWebLink onClick={onContinueWeb} />
      </div>
    )
  }

  const showReceived = status === 'accepted' && !editing

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const googlePlayEmail = email.trim()
    if (!googlePlayEmail || submitting) {
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await submitPlayStoreAccess({
        googlePlayEmail,
        establishmentId,
      })
      setStatus('accepted')
      setEditing(false)
      setEmail('')
    } catch {
      setError('La demande n’a pas pu être transmise. Réessayez.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-[#172e27]">Télécharger sur Android</h1>
      <p className="text-sm leading-6 text-[#40564d]">
        Pour installer SPORE sur Google Play, nous devons autoriser le compte Google utilisé dans
        votre Play Store. Cette adresse n’est pas votre identifiant SPORE.
      </p>
      {showReceived ? (
        <div className="space-y-4">
          <p className="rounded-lg bg-[#edf6f0] p-4 text-sm leading-6 text-[#172e27]">
            {RECEIVED_MESSAGE}
          </p>
          <Button
            type="button"
            className={primaryButtonClassName}
            onClick={() => {
              setEmail('')
              setError(null)
              setEditing(true)
            }}
          >
            Corriger le mail
          </Button>
        </div>
      ) : (
        <form className="space-y-3" onSubmit={(event) => void handleSubmit(event)}>
          <label className="block space-y-1.5" htmlFor="play-store-email">
            <span className="text-sm font-medium text-[#172e27]">
              Adresse du compte Google utilisé sur le Play Store
            </span>
            <Input
              id="play-store-email"
              type="email"
              autoComplete="off"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <p className="flex items-start gap-2.5 rounded-lg bg-[#edf6f0] px-3.5 py-3 text-sm leading-5 text-[#172e27]">
            <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            <span>
              Ouvrez Play Store, touchez votre photo de profil et vérifiez l’adresse du{' '}
              <strong className="font-bold">compte sélectionné</strong>.
            </span>
          </p>
          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}
          <Button
            type="submit"
            disabled={submitting || email.trim().length === 0}
            className={primaryButtonClassName}
          >
            {submitting ? 'Envoi…' : 'Demander mon accès'}
          </Button>
        </form>
      )}
      <AccessWebLink onClick={onContinueWeb} />
    </div>
  )
}
