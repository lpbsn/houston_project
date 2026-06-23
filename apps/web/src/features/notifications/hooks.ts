import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  notificationsQueryKeys,
  type NotificationListStatus,
} from './api'

export function useNotificationsInfiniteQuery(
  establishmentId: string | null,
  status: NotificationListStatus = 'inbox',
) {
  return useInfiniteQuery({
    queryKey: establishmentId
      ? notificationsQueryKeys.list(establishmentId, status)
      : ['notifications', 'list', 'none'],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchNotifications(establishmentId, {
        cursor: pageParam,
        status,
      })
    },
    getNextPageParam: (lastPage) => {
      if (!lastPage.has_more || !lastPage.next_cursor) {
        return undefined
      }
      return lastPage.next_cursor
    },
    enabled: Boolean(establishmentId),
  })
}

export function useMarkNotificationReadMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (notificationId: string) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return markNotificationRead(establishmentId, notificationId)
    },
    onSuccess: () => {
      if (!establishmentId) {
        return
      }
      void queryClient.invalidateQueries({
        queryKey: notificationsQueryKeys.lists(establishmentId),
      })
    },
  })
}

export function useMarkAllNotificationsReadMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return markAllNotificationsRead(establishmentId)
    },
    onSuccess: () => {
      if (!establishmentId) {
        return
      }
      void queryClient.invalidateQueries({
        queryKey: notificationsQueryKeys.lists(establishmentId),
      })
    },
  })
}
