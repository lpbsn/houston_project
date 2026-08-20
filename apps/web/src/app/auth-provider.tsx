import {
  createContext,
  type PropsWithChildren,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { clearApiClientAuth, configureApiClientAuth } from '@/api/client'

import {
  AuthApiError,
  bootstrapQueryKey,
  clearAuthState,
  fetchBootstrap,
  login,
  logout,
  refreshAccessToken,
  restoreSession,
} from '@/features/auth/api'
import { getAccessToken, useAccessToken } from '@/features/auth/session'
import type { BootstrapResponse, LoginRequest } from '@/features/auth/types'
import type { PendingOnboardingMembership } from '@/features/auth/lib/pending-onboarding'
import {
  applyPendingNativePushTap,
  setNativePushActiveEstablishmentGetter,
  setNativePushActiveUserIdGetter,
  syncNativePushTokenIfGranted,
} from '@/lib/native-push-session'
import { setNativeDeepLinkSessionGetters } from '@/lib/native-deep-link-session'

type AuthContextValue = {
  activeMembership: BootstrapResponse['active_membership']
  bootstrap: BootstrapResponse | null
  hasAccessToken: boolean
  hasOperationalAccess: boolean
  isAuthenticated: boolean
  isBootstrapping: boolean
  isLoggingIn: boolean
  isLoggingOut: boolean
  isReady: boolean
  login: (input: LoginRequest) => Promise<void>
  loginError: AuthApiError | Error | null
  logout: () => Promise<void>
  memberships: BootstrapResponse['memberships']
  pendingOnboardingMemberships: PendingOnboardingMembership[]
  user: BootstrapResponse['user'] | null
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: PropsWithChildren) {
  const accessToken = useAccessToken()
  const [isSessionResolved, setIsSessionResolved] = useState(false)

  useEffect(() => {
    configureApiClientAuth({
      getAccessToken,
      refreshAccessToken,
      clearAuth: clearAuthState,
    })

    return () => {
      clearApiClientAuth()
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    async function resolveSession() {
      try {
        await restoreSession()
      } finally {
        if (!cancelled) {
          setIsSessionResolved(true)
        }
      }
    }

    void resolveSession()

    return () => {
      cancelled = true
    }
  }, [])

  const bootstrapQuery = useQuery({
    queryKey: bootstrapQueryKey,
    queryFn: fetchBootstrap,
    enabled: isSessionResolved && Boolean(accessToken),
    retry: false,
    staleTime: 5 * 60_000,
  })

  useEffect(() => {
    if (!bootstrapQuery.isError) {
      return
    }

    const error = bootstrapQuery.error
    if (error instanceof AuthApiError && error.status === 401) {
      clearAuthState()
    }
  }, [bootstrapQuery.isError, bootstrapQuery.error])

  const loginMutation = useMutation({
    mutationFn: async (input: LoginRequest) => {
      await login(input)
    },
    onSuccess: () => {
      setIsSessionResolved(true)
    },
  })

  const logoutMutation = useMutation({
    mutationFn: logout,
  })

  const isBootstrapping = Boolean(accessToken) && bootstrapQuery.isPending
  const isReady = isSessionResolved && !isBootstrapping
  const bootstrap = bootstrapQuery.data ?? null
  const isAuthenticated = Boolean(accessToken) && Boolean(bootstrap)

  useEffect(() => {
    setNativePushActiveEstablishmentGetter(
      () => bootstrap?.active_membership?.establishment_id ?? null,
    )
    setNativePushActiveUserIdGetter(() => bootstrap?.user?.id ?? null)
    setNativeDeepLinkSessionGetters({
      isReady: () => isReady,
      isAuthenticated: () => isAuthenticated,
    })
  }, [bootstrap?.active_membership?.establishment_id, bootstrap?.user?.id, isAuthenticated, isReady])

  useEffect(() => {
    if (!isAuthenticated || !isReady) {
      return
    }
    void syncNativePushTokenIfGranted()
  }, [isAuthenticated, isReady, bootstrap?.user?.id])

  useEffect(() => {
    if (!isAuthenticated || !isReady) {
      return
    }
    void applyPendingNativePushTap()
  }, [isAuthenticated, isReady, bootstrap?.active_membership?.establishment_id])

  const value = useMemo<AuthContextValue>(
    () => ({
      activeMembership: bootstrap?.active_membership ?? null,
      bootstrap,
      hasAccessToken: Boolean(accessToken),
      hasOperationalAccess: Boolean(bootstrap?.active_membership),
      isAuthenticated,
      isBootstrapping,
      isLoggingIn: loginMutation.isPending,
      isLoggingOut: logoutMutation.isPending,
      isReady,
      login: async (input: LoginRequest) => {
        await loginMutation.mutateAsync(input)
      },
      loginError:
        loginMutation.error instanceof Error ? (loginMutation.error as AuthApiError | Error) : null,
      logout: async () => {
        try {
          await logoutMutation.mutateAsync()
        } finally {
          clearAuthState()
          setIsSessionResolved(true)
        }
      },
      memberships: bootstrap?.memberships ?? [],
      pendingOnboardingMemberships: bootstrap?.pending_onboarding_memberships ?? [],
      user: bootstrap?.user ?? null,
    }),
    [
      accessToken,
      bootstrap,
      isAuthenticated,
      isBootstrapping,
      isReady,
      logoutMutation,
      loginMutation,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider.')
  }

  return context
}
