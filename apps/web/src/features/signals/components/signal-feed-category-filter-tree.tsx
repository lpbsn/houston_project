import { ChevronDown } from 'lucide-react'
import { Accordion } from 'radix-ui'
import { useMemo, useState } from 'react'

import type { OperationalScopeTree } from '@/features/auth/lib/membership-scope'

import {
  getDomainSelectionState,
  getModuleSelectionState,
  getSubjectSelectionState,
  toggleDomainKey,
  toggleModuleKey,
  toggleSubjectKey,
  type CategoryKeySelection,
} from '../lib/signal-feed-category-selection'
import { SignalFeedCategoryCheckbox } from './signal-feed-category-checkbox'

type SignalFeedCategoryFilterTreeProps = {
  disabled?: boolean
  onChange: (selection: CategoryKeySelection) => void
  selection: CategoryKeySelection
  tree: OperationalScopeTree
}

export function SignalFeedCategoryFilterTree({
  disabled = false,
  onChange,
  selection,
  tree,
}: SignalFeedCategoryFilterTreeProps) {
  const [expandedModuleId, setExpandedModuleId] = useState<string | undefined>(
    tree.displayModules[0]?.id,
  )

  const effectiveExpandedModuleId = useMemo(() => {
    if (
      expandedModuleId &&
      tree.displayModules.some((module) => module.id === expandedModuleId)
    ) {
      return expandedModuleId
    }
    return tree.displayModules[0]?.id
  }, [expandedModuleId, tree.displayModules])

  if (tree.displayModules.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-[#7D7B75]">
        Aucune catégorie disponible.
      </p>
    )
  }

  return (
    <Accordion.Root
      className="space-y-2"
      collapsible
      type="single"
      value={effectiveExpandedModuleId}
      onValueChange={setExpandedModuleId}
    >
      {tree.displayModules.map((moduleNode) => (
        <Accordion.Item
          key={moduleNode.id}
          className="overflow-hidden rounded-lg border border-[#E8E6DF] bg-[#F5F4F0]"
          value={moduleNode.id}
        >
          <Accordion.Header className="flex items-center gap-1 px-2 py-2">
            <SignalFeedCategoryCheckbox
              disabled={disabled}
              label={moduleNode.label}
              levelLabel="Module"
              onToggle={() => {
                const checked = getModuleSelectionState(moduleNode, selection) === 'checked'
                onChange(toggleModuleKey(selection, moduleNode.key, !checked))
              }}
              selectionState={getModuleSelectionState(moduleNode, selection)}
            />
            <Accordion.Trigger className="group flex shrink-0 items-center justify-center rounded-md p-1 hover:bg-white/80">
              <ChevronDown className="size-4 text-[#7D7B75] transition-transform group-data-[state=open]:rotate-180" />
              <span className="sr-only">Afficher les domaines</span>
            </Accordion.Trigger>
          </Accordion.Header>

          <Accordion.Content className="border-t border-[#E8E6DF] bg-white px-2 py-2">
            <div className="space-y-2">
              {moduleNode.domains.map((domainNode) => (
                <div
                  key={domainNode.id}
                  className="rounded-lg border border-[#E8E6DF] bg-[#F5F4F0]/50 px-2 py-2"
                >
                  <SignalFeedCategoryCheckbox
                    disabled={disabled}
                    label={domainNode.label}
                    levelLabel="Domaine"
                    onToggle={() => {
                      const checked =
                        getDomainSelectionState(domainNode, selection) === 'checked'
                      onChange(toggleDomainKey(selection, domainNode.key, !checked))
                    }}
                    selectionState={getDomainSelectionState(domainNode, selection)}
                  />

                  {domainNode.subjects.length > 0 ? (
                    <div className="mt-2 space-y-2 border-l-2 border-[#E8E6DF] pl-3">
                      {domainNode.subjects.map((subjectNode) => (
                        <SignalFeedCategoryCheckbox
                          key={subjectNode.id}
                          compact
                          disabled={disabled}
                          label={subjectNode.label}
                          levelLabel="Sujet"
                          onToggle={() => {
                            const checked =
                              getSubjectSelectionState(subjectNode.key, selection) ===
                              'checked'
                            onChange(toggleSubjectKey(selection, subjectNode.key, !checked))
                          }}
                          selectionState={getSubjectSelectionState(subjectNode.key, selection)}
                        />
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </Accordion.Content>
        </Accordion.Item>
      ))}
    </Accordion.Root>
  )
}
