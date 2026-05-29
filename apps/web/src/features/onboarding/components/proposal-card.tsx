import {
  Bot,
  CheckCircle2,
  ClipboardCheck,
  LoaderCircle,
  Route,
  ShieldAlert,
  Sparkles,
  Tags,
  XCircle,
} from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  useApplyOnboardingProposal,
  useGenerateOnboardingProposal,
  useOnboardingProposal,
  useOnboardingProposals,
  useProposalItemMutation,
  useProposalSectionDecision,
  useRejectOnboardingProposal,
} from '@/features/onboarding/hooks'
import type {
  DecisionEnum,
  OnboardingProposalResponse,
  ProposalValidationErrorItem,
  SectionEnum,
} from '@/features/onboarding/types'
import { OnboardingApiError } from '@/features/onboarding/api'
import {
  OnboardingErrorState,
  OnboardingLoadingState,
  OnboardingNotice,
  RetryButton,
  getOnboardingErrorMessage,
} from './onboarding-state'

type ProposalCardProps = {
  sessionId: string
}

type ProposalPayload = OnboardingProposalResponse['payload']
type ProposalSectionKey = Exclude<keyof ProposalPayload, 'schema_version'>

const REMOVABLE_TAXONOMY_SECTIONS = [
  'operational_modules',
  'operational_domains',
  'operational_subjects',
] as const satisfies readonly SectionEnum[]

type RemovableTaxonomySection = (typeof REMOVABLE_TAXONOMY_SECTIONS)[number]

const REVIEWABLE_PROPOSAL_STATUSES = new Set(['ready', 'partially_validated', 'validated'])

function isRemovableTaxonomySection(
  sectionKey: ProposalSectionKey,
): sectionKey is RemovableTaxonomySection {
  return REMOVABLE_TAXONOMY_SECTIONS.includes(sectionKey as RemovableTaxonomySection)
}

function canMutateProposalItems(proposal: OnboardingProposalResponse) {
  return REVIEWABLE_PROPOSAL_STATUSES.has(proposal.status)
}

const PROPOSAL_SECTIONS: {
  emptyMessage: string
  key: ProposalSectionKey
  title: string
}[] = [
  {
    key: 'operational_modules',
    title: 'Modules',
    emptyMessage: 'No module suggestions were returned.',
  },
  {
    key: 'operational_domains',
    title: 'Domains',
    emptyMessage: 'No domain suggestions were returned.',
  },
  {
    key: 'operational_subjects',
    title: 'Subjects',
    emptyMessage: 'No subject suggestions were returned.',
  },
  {
    key: 'operational_units',
    title: 'Units',
    emptyMessage: 'No unit suggestions were returned.',
  },
  {
    key: 'runtime_vocabulary',
    title: 'Vocabulary',
    emptyMessage: 'No vocabulary suggestions were returned.',
  },
  {
    key: 'runtime_tags',
    title: 'Runtime tags',
    emptyMessage: 'No runtime tag suggestions were returned.',
  },
  {
    key: 'routing_hints',
    title: 'Routing hints',
    emptyMessage: 'No routing hint suggestions were returned.',
  },
]

function sortByNewest(proposals: OnboardingProposalResponse[]) {
  return [...proposals].sort((left, right) => right.created_at.localeCompare(left.created_at))
}

function getProposalErrorItems(error: unknown) {
  return error instanceof OnboardingApiError ? error.proposalErrors : []
}

function formatDateTime(value: string | null) {
  if (!value) {
    return 'Not yet'
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function formatConfidence(value: number | null | undefined) {
  if (typeof value !== 'number') {
    return null
  }

  return `${Math.round(value * 100)}%`
}

export function ProposalCard({ sessionId }: ProposalCardProps) {
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [pendingSection, setPendingSection] = useState<string | null>(null)
  const [pendingRemoveItem, setPendingRemoveItem] = useState<string | null>(null)
  const proposalsQuery = useOnboardingProposals(sessionId)
  const proposals = useMemo(() => sortByNewest(proposalsQuery.data ?? []), [proposalsQuery.data])
  const effectiveSelectedProposalId =
    proposals.find((proposal) => proposal.id === selectedProposalId)?.id ?? proposals[0]?.id ?? null

  const selectedListProposal =
    proposals.find((proposal) => proposal.id === effectiveSelectedProposalId) ?? null
  const detailQuery = useOnboardingProposal(sessionId, effectiveSelectedProposalId, {
    enabled: Boolean(effectiveSelectedProposalId),
  })
  const selectedProposal = detailQuery.data ?? selectedListProposal
  const generateMutation = useGenerateOnboardingProposal(sessionId)
  const sectionDecisionMutation = useProposalSectionDecision(sessionId, selectedProposal?.id ?? '')
  const rejectMutation = useRejectOnboardingProposal(sessionId, selectedProposal?.id ?? '')
  const applyMutation = useApplyOnboardingProposal(sessionId, selectedProposal?.id ?? '')
  const itemMutation = useProposalItemMutation(sessionId, selectedProposal?.id ?? '')
  const activeMutationError =
    generateMutation.error ??
    sectionDecisionMutation.error ??
    rejectMutation.error ??
    applyMutation.error ??
    itemMutation.error
  const activeProposalErrors = getProposalErrorItems(activeMutationError)
  const isCommandPending =
    generateMutation.isPending ||
    sectionDecisionMutation.isPending ||
    rejectMutation.isPending ||
    applyMutation.isPending ||
    itemMutation.isPending
  const canRemoveItems = selectedProposal ? canMutateProposalItems(selectedProposal) : false

  async function handleGenerateProposal() {
    setSuccessMessage(null)

    try {
      const response = await generateMutation.mutateAsync(undefined)
      setSelectedProposalId(response.proposal.id)
      setSuccessMessage('AI proposal generated. Review each section before applying it.')
    } catch {
      setSuccessMessage(null)
    }
  }

  async function handleSectionDecision(section: string, decision: DecisionEnum) {
    if (!selectedProposal) {
      return
    }

    setSuccessMessage(null)
    setPendingSection(`${section}:${decision}`)

    try {
      await sectionDecisionMutation.mutateAsync({ section, decision })
      setSuccessMessage(`Section ${decision}.`)
    } catch {
      setSuccessMessage(null)
    } finally {
      setPendingSection(null)
    }
  }

  async function handleRejectProposal() {
    if (!selectedProposal) {
      return
    }

    setSuccessMessage(null)

    try {
      await rejectMutation.mutateAsync()
      setSuccessMessage('Proposal rejected.')
    } catch {
      setSuccessMessage(null)
    }
  }

  async function handleApplyProposal() {
    if (!selectedProposal) {
      return
    }

    setSuccessMessage(null)

    try {
      await applyMutation.mutateAsync()
      setSuccessMessage('Proposal applied. Runtime configuration was refreshed from the backend.')
    } catch {
      setSuccessMessage(null)
    }
  }

  async function handleRemoveItem(section: RemovableTaxonomySection, key: string) {
    if (!selectedProposal) {
      return
    }

    setSuccessMessage(null)
    setPendingRemoveItem(`${section}:${key}`)

    try {
      await itemMutation.mutateAsync({
        action: 'remove',
        section,
        key,
      })
      setSuccessMessage('Item retiré de la proposition.')
    } catch {
      setSuccessMessage(null)
    } finally {
      setPendingRemoveItem(null)
    }
  }

  if (proposalsQuery.isPending) {
    return <OnboardingLoadingState label="Loading onboarding proposals..." />
  }

  if (proposalsQuery.error) {
    return (
      <div className="space-y-3">
        <OnboardingErrorState
          error={proposalsQuery.error}
          fallback="Onboarding proposals could not be loaded."
        />
        <RetryButton
          onClick={() => {
            void proposalsQuery.refetch()
          }}
        />
      </div>
    )
  }

  return (
    <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
      <CardHeader className="gap-3">
        <div className="flex flex-wrap gap-2">
          <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
            Proposals
          </Badge>
          <Badge variant="outline" className="border-[#ebe2d5] bg-[#fbf7f0]">
            AI suggests, backend applies
          </Badge>
        </div>

        <div className="space-y-2">
          <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
            Proposal review
          </CardTitle>
          <CardDescription className="text-sm leading-6">
            Generate and review onboarding suggestions. Applying a proposal updates runtime setup
            through the backend and does not activate the establishment.
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <Button
          type="button"
          className="h-11 w-full rounded-[1rem]"
          disabled={generateMutation.isPending}
          onClick={handleGenerateProposal}
        >
          {generateMutation.isPending ? (
            <>
              <LoaderCircle className="size-4 animate-spin" />
              Generating proposal...
            </>
          ) : (
            <>
              <Sparkles className="size-4" />
              Generate AI proposal
            </>
          )}
        </Button>

        {proposals.length === 0 ? (
          <OnboardingNotice
            tone="muted"
            title="No proposal yet."
            message="Generate an AI proposal after the activity description is available. The backend will create a proposal only; it will not apply runtime configuration automatically."
          />
        ) : null}

        {proposals.length > 0 ? (
          <ProposalPicker
            proposals={proposals}
            selectedProposalId={effectiveSelectedProposalId}
            onSelect={(proposalId) => {
              setSelectedProposalId(proposalId)
              setSuccessMessage(null)
            }}
          />
        ) : null}

        {detailQuery.isFetching && selectedListProposal ? (
          <div className="flex items-center gap-2 rounded-[1rem] border border-[#ebe2d5] bg-[#fbf7f0] px-4 py-3 text-sm text-muted-foreground">
            <LoaderCircle className="size-4 animate-spin text-[color:var(--primary)]" />
            Refreshing selected proposal...
          </div>
        ) : null}

        {detailQuery.error ? (
          <OnboardingErrorState
            error={detailQuery.error}
            fallback="Selected proposal could not be loaded."
          />
        ) : null}

        {selectedProposal ? (
          <>
            <ProposalSummary proposal={selectedProposal} />
            <ValidationErrorList errors={selectedProposal.validation_errors} />
            {PROPOSAL_SECTIONS.map((section) => {
              const removableSection = isRemovableTaxonomySection(section.key)
                ? section.key
                : null

              return (
                <ProposalSuggestionSection
                  canRemoveItems={canRemoveItems && removableSection !== null}
                  decisionState={selectedProposal.section_validation[section.key]}
                  disabled={isCommandPending}
                  emptyMessage={section.emptyMessage}
                  errors={selectedProposal.validation_errors.filter(
                    (error) => error.section === section.key,
                  )}
                  items={selectedProposal.payload[section.key]}
                  key={section.key}
                  pendingRemoveItem={pendingRemoveItem}
                  pendingSection={pendingSection}
                  sectionKey={section.key}
                  title={section.title}
                  onDecision={handleSectionDecision}
                  onRemoveItem={
                    removableSection
                      ? (key) => {
                          void handleRemoveItem(removableSection, key)
                        }
                      : undefined
                  }
                />
              )
            })}

            <ProposalCommands
              applyError={applyMutation.error}
              applyPending={applyMutation.isPending}
              disabled={!selectedProposal || isCommandPending}
              rejectError={rejectMutation.error}
              rejectPending={rejectMutation.isPending}
              onApply={handleApplyProposal}
              onReject={handleRejectProposal}
            />
          </>
        ) : null}

        {activeMutationError ? (
          <ProposalMutationError error={activeMutationError} proposalErrors={activeProposalErrors} />
        ) : null}

        {successMessage ? (
          <div className="flex items-center gap-2 rounded-[1rem] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            <CheckCircle2 className="size-4" />
            {successMessage}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

function ProposalPicker({
  onSelect,
  proposals,
  selectedProposalId,
}: {
  onSelect: (proposalId: string) => void
  proposals: OnboardingProposalResponse[]
  selectedProposalId: string | null
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {proposals.map((proposal) => (
        <button
          key={proposal.id}
          type="button"
          className={`rounded-[1rem] border px-4 py-3 text-left transition-colors ${
            selectedProposalId === proposal.id
              ? 'border-[color:var(--primary)] bg-[color:var(--primary)]/8'
              : 'border-[#ebe2d5] bg-white hover:bg-[#fffaf2]'
          }`}
          onClick={() => {
            onSelect(proposal.id)
          }}
        >
          <div className="mb-2 flex flex-wrap gap-2">
            <Badge variant="outline" className="border-[#ebe2d5] bg-white">
              {proposal.source}
            </Badge>
            <Badge variant="outline" className="border-[#ebe2d5] bg-[#fbf7f0]">
              {proposal.status}
            </Badge>
          </div>
          <div className="truncate text-sm font-semibold">Proposal {proposal.id}</div>
          <div className="mt-1 text-xs text-muted-foreground">
            Created {formatDateTime(proposal.created_at)}
          </div>
        </button>
      ))}
    </div>
  )
}

function ProposalSummary({ proposal }: { proposal: OnboardingProposalResponse }) {
  return (
    <section className="rounded-[1.25rem] border border-[#ebe2d5] bg-[#fbf7f0] px-4 py-4">
      <div className="mb-3 flex flex-wrap gap-2">
        <Badge className="bg-[color:var(--primary)] text-primary-foreground">
          {proposal.status}
        </Badge>
        <Badge variant="outline" className="border-[#ebe2d5] bg-white">
          {proposal.source}
        </Badge>
        <Badge variant="outline" className="border-[#ebe2d5] bg-white">
          schema {proposal.payload.schema_version}
        </Badge>
      </div>

      <div className="grid gap-2 text-sm sm:grid-cols-2">
        <SummaryRow label="Created" value={formatDateTime(proposal.created_at)} />
        <SummaryRow label="Updated" value={formatDateTime(proposal.updated_at)} />
        <SummaryRow label="Validated" value={formatDateTime(proposal.validated_at)} />
        <SummaryRow label="Applied" value={formatDateTime(proposal.applied_at)} />
      </div>
    </section>
  )
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1rem] border border-[#ebe2d5] bg-white px-3 py-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm font-semibold">{value}</div>
    </div>
  )
}

function ProposalSuggestionSection({
  canRemoveItems,
  decisionState,
  disabled,
  emptyMessage,
  errors,
  items,
  onDecision,
  onRemoveItem,
  pendingRemoveItem,
  pendingSection,
  sectionKey,
  title,
}: {
  canRemoveItems: boolean
  decisionState: string | undefined
  disabled: boolean
  emptyMessage: string
  errors: ProposalValidationErrorItem[]
  items: ProposalPayload[ProposalSectionKey]
  onDecision: (section: string, decision: DecisionEnum) => void
  onRemoveItem?: (key: string) => void
  pendingRemoveItem: string | null
  pendingSection: string | null
  sectionKey: ProposalSectionKey
  title: string
}) {
  return (
    <section className="rounded-[1.25rem] border border-[#ece5da] bg-white px-4 py-4 shadow-[0_14px_34px_-32px_rgba(46,72,173,0.22)]">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-[color:var(--primary)]/10 p-2 text-[color:var(--primary)]">
              <SectionIcon sectionKey={sectionKey} />
            </span>
            <div>
              <div className="text-sm font-semibold">{title}</div>
              <div className="text-xs text-muted-foreground">
                {items.length} suggested · {decisionState ?? 'no decision'}
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 sm:flex">
          <Button
            type="button"
            variant="outline"
            className="h-10 rounded-[1rem] border-emerald-200 bg-emerald-50 text-emerald-700"
            disabled={disabled}
            onClick={() => {
              onDecision(sectionKey, 'accepted')
            }}
          >
            {pendingSection === `${sectionKey}:accepted` ? (
              <LoaderCircle className="size-4 animate-spin" />
            ) : (
              <CheckCircle2 className="size-4" />
            )}
            Accept
          </Button>
          <Button
            type="button"
            variant="outline"
            className="h-10 rounded-[1rem] border-[#ebe2d5] bg-[#fbf7f0]"
            disabled={disabled}
            onClick={() => {
              onDecision(sectionKey, 'skipped')
            }}
          >
            {pendingSection === `${sectionKey}:skipped` ? (
              <LoaderCircle className="size-4 animate-spin" />
            ) : (
              <XCircle className="size-4" />
            )}
            Skip
          </Button>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="rounded-[1rem] border border-dashed border-[#ddd3c5] bg-[#fffaf2] px-4 py-3 text-sm text-muted-foreground">
          {emptyMessage}
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item, index) => {
            const itemKey = getSuggestionKey(item, index)
            const removePending = pendingRemoveItem === `${sectionKey}:${itemKey}`

            return (
              <ProposalSuggestionItem
                item={item}
                key={itemKey}
                removePending={removePending}
                removable={canRemoveItems && onRemoveItem !== undefined && 'key' in item}
                sectionKey={sectionKey}
                onRemove={
                  onRemoveItem && 'key' in item && typeof item.key === 'string'
                    ? () => {
                        onRemoveItem(item.key)
                      }
                    : undefined
                }
              />
            )
          })}
        </div>
      )}

      {errors.length > 0 ? <ValidationErrorList errors={errors} title="Section errors" /> : null}
    </section>
  )
}

function SectionIcon({ sectionKey }: { sectionKey: ProposalSectionKey }) {
  if (sectionKey === 'operational_subjects') {
    return <ClipboardCheck className="size-4" />
  }

  if (sectionKey === 'runtime_tags') {
    return <Tags className="size-4" />
  }

  if (sectionKey === 'routing_hints') {
    return <Route className="size-4" />
  }

  if (sectionKey === 'runtime_vocabulary') {
    return <ClipboardCheck className="size-4" />
  }

  return <Bot className="size-4" />
}

function ProposalSuggestionItem({
  item,
  onRemove,
  removePending,
  removable,
  sectionKey,
}: {
  item: ProposalPayload[ProposalSectionKey][number]
  onRemove?: () => void
  removePending?: boolean
  removable?: boolean
  sectionKey: ProposalSectionKey
}) {
  const removeAction =
    removable && onRemove ? (
      <Button
        type="button"
        variant="outline"
        className="h-9 shrink-0 rounded-[0.85rem] border-[#f4d5d5] bg-white px-3 text-[#9d3b33] hover:bg-[#fff3f2]"
        disabled={removePending}
        onClick={onRemove}
      >
        {removePending ? <LoaderCircle className="size-4 animate-spin" /> : null}
        Retirer
      </Button>
    ) : undefined

  if (sectionKey === 'routing_hints') {
    const routingHint = item as ProposalPayload['routing_hints'][number]

    return (
      <SuggestionShell
        action={removeAction}
        badges={[
          ...(routingHint.suggested_domain_keys ?? []),
          routingHint.suggested_unit_key ?? null,
        ]}
        confidence={formatConfidence(routingHint.confidence_score)}
        reason={routingHint.reason}
        subtitle="Routing pattern"
        title={routingHint.pattern}
      />
    )
  }

  if (sectionKey === 'runtime_vocabulary') {
    const vocabulary = item as ProposalPayload['runtime_vocabulary'][number]

    return (
      <SuggestionShell
        action={removeAction}
        badges={[vocabulary.mapped_domain_key ?? null, vocabulary.mapped_unit_key ?? null]}
        reason={vocabulary.reason}
        subtitle={vocabulary.meaning}
        title={vocabulary.term}
      />
    )
  }

  if (sectionKey === 'runtime_tags') {
    const runtimeTag = item as ProposalPayload['runtime_tags'][number]

    return (
      <SuggestionShell
        action={removeAction}
        badges={runtimeTag.related_domain_keys ?? []}
        reason={runtimeTag.reason}
        subtitle={runtimeTag.key}
        title={runtimeTag.label}
      />
    )
  }

  if (sectionKey === 'operational_subjects') {
    const subject = item as ProposalPayload['operational_subjects'][number]

    return (
      <SuggestionShell
        action={removeAction}
        badges={[subject.domain_key, subject.module_key ?? null]}
        confidence={formatConfidence(subject.confidence_score)}
        reason={subject.reason}
        subtitle={subject.key}
        title={subject.label}
      />
    )
  }

  if (sectionKey === 'operational_domains') {
    const domain = item as ProposalPayload['operational_domains'][number]

    return (
      <SuggestionShell
        action={removeAction}
        badges={[domain.module_key]}
        confidence={formatConfidence(domain.confidence_score)}
        reason={domain.reason}
        subtitle={domain.key}
        title={domain.label}
      />
    )
  }

  const keyedItem = item as ProposalPayload['operational_modules'][number] &
    ProposalPayload['operational_units'][number]

  return (
    <SuggestionShell
      action={removeAction}
      badges={'related_modules' in keyedItem ? (keyedItem.related_modules ?? []) : []}
      confidence={formatConfidence(keyedItem.confidence_score)}
      reason={keyedItem.reason}
      subtitle={keyedItem.key}
      title={keyedItem.label}
    />
  )
}

function SuggestionShell({
  action,
  badges,
  confidence,
  reason,
  subtitle,
  title,
}: {
  action?: ReactNode
  badges: (string | null | undefined)[]
  confidence?: string | null
  reason?: string
  subtitle: string
  title: string
}) {
  const visibleBadges = badges.filter((badge): badge is string => Boolean(badge))

  return (
    <div className="rounded-[1rem] border border-[#ebe2d5] bg-[#fffdf9] px-3 py-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="text-sm font-semibold">{title}</div>
          <div className="text-xs text-muted-foreground">{subtitle}</div>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
          {confidence ? (
            <Badge variant="outline" className="w-fit border-[#ebe2d5] bg-white">
              {confidence}
            </Badge>
          ) : null}
          {action}
        </div>
      </div>

      {reason ? <p className="mt-2 text-sm leading-6 text-muted-foreground">{reason}</p> : null}

      {visibleBadges.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {visibleBadges.map((badge) => (
            <Badge key={badge} variant="outline" className="border-[#ebe2d5] bg-[#fbf7f0]">
              {badge}
            </Badge>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function getSuggestionKey(item: ProposalPayload[ProposalSectionKey][number], index: number) {
  if ('key' in item && typeof item.key === 'string') {
    return item.key
  }

  if ('term' in item && typeof item.term === 'string') {
    return item.term
  }

  if ('pattern' in item && typeof item.pattern === 'string') {
    return item.pattern
  }

  return `${index}`
}

function ValidationErrorList({
  errors,
  title = 'Validation errors',
}: {
  errors: ProposalValidationErrorItem[]
  title?: string
}) {
  if (errors.length === 0) {
    return null
  }

  return (
    <div className="space-y-2 rounded-[1rem] border border-[#f4d5d5] bg-[#fff8f6] px-4 py-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-[#87352f]">
        <ShieldAlert className="size-4" />
        {title}
      </div>
      {errors.map((error, index) => (
        <div
          key={`${error.code}-${error.section ?? 'section'}-${error.key ?? index}`}
          className="flex flex-col gap-2 rounded-[0.9rem] border border-[#f4d5d5] bg-white px-3 py-3 text-sm sm:flex-row sm:items-start sm:justify-between"
        >
          <div className="text-[#87352f]">{error.code}</div>
          <div className="flex flex-wrap gap-2">
            {error.section ? <Badge variant="outline">{error.section}</Badge> : null}
            {error.field ? <Badge variant="outline">{error.field}</Badge> : null}
            {error.key ? <Badge variant="outline">{error.key}</Badge> : null}
          </div>
        </div>
      ))}
    </div>
  )
}

function ProposalMutationError({
  error,
  proposalErrors,
}: {
  error: unknown
  proposalErrors: ProposalValidationErrorItem[]
}) {
  return (
    <div className="space-y-3 rounded-[1rem] border border-[#f4d5d5] bg-[#fff3f2] px-4 py-3 text-sm text-[#9d3b33]">
      <div>{getOnboardingErrorMessage(error, 'Proposal command could not be completed.')}</div>
      {proposalErrors.length > 0 ? <ValidationErrorList errors={proposalErrors} /> : null}
    </div>
  )
}

function ProposalCommands({
  applyError,
  applyPending,
  disabled,
  onApply,
  onReject,
  rejectError,
  rejectPending,
}: {
  applyError: unknown
  applyPending: boolean
  disabled: boolean
  onApply: () => void
  onReject: () => void
  rejectError: unknown
  rejectPending: boolean
}) {
  return (
    <section className="space-y-3 rounded-[1.25rem] border border-[#ebe2d5] bg-[#fbf7f0] px-4 py-4">
      <div className="space-y-2">
        <div className="text-sm font-semibold">Apply proposal</div>
        <p className="text-sm leading-6 text-muted-foreground">
          Apply is an explicit backend command. It writes accepted proposal data into runtime
          configuration and does not activate the establishment.
        </p>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        <Button
          type="button"
          variant="outline"
          className="h-11 w-full rounded-[1rem] border-[#f4d5d5] bg-white text-[#9d3b33]"
          disabled={disabled || rejectPending}
          onClick={onReject}
        >
          {rejectPending ? (
            <>
              <LoaderCircle className="size-4 animate-spin" />
              Rejecting...
            </>
          ) : (
            <>
              <XCircle className="size-4" />
              Reject proposal
            </>
          )}
        </Button>
        <Button
          type="button"
          className="h-11 w-full rounded-[1rem]"
          disabled={disabled || applyPending}
          onClick={onApply}
        >
          {applyPending ? (
            <>
              <LoaderCircle className="size-4 animate-spin" />
              Applying...
            </>
          ) : (
            <>
              <ClipboardCheck className="size-4" />
              Apply proposal
            </>
          )}
        </Button>
      </div>

      {rejectError ? (
        <div className="text-sm text-[#9d3b33]">
          {getOnboardingErrorMessage(rejectError, 'Proposal could not be rejected.')}
        </div>
      ) : null}
      {applyError ? (
        <div className="text-sm text-[#9d3b33]">
          {getOnboardingErrorMessage(applyError, 'Proposal could not be applied.')}
        </div>
      ) : null}
    </section>
  )
}
