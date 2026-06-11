import { ArrowRight, ClipboardCheck } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { EstablishmentSelectorCard } from '@/features/auth/components/establishment-selector-card'
import { EstablishmentSummaryCard } from '@/features/auth/components/establishment-summary-card'
import { MembershipInviteCard } from '@/features/auth/components/membership-invite-card'
import { MembershipManagementCard } from '@/features/auth/components/membership-management-card'
import { useAppPageWorkspace } from '@/features/auth/hooks/use-app-page-workspace'
import {
  canInviteFromBootstrapHints,
  canManageRuntimeConfigFromBootstrapHints,
  getBootstrapPermissionHints,
} from '@/features/auth/lib/bootstrap-permission-hints'
import { toErrorMessage } from '@/lib/error-message'

export function AppPage({ onNavigate }: { onNavigate?: (path: string) => void }) {
  const { bootstrap } = useAuth()
  const permissionHints = getBootstrapPermissionHints(bootstrap)
  const canManageRuntimeConfig = canManageRuntimeConfigFromBootstrapHints(permissionHints)
  const canInvite = canInviteFromBootstrapHints(permissionHints)

  const {
    activeMembership,
    actorRole,
    businessUnitQuery,
    deactivateMutation,
    effectiveSelectedMembershipId,
    handleDeactivateMembership,
    handleRoleChange,
    handleSaveMembership,
    handleScopesChange,
    handleSelectEstablishment,
    handleSelectMembership,
    membershipDetailQuery,
    membershipList,
    membershipMutationError,
    memberships,
    membershipsQuery,
    needsEstablishmentSelection,
    pendingEstablishmentId,
    roleDraft,
    scopeBusinessUnitError,
    selectedMembership,
    selectedScopes,
    selectorError,
    updateMutation,
    workspaceSummaryQuery,
  } = useAppPageWorkspace({ membershipManagementEnabled: canManageRuntimeConfig })

  return (
    <div className="space-y-4 sm:space-y-5">
      <EstablishmentSummaryCard
        isLoading={workspaceSummaryQuery.isPending}
        summary={workspaceSummaryQuery.data ?? null}
        errorMessage={
          workspaceSummaryQuery.error
            ? toErrorMessage(
                workspaceSummaryQuery.error,
                'Establishment summary is unavailable.',
              )
            : null
        }
      />

      {needsEstablishmentSelection ? (
        <EstablishmentSelectorCard
          memberships={memberships}
          pendingEstablishmentId={pendingEstablishmentId}
          onSelect={handleSelectEstablishment}
          errorMessage={selectorError}
        />
      ) : null}

      {activeMembership ? (
        <Card className="rounded-[1.75rem] border-[#e7dfd1] bg-[#fffaf2]">
          <CardHeader className="gap-2">
            <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
              Terrain
            </Badge>
            <CardTitle className="text-xl font-semibold">Faire remonter une observation</CardTitle>
            <CardDescription className="text-sm">
              Texte ou dictée audio, photos optionnelles (max. 3).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="h-11 w-full rounded-[1rem] sm:w-auto">
              <a href="/app/report">
                Ouvrir le reporting
                <ArrowRight className="size-4" />
              </a>
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {activeMembership && canManageRuntimeConfig ? (
        <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
          <CardHeader className="gap-3">
            <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
              Configuration
            </Badge>
            <div className="space-y-2">
              <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
                Configuration opérationnelle
              </CardTitle>
              <CardDescription className="text-sm leading-6">
                Consultez et modifiez les pôles, sujets et descriptions de votre établissement
                actif.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3 rounded-[1.15rem] border border-[#ebe2d5] bg-[#fbf7f0] px-4 py-3 text-sm text-muted-foreground">
              <span className="rounded-full bg-[color:var(--primary)]/10 p-2 text-[color:var(--primary)]">
                <ClipboardCheck className="size-4" />
              </span>
              <span>{activeMembership.establishment_name}</span>
            </div>
            <Button
              type="button"
              className="h-11 rounded-[1rem]"
              onClick={() => onNavigate?.('/app/operational-config')}
            >
              Modifier l’onboarding
              <ArrowRight className="size-4" />
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {activeMembership ? (
        canManageRuntimeConfig ? (
          <>
            <MembershipManagementCard
              actorRole={actorRole}
              businessUnitTree={businessUnitQuery.data ?? null}
              errorMessage={membershipMutationError}
              isDeactivating={deactivateMutation.isPending}
              isLoadingBusinessUnits={businessUnitQuery.isPending}
              isLoadingList={membershipsQuery.isPending}
              isLoadingMembership={membershipDetailQuery.isPending}
              isSaving={updateMutation.isPending}
              memberships={membershipList}
              onDeactivate={handleDeactivateMembership}
              onRoleChange={handleRoleChange}
              onSave={handleSaveMembership}
              onScopesChange={handleScopesChange}
              onSelectMembership={handleSelectMembership}
              roleDraft={roleDraft}
              scopeBusinessUnitError={scopeBusinessUnitError}
              selectedMembership={selectedMembership}
              selectedMembershipId={effectiveSelectedMembershipId}
              selectedScopes={selectedScopes}
            />
            {canInvite ? (
              <MembershipInviteCard establishmentId={activeMembership.establishment_id} />
            ) : null}
          </>
        ) : canInvite ? (
          <MembershipInviteCard establishmentId={activeMembership.establishment_id} />
        ) : (
          <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
            <CardHeader className="gap-3">
              <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
                Memberships
              </Badge>
              <div className="space-y-2">
                <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
                  Membership management unavailable
                </CardTitle>
                <CardDescription className="text-sm leading-6">
                  Your current role is{' '}
                  <span className="font-semibold text-foreground">{activeMembership.role}</span>.
                  Only owners and directors can manage memberships or send invitations.
                </CardDescription>
              </div>
            </CardHeader>
          </Card>
        )
      ) : (
        <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
          <CardHeader className="gap-3">
            <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
              Establishment
            </Badge>
            <div className="space-y-2">
              <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
                Select an establishment to continue
              </CardTitle>
              <CardDescription className="text-sm leading-6">
                Choose one establishment to view its summary and available management tools.
              </CardDescription>
            </div>
          </CardHeader>
        </Card>
      )}
    </div>
  )
}
