import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { fetchPlayStoreAccess, submitPlayStoreAccess } from '@/features/install/api'
import type { AndroidChoice } from '@/features/install/distribution'

const RECEIVED_MESSAGE =
  'Demande reçue. Elle a été transmise à l’équipe SPORE. L’autorisation Google Play n’est pas encore confirmée.'

type AndroidAccessProps = {
  choice: AndroidChoice
  establishmentId?: string
  onContinueWeb: () => void
  onChooseAnother: () => void
}

export function AndroidAccess({
  choice,
  establishmentId,
  onContinueWeb,
  onChooseAnother,
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
        <Button asChild className="h-12 w-full rounded-2xl bg-[#004d3b] text-white hover:bg-[#003b2d]">
          <a href={choice.href} target="_blank" rel="noopener noreferrer">
            Ouvrir Google Play
          </a>
        </Button>
        <SecondaryActions onContinueWeb={onContinueWeb} onChooseAnother={onChooseAnother} />
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
        <SecondaryActions onContinueWeb={onContinueWeb} onChooseAnother={onChooseAnother} />
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
      <h1 className="text-2xl font-bold text-[#172e27]">Préparer l’accès à Google Play</h1>
      <p className="text-sm leading-6 text-[#40564d]">
        Pour installer SPORE sur Google Play, nous devons autoriser le compte Google utilisé dans
        votre Play Store. Cette adresse n’est pas votre identifiant SPORE.
      </p>
      {showReceived ? (
        <div className="space-y-4">
          <p className="rounded-2xl bg-[#edf6f0] p-4 text-sm leading-6 text-[#172e27]">
            {RECEIVED_MESSAGE}
          </p>
          <Button
            type="button"
            variant="outline"
            className="h-11 w-full rounded-2xl"
            onClick={() => {
              setEmail('')
              setError(null)
              setEditing(true)
            }}
          >
            Corriger l’adresse
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
          <p className="text-sm leading-6 text-[#40564d]">
            Sur votre Android, ouvrez Play Store, puis la photo de profil, et vérifiez l’adresse
            sélectionnée.
          </p>
          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}
          <Button
            type="submit"
            disabled={submitting || email.trim().length === 0}
            className="h-12 w-full rounded-2xl bg-[#004d3b] text-white hover:bg-[#003b2d]"
          >
            {submitting ? 'Envoi…' : 'Demander mon accès'}
          </Button>
        </form>
      )}
      <SecondaryActions onContinueWeb={onContinueWeb} onChooseAnother={onChooseAnother} />
    </div>
  )
}

function SecondaryActions({
  onContinueWeb,
  onChooseAnother,
}: {
  onContinueWeb: () => void
  onChooseAnother: () => void
}) {
  return (
    <div className="space-y-2">
      <Button type="button" variant="outline" className="h-11 w-full rounded-2xl" onClick={onContinueWeb}>
        Continuer sur le Web
      </Button>
      <Button type="button" variant="ghost" className="h-11 w-full rounded-2xl" onClick={onChooseAnother}>
        Choisir un autre appareil
      </Button>
    </div>
  )
}
