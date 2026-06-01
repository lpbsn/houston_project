import { ChevronDown, Layers3 } from 'lucide-react'
import { Accordion } from 'radix-ui'
import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import {
  buildProposalModuleTree,
  countModuleSubjects,
  type ProposalDomainTreeNode,
  type ProposalModuleTreeNode,
} from '@/features/onboarding/lib/build-proposal-module-tree'
import type {
  DecisionEnum,
  OnboardingProposalResponse,
  ProposalValidationErrorItem,
  SectionEnum,
} from '@/features/onboarding/types'
import {
  formatProposalConfidence,
  getProposalSuggestionKey,
  ProposalSuggestionItem,
} from './proposal-suggestion-item'
import {
  ProposalSectionDecisionControls,
  TAXONOMY_SECTION_DECISIONS,
} from './proposal-section-decision-controls'

type ProposalPayload = OnboardingProposalResponse['payload']

type ProposalTaxonomyReviewProps = {
  canRemoveItems: boolean
  disabled: boolean
  onDecision: (section: SectionEnum, decision: DecisionEnum) => void
  onRemoveItem: (section: 'operational_modules' | 'operational_domains' | 'operational_subjects', key: string) => void
  payload: ProposalPayload
  pendingRemoveItem: string | null
  pendingSection: string | null
  sectionValidation: OnboardingProposalResponse['section_validation']
  validationErrors: ProposalValidationErrorItem[]
}

export function ProposalTaxonomyReview({
  canRemoveItems,
  disabled,
  onDecision,
  onRemoveItem,
  payload,
  pendingRemoveItem,
  pendingSection,
  sectionValidation,
  validationErrors,
}: ProposalTaxonomyReviewProps) {
  const moduleTree = useMemo(() => buildProposalModuleTree(payload), [payload])
  const [expandedModuleKey, setExpandedModuleKey] = useState<string | undefined>(
    () => moduleTree[0]?.module.key,
  )

  const taxonomyErrors = validationErrors.filter((error) =>
    TAXONOMY_SECTION_DECISIONS.some(({ section }) => error.section === section),
  )

  return (
    <section className="rounded-[1.25rem] border border-[#ece5da] bg-white px-4 py-4 shadow-[0_14px_34px_-32px_rgba(46,72,173,0.22)]">
      <div className="mb-4 space-y-2">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-[color:var(--primary)]/10 p-2 text-[color:var(--primary)]">
            <Layers3 className="size-4" />
          </span>
          <div>
            <div className="text-sm font-semibold">Operational structure</div>
            <div className="text-xs text-muted-foreground">
              {moduleTree.length} module{moduleTree.length === 1 ? '' : 's'} · review module →
              domain → subject before confirming each section below
            </div>
          </div>
        </div>
        <p className="text-sm leading-6 text-muted-foreground">
          Expand one module at a time to review its domains and subjects together. Accept or skip
          each taxonomy section when the full structure looks right.
        </p>
      </div>

      {moduleTree.length === 0 ? (
        <div className="mb-4 rounded-[1rem] border border-dashed border-[#ddd3c5] bg-[#fffaf2] px-4 py-3 text-sm text-muted-foreground">
          No module suggestions were returned.
        </div>
      ) : (
        <Accordion.Root
          className="mb-4 space-y-2"
          collapsible
          type="single"
          value={expandedModuleKey}
          onValueChange={setExpandedModuleKey}
        >
          {moduleTree.map((moduleNode) => (
            <ProposalModuleAccordionItem
              canRemoveItems={canRemoveItems}
              key={moduleNode.module.key}
              moduleNode={moduleNode}
              pendingRemoveItem={pendingRemoveItem}
              validationErrors={validationErrors}
              onRemoveItem={onRemoveItem}
            />
          ))}
        </Accordion.Root>
      )}

      <div className="space-y-2">
        <div className="text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
          Section decisions
        </div>
        <div className="grid gap-2 lg:grid-cols-3">
          {TAXONOMY_SECTION_DECISIONS.map(({ section, title }) => (
            <ProposalSectionDecisionControls
              decisionState={sectionValidation[section]}
              disabled={disabled}
              key={section}
              pendingSection={pendingSection}
              section={section}
              title={title}
              onDecision={onDecision}
            />
          ))}
        </div>
      </div>

      {taxonomyErrors.length > 0 ? (
        <div className="mt-4 space-y-2 rounded-[1rem] border border-[#f4d5d5] bg-[#fff8f6] px-4 py-3">
          <div className="text-sm font-semibold text-[#87352f]">Taxonomy validation errors</div>
          {taxonomyErrors.map((error, index) => (
            <div
              key={`${error.code}-${error.section ?? 'section'}-${error.key ?? index}`}
              className="rounded-[0.9rem] border border-[#f4d5d5] bg-white px-3 py-2 text-sm text-[#87352f]"
            >
              {error.code}
              {error.key ? ` · ${error.key}` : null}
            </div>
          ))}
        </div>
      ) : null}
    </section>
  )
}

function ProposalModuleAccordionItem({
  canRemoveItems,
  moduleNode,
  onRemoveItem,
  pendingRemoveItem,
  validationErrors,
}: {
  canRemoveItems: boolean
  moduleNode: ProposalModuleTreeNode
  onRemoveItem: ProposalTaxonomyReviewProps['onRemoveItem']
  pendingRemoveItem: string | null
  validationErrors: ProposalValidationErrorItem[]
}) {
  const subjectCount = countModuleSubjects(moduleNode)
  const moduleErrors = validationErrors.filter(
    (error) => error.section === 'operational_modules' && error.key === moduleNode.module.key,
  )

  return (
    <Accordion.Item
      className="overflow-hidden rounded-[1rem] border border-[#ebe2d5] bg-[#fffdf9]"
      value={moduleNode.module.key}
    >
      <Accordion.Header>
        <Accordion.Trigger className="group flex w-full items-start justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-[#fffaf2]">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold">{moduleNode.module.label}</span>
              {moduleNode.isUnassigned ? (
                <Badge variant="outline" className="border-[#f4d5d5] bg-[#fff3f2] text-[#9d3b33]">
                  Unassigned
                </Badge>
              ) : null}
              {formatProposalConfidence(moduleNode.module.confidence_score) ? (
                <Badge variant="outline" className="border-[#ebe2d5] bg-white">
                  {formatProposalConfidence(moduleNode.module.confidence_score)}
                </Badge>
              ) : null}
            </div>
            <div className="text-xs text-muted-foreground">{moduleNode.module.key}</div>
            <div className="text-xs text-muted-foreground">
              {moduleNode.domains.length} domain{moduleNode.domains.length === 1 ? '' : 's'} ·{' '}
              {subjectCount} subject{subjectCount === 1 ? '' : 's'}
            </div>
          </div>
          <ChevronDown className="mt-0.5 size-4 shrink-0 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
        </Accordion.Trigger>
      </Accordion.Header>

      <Accordion.Content className="border-t border-[#ebe2d5] px-4 py-4 data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down">
        {!moduleNode.isUnassigned ? (
          <div className="mb-4">
            <ProposalSuggestionItem
              displayMode="nested-module"
              item={moduleNode.module}
              removable={canRemoveItems}
              removePending={
                pendingRemoveItem === `operational_modules:${moduleNode.module.key}`
              }
              sectionKey="operational_modules"
              onRemove={
                canRemoveItems
                  ? () => {
                      onRemoveItem('operational_modules', moduleNode.module.key)
                    }
                  : undefined
              }
            />
          </div>
        ) : moduleNode.module.reason ? (
          <p className="mb-4 text-sm leading-6 text-muted-foreground">{moduleNode.module.reason}</p>
        ) : null}

        {moduleNode.domains.length === 0 ? (
          <div className="rounded-[1rem] border border-dashed border-[#ddd3c5] bg-[#fffaf2] px-4 py-3 text-sm text-muted-foreground">
            No domains were suggested for this module.
          </div>
        ) : (
          <div className="space-y-4 border-l-2 border-[#ebe2d5] pl-4">
            {moduleNode.domains.map((domainNode) => (
              <ProposalDomainBlock
                canRemoveItems={canRemoveItems}
                domainNode={domainNode}
                key={domainNode.domain.key}
                pendingRemoveItem={pendingRemoveItem}
                validationErrors={validationErrors}
                onRemoveItem={onRemoveItem}
              />
            ))}
          </div>
        )}

        {moduleErrors.length > 0 ? (
          <div className="mt-4 space-y-2">
            {moduleErrors.map((error, index) => (
              <div
                key={`${error.code}-${index}`}
                className="rounded-[0.9rem] border border-[#f4d5d5] bg-[#fff8f6] px-3 py-2 text-sm text-[#87352f]"
              >
                {error.code}
              </div>
            ))}
          </div>
        ) : null}
      </Accordion.Content>
    </Accordion.Item>
  )
}

function ProposalDomainBlock({
  canRemoveItems,
  domainNode,
  onRemoveItem,
  pendingRemoveItem,
  validationErrors,
}: {
  canRemoveItems: boolean
  domainNode: ProposalDomainTreeNode
  onRemoveItem: ProposalTaxonomyReviewProps['onRemoveItem']
  pendingRemoveItem: string | null
  validationErrors: ProposalValidationErrorItem[]
}) {
  const domainErrors = validationErrors.filter(
    (error) =>
      error.section === 'operational_domains' && error.key === domainNode.domain.key,
  )

  return (
    <div className="space-y-3">
      <ProposalSuggestionItem
        displayMode="nested-domain"
        item={domainNode.domain}
        removable={canRemoveItems}
        removePending={pendingRemoveItem === `operational_domains:${domainNode.domain.key}`}
        sectionKey="operational_domains"
        onRemove={
          canRemoveItems
            ? () => {
                onRemoveItem('operational_domains', domainNode.domain.key)
              }
            : undefined
        }
      />

      {domainNode.subjects.length === 0 ? (
        <div className="rounded-[1rem] border border-dashed border-[#ddd3c5] bg-[#fffaf2] px-3 py-2 text-xs text-muted-foreground">
          No subjects were suggested for this domain.
        </div>
      ) : (
        <div className="space-y-2 border-l-2 border-[#f0e8dc] pl-3">
          {domainNode.subjects.map((subject, index) => {
            const subjectKey = getProposalSuggestionKey(subject, index)

            return (
              <ProposalSuggestionItem
                displayMode="nested-subject"
                item={subject}
                key={subjectKey}
                removable={canRemoveItems}
                removePending={
                  pendingRemoveItem === `operational_subjects:${subjectKey}`
                }
                sectionKey="operational_subjects"
                onRemove={
                  canRemoveItems
                    ? () => {
                        onRemoveItem('operational_subjects', subject.key)
                      }
                    : undefined
                }
              />
            )
          })}
        </div>
      )}

      {domainErrors.length > 0 ? (
        <div className="space-y-2">
          {domainErrors.map((error, index) => (
            <div
              key={`${error.code}-${index}`}
              className="rounded-[0.9rem] border border-[#f4d5d5] bg-[#fff8f6] px-3 py-2 text-xs text-[#87352f]"
            >
              {error.code}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}
