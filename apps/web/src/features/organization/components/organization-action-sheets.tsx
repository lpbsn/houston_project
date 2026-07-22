import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TerrainBottomSheet } from '@/components/ui/terrain'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type CreateEstablishmentSheetProps = {
  open: boolean
  onClose: () => void
  onSubmit: (name: string) => Promise<void>
  isSubmitting: boolean
  errorMessage: string | null
}

export function CreateEstablishmentSheet({
  open,
  onClose,
  onSubmit,
  isSubmitting,
  errorMessage,
}: CreateEstablishmentSheetProps) {
  const [name, setName] = useState('')

  return (
    <TerrainBottomSheet
      title="Ajouter un établissement"
      open={open}
      onClose={onClose}
      footer={
        <Button
          type="button"
          className="w-full"
          disabled={isSubmitting || name.trim().length === 0}
          onClick={async () => {
            await onSubmit(name.trim())
            setName('')
          }}
        >
          Créer
        </Button>
      }
    >
      <div className="space-y-3 p-4">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-[#1a1a1a]">Nom</span>
          <Input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Nom de l’établissement"
            autoComplete="organization"
          />
        </label>
        {errorMessage ? (
          <p className={cn('text-sm text-red-600')}>{errorMessage}</p>
        ) : (
          <p className={cn('text-xs', terrain.muted)}>
            L’établissement sera créé en configuration. Votre établissement actif ne change pas.
          </p>
        )}
      </div>
    </TerrainBottomSheet>
  )
}

type InviteOwnerSheetProps = {
  open: boolean
  onClose: () => void
  onSubmit: (input: {
    email: string
    first_name: string
    last_name: string
  }) => Promise<void>
  isSubmitting: boolean
  errorMessage: string | null
}

export function InviteOwnerSheet({
  open,
  onClose,
  onSubmit,
  isSubmitting,
  errorMessage,
}: InviteOwnerSheetProps) {
  const [email, setEmail] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')

  return (
    <TerrainBottomSheet
      title="Inviter un propriétaire"
      open={open}
      onClose={onClose}
      footer={
        <Button
          type="button"
          className="w-full"
          disabled={
            isSubmitting ||
            email.trim().length === 0 ||
            firstName.trim().length === 0 ||
            lastName.trim().length === 0
          }
          onClick={async () => {
            await onSubmit({
              email: email.trim(),
              first_name: firstName.trim(),
              last_name: lastName.trim(),
            })
            setEmail('')
            setFirstName('')
            setLastName('')
          }}
        >
          Inviter
        </Button>
      }
    >
      <div className="space-y-3 p-4">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-[#1a1a1a]">Prénom</span>
          <Input value={firstName} onChange={(event) => setFirstName(event.target.value)} />
        </label>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-[#1a1a1a]">Nom</span>
          <Input value={lastName} onChange={(event) => setLastName(event.target.value)} />
        </label>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-[#1a1a1a]">Email</span>
          <Input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
          />
        </label>
        {errorMessage ? <p className="text-sm text-red-600">{errorMessage}</p> : null}
      </div>
    </TerrainBottomSheet>
  )
}
