import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { platformQueryKeys, startPlatformOnboarding } from '@/features/platform/api'
import {
  PlatformCollectionState,
  PlatformLoadMore,
  PlatformRowAction,
  PlatformTable,
  PlatformTableCell,
  PlatformTableRow,
  PlatformTableSkeleton,
} from '@/features/platform/components/platform-collection-table'
import { PlatformDialog } from '@/features/platform/components/platform-dialog'
import { PlatformLink } from '@/features/platform/components/platform-link'
import { PlatformListToolbar } from '@/features/platform/components/platform-list-toolbar'
import {
  PlatformFunctionalStatusBadge,
  PlatformPageHeader,
} from '@/features/platform/components/platform-status-badge'
import { usePlatformOnboardingsQuery } from '@/features/platform/hooks'
import { getCompleteErrorMessage } from '@/features/onboarding/lib/onboarding-draft-errors'
import { usePlatformListSearch, withSearchQuery } from '@/features/platform/lib/platform-search'

const COLUMNS = ['Organisation', 'Établissement', 'État fonctionnel', 'Action']

export function PlatformOnboardingsPage() {
  const { q, replaceParams } = usePlatformListSearch('/platform/onboardings')
  const listQuery = usePlatformOnboardingsQuery(q)
  const items = listQuery.data?.pages.flatMap((page) => page.results) ?? []
  const [createOpen, setCreateOpen] = useState(false)
  const createTriggerRef = useRef<HTMLButtonElement>(null)
  const wasCreateOpen = useRef(false)

  useEffect(() => {
    if (wasCreateOpen.current && !createOpen) {
      createTriggerRef.current?.focus()
    }
    wasCreateOpen.current = createOpen
  }, [createOpen])

  return (
    <div>
      <PlatformPageHeader
        title="Onboardings"
        description="Démarrer, reprendre et finaliser les configurations d’établissement."
        action={
          <Button
            ref={createTriggerRef}
            type="button"
            className="h-10"
            onClick={() => setCreateOpen(true)}
          >
            Nouvel onboarding
          </Button>
        }
      />
      <NewOnboardingDialog open={createOpen} onClose={() => setCreateOpen(false)} />
      <PlatformListToolbar
        q={q}
        onQueryChange={(value) => replaceParams({ q: value })}
        placeholder="Organisation ou établissement"
      />
      <PlatformCollectionState
        isPending={listQuery.isPending}
        isError={listQuery.isError}
        isEmpty={items.length === 0}
        hasQuery={Boolean(q)}
        emptyLabel="Aucun onboarding pour le moment."
        noResultsLabel="Aucun résultat pour cette recherche."
        errorLabel="Impossible de charger les onboardings."
        onRetry={() => void listQuery.refetch()}
        skeleton={<PlatformTableSkeleton columns={COLUMNS} />}
      >
        <PlatformTable columns={COLUMNS}>
          {items.map((item) => {
            const href = withSearchQuery(`/platform/onboardings/${item.id}`, q)
            return (
              <PlatformTableRow key={item.id}>
                <PlatformTableCell>
                  <PlatformLink href={href} className="font-medium hover:underline">
                    {item.organization_name}
                  </PlatformLink>
                </PlatformTableCell>
                <PlatformTableCell>{item.establishment_name ?? '—'}</PlatformTableCell>
                <PlatformTableCell>
                  <PlatformFunctionalStatusBadge status={item.functional_status} />
                </PlatformTableCell>
                <PlatformTableCell>
                  <PlatformRowAction href={href} label="Ouvrir l’onboarding" />
                </PlatformTableCell>
              </PlatformTableRow>
            )
          })}
        </PlatformTable>
        <PlatformLoadMore
          hasNextPage={Boolean(listQuery.hasNextPage)}
          isFetchingNextPage={listQuery.isFetchingNextPage}
          onLoadMore={() => void listQuery.fetchNextPage()}
        />
      </PlatformCollectionState>
    </div>
  )
}

function NewOnboardingDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()
  const { navigate } = usePlatformListSearch('/platform/onboardings')
  const [organizationName, setOrganizationName] = useState('')
  const [establishmentName, setEstablishmentName] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const startMutation = useMutation({
    mutationFn: startPlatformOnboarding,
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: platformQueryKeys.all })
      onClose()
      navigate(`/platform/onboardings/${created.id}`)
    },
    onError: (error) => {
      setFormError(getCompleteErrorMessage(error, 'Impossible de démarrer l’onboarding.'))
    },
  })

  useEffect(() => {
    if (open) {
      setOrganizationName('')
      setEstablishmentName('')
      setFormError(null)
    }
  }, [open])

  return (
    <PlatformDialog
      open={open}
      title="Nouvel onboarding"
      closeDisabled={startMutation.isPending}
      onClose={() => {
        if (!startMutation.isPending) {
          onClose()
        }
      }}
    >
      <form
        className="grid gap-3"
        onSubmit={(event) => {
          event.preventDefault()
          setFormError(null)
          startMutation.mutate({
            organization_name: organizationName.trim(),
            establishment_name: establishmentName.trim() || null,
          })
        }}
      >
        <Input
          required
          autoFocus
          value={organizationName}
          onChange={(event) => setOrganizationName(event.target.value)}
          placeholder="Nom de l’organisation"
          disabled={startMutation.isPending}
        />
        <Input
          value={establishmentName}
          onChange={(event) => setEstablishmentName(event.target.value)}
          placeholder="Nom de l’établissement (optionnel)"
          disabled={startMutation.isPending}
        />
        {formError ? (
          <p className="text-sm text-[var(--platform-status-problem-fg)]">{formError}</p>
        ) : null}
        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            className="h-10"
            disabled={startMutation.isPending}
            onClick={onClose}
          >
            Annuler
          </Button>
          <Button
            type="submit"
            className="h-10"
            disabled={startMutation.isPending || !organizationName.trim()}
          >
            {startMutation.isPending ? 'Démarrage…' : 'Démarrer'}
          </Button>
        </div>
      </form>
    </PlatformDialog>
  )
}
