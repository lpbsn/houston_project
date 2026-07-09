import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useUpdateNotificationPreferencesMutation } from '@/features/notifications/hooks'

import { getLocalPushSubscription } from './lib/local-subscription'
import { registerWebPushSubscription, rollbackWebPushRegistration } from './lib/subscription'
import {
  getBrowserPushSupportEnvironment,
  getPushToggleMessage,
  resolvePushToggleState,
} from './lib/support'

export const pushQueryKeys = {
  localSubscription: ['push', 'local-subscription'] as const,
}

export function useWebPushToggle(
  establishmentId: string | null,
  preferences:
    | {
        notifications_enabled: boolean
        push_enabled: boolean
      }
    | undefined,
  options: { isPreferencesLoading?: boolean } = {},
) {
  const queryClient = useQueryClient()
  const env = getBrowserPushSupportEnvironment()
  const updatePreferencesMutation = useUpdateNotificationPreferencesMutation(establishmentId)

  const localSubscriptionQuery = useQuery({
    queryKey: pushQueryKeys.localSubscription,
    queryFn: getLocalPushSubscription,
    enabled:
      env.hasServiceWorker &&
      env.hasPushManager &&
      env.permission !== 'denied' &&
      !(env.isIosDevice && !env.isStandalonePwa),
    staleTime: 30_000,
  })

  const state = resolvePushToggleState({
    env,
    pushEnabled: preferences?.push_enabled ?? false,
    hasLocalSubscription: localSubscriptionQuery.data != null,
  })

  const enablePushMutation = useMutation({
    mutationFn: async () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }

      const registration = await registerWebPushSubscription()
      try {
        return await updatePreferencesMutation.mutateAsync({ push_enabled: true })
      } catch (error) {
        await rollbackWebPushRegistration(registration)
        throw error
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: pushQueryKeys.localSubscription })
    },
  })

  const isPending =
    options.isPreferencesLoading ||
    localSubscriptionQuery.isLoading ||
    updatePreferencesMutation.isPending ||
    enablePushMutation.isPending

  const disabled =
    isPending ||
    preferences?.notifications_enabled === false ||
    state === 'unsupported' ||
    state === 'ios_not_installed' ||
    state === 'permission_denied'

  const handleToggle = (checked: boolean) => {
    if (checked) {
      updatePreferencesMutation.reset()
      enablePushMutation.mutate()
      return
    }

    enablePushMutation.reset()
    updatePreferencesMutation.mutate({ push_enabled: false })
  }

  return {
    state,
    message: getPushToggleMessage(state),
    notificationsBlockedMessage:
      preferences?.notifications_enabled === false
        ? "Activez d'abord les notifications."
        : null,
    checked: state === 'enabled',
    disabled,
    isPending,
    isError: updatePreferencesMutation.isError || enablePushMutation.isError,
    errorMessage:
      enablePushMutation.error instanceof Error
        ? enablePushMutation.error.message
        : updatePreferencesMutation.isError
          ? 'La mise à jour des notifications push a échoué.'
          : null,
    onToggle: handleToggle,
  }
}
