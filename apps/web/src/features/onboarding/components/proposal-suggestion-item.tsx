import { LoaderCircle } from 'lucide-react'
import { type ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { OnboardingProposalResponse } from '@/features/onboarding/types'

type ProposalPayload = OnboardingProposalResponse['payload']
type ProposalSectionKey = Exclude<keyof ProposalPayload, 'schema_version'>

export function formatProposalConfidence(value: number | null | undefined) {
  if (typeof value !== 'number') {
    return null
  }

  return `${Math.round(value * 100)}%`
}

export function getProposalSuggestionKey(
  item: ProposalPayload[ProposalSectionKey][number],
  index: number,
) {
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

type ProposalSuggestionItemProps = {
  displayMode?: 'default' | 'nested-domain' | 'nested-subject' | 'nested-module'
  item: ProposalPayload[ProposalSectionKey][number]
  onRemove?: () => void
  removePending?: boolean
  removable?: boolean
  sectionKey: ProposalSectionKey
}

export function ProposalSuggestionItem({
  displayMode = 'default',
  item,
  onRemove,
  removePending,
  removable,
  sectionKey,
}: ProposalSuggestionItemProps) {
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
        confidence={formatProposalConfidence(routingHint.confidence_score)}
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
        badges={
          displayMode === 'nested-subject'
            ? []
            : [subject.domain_key, subject.module_key ?? null]
        }
        confidence={formatProposalConfidence(subject.confidence_score)}
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
        badges={displayMode === 'nested-domain' ? [] : [domain.module_key]}
        confidence={formatProposalConfidence(domain.confidence_score)}
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
      badges={
        displayMode === 'nested-module'
          ? []
          : 'related_modules' in keyedItem
            ? (keyedItem.related_modules ?? [])
            : []
      }
      confidence={formatProposalConfidence(keyedItem.confidence_score)}
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
