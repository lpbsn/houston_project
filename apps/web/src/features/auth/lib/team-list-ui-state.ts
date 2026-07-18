import type { AppRoute } from '@/app/app-routes'
import type { TeamMembershipStatus } from '@/features/auth/lib/team-members'

export type TeamListUiState = {
  searchQuery: string
  selectedStatuses: ReadonlySet<TeamMembershipStatus>
}

const EMPTY_STATE: TeamListUiState = {
  searchQuery: '',
  selectedStatuses: new Set(),
}

let storedEstablishmentId: string | null = null
let storedState: TeamListUiState = {
  searchQuery: '',
  selectedStatuses: new Set(),
}

function cloneState(state: TeamListUiState): TeamListUiState {
  return {
    searchQuery: state.searchQuery,
    selectedStatuses: new Set(state.selectedStatuses),
  }
}

export function shouldPreserveTeamListUiState(route: AppRoute): boolean {
  if (route.kind === 'team-member-detail') {
    return true
  }
  return route.kind === 'static' && route.path === '/team'
}

export function getTeamListUiState(establishmentId: string | null): TeamListUiState {
  if (!establishmentId || establishmentId !== storedEstablishmentId) {
    return cloneState(EMPTY_STATE)
  }
  return cloneState(storedState)
}

export function setTeamListUiState(establishmentId: string, state: TeamListUiState): void {
  storedEstablishmentId = establishmentId
  storedState = cloneState(state)
}

export function resetTeamListUiState(): void {
  storedEstablishmentId = null
  storedState = cloneState(EMPTY_STATE)
}
