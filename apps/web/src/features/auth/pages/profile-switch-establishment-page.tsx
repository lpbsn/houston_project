import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Building2, LoaderCircle, Plus } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import {
  bootstrapQueryKey,
  createEstablishment,
  fetchBootstrap,
  switchEstablishment,
} from '@/features/auth/api'
import {
  canCreateEstablishmentFromBootstrapHints,
  getBootstrapPermissionHints,
} from '@/features/auth/lib/bootstrap-permission-hints'
import { toRoleEnum } from '@/features/auth/lib/role'
import {
  buildOnboardingUrl,
  buildOnboardingUrlFromIds,
} from '@/features/auth/lib/pending-onboarding'
import { Button } from '@/components/ui/button'
import { HoustonBadge, TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { toErrorMessage } from '@/lib/error-message'
import { purgeNonAuthQueries } from '@/lib/query-invalidation'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type ProfileSwitchEstablishmentPageProps = {
  onNavigate: (path: string, options?: { replace?: boolean }) => void
}

const ROLE_DISPLAY_LABELS = {
  owner: 'Propriétaire',
  director: 'Directeur',
  manager: 'Manager',
  staff: 'Équipe',
} as const

const DRAFT_STATUS_LABEL = 'Brouillon'

export function ProfileSwitchEstablishmentPage({
  onNavigate,
}: ProfileSwitchEstablishmentPageProps) {
  const queryClient = useQueryClient()
  const {
    activeMembership,
    bootstrap,
    isBootstrapping,
    isReady,
    memberships,
    pendingOnboardingMemberships = [],
  } = useAuth()
  const pendingMemberships = pendingOnboardingMemberships ?? []
  const permissionHints = getBootstrapPermissionHints(bootstrap)
  const canCreate = canCreateEstablishmentFromBootstrapHints(permissionHints)
  const [pendingEstablishmentId, setPendingEstablishmentId] = useState<string | null>(null)
  const [selectorError, setSelectorError] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [createName, setCreateName] = useState('')
  const [createError, setCreateError] = useState<string | null>(null)
  const isSwitchingRef = useRef(false)
  const isCreatingRef = useRef(false)
  const activeEstablishmentId = activeMembership?.establishment_id ?? null
  const isSwitching = pendingEstablishmentId !== null

  const switchMutation = useMutation({
    mutationFn: switchEstablishment,
  })

  const createMutation = useMutation({
    mutationFn: createEstablishment,
  })

  async function handleSelectEstablishment(establishmentId: string) {
    if (establishmentId === activeEstablishmentId || isSwitchingRef.current) {
      return
    }

    isSwitchingRef.current = true
    setSelectorError(null)
    setPendingEstablishmentId(establishmentId)

    try {
      await switchMutation.mutateAsync({ establishment_id: establishmentId })
      onNavigate('/app/operational-config', { replace: true })
    } catch (error) {
      setSelectorError(
        toErrorMessage(error, 'Impossible de sélectionner cet établissement.'),
      )
    } finally {
      isSwitchingRef.current = false
      setPendingEstablishmentId(null)
    }
  }

  function handleResumeOnboarding(pending: (typeof pendingOnboardingMemberships)[number]) {
    onNavigate(buildOnboardingUrl(pending), { replace: true })
  }

  async function handleCreateEstablishment() {
    if (isCreatingRef.current) {
      return
    }

    const trimmedName = createName.trim()
    if (!trimmedName) {
      setCreateError('Le nom de l’établissement est requis.')
      return
    }

    isCreatingRef.current = true
    setCreateError(null)

    try {
      const created = await createMutation.mutateAsync({ name: createName })
      const onboardingUrl = buildOnboardingUrlFromIds(
        created.establishment_id,
        created.onboarding_session_id,
      )
      purgeNonAuthQueries(queryClient)
      await queryClient.invalidateQueries({ queryKey: bootstrapQueryKey })
      await queryClient.fetchQuery({
        queryKey: bootstrapQueryKey,
        queryFn: fetchBootstrap,
      })
      onNavigate(onboardingUrl, { replace: true })
    } catch (error) {
      setCreateError(
        toErrorMessage(error, 'Impossible de créer cet établissement.'),
      )
    } finally {
      isCreatingRef.current = false
    }
  }

  if (!isReady || isBootstrapping) {
    return <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Chargement...</p>
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 px-3 pb-4 pt-3">
      {memberships.length > 0 ? (
        <section className="space-y-2">
          <TerrainSectionLabel>Actifs</TerrainSectionLabel>
          <p className={cn('px-0.5 text-sm', terrain.muted)}>
            Sélectionnez l&apos;établissement avec lequel vous souhaitez travailler.
          </p>
          <div className="space-y-2">
            {memberships.map((membership) => {
              const isActive = membership.establishment_id === activeEstablishmentId
              const isPending = pendingEstablishmentId === membership.establishment_id
              const role = toRoleEnum(membership.role)
              const roleLabel = role ? ROLE_DISPLAY_LABELS[role] : membership.role

              return (
                <button
                  key={membership.id}
                  type="button"
                  className={cn(
                    'w-full text-left active:opacity-90',
                    isActive && 'cursor-default',
                  )}
                  disabled={isActive || isSwitching || createMutation.isPending}
                  onClick={() => {
                    void handleSelectEstablishment(membership.establishment_id)
                  }}
                >
                  <TerrainCard
                    className={cn(
                      'flex min-h-11 items-center gap-3 p-4',
                      isActive && 'border-[#1D9E75]/30 bg-[#F7FCFA]',
                    )}
                  >
                    <span
                      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#EEF2FF] text-[#1B4FD8]"
                      aria-hidden
                    >
                      <Building2 className="h-5 w-5" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-[#1a1a1a]">
                        {membership.establishment_name}
                      </span>
                      <span className={cn('mt-0.5 block truncate text-xs', terrain.muted)}>
                        {membership.organization_name} · {roleLabel}
                      </span>
                    </span>
                    {isPending ? (
                      <LoaderCircle
                        className="h-4 w-4 shrink-0 animate-spin text-[#1B4FD8]"
                        aria-hidden
                      />
                    ) : isActive ? (
                      <HoustonBadge variant="green">Actif</HoustonBadge>
                    ) : null}
                  </TerrainCard>
                </button>
              )
            })}
          </div>
        </section>
      ) : null}

      {pendingMemberships.length > 0 ? (
        <section className="space-y-2">
          <TerrainSectionLabel>En configuration</TerrainSectionLabel>
          <div className="space-y-2">
            {pendingMemberships.map((pending) => (
              <TerrainCard key={pending.id} className="space-y-3 p-4">
                <div className="flex items-start gap-3">
                  <span
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#FFF4E5] text-[#B86E00]"
                    aria-hidden
                  >
                    <Building2 className="h-5 w-5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-[#1a1a1a]">
                      {pending.establishment_name}
                    </p>
                    <p className={cn('mt-0.5 text-xs', terrain.muted)}>{DRAFT_STATUS_LABEL}</p>
                  </div>
                  <HoustonBadge variant="amber">Draft</HoustonBadge>
                </div>
                {pending.can_continue_onboarding ? (
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    disabled={isSwitching || createMutation.isPending}
                    onClick={() => handleResumeOnboarding(pending)}
                  >
                    Reprendre la configuration
                  </Button>
                ) : null}
              </TerrainCard>
            ))}
          </div>
        </section>
      ) : null}

      {canCreate ? (
        <section className="space-y-2">
          {!showCreateForm ? (
            <Button
              type="button"
              variant="outline"
              className="w-full"
              disabled={isSwitching || createMutation.isPending}
              onClick={() => {
                setShowCreateForm(true)
                setCreateError(null)
              }}
            >
              <Plus className="mr-2 h-4 w-4" aria-hidden />
              Ajouter un établissement
            </Button>
          ) : (
            <TerrainCard className="space-y-3 p-4">
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-[#1a1a1a]">
                  Nom de l&apos;établissement
                </span>
                <input
                  type="text"
                  value={createName}
                  onChange={(event) => setCreateName(event.target.value)}
                  className="w-full rounded-xl border border-[#E8E6DF] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#1B4FD8]"
                  placeholder="Ex. Hôtel du Parc"
                  disabled={createMutation.isPending}
                  autoFocus
                />
              </label>
              {createError ? <p className="text-sm text-[#E24B4A]">{createError}</p> : null}
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  className="flex-1"
                  disabled={createMutation.isPending}
                  onClick={() => {
                    setShowCreateForm(false)
                    setCreateName('')
                    setCreateError(null)
                  }}
                >
                  Annuler
                </Button>
                <Button
                  type="button"
                  className="flex-1"
                  disabled={createMutation.isPending}
                  onClick={() => {
                    void handleCreateEstablishment()
                  }}
                >
                  {createMutation.isPending ? (
                    <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
                  ) : (
                    'Créer'
                  )}
                </Button>
              </div>
            </TerrainCard>
          )}
        </section>
      ) : null}

      {selectorError ? <p className="text-sm text-[#E24B4A]">{selectorError}</p> : null}
    </div>
  )
}
