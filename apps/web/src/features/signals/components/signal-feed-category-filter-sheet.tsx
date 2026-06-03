import { useQuery } from '@tanstack/react-query'
import { LoaderCircle } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'

import { Input } from '@/components/ui/input'
import { TerrainErrorState } from '@/components/ui/terrain'
import {
  buildOperationalScopeTree,
  filterTreeBySearch,
} from '@/features/auth/lib/membership-scope'
import { getOperationalTaxonomy, operationalTaxonomyQueryKey } from '@/features/auth/api'

import {
  collectCategoryKeysFromTree,
  mergeCategorySelections,
  type CategoryKeySelection,
} from '../lib/signal-feed-category-selection'
import type { SignalFeedFilters } from '../lib/signal-feed-filters'
import { SignalFeedBottomSheet } from './signal-feed-bottom-sheet'
import { SignalFeedCategoryFilterTree } from './signal-feed-category-filter-tree'
import { SignalFeedFilterPanelFooter } from './signal-feed-filter-panel-footer'

type SignalFeedCategoryFilterSheetProps = {
  establishmentId: string
  appliedFilters: SignalFeedFilters
  onClose: () => void
  onApply: (filters: SignalFeedFilters) => void
}

export function SignalFeedCategoryFilterSheet({
  establishmentId,
  appliedFilters,
  onClose,
  onApply,
}: SignalFeedCategoryFilterSheetProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [draftSelection, setDraftSelection] = useState<CategoryKeySelection>(() => ({
    moduleKeys: [...appliedFilters.moduleKeys],
    domainKeys: [...appliedFilters.domainKeys],
    subjectKeys: [...appliedFilters.subjectKeys],
  }))

  const taxonomyQuery = useQuery({
    queryKey: operationalTaxonomyQueryKey(establishmentId),
    queryFn: () => getOperationalTaxonomy(establishmentId),
    enabled: Boolean(establishmentId),
  })

  const tree = useMemo(
    () => (taxonomyQuery.data ? buildOperationalScopeTree(taxonomyQuery.data) : null),
    [taxonomyQuery.data],
  )

  const filteredTree = useMemo(
    () => (tree ? filterTreeBySearch(tree, searchQuery) : null),
    [tree, searchQuery],
  )

  function handleSelectAll() {
    if (!filteredTree) {
      return
    }
    setDraftSelection((current) => mergeCategorySelections(current, collectCategoryKeysFromTree(filteredTree)))
  }

  function handleClearAll() {
    setDraftSelection({
      moduleKeys: [],
      domainKeys: [],
      subjectKeys: [],
    })
  }

  function handleApply() {
    onApply({
      ...appliedFilters,
      moduleKeys: draftSelection.moduleKeys,
      domainKeys: draftSelection.domainKeys,
      subjectKeys: draftSelection.subjectKeys,
    })
    onClose()
  }

  let body: ReactNode
  if (taxonomyQuery.isLoading) {
    body = (
      <div className="flex items-center justify-center py-12 text-[#7D7B75]">
        <LoaderCircle className="h-6 w-6 animate-spin" />
      </div>
    )
  } else if (taxonomyQuery.isError) {
    body = (
      <TerrainErrorState
        message="Impossible de charger les catégories."
        onRetry={() => void taxonomyQuery.refetch()}
      />
    )
  } else if (filteredTree) {
    body = (
      <div className="space-y-3">
        <p className="text-xs leading-relaxed text-[#6b5f52]">
          Sélectionner un <strong>module</strong> filtre les signaux de ce module. Sélectionner un{' '}
          <strong>domaine</strong> filtre les signaux de ce domaine. Sélectionner un{' '}
          <strong>sujet</strong> filtre ce sujet précis. Les catégories cochées se combinent entre
          elles (au moins une doit correspondre).
        </p>
        <Input
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Rechercher un module, domaine ou sujet…"
          className="h-9 border-[#E8E6DF] bg-white text-sm"
        />
        {filteredTree.displayModules.length === 0 ? (
          <p className="py-4 text-center text-sm text-[#7D7B75]">Aucune catégorie trouvée.</p>
        ) : (
          <SignalFeedCategoryFilterTree
            disabled={false}
            selection={draftSelection}
            tree={filteredTree}
            onChange={setDraftSelection}
          />
        )}
      </div>
    )
  } else {
    body = null
  }

  const panelDisabled = taxonomyQuery.isLoading || taxonomyQuery.isError

  return (
    <SignalFeedBottomSheet
      title="Catégorie"
      open
      onClose={onClose}
      footer={
        <SignalFeedFilterPanelFooter
          applyDisabled={panelDisabled}
          selectAllDisabled={panelDisabled || !filteredTree?.displayModules.length}
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
