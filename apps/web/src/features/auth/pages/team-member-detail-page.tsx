import { useMemo, useState } from 'react'
import { ArrowLeft, LoaderCircle } from 'lucide-react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { BusinessUnitScopeSelector } from '@/components/domain/business-unit-scope-selector'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  HoustonBadge,
  TerrainCard,
  TerrainDetailFieldCard,
  TerrainErrorState,
  TerrainSectionLabel,
  TerrainSwitch,
} from '@/components/ui/terrain'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import {
  useActivateMembershipMutation,
  useDeactivateMembershipMutation,
  useTeamMemberDetailQuery,
  useUpdateMembershipMutation,
  useUpdateProfileMutation,
} from '@/features/auth/hooks/use-team-members'
import { businessUnitScopesFromApiItems } from '@/features/auth/lib/business-unit-scope'
import { resolveMembershipManagementErrorMessage } from '@/features/auth/lib/membership-management-errors'
import {
  canChangeMembershipRoleViaPatch,
  canEditMembershipOperationalScopes,
  getEditableRoleOptions,
} from '@/features/auth/lib/membership-rbac'
import {
  buildMemberDisplayName,
  getTeamMembershipStatusBadge,
  membershipIsActive,
  membershipIsInvited,
  normalizeTeamRole,
} from '@/features/auth/lib/team-members'
import { toRoleEnum } from '@/features/auth/lib/role'
import type { EstablishmentMembershipResponse, RoleEnum } from '@/features/auth/types'
import { terrain, terrainBackButtonClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

const ROLE_PILL_OPTIONS: RoleEnum[] = ['owner', 'director', 'manager', 'staff']

const ROLE_PILL_LABELS: Record<RoleEnum, string> = {
  owner: 'Propriétaire',
  director: 'Directeur',
  manager: 'Manager',
  staff: 'Équipe',
}

const OWNER_DEACTIVATE_CONFIRM_MESSAGE =
  'Désactiver ce propriétaire le désactivera sur tous les établissements brouillon et actifs de l’organisation. Continuer ?'

type TeamMemberDetailPageProps = {
  membershipId: string
}

type EditorDraft = {
  firstName: string
  lastName: string
  email: string
  role: RoleEnum
  scopes: ReturnType<typeof businessUnitScopesFromApiItems>
}

function buildEditorDraft(membership: EstablishmentMembershipResponse): EditorDraft {
  return {
    firstName: membership.user.first_name ?? '',
    lastName: membership.user.last_name ?? '',
    email: membership.user.email ?? '',
    role: normalizeTeamRole(membership.role),
    scopes: businessUnitScopesFromApiItems(membership.scopes),
  }
}

function hasEditableFields(membership: EstablishmentMembershipResponse | undefined): boolean {
  if (!membership?.permission_hints) {
    return false
  }
  const hints = membership.permission_hints
  return (
    hints.can_edit_personal_info ||
    hints.can_edit_role ||
    hints.can_edit_scopes ||
    hints.can_edit_status
  )
}

export function TeamMemberDetailPage({ membershipId }: TeamMemberDetailPageProps) {
  const { navigate } = useAppRoute()
  const { activeMembership } = useAuth()
  const detailQuery = useTeamMemberDetailQuery(membershipId)
  const membership = detailQuery.data
  const establishmentId = activeMembership?.establishment_id ?? null

  const [isEditing, setIsEditing] = useState(false)
  const [draft, setDraft] = useState<EditorDraft | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const updateMembershipMutation = useUpdateMembershipMutation(membershipId)
  const activateMutation = useActivateMembershipMutation(membershipId)
  const deactivateMutation = useDeactivateMembershipMutation(membershipId)
  const updateProfileMutation = useUpdateProfileMutation()

  const currentRole = membership ? normalizeTeamRole(membership.role) : null
  const draftRole = isEditing && draft ? draft.role : currentRole
  const needsScopeEditor =
    Boolean(draftRole && canEditMembershipOperationalScopes(draftRole)) &&
    (Boolean(membership?.permission_hints?.can_edit_scopes) ||
      (isEditing && currentRole === 'director'))

  const businessUnitQuery = useBusinessUnitTreeQuery(establishmentId, {
    enabled: Boolean(establishmentId && needsScopeEditor),
    staleTime: 60_000,
  })

  const actorRole = toRoleEnum(activeMembership?.role)
  const editableRoleOptions = useMemo(
    () => (actorRole && currentRole ? getEditableRoleOptions(actorRole, currentRole) : []),
    [actorRole, currentRole],
  )
  const roleEditableViaPatch = currentRole
    ? canChangeMembershipRoleViaPatch(currentRole)
    : false

  const isSaving =
    updateMembershipMutation.isPending ||
    activateMutation.isPending ||
    deactivateMutation.isPending ||
    updateProfileMutation.isPending

  const isStatusPending = activateMutation.isPending || deactivateMutation.isPending

  if (detailQuery.isPending) {
    return <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Chargement du membre...</p>
  }

  if (detailQuery.isError || !membership || !currentRole) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message="Ce membre est introuvable."
        retryLabel="Retour à l'équipe"
        onRetry={() => navigate('/team')}
      />
    )
  }

  const displayName = buildMemberDisplayName(membership)
  const statusBadge = getTeamMembershipStatusBadge(membership)
  const hints = membership.permission_hints
  const isOwnerTarget = currentRole === 'owner'
  const showScopesSection = Boolean(draftRole && canEditMembershipOperationalScopes(draftRole))
  const canEdit = hasEditableFields(membership)
  const invited = membershipIsInvited(membership)
  const isActive = membershipIsActive(membership)

  const beginEditing = () => {
    setDraft(buildEditorDraft(membership))
    setErrorMessage(null)
    setIsEditing(true)
  }

  const cancelEditing = () => {
    setDraft(null)
    setErrorMessage(null)
    setIsEditing(false)
  }

  const handleSave = async () => {
    if (!draft) {
      return
    }

    setErrorMessage(null)

    try {
      const membershipUpdates: { role?: RoleEnum; scopes?: typeof draft.scopes } = {}
      let profileChanged = false
      const profilePayload: { first_name?: string; last_name?: string; email?: string } = {}

      if (hints?.can_edit_personal_info) {
        if (draft.firstName.trim() !== (membership.user.first_name ?? '')) {
          profilePayload.first_name = draft.firstName.trim()
          profileChanged = true
        }
        if (draft.lastName.trim() !== (membership.user.last_name ?? '')) {
          profilePayload.last_name = draft.lastName.trim()
          profileChanged = true
        }
        if ((draft.email.trim() || null) !== (membership.user.email ?? null)) {
          profilePayload.email = draft.email.trim() || null
          profileChanged = true
        }
      }

      const roleChanged =
        hints?.can_edit_role &&
        roleEditableViaPatch &&
        draft.role !== normalizeTeamRole(membership.role)

      if (roleChanged) {
        if (!canEditMembershipOperationalScopes(draft.role)) {
          throw new Error('Ce changement de rôle n’est pas autorisé.')
        }
        if (draft.scopes.length === 0) {
          throw new Error('Sélectionnez au moins un pôle d’activité pour ce rôle.')
        }
        membershipUpdates.role = draft.role
        membershipUpdates.scopes = draft.scopes
      } else if (hints?.can_edit_scopes && canEditMembershipOperationalScopes(draft.role)) {
        const currentScopeIds = membership.scopes.map((scope) => scope.scope_id).sort()
        const nextScopeIds = draft.scopes.map((scope) => scope.scope_id).sort()
        if (currentScopeIds.join(',') !== nextScopeIds.join(',')) {
          membershipUpdates.scopes = draft.scopes
        }
      }

      if (profileChanged) {
        await updateProfileMutation.mutateAsync(profilePayload)
      }

      if (membershipUpdates.role || membershipUpdates.scopes) {
        await updateMembershipMutation.mutateAsync(membershipUpdates)
      }

      setIsEditing(false)
      setDraft(null)
    } catch (error) {
      setErrorMessage(
        resolveMembershipManagementErrorMessage(
          error,
          'Les modifications n’ont pas pu être enregistrées.',
        ),
      )
    }
  }

  const handleStatusToggle = async (checked: boolean) => {
    if (!hints?.can_edit_status || invited) {
      return
    }

    if (!checked && isOwnerTarget) {
      if (!window.confirm(OWNER_DEACTIVATE_CONFIRM_MESSAGE)) {
        return
      }
    }

    setErrorMessage(null)

    try {
      if (checked) {
        await activateMutation.mutateAsync()
      } else {
        await deactivateMutation.mutateAsync()
      }
    } catch (error) {
      setErrorMessage(
        resolveMembershipManagementErrorMessage(error, 'Le statut n’a pas pu être mis à jour.'),
      )
    }
  }

  const effectiveDraft = isEditing && draft ? draft : buildEditorDraft(membership)
  const effectiveRole = isEditing && draft ? draft.role : currentRole
  const canEditScopesInForm =
    isEditing &&
    canEditMembershipOperationalScopes(effectiveRole) &&
    (Boolean(hints?.can_edit_scopes) || currentRole === 'director')

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="shrink-0 border-b border-[#E8E6DF] bg-white px-4 pb-3 pt-[max(0.75rem,env(safe-area-inset-top))]">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <Button
              type="button"
              variant="ghost"
              className={terrainBackButtonClassName()}
              onClick={() => navigate('/team')}
            >
              <ArrowLeft className="mr-1 h-4 w-4" />
              Retour
            </Button>
            <div className="mt-2 flex min-w-0 items-center gap-2">
              <h1 className="min-w-0 truncate text-xl font-semibold text-[#1a1a1a]">{displayName}</h1>
              {statusBadge ? (
                <HoustonBadge variant={statusBadge.variant} className="shrink-0 normal-case">
                  {statusBadge.label}
                </HoustonBadge>
              ) : null}
            </div>
          </div>
          {canEdit && !isEditing ? (
            <Button
              type="button"
              variant="outline"
              className="mt-6 h-9 rounded-xl border-[#D7D4CB] px-3 text-sm"
              onClick={beginEditing}
            >
              Modifier
            </Button>
          ) : null}
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-4 px-3 py-4">
        <section className="space-y-2">
          <TerrainSectionLabel>Informations</TerrainSectionLabel>
          <TerrainCard className="divide-y divide-[#E8E6DF] p-0">
            <TerrainDetailFieldCard label="Prénom">
              {isEditing && hints?.can_edit_personal_info ? (
                <Input
                  value={effectiveDraft.firstName}
                  onChange={(event) =>
                    setDraft((current) =>
                      current ? { ...current, firstName: event.target.value } : current,
                    )
                  }
                  className="h-9 border-[#E8E6DF]"
                />
              ) : (
                <span>{membership.user.first_name || '—'}</span>
              )}
            </TerrainDetailFieldCard>
            <TerrainDetailFieldCard label="Nom">
              {isEditing && hints?.can_edit_personal_info ? (
                <Input
                  value={effectiveDraft.lastName}
                  onChange={(event) =>
                    setDraft((current) =>
                      current ? { ...current, lastName: event.target.value } : current,
                    )
                  }
                  className="h-9 border-[#E8E6DF]"
                />
              ) : (
                <span>{membership.user.last_name || '—'}</span>
              )}
            </TerrainDetailFieldCard>
            <TerrainDetailFieldCard label="Email">
              {isEditing && hints?.can_edit_personal_info ? (
                <Input
                  type="email"
                  value={effectiveDraft.email}
                  onChange={(event) =>
                    setDraft((current) =>
                      current ? { ...current, email: event.target.value } : current,
                    )
                  }
                  className="h-9 border-[#E8E6DF]"
                />
              ) : membership.user.email ? (
                <a href={`mailto:${membership.user.email}`} className="text-[#1B4FD8]">
                  {membership.user.email}
                </a>
              ) : (
                <span>—</span>
              )}
            </TerrainDetailFieldCard>
          </TerrainCard>
        </section>

        <section className="space-y-2">
          <TerrainSectionLabel>Poste</TerrainSectionLabel>
          <TerrainCard className="p-3">
            <div className="flex flex-wrap gap-2">
              {ROLE_PILL_OPTIONS.map((role) => {
                const isSelected = effectiveRole === role
                const canSelectDestination =
                  roleEditableViaPatch && editableRoleOptions.includes(role)
                const isDisabled =
                  !isEditing || !hints?.can_edit_role || (!canSelectDestination && !isSelected)

                return (
                  <button
                    key={role}
                    type="button"
                    disabled={isDisabled || (isSelected && !canSelectDestination)}
                    onClick={() =>
                      setDraft((current) =>
                        current
                          ? {
                              ...current,
                              role,
                              scopes: canEditMembershipOperationalScopes(role)
                                ? current.scopes
                                : [],
                            }
                          : current,
                      )
                    }
                    className={cn(
                      'rounded-full border px-3 py-1.5 text-sm font-medium transition',
                      isSelected
                        ? 'border-[#1B4FD8] bg-[#1B4FD8] text-white'
                        : 'border-[#E8E6DF] bg-[#FAFAF8] text-[#5C5A54]',
                      isDisabled && 'cursor-default opacity-80',
                    )}
                  >
                    {ROLE_PILL_LABELS[role]}
                  </button>
                )
              })}
            </div>
            {isOwnerTarget ? (
              <p className="mt-3 text-sm text-[#5f574d]">
                Le rôle propriétaire ne peut pas être modifié ici. Utilisez l’invitation pour
                ajouter un propriétaire, ou l’activation / désactivation pour le cycle de vie.
              </p>
            ) : null}
          </TerrainCard>
        </section>

        {showScopesSection ? (
          <section className="space-y-2">
            <TerrainSectionLabel>Pôle d&apos;activité</TerrainSectionLabel>
            <TerrainCard className="p-3">
              {canEditScopesInForm ? (
                <BusinessUnitScopeSelector
                  tree={businessUnitQuery.data ?? null}
                  selectedScopes={effectiveDraft.scopes}
                  onChange={(scopes) =>
                    setDraft((current) => (current ? { ...current, scopes } : current))
                  }
                  isLoading={businessUnitQuery.isPending}
                  disabled={isSaving}
                />
              ) : membership.scopes.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {membership.scopes.map((scope) => (
                    <HoustonBadge key={scope.scope_id} variant="gray">
                      {scope.scope_label || scope.scope_id}
                    </HoustonBadge>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-[#7D7B75]">Aucun pôle d&apos;activité assigné.</p>
              )}
            </TerrainCard>
          </section>
        ) : null}

        <section className="space-y-2">
          <TerrainSectionLabel>Autorisation</TerrainSectionLabel>
          <TerrainCard className="p-0">
            <TerrainSwitch
              label="Actif"
              checked={isActive}
              disabled={!hints?.can_edit_status || invited || isStatusPending || isEditing}
              onCheckedChange={handleStatusToggle}
            />
            {invited ? (
              <p className="px-4 pb-3.5 text-xs text-[#7D7B75]">
                {isOwnerTarget
                  ? 'Invitation propriétaire en attente : la désactivation retire l’invitation sur tous les établissements brouillon et actifs de l’organisation. Le membre devient actif après configuration du mot de passe.'
                  : 'Invitation en attente : le membre devient actif après configuration du mot de passe.'}
              </p>
            ) : isOwnerTarget ? (
              <p className="px-4 pb-3.5 text-xs text-[#7D7B75]">
                Désactiver ou réactiver un propriétaire applique le changement à tous les
                établissements brouillon et actifs de l’organisation.
              </p>
            ) : null}
          </TerrainCard>
        </section>

        {errorMessage ? (
          <p className="text-sm text-[#E24B4A]" role="alert">
            {errorMessage}
          </p>
        ) : null}

        {isEditing ? (
          <div className="flex flex-col gap-2 pb-2">
            <Button
              type="button"
              className="h-11 rounded-xl"
              disabled={isSaving}
              onClick={() => void handleSave()}
            >
              {isSaving ? (
                <>
                  <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                  Enregistrement...
                </>
              ) : (
                'Enregistrer'
              )}
            </Button>
            <Button
              type="button"
              variant="outline"
              className="h-11 rounded-xl"
              disabled={isSaving}
              onClick={cancelEditing}
            >
              Annuler
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  )
}
