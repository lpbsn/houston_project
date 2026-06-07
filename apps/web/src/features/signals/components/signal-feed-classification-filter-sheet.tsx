import { useQuery } from '@tanstack/react-query'
import { LoaderCircle } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'

import { Input } from '@/components/ui/input'
import { TerrainErrorState } from '@/components/ui/terrain'
import { buildBusinessUnitScopeTree } from '@/features/auth/lib/business-unit-scope'
import { businessUnitTreeQueryKey, getBusinessUnitTree } from '@/features/auth/api'

import {
  collectClassificationKeysFromTree,
  filterBusinessUnitsBySearch,
  mergeClassificationSelections,
  type ClassificationKeySelection,
} from '../lib/signal-feed-classification-selection'
import type { SignalFeedFilters } from '../lib/signal-feed-filters'
import { SignalFeedBottomSheet } from './signal-feed-bottom-sheet'
import { SignalFeedClassificationFilterTree } from './signal-feed-classification-filter-tree'
import { SignalFeedFilterPanelFooter } from './signal-feed-filter-panel-footer'

type SignalFeedClassificationFilterSheetProps = {
  establishmentId: string
  appliedFilters: SignalFeedFilters
  onClose: () => void
  onApply: (filters: SignalFeedFilters) => void
}

export function SignalFeedClassificationFilterSheet({
  establishmentId,
  appliedFilters,
  onClose,
  onApply,
}: SignalFeedClassificationFilterSheetProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [draftSelection, setDraftSelection] = useState<ClassificationKeySelection>(() => ({
    businessUnitKeys: [...appliedFilters.businessUnitKeys],
    activitySubjectIds: [...appliedFilters.activitySubjectIds],
  }))

  const treeQuery = useQuery({
    queryKey: businessUnitTreeQueryKey(establishmentId),
    queryFn: () => getBusinessUnitTree(establishmentId),
    enabled: Boolean(establishmentId),
  })

  const businessUnits = useMemo(() => {
    if (!treeQuery.data) {
      return []
    }
    return buildBusinessUnitScopeTree(treeQuery.data).businessUnits
  }, [treeQuery.data])

  const filteredBusinessUnits = useMemo(
    () => filterBusinessUnitsBySearch(businessUnits, searchQuery),
    [businessUnits, searchQuery],
  )

  function handleSelectAll() {
    if (filteredBusinessUnits.length === 0) {
      return
    }
    setDraftSelection((current) =>
      mergeClassificationSelections(
        current,
        collectClassificationKeysFromTree(filteredBusinessUnits),
      ),
    )
  }

  function handleClearAll() {
    setDraftSelection({
      businessUnitKeys: [],
      activitySubjectIds: [],
    })
  }

  function handleApply() {
    onApply({
      ...appliedFilters,
      businessUnitKeys: draftSelection.businessUnitKeys,
      activitySubjectIds: draftSelection.activitySubjectIds,
    })
    onClose()
  }

  let body: ReactNode
  if (treeQuery.isLoading) {
    body = (
      <div className="flex items-center justify-center py-12 text-[#7D7B75]">
        <LoaderCircle className="h-6 w-6 animate-spin" />
      </div>
    )
  } else if (treeQuery.isError) {
    body = (
      <TerrainErrorState
        message="Impossible de charger les pôles et sujets."
        onRetry={() => void treeQuery.refetch()}
      />
    )
  } else {
    body = (
      <div className="space-y-3">
        <p className="text-xs leading-relaxed text-[#6b5f52]">
          Sélectionner un <strong>pôle</strong> filtre les signaux liés à ce pôle (impact ou
          responsabilité). Sélectionner un <strong>sujet</strong> filtre ce sujet précis. Pôle et
          sujet se combinent lorsqu&apos;ils sont tous deux sélectionnés.
        </p>
        <Input
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Rechercher un pôle ou un sujet…"
          className="h-9 border-[#E8E6DF] bg-white text-sm"
        />
        {filteredBusinessUnits.length === 0 ? (
          <p className="py-4 text-center text-sm text-[#7D7B75]">Aucun pôle ou sujet trouvé.</p>
        ) : (
          <SignalFeedClassificationFilterTree
            businessUnits={filteredBusinessUnits}
            disabled={false}
            selection={draftSelection}
            onChange={setDraftSelection}
          />
        )}
      </div>
    )
  }

  const panelDisabled = treeQuery.isLoading || treeQuery.isError

  return (
    <SignalFeedBottomSheet
      title="Pôle / Sujet"
      open
      onClose={onClose}
      footer={
        <SignalFeedFilterPanelFooter
          applyDisabled={panelDisabled}
          selectAllDisabled={panelDisabled || filteredBusinessUnits.length === 0}
          onSelectAll={handleSelectAll}
          onClearAll={handleClearAll}
          onCancel={onClose}
          onApply={handleApply}
        />
      }
    >
      {body}
    </SignalFeedBottomSheet>
  )
}
