import { useInfiniteQuery } from '@tanstack/react-query'

import {
  listPlatformEstablishments,
  listPlatformMemberships,
  listPlatformOnboardings,
  listPlatformOrganizations,
  listPlatformUsers,
  platformQueryKeys,
  type PlatformMembershipFilters,
} from './api'

function nextCursorParam<T extends { next_cursor: string | null }>(lastPage: T) {
  return lastPage.next_cursor || undefined
}

export function usePlatformOnboardingsQuery(q: string) {
  return useInfiniteQuery({
    queryKey: platformQueryKeys.onboardings(q),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => listPlatformOnboardings(q, pageParam),
    getNextPageParam: nextCursorParam,
  })
}

export function usePlatformOrganizationsQuery(q: string) {
  return useInfiniteQuery({
    queryKey: platformQueryKeys.organizations(q),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => listPlatformOrganizations(q, pageParam),
    getNextPageParam: nextCursorParam,
  })
}

export function usePlatformEstablishmentsQuery(q: string, organizationId = '') {
  return useInfiniteQuery({
    queryKey: platformQueryKeys.establishments(q, organizationId),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      listPlatformEstablishments(q, {
        cursor: pageParam,
        organization_id: organizationId || undefined,
      }),
    getNextPageParam: nextCursorParam,
  })
}

export function usePlatformUsersQuery(q: string) {
  return useInfiniteQuery({
    queryKey: platformQueryKeys.users(q),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => listPlatformUsers(q, pageParam),
    getNextPageParam: nextCursorParam,
  })
}

export function usePlatformMembershipsQuery(filters: PlatformMembershipFilters, enabled = true) {
  return useInfiniteQuery({
    queryKey: platformQueryKeys.memberships(filters),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => listPlatformMemberships(filters, pageParam),
    getNextPageParam: nextCursorParam,
    enabled,
  })
}
