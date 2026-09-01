import { useState } from 'react'

import { AuthApiError, deleteAccount, fetchAccountDeletionPreview } from '@/features/auth/api'
import { TerrainCard } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

const PUBLIC_DELETION_URL = 'https://spore-os.com/supprimer-compte/'

type AccountDeletionPreview = {
  requires_organization_closure: boolean
  organizations: Array<{ id: string; name: string; establishment_names: string[] }>
  leaves_establishments_without_director: Array<{ id: string; name: string }>
}

type AccountDeletionCardProps = {
  disabled?: boolean
  onDeleted: () => Promise<void> | void
}

export function AccountDeletionCard({ disabled = false, onDeleted }: AccountDeletionCardProps) {
  const [open, setOpen] = useState(false)
  const [preview, setPreview] = useState<AccountDeletionPreview | null>(null)
  const [password, setPassword] = useState('')
  const [closeOrganizations, setCloseOrganizations] = useState(false)
  const [isLoadingPreview, setIsLoadingPreview] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [previewReloadFailed, setPreviewReloadFailed] = useState(false)

  async function loadPreview() {
    setIsLoadingPreview(true)
    try {
      const data = await fetchAccountDeletionPreview()
      setPreview(data)
      setPreviewReloadFailed(false)
      return data
    } finally {
      setIsLoadingPreview(false)
    }
  }

  async function openForm() {
    setError(null)
    setPreviewReloadFailed(false)
    setOpen(true)
    try {
      await loadPreview()
    } catch {
      setError('Impossible de charger les conséquences de la suppression.')
    }
  }

  async function retryPreview() {
    setError(null)
    try {
      const data = await loadPreview()
      if (data.requires_organization_closure) {
        setError('Cochez la fermeture de votre organisation pour continuer.')
      }
    } catch {
      setPreviewReloadFailed(true)
      setError('Impossible de recharger les conséquences de la suppression.')
    }
  }

  async function submit() {
    if (!preview) {
      return
    }
    setError(null)
    setIsSubmitting(true)
    try {
      await deleteAccount({
        password,
        close_organizations: preview.requires_organization_closure ? closeOrganizations : false,
      })
      await onDeleted()
    } catch (caught) {
      if (caught instanceof AuthApiError && caught.code === 'organization_closure_required') {
        try {
          const data = await loadPreview()
          if (data.requires_organization_closure) {
            setError('Cochez la fermeture de votre organisation pour continuer.')
          }
        } catch {
          setPreviewReloadFailed(true)
          setError('Impossible de recharger les conséquences de la suppression.')
        }
      } else if (caught instanceof AuthApiError && caught.status === 403) {
        setError('Mot de passe incorrect.')
      } else {
        setError('La suppression n’a pas pu aboutir.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const canSubmit =
    Boolean(password) &&
    !isSubmitting &&
    !isLoadingPreview &&
    preview !== null &&
    !previewReloadFailed &&
    (!preview.requires_organization_closure || closeOrganizations)

  return (
    <TerrainCard padding="sm" className="space-y-3">
      {open ? (
        <div className="space-y-3">
          <p className="text-sm font-medium text-[#1a1a1a]">Supprimer mon compte</p>
          <p className="text-sm text-[#5c5a54]">
            Cette action retire votre identifiant et le contenu que vous avez soumis. Les
            signaux et plans d’action de l’établissement peuvent rester, sans votre nom.
          </p>
          {preview?.requires_organization_closure ? (
            <label className="flex items-start gap-2 text-sm text-[#1a1a1a]">
              <input
                type="checkbox"
                className="mt-1"
                checked={closeOrganizations}
                onChange={(event) => setCloseOrganizations(event.target.checked)}
              />
              <span>
                Fermer mon organisation
                {preview.organizations[0]
                  ? ` (${preview.organizations[0].name})`
                  : ''}{' '}
                et ses établissements.
              </span>
            </label>
          ) : null}
          {preview && preview.leaves_establishments_without_director.length > 0 ? (
            <p className="text-sm text-[#5c5a54]">
              Après suppression, plus de directeur sur{' '}
              {preview.leaves_establishments_without_director
                .map((item) => item.name)
                .join(', ')}
              . Un propriétaire pourra en inviter un autre.
            </p>
          ) : null}
          <input
            type="password"
            autoComplete="current-password"
            placeholder="Mot de passe"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="min-h-11 w-full rounded-md border border-[#E8E6DF] px-3 text-sm"
          />
          {error ? <p className="text-sm text-[#E24B4A]">{error}</p> : null}
          {previewReloadFailed ? (
            <button
              type="button"
              className="min-h-11 w-full text-sm font-medium text-[#1a1a1a] underline"
              disabled={isLoadingPreview || isSubmitting}
              onClick={() => {
                void retryPreview()
              }}
            >
              Recharger les conséquences
            </button>
          ) : null}
          <a
            href={PUBLIC_DELETION_URL}
            className="block text-sm text-[#5c5a54] underline"
            target="_blank"
            rel="noreferrer"
          >
            Autre moyen de demander la suppression
          </a>
          <div className="flex gap-2">
            <button
              type="button"
              className="min-h-11 flex-1 text-sm text-[#5c5a54]"
              disabled={isSubmitting}
              onClick={() => {
                setOpen(false)
                setPassword('')
                setError(null)
                setPreviewReloadFailed(false)
              }}
            >
              Annuler
            </button>
            <button
              type="button"
              className={cn(
                'min-h-11 flex-1 text-sm font-medium text-[#E24B4A]',
                !canSubmit && 'opacity-60',
              )}
              disabled={!canSubmit}
              onClick={() => {
                void submit()
              }}
            >
              {isSubmitting ? 'Suppression...' : 'Confirmer la suppression'}
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          className={cn(
            'flex min-h-11 w-full items-center justify-center text-sm font-medium text-[#E24B4A]',
            disabled && 'opacity-60',
          )}
          disabled={disabled}
          onClick={() => {
            void openForm()
          }}
        >
          Supprimer mon compte
        </button>
      )}
    </TerrainCard>
  )
}
