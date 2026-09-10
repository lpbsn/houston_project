import { useState } from 'react'
import { Plus } from 'lucide-react'

import {
  canCreateEstablishmentFromBootstrapHints,
  getBootstrapPermissionHints,
} from '@/features/auth/lib/bootstrap-permission-hints'
import { buildOnboardingUrlFromIds } from '@/features/auth/lib/pending-onboarding'
import type { BootstrapResponse } from '@/features/auth/types'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

import { useCreateOrganizationEstablishmentMutation } from '../hooks'

type CreateEstablishmentActionProps = {
  bootstrap: BootstrapResponse | null | undefined
  navigate: (path: string, options?: { replace?: boolean }) => void
  triggerVariant: 'sidebar' | 'organization'
}

export function CreateEstablishmentAction({
  bootstrap,
  navigate,
  triggerVariant,
}: CreateEstablishmentActionProps) {
  const canCreate = canCreateEstablishmentFromBootstrapHints(
    getBootstrapPermissionHints(bootstrap),
  )

  if (!canCreate) {
    return null
  }

  return (
    <CreateEstablishmentActionReady navigate={navigate} triggerVariant={triggerVariant} />
  )
}

function CreateEstablishmentActionReady({
  navigate,
  triggerVariant,
}: Omit<CreateEstablishmentActionProps, 'bootstrap'>) {
  const createMutation = useCreateOrganizationEstablishmentMutation()
  const [error, setError] = useState<string | null>(null)

  async function provisionUnnamed() {
    if (createMutation.isPending) {
      return
    }
    setError(null)
    try {
      const created = await createMutation.mutateAsync()
      navigate(
        buildOnboardingUrlFromIds(created.establishment_id, created.onboarding_session_id),
      )
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Création impossible.')
    }
  }

  const trigger =
    triggerVariant === 'sidebar' ? (
      <button
        type="button"
        onClick={() => {
          void provisionUnnamed()
        }}
        disabled={createMutation.isPending}
        className={cn(
          'flex min-h-10 w-full items-center gap-2 rounded-lg px-3 text-sm font-medium',
          'text-white/75 transition-colors hover:bg-white/8 hover:text-white',
          'disabled:opacity-60',
        )}
      >
        <Plus className="h-4 w-4 shrink-0" aria-hidden />
        <span className="truncate">Ajouter un établissement</span>
      </button>
    ) : (
      <Button
        type="button"
        onClick={() => {
          void provisionUnnamed()
        }}
        disabled={createMutation.isPending}
      >
        Ajouter un établissement
      </Button>
    )

  return (
    <div className={triggerVariant === 'sidebar' ? 'shrink-0 space-y-1 px-3 pt-4' : 'space-y-1'}>
      {trigger}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  )
}
