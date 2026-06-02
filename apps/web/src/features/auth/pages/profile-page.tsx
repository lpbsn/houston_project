import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { canSeeInviteMemberButton } from '@/features/auth/lib/invitation-rbac'
import type { RoleEnum } from '@/features/auth/types'

const MANAGEMENT_ROLES = new Set(['owner', 'director', 'manager'])
const INVITATION_ROLES: RoleEnum[] = ['owner', 'director', 'manager', 'staff']

function toRoleEnum(role: string | null | undefined): RoleEnum | null {
  if (!role) {
    return null
  }

  return INVITATION_ROLES.find((candidate) => candidate === role) ?? null
}

function readOptionalUserName(user: unknown, key: 'first_name' | 'last_name') {
  if (!user || typeof user !== 'object') {
    return null
  }

  const value = (user as Record<string, unknown>)[key]
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null
}

function toScopeSummaryText(scopeSummary: unknown) {
  if (!scopeSummary || typeof scopeSummary !== 'object') {
    return null
  }

  const summary = scopeSummary as Record<string, unknown>
  const moduleCount = typeof summary.module_count === 'number' ? summary.module_count : null
  const domainCount = typeof summary.domain_count === 'number' ? summary.domain_count : null
  const subjectCount = typeof summary.subject_count === 'number' ? summary.subject_count : null

  if (moduleCount === null || domainCount === null || subjectCount === null) {
    return null
  }

  return `${moduleCount} modules, ${domainCount} domaines, ${subjectCount} sujets`
}

export function ProfilePage() {
  const { activeMembership, user } = useAuth()

  const firstName = readOptionalUserName(user, 'first_name')
  const lastName = readOptionalUserName(user, 'last_name')
  const identityLabel = user ? (user.email ?? user.username) : null
  const role = toRoleEnum(activeMembership?.role)
  const canAccessManagement = role ? MANAGEMENT_ROLES.has(role) : false
  const canInviteMember = canSeeInviteMemberButton(role)
  const scopeSummary = toScopeSummaryText(activeMembership?.scope_summary)

  return (
    <div className="space-y-4">
      <Card className="rounded-2xl border-[#E8E6DF] bg-white p-5">
        <h2 className="text-base font-semibold text-[#1a1a1a]">Informations utilisateur</h2>
        <dl className="mt-4 space-y-3 text-sm text-[#5f574d]">
          {firstName ? (
            <div className="space-y-1">
              <dt className="text-xs uppercase tracking-[0.04em] text-[#7d7b75]">Prenom</dt>
              <dd className="font-medium text-[#1a1a1a]">{firstName}</dd>
            </div>
          ) : null}
          {lastName ? (
            <div className="space-y-1">
              <dt className="text-xs uppercase tracking-[0.04em] text-[#7d7b75]">Nom</dt>
              <dd className="font-medium text-[#1a1a1a]">{lastName}</dd>
            </div>
          ) : null}
          {identityLabel ? (
            <div className="space-y-1">
              <dt className="text-xs uppercase tracking-[0.04em] text-[#7d7b75]">Identifiant</dt>
              <dd className="font-medium text-[#1a1a1a]">{identityLabel}</dd>
            </div>
          ) : null}
        </dl>
      </Card>

      <Card className="rounded-2xl border-[#E8E6DF] bg-white p-5">
        <h2 className="text-base font-semibold text-[#1a1a1a]">Membership actif</h2>
        <dl className="mt-4 space-y-3 text-sm text-[#5f574d]">
          {role ? (
            <div className="space-y-1">
              <dt className="text-xs uppercase tracking-[0.04em] text-[#7d7b75]">Role courant</dt>
              <dd className="font-medium capitalize text-[#1a1a1a]">{role}</dd>
            </div>
          ) : null}
          {activeMembership?.establishment_name ? (
            <div className="space-y-1">
              <dt className="text-xs uppercase tracking-[0.04em] text-[#7d7b75]">Etablissement</dt>
              <dd className="font-medium text-[#1a1a1a]">{activeMembership.establishment_name}</dd>
            </div>
          ) : null}
          {activeMembership?.organization_name ? (
            <div className="space-y-1">
              <dt className="text-xs uppercase tracking-[0.04em] text-[#7d7b75]">Organisation</dt>
              <dd className="font-medium text-[#1a1a1a]">{activeMembership.organization_name}</dd>
            </div>
          ) : null}
          {activeMembership?.status ? (
            <div className="space-y-1">
              <dt className="text-xs uppercase tracking-[0.04em] text-[#7d7b75]">Statut membership</dt>
              <dd className="font-medium text-[#1a1a1a]">{activeMembership.status}</dd>
            </div>
          ) : null}
          {scopeSummary ? (
            <div className="space-y-1">
              <dt className="text-xs uppercase tracking-[0.04em] text-[#7d7b75]">
                Perimetre operationnel
              </dt>
              <dd className="font-medium text-[#1a1a1a]">{scopeSummary}</dd>
            </div>
          ) : null}
        </dl>

        {canAccessManagement ? (
          <Button asChild className="mt-5 h-11 rounded-xl bg-[#1B4FD8] text-white hover:bg-[#1B4FD8]/95">
            <a href="/app">Espace gestion</a>
          </Button>
        ) : null}

        {activeMembership && canInviteMember ? (
          <Button asChild variant="outline" className="mt-3 h-11 rounded-xl">
            <a href="/team/invite">Inviter un membre</a>
          </Button>
        ) : null}
      </Card>
    </div>
  )
}
