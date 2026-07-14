import { Copy, LoaderCircle, UserPlus } from 'lucide-react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { TerrainFeedback } from '@/components/domain/terrain-feedback'
import { BusinessUnitScopeSelector } from '@/components/domain/business-unit-scope-selector'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  TerrainCard,
  TerrainErrorState,
  TerrainFieldLabel,
  TerrainSectionLabel,
} from '@/components/ui/terrain'
import { useMembershipInviteForm } from '@/features/auth/hooks/use-membership-invite-form'
import { buildInvitationCreatedMessage } from '@/features/auth/lib/invitation-messaging'
import {
  canInviteFromBootstrapHints,
  getBootstrapPermissionHints,
} from '@/features/auth/lib/bootstrap-permission-hints'
import { getAllowedInviteTargetRoles } from '@/features/auth/lib/invitation-rbac'
import { toRoleEnum } from '@/features/auth/lib/role'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

export function TeamInvitePage() {
  const { navigate } = useAppRoute()
  const { activeMembership, bootstrap } = useAuth()
  const permissionHints = getBootstrapPermissionHints(bootstrap)
  const role = toRoleEnum(activeMembership?.role)
  const allowedTargetRoles = getAllowedInviteTargetRoles(role)
  const canAccess = Boolean(activeMembership) && canInviteFromBootstrapHints(permissionHints)

  if (!canAccess || !activeMembership) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message="Votre profil actuel ne vous permet pas de créer des invitations."
        retryLabel="Retour à l'équipe"
        onRetry={() => navigate('/team')}
      />
    )
  }

  return (
    <TeamInviteForm
      establishmentId={activeMembership.establishment_id}
      allowedTargetRoles={allowedTargetRoles}
    />
  )
}

type TeamInviteFormProps = {
  establishmentId: string
  allowedTargetRoles: ReturnType<typeof getAllowedInviteTargetRoles>
}

function TeamInviteForm({ establishmentId, allowedTargetRoles }: TeamInviteFormProps) {
  const {
    form,
    setForm,
    selectedBusinessUnitScopes,
    setSelectedBusinessUnitScopes,
    invitationLink,
    invitedEmail,
    copyMessage,
    errorMessage,
    isSubmitting,
    businessUnitQuery,
    roleOptions,
    hasRoleOptions,
    selectedRole,
    isManagerRestrictedToStaff,
    canSubmit,
    handleSubmit,
    handleCopyLink,
  } = useMembershipInviteForm({ establishmentId, allowedTargetRoles })

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 px-3 pb-4 pt-3">
      {!hasRoleOptions ? (
        <p className={cn('px-0.5 text-sm', terrain.muted)}>
          Aucun rôle invitable pour votre profil.
        </p>
      ) : null}

      {isManagerRestrictedToStaff ? (
        <TerrainCard className="text-sm text-[#5f574d]">
          Vous pouvez inviter uniquement un membre Staff dans votre périmètre opérationnel.
        </TerrainCard>
      ) : null}

      {hasRoleOptions ? (
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <section className="space-y-2">
            <TerrainSectionLabel>Identité</TerrainSectionLabel>
            <TerrainCard className="space-y-3 p-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <TerrainFieldLabel>First name</TerrainFieldLabel>
                  <Input
                    value={form.first_name}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, first_name: event.target.value }))
                    }
                    className="h-9 border-[#E8E6DF]"
                  />
                </div>
                <div className="space-y-1.5">
                  <TerrainFieldLabel>Last name</TerrainFieldLabel>
                  <Input
                    value={form.last_name}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, last_name: event.target.value }))
                    }
                    className="h-9 border-[#E8E6DF]"
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <TerrainFieldLabel>Email</TerrainFieldLabel>
                <Input
                  type="email"
                  value={form.email}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, email: event.target.value }))
                  }
                  className="h-9 border-[#E8E6DF]"
                />
              </div>
            </TerrainCard>
          </section>

          <section className="space-y-2">
            <TerrainSectionLabel>Role</TerrainSectionLabel>
            <TerrainCard className="p-3">
              {roleOptions.length === 1 ? (
                <Button type="button" className="h-9 rounded-xl capitalize" disabled>
                  {roleOptions[0]}
                </Button>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {roleOptions.map((roleOption) => (
                    <Button
                      key={roleOption}
                      type="button"
                      variant={selectedRole === roleOption ? 'default' : 'outline'}
                      className="h-9 rounded-xl capitalize"
                      onClick={() => setForm((current) => ({ ...current, role: roleOption }))}
                    >
                      {roleOption}
                    </Button>
                  ))}
                </div>
              )}
            </TerrainCard>
          </section>

          <section className="space-y-2">
            <TerrainSectionLabel>Pôles d&apos;activité</TerrainSectionLabel>
            <BusinessUnitScopeSelector
              tree={businessUnitQuery.data ?? null}
              selectedScopes={selectedBusinessUnitScopes}
              onChange={setSelectedBusinessUnitScopes}
              isLoading={businessUnitQuery.isPending}
              errorMessage={
                businessUnitQuery.error
                  ? businessUnitQuery.error instanceof Error
                    ? businessUnitQuery.error.message
                    : 'Les pôles d’activité sont indisponibles.'
                  : null
              }
              disabled={isSubmitting}
            />
          </section>

          {errorMessage ? <TerrainFeedback variant="error" message={errorMessage} /> : null}

          <Button
            type="submit"
            disabled={!canSubmit || isSubmitting}
            className="h-11 w-full rounded-xl"
          >
            {isSubmitting ? (
              <>
                <LoaderCircle className="size-4 animate-spin" />
                Creating invitation...
              </>
            ) : (
              <>
                <UserPlus className="size-4" />
                Create invitation
              </>
            )}
          </Button>
        </form>
      ) : null}

      {invitationLink && invitedEmail ? (
        <section className="space-y-2">
          <TerrainSectionLabel>Invitation</TerrainSectionLabel>
          <TerrainCard className="space-y-3 p-3">
            <TerrainFeedback
              variant="success"
              message={buildInvitationCreatedMessage(invitedEmail ?? '')}
            />
            <p className="break-all text-sm text-muted-foreground">{invitationLink}</p>
            <Button
              type="button"
              variant="outline"
              className="h-10 w-full rounded-xl"
              onClick={handleCopyLink}
            >
              <Copy className="size-4" />
              Copy invitation link
            </Button>
            {copyMessage ? <p className={cn('text-sm', terrain.muted)}>{copyMessage}</p> : null}
          </TerrainCard>
        </section>
      ) : null}
    </div>
  )
}
