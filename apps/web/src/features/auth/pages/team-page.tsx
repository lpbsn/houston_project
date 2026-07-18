import { useEffect, useRef, useState } from 'react'
import { ChevronRight, Search, UserPlus } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  TerrainCard,
  TerrainEmptyState,
  TerrainErrorState,
} from '@/components/ui/terrain'
import { TeamMemberList } from '@/features/auth/components/team/team-member-list'
import { TeamStatusFilters } from '@/features/auth/components/team/team-status-filters'
import {
  canInviteFromBootstrapHints,
  canViewTeamFromBootstrapHints,
  getBootstrapPermissionHints,
} from '@/features/auth/lib/bootstrap-permission-hints'
import {
  getTeamListUiState,
  setTeamListUiState,
} from '@/features/auth/lib/team-list-ui-state'
import {
  countTeamMembersByStatus,
  groupTeamMembersByRole,
  toggleTeamMemberStatusFilter,
  type TeamMembershipStatus,
} from '@/features/auth/lib/team-members'
import { useTeamMembersQuery } from '@/features/auth/hooks/use-team-members'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type TeamPageProps = {
  onNavigate?: (pathname: string) => void
}

export function TeamPage({ onNavigate }: TeamPageProps) {
  const { activeMembership, bootstrap, isBootstrapping, isReady } = useAuth()
  const permissionHints = getBootstrapPermissionHints(bootstrap)
  const canInvite = canInviteFromBootstrapHints(permissionHints)
  const canViewTeam = canViewTeamFromBootstrapHints(permissionHints)
  const establishmentId = activeMembership?.establishment_id ?? null

  const initialUiState = getTeamListUiState(establishmentId)
  const [searchQuery, setSearchQuery] = useState(initialUiState.searchQuery)
  const [selectedStatuses, setSelectedStatuses] = useState<ReadonlySet<TeamMembershipStatus>>(
    initialUiState.selectedStatuses,
  )
  const previousEstablishmentIdRef = useRef(establishmentId)

  const membersQuery = useTeamMembersQuery()

  useEffect(() => {
    if (previousEstablishmentIdRef.current === establishmentId) {
      return
    }
    previousEstablishmentIdRef.current = establishmentId
    const next = getTeamListUiState(establishmentId)
    setSearchQuery(next.searchQuery)
    setSelectedStatuses(next.selectedStatuses)
  }, [establishmentId])

  useEffect(() => {
    if (!establishmentId) {
      return
    }
    setTeamListUiState(establishmentId, { searchQuery, selectedStatuses })
  }, [establishmentId, searchQuery, selectedStatuses])

  if (!isReady || isBootstrapping) {
    return <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Chargement...</p>
  }

  if (!canViewTeam) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message="Vous n'avez pas accès à l'équipe."
        retryLabel="Retour au profil"
        onRetry={() => onNavigate?.('/general')}
      />
    )
  }

  const members = membersQuery.data ?? []
  const statusCounts = countTeamMembersByStatus(members)
  const sections = groupTeamMembersByRole(members, searchQuery, selectedStatuses)
  const hasActiveCriteria = searchQuery.trim().length > 0 || selectedStatuses.size > 0
  const isEmptyEstablishment = !membersQuery.isPending && !membersQuery.isError && members.length === 0
  const isFilteredEmpty =
    !membersQuery.isPending && !membersQuery.isError && members.length > 0 && sections.length === 0

  const resetCriteria = () => {
    setSearchQuery('')
    setSelectedStatuses(new Set())
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 px-3 pb-4 pt-3">
      {canInvite ? (
        <button
          type="button"
          className="w-full text-left active:opacity-90"
          onClick={() => onNavigate?.('/team/invite')}
        >
          <TerrainCard className="flex min-h-11 items-center gap-3 p-4">
            <span
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#EEF2FF] text-[#1B4FD8]"
              aria-hidden
            >
              <UserPlus className="h-5 w-5" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold text-[#1a1a1a]">Inviter un membre</span>
              <span className={cn('mt-0.5 block text-xs', terrain.muted)}>
                Créer un lien d&apos;invitation
              </span>
            </span>
            <ChevronRight className="h-4 w-4 shrink-0 text-[#a3a19a]" aria-hidden />
          </TerrainCard>
        </button>
      ) : null}

      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#a3a19a]" />
        <Input
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Rechercher un membre…"
          className="h-10 border-[#E8E6DF] pl-9"
          autoComplete="off"
        />
      </div>

      <TeamStatusFilters
        counts={statusCounts}
        selectedStatuses={selectedStatuses}
        onSelectTous={() => setSelectedStatuses(new Set())}
        onToggleStatus={(status) =>
          setSelectedStatuses((current) => toggleTeamMemberStatusFilter(current, status))
        }
      />

      {membersQuery.isPending ? (
        <p className={cn('px-1 py-2 text-sm', terrain.muted)}>Chargement des membres...</p>
      ) : membersQuery.isError ? (
        <TerrainErrorState
          message="La liste des membres n'a pas pu être chargée."
          retryLabel="Réessayer"
          onRetry={() => void membersQuery.refetch()}
        />
      ) : isEmptyEstablishment ? (
        <TerrainEmptyState
          title="Aucun membre"
          description="Aucun membre n'est disponible pour cet établissement."
        />
      ) : isFilteredEmpty ? (
        <div className="space-y-3">
          <TerrainEmptyState
            title="Aucun membre"
            description="Aucun membre ne correspond à vos critères."
          />
          {hasActiveCriteria ? (
            <Button
              type="button"
              variant="outline"
              className="h-10 w-full rounded-xl border-[#D7D4CB]"
              onClick={resetCriteria}
            >
              Réinitialiser
            </Button>
          ) : null}
        </div>
      ) : (
        <TeamMemberList
          sections={sections}
          activeMembershipId={activeMembership?.id ?? null}
          onSelectMember={(membershipId) => onNavigate?.(`/team/${membershipId}`)}
        />
      )}
    </div>
  )
}
