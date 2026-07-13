import { useCallback } from 'react'
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  fetchNotificationPreferences,
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  notificationsQueryKeys,
  updateNotificationPreferences,
  type NotificationListFilter,
} from './api'
import { resolveNotificationPath } from './lib/notification-navigation'
import type { NotificationItem, NotificationPreferencesUpdate } from './types'

export function useNotificationsInfiniteQuery(
  establishmentId: string | null,
  filter: NotificationListFilter = 'all',
) {
  return useInfiniteQuery({
    queryKey: establishmentId
      ? notificationsQueryKeys.list(establishmentId, filter)
      : ['notifications', 'list', 'none'],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchNotifications(establishmentId, {
        cursor: pageParam,
        filter,
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

type UseNotificationSelectionOptions = {
  onNavigate: (pathname: string) => void
  onClosePanel?: () => void
}

export function useNotificationSelection(
  establishmentId: string | null,
  { onNavigate, onClosePanel }: UseNotificationSelectionOptions,
) {
  const markReadMutation = useMarkNotificationReadMutation(establishmentId)

  const handleSelectNotification = useCallback(
    (notification: NotificationItem) => {
      const path = resolveNotificationPath(notification)

      if (path) {
        onClosePanel?.()
        onNavigate(path)
        if (notification.status === 'unread') {
          void markReadMutation.mutate(notification.id)
        }
        return
      }

      if (notification.status === 'unread') {
        void markReadMutation.mutate(notification.id)
      }
    },
    [markReadMutation, onClosePanel, onNavigate],
  )

  return { handleSelectNotification }
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

export function useNotificationPreferencesQuery(establishmentId: string | null) {
  return useQuery({
    queryKey: establishmentId
      ? notificationsQueryKeys.preferences(establishmentId)
      : ['notifications', 'preferences', 'none'],
    queryFn: () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchNotificationPreferences(establishmentId)
    },
    enabled: Boolean(establishmentId),
  })
}

export function useUpdateNotificationPreferencesMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (input: NotificationPreferencesUpdate) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return updateNotificationPreferences(establishmentId, input)
    },
    onSuccess: () => {
      if (!establishmentId) {
        return
      }
      void queryClient.invalidateQueries({
        queryKey: notificationsQueryKeys.preferences(establishmentId),
      })
    },
  })
}
