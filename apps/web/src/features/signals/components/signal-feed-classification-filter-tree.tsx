import { ChevronDown } from 'lucide-react'
import { Accordion } from 'radix-ui'
import { useMemo, useState } from 'react'

import type { BusinessUnitNode } from '@/features/auth/lib/business-unit-scope'

import {
  getActivitySubjectSelectionState,
  getBusinessUnitSelectionState,
  toggleActivitySubjectId,
  toggleBusinessUnitKey,
  type ClassificationKeySelection,
} from '../lib/signal-feed-classification-selection'
import { SignalFeedCategoryCheckbox } from './signal-feed-category-checkbox'

type SignalFeedClassificationFilterTreeProps = {
  businessUnits: BusinessUnitNode[]
  disabled?: boolean
  onChange: (selection: ClassificationKeySelection) => void
  selection: ClassificationKeySelection
}

export function SignalFeedClassificationFilterTree({
  businessUnits,
  disabled = false,
  onChange,
  selection,
}: SignalFeedClassificationFilterTreeProps) {
  const [expandedBusinessUnitId, setExpandedBusinessUnitId] = useState<string | undefined>(
    businessUnits[0]?.id,
  )

  const effectiveExpandedBusinessUnitId = useMemo(() => {
    if (
      expandedBusinessUnitId &&
      businessUnits.some((businessUnit) => businessUnit.id === expandedBusinessUnitId)
    ) {
      return expandedBusinessUnitId
    }
    return businessUnits[0]?.id
  }, [businessUnits, expandedBusinessUnitId])

  if (businessUnits.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-[#7D7B75]">
        Aucun pôle disponible.
      </p>
    )
  }

  return (
    <Accordion.Root
      className="space-y-2"
      collapsible
      type="single"
      value={effectiveExpandedBusinessUnitId}
      onValueChange={setExpandedBusinessUnitId}
    >
      {businessUnits.map((businessUnit) => (
        <Accordion.Item
          key={businessUnit.id}
          className="overflow-hidden rounded-lg border border-[#E8E6DF] bg-[#F5F4F0]"
          value={businessUnit.id}
        >
          <Accordion.Header className="flex items-center gap-1 px-2 py-2">
            <SignalFeedCategoryCheckbox
              disabled={disabled}
              label={businessUnit.label}
              levelLabel="Pôle"
              onToggle={() => {
                const checked =
                  getBusinessUnitSelectionState(businessUnit, selection) === 'checked'
                onChange(toggleBusinessUnitKey(selection, businessUnit.key, !checked))
              }}
              selectionState={getBusinessUnitSelectionState(businessUnit, selection)}
            />
            <Accordion.Trigger className="group flex shrink-0 items-center justify-center rounded-md p-1 hover:bg-white/80">
              <ChevronDown className="size-4 text-[#7D7B75] transition-transform group-data-[state=open]:rotate-180" />
              <span className="sr-only">Afficher les sujets</span>
            </Accordion.Trigger>
          </Accordion.Header>

          <Accordion.Content className="border-t border-[#E8E6DF] bg-white px-2 py-2">
            {businessUnit.activity_subjects.length > 0 ? (
              <div className="space-y-2 border-l-2 border-[#E8E6DF] pl-3">
                {businessUnit.activity_subjects.map((subject) => (
                  <SignalFeedCategoryCheckbox
                    key={subject.id}
                    compact
                    disabled={disabled}
                    label={subject.label}
                    levelLabel="Sujet"
                    onToggle={() => {
                      const checked =
                        getActivitySubjectSelectionState(subject.id, selection) === 'checked'
                      onChange(toggleActivitySubjectId(selection, subject.id, !checked))
                    }}
                    selectionState={getActivitySubjectSelectionState(subject.id, selection)}
                  />
                ))}
              </div>
            ) : (
              <p className="py-2 text-sm text-[#7D7B75]">Aucun sujet pour ce pôle.</p>
            )}
          </Accordion.Content>
        </Accordion.Item>
      ))}
    </Accordion.Root>
  )
}
