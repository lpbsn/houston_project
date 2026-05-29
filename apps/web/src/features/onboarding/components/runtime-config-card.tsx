import { BookOpenText, Boxes, ClipboardList, Layers3, Route, Tags } from 'lucide-react'
import type { ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { RuntimeConfigResponse } from '@/features/onboarding/types'
import {
  OnboardingErrorState,
  OnboardingLoadingState,
  OnboardingNotice,
  RetryButton,
} from './onboarding-state'

type RuntimeConfigCardProps = {
  error: unknown
  isLoading: boolean
  onRetry: () => void
  runtimeConfig: RuntimeConfigResponse | null
}

type KeyedRuntimeItem = RuntimeConfigResponse['active_modules'][number]
type RuntimeVocabularyItem = RuntimeConfigResponse['optional_vocabulary'][number]
type RuntimeTagItem = RuntimeConfigResponse['optional_runtime_tags'][number]
type RoutingHintItem = RuntimeConfigResponse['optional_routing_hints'][number]

export function RuntimeConfigCard({
  error,
  isLoading,
  onRetry,
  runtimeConfig,
}: RuntimeConfigCardProps) {
  if (isLoading) {
    return <OnboardingLoadingState label="Loading runtime configuration..." />
  }

  if (error) {
    return (
      <div className="space-y-3">
        <OnboardingErrorState
          error={error}
          fallback="Runtime configuration could not be loaded."
        />
        <RetryButton onClick={onRetry} />
      </div>
    )
  }

  if (!runtimeConfig) {
    return (
      <OnboardingNotice
        tone="muted"
        title="Runtime configuration is not available yet."
        message="Start or load an onboarding session before reviewing runtime setup."
      />
    )
  }

  return (
    <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
      <CardHeader className="gap-3">
        <div className="flex flex-wrap gap-2">
          <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
            Runtime config
          </Badge>
          <Badge variant="outline" className="border-[#ebe2d5] bg-[#fbf7f0]">
            Read-only
          </Badge>
        </div>

        <div className="space-y-2">
          <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
            Runtime setup
          </CardTitle>
          <CardDescription className="text-sm leading-6">
            This screen displays the backend runtime configuration currently exposed for the
            onboarding session.
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <ReadOnlyDescription description={runtimeConfig.activity_description?.description ?? null} />

        <RuntimeSection
          icon={<Layers3 className="size-4" />}
          title="Active modules"
          count={runtimeConfig.active_modules.length}
          emptyMessage="No active modules were returned."
        >
          <KeyedItemList items={runtimeConfig.active_modules} />
        </RuntimeSection>

        <RuntimeSection
          icon={<Boxes className="size-4" />}
          title="Active domains"
          count={runtimeConfig.active_domains.length}
          emptyMessage="No active operational domains were returned."
        >
          <KeyedItemList items={runtimeConfig.active_domains} />
        </RuntimeSection>

        <RuntimeSection
          icon={<ClipboardList className="size-4" />}
          title="Optional units"
          count={runtimeConfig.optional_units.length}
          emptyMessage="No optional units were returned."
        >
          <KeyedItemList items={runtimeConfig.optional_units} />
        </RuntimeSection>

        <RuntimeSection
          icon={<BookOpenText className="size-4" />}
          title="Vocabulary"
          count={runtimeConfig.optional_vocabulary.length}
          emptyMessage="No vocabulary terms were returned."
        >
          <VocabularyList items={runtimeConfig.optional_vocabulary} />
        </RuntimeSection>

        <RuntimeSection
          icon={<Tags className="size-4" />}
          title="Runtime tags"
          count={runtimeConfig.optional_runtime_tags.length}
          emptyMessage="No runtime tags were returned."
        >
          <RuntimeTagList items={runtimeConfig.optional_runtime_tags} />
        </RuntimeSection>

        <RuntimeSection
          icon={<Route className="size-4" />}
          title="Routing hints"
          count={runtimeConfig.optional_routing_hints.length}
          emptyMessage="No routing hints were returned."
        >
          <RoutingHintList items={runtimeConfig.optional_routing_hints} />
        </RuntimeSection>
      </CardContent>
    </Card>
  )
}

function ReadOnlyDescription({ description }: { description: string | null }) {
  return (
    <div className="rounded-[1.25rem] border border-[#ebe2d5] bg-[#fbf7f0] px-4 py-4">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="text-sm font-semibold">Activity description</div>
        <Badge variant="outline" className="border-[#ebe2d5] bg-white">
          Backend value
        </Badge>
      </div>
      <p className="text-sm leading-6 text-muted-foreground">
        {description || 'No activity description is currently returned in runtime config.'}
      </p>
    </div>
  )
}

function RuntimeSection({
  children,
  count,
  emptyMessage,
  icon,
  title,
}: {
  children: ReactNode
  count: number
  emptyMessage: string
  icon: ReactNode
  title: string
}) {
  return (
    <section className="rounded-[1.25rem] border border-[#ece5da] bg-white px-4 py-4 shadow-[0_14px_34px_-32px_rgba(46,72,173,0.22)]">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-[color:var(--primary)]/10 p-2 text-[color:var(--primary)]">
            {icon}
          </span>
          <div>
            <div className="text-sm font-semibold">{title}</div>
            <div className="text-xs text-muted-foreground">{count} returned</div>
          </div>
        </div>
        <Badge variant="outline" className="border-[#ebe2d5] bg-[#fbf7f0]">
          {count}
        </Badge>
      </div>

      {count === 0 ? (
        <div className="rounded-[1rem] border border-dashed border-[#ddd3c5] bg-[#fffaf2] px-4 py-3 text-sm text-muted-foreground">
          {emptyMessage}
        </div>
      ) : (
        children
      )}
    </section>
  )
}

function KeyedItemList({ items }: { items: KeyedRuntimeItem[] }) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {items.map((item) => (
        <div key={item.id} className="rounded-[1rem] border border-[#ebe2d5] bg-[#fffdf9] px-3 py-3">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold">{item.label}</div>
              <div className="truncate text-xs text-muted-foreground">{item.key}</div>
            </div>
            <Badge variant="outline" className="shrink-0 border-[#ebe2d5] bg-white">
              {item.source}
            </Badge>
          </div>
        </div>
      ))}
    </div>
  )
}

function VocabularyList({ items }: { items: RuntimeVocabularyItem[] }) {
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.id} className="rounded-[1rem] border border-[#ebe2d5] bg-[#fffdf9] px-3 py-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <div className="text-sm font-semibold">{item.term}</div>
              <div className="text-sm leading-6 text-muted-foreground">{item.meaning}</div>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              {item.mapped_domain_key ? <Badge variant="outline">{item.mapped_domain_key}</Badge> : null}
              {item.mapped_unit_key ? <Badge variant="outline">{item.mapped_unit_key}</Badge> : null}
              <Badge variant="outline" className="border-[#ebe2d5] bg-white">
                {item.source}
              </Badge>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function RuntimeTagList({ items }: { items: RuntimeTagItem[] }) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {items.map((item) => (
        <div key={item.id} className="rounded-[1rem] border border-[#ebe2d5] bg-[#fffdf9] px-3 py-3">
          <div className="mb-2 text-sm font-semibold">{item.label}</div>
          <div className="mb-3 text-xs text-muted-foreground">{item.key}</div>
          <Badge variant="outline" className="border-[#ebe2d5] bg-white">
            {item.source}
          </Badge>
          <div className="mt-2 flex flex-wrap gap-2">
            {item.domain_keys.map((domainKey) => (
              <Badge key={domainKey} variant="outline" className="border-[#ebe2d5] bg-[#fbf7f0]">
                {domainKey}
              </Badge>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function RoutingHintList({ items }: { items: RoutingHintItem[] }) {
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.id} className="rounded-[1rem] border border-[#ebe2d5] bg-[#fffdf9] px-3 py-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <div className="text-sm font-semibold">{item.pattern}</div>
              <div className="text-xs text-muted-foreground">
                Suggested unit: {item.suggested_unit_key ?? 'none'}
              </div>
            </div>
            <Badge variant="outline" className="w-fit border-[#ebe2d5] bg-white">
              {item.source}
            </Badge>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {item.domain_keys.map((domainKey) => (
              <Badge key={domainKey} variant="outline" className="border-[#ebe2d5] bg-[#fbf7f0]">
                {domainKey}
              </Badge>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
