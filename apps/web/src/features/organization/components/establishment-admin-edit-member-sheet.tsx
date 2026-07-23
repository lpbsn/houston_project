import { useEffect, useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { TerrainBottomSheet } from '@/components/ui/terrain'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  establishmentAdminInviteRequiresScopes,
  type EstablishmentAdminInviteRole,
} from '../lib/establishment-admin-invite-roles'
import type {
  EstablishmentAdminMemberFilterOptions,
  EstablishmentAdminMembership,
  PatchedEstablishmentAdminMembershipUpdateRequest,
} from '../types'
import { formatOrgRole } from './organization-establishments-tab'

type EditEstablishmentMemberSheetProps = {
  open: boolean
  member: EstablishmentAdminMembership | null
  onClose: () => void
  onSubmit: (body: PatchedEstablishmentAdminMembershipUpdateRequest) => Promise<void>
  isSubmitting: boolean
  errorMessage: string | null
  allowedRoles: EstablishmentAdminInviteRole[]
  filterOptions: EstablishmentAdminMemberFilterOptions | undefined
}

function toAdminRole(role: string): EstablishmentAdminInviteRole | null {
  if (role === 'director' || role === 'manager' || role === 'staff') {
    return role
  }
  return null
}

export function EditEstablishmentMemberSheet({
  open,
  member,
  onClose,
  onSubmit,
  isSubmitting,
  errorMessage,
  allowedRoles,
  filterOptions,
}: EditEstablishmentMemberSheetProps) {
  const currentRole = member ? toAdminRole(member.role) : null
  const roleOptions = useMemo(() => {
    if (!currentRole) {
      return allowedRoles
    }
    if (allowedRoles.includes(currentRole)) {
      return allowedRoles
    }
    return [currentRole, ...allowedRoles]
  }, [allowedRoles, currentRole])

  const [role, setRole] = useState<EstablishmentAdminInviteRole>(currentRole ?? 'staff')
  const [selectedBuIds, setSelectedBuIds] = useState<string[]>([])

  useEffect(() => {
    if (!open || !member) {
      return
    }
    const nextRole = toAdminRole(member.role) ?? allowedRoles[0] ?? 'staff'
    setRole(nextRole)
    setSelectedBuIds(member.business_units.map((unit) => unit.id))
  }, [allowedRoles, member, open])

  const effectiveRole = useMemo(() => {
    if (roleOptions.includes(role)) return role
    return roleOptions[0] ?? 'staff'
  }, [role, roleOptions])

  const canEditRole = Boolean(member?.permission_hints.can_edit_role)
  const needsScopes = establishmentAdminInviteRequiresScopes(effectiveRole)
  const canEditScopes =
    Boolean(member?.permission_hints.can_edit_scopes) ||
    (canEditRole && needsScopes && effectiveRole !== currentRole)
  const businessUnits = filterOptions?.business_units ?? []

  const roleChanged = canEditRole && currentRole !== null && effectiveRole !== currentRole
  const initialBuIds = member?.business_units.map((unit) => unit.id) ?? []
  const scopesChanged =
    canEditScopes &&
    needsScopes &&
    (selectedBuIds.length !== initialBuIds.length ||
      selectedBuIds.some((id) => !initialBuIds.includes(id)))

  const canSubmit =
    Boolean(member) &&
    (roleChanged || scopesChanged) &&
    (!needsScopes || selectedBuIds.length > 0)

  const displayName = member
    ? [member.first_name, member.last_name].filter(Boolean).join(' ').trim() || member.email
    : ''

  return (
    <TerrainBottomSheet
      title="Modifier le membre"
      open={open && member !== null}
      onClose={onClose}
      footer={
        <Button
          type="button"
          className="w-full"
          disabled={isSubmitting || !canSubmit}
          onClick={async () => {
            if (!member) {
              return
            }
            const body: PatchedEstablishmentAdminMembershipUpdateRequest = {}
            if (canEditRole && roleChanged) {
              body.role = effectiveRole
            }
            if (needsScopes) {
              body.scopes = selectedBuIds.map((scope_id) => ({
                scope_type: 'business_unit' as const,
                scope_id,
              }))
            } else if (roleChanged && effectiveRole === 'director') {
              body.scopes = []
            }
            if (!body.role && body.scopes === undefined) {
              return
            }
            await onSubmit(body)
          }}
        >
          Enregistrer
        </Button>
      }
    >
      <div className="space-y-3 p-4">
        <p className="text-sm font-medium text-[#1a1a1a]">{displayName}</p>
        <p className={cn('text-xs', terrain.muted)}>{member?.email}</p>

        {canEditRole ? (
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-[#1a1a1a]">Rôle</span>
            <select
              className="min-h-11 w-full rounded-xl border border-[#E8E6E1] bg-white px-3 text-sm"
              value={effectiveRole}
              onChange={(event) => {
                setRole(event.target.value as EstablishmentAdminInviteRole)
              }}
            >
              {roleOptions.map((option) => (
                <option key={option} value={option}>
                  {formatOrgRole(option)}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <p className="text-sm text-[#1a1a1a]">
            Rôle : {currentRole ? formatOrgRole(currentRole) : member?.role}
          </p>
        )}

        {needsScopes && canEditScopes ? (
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
