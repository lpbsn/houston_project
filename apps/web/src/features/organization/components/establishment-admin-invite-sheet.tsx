import { useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TerrainBottomSheet } from '@/components/ui/terrain'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  establishmentAdminInviteRequiresScopes,
  type EstablishmentAdminInviteRole,
} from '../lib/establishment-admin-invite-roles'
import type { EstablishmentAdminMemberFilterOptions } from '../types'
import { formatOrgRole } from './organization-establishments-tab'

type InviteEstablishmentMemberSheetProps = {
  open: boolean
  onClose: () => void
  onSubmit: (input: {
    email: string
    first_name: string
    last_name: string
    role: EstablishmentAdminInviteRole
    scopes: Array<{ scope_type: 'business_unit'; scope_id: string }>
  }) => Promise<void>
  isSubmitting: boolean
  errorMessage: string | null
  allowedRoles: EstablishmentAdminInviteRole[]
  filterOptions: EstablishmentAdminMemberFilterOptions | undefined
}

export function InviteEstablishmentMemberSheet({
  open,
  onClose,
  onSubmit,
  isSubmitting,
  errorMessage,
  allowedRoles,
  filterOptions,
}: InviteEstablishmentMemberSheetProps) {
  const [email, setEmail] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [role, setRole] = useState<EstablishmentAdminInviteRole>(
    allowedRoles[0] ?? 'staff',
  )
  const [selectedBuIds, setSelectedBuIds] = useState<string[]>([])

  const effectiveRole = useMemo(() => {
    if (allowedRoles.includes(role)) return role
    return allowedRoles[0] ?? 'staff'
  }, [allowedRoles, role])

  const needsScopes = establishmentAdminInviteRequiresScopes(effectiveRole)
  const businessUnits = filterOptions?.business_units ?? []

  function reset() {
    setEmail('')
    setFirstName('')
    setLastName('')
    setRole(allowedRoles[0] ?? 'staff')
    setSelectedBuIds([])
  }

  return (
    <TerrainBottomSheet
      title="Inviter un membre"
      open={open}
      onClose={() => {
        reset()
        onClose()
      }}
      footer={
        <Button
          type="button"
          className="w-full"
          disabled={
            isSubmitting ||
            !email.trim() ||
            !firstName.trim() ||
            !lastName.trim() ||
            allowedRoles.length === 0 ||
            (needsScopes && selectedBuIds.length === 0)
          }
          onClick={async () => {
            await onSubmit({
              email: email.trim(),
              first_name: firstName.trim(),
              last_name: lastName.trim(),
              role: effectiveRole,
              scopes: needsScopes
                ? selectedBuIds.map((scope_id) => ({
                    scope_type: 'business_unit' as const,
                    scope_id,
                  }))
                : [],
            })
            reset()
          }}
        >
          Envoyer l’invitation
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
        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-[#1a1a1a]">Rôle</span>
          <select
            className="min-h-11 w-full rounded-xl border border-[#E8E6E1] bg-white px-3 text-sm"
            value={effectiveRole}
            onChange={(event) => {
              setRole(event.target.value as EstablishmentAdminInviteRole)
              setSelectedBuIds([])
            }}
          >
            {allowedRoles.map((option) => (
              <option key={option} value={option}>
                {formatOrgRole(option)}
              </option>
            ))}
          </select>
        </label>
        {needsScopes ? (
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium text-[#1a1a1a]">Pôles</legend>
            {businessUnits.length === 0 ? (
              <p className={cn('text-xs', terrain.muted)}>Aucun pôle actif disponible.</p>
            ) : (
              businessUnits.map((unit) => {
                const checked = selectedBuIds.includes(unit.id)
                return (
                  <label key={unit.id} className="flex min-h-11 items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => {
                        setSelectedBuIds((current) =>
                          checked
                            ? current.filter((id) => id !== unit.id)
                            : [...current, unit.id],
                        )
                      }}
                    />
                    {unit.label}
                  </label>
                )
              })
            )}
          </fieldset>
        ) : null}
        {errorMessage ? <p className="text-sm text-red-600">{errorMessage}</p> : null}
      </div>
    </TerrainBottomSheet>
  )
}
