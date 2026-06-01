import { ChevronDown, Layers3, LoaderCircle, Search } from 'lucide-react'
import { Accordion } from 'radix-ui'
import { useEffect, useMemo, useRef, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  buildSelectedScopeSummary,
  filterTreeBySearch,
  getScopeSelectionState,
  toggleScopeSelection,
  type MembershipScopeSelection,
  type OperationalScopeTree,
  type ScopeSelectionState,
  type ScopeType,
} from '@/features/auth/lib/membership-scope'
import { cn } from '@/lib/utils'

type OperationalScopeSelectorProps = {
  disabled?: boolean
  errorMessage?: string | null
  isLoading?: boolean
  onChange: (scopes: MembershipScopeSelection[]) => void
  readOnly?: boolean
  selectedScopes: MembershipScopeSelection[]
  tree: OperationalScopeTree | null
}

export function OperationalScopeSelector({
  disabled = false,
  errorMessage = null,
  isLoading = false,
  onChange,
  readOnly = false,
  selectedScopes,
  tree,
}: OperationalScopeSelectorProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const filteredTree = useMemo(
    () => (tree ? filterTreeBySearch(tree, searchQuery) : null),
    [searchQuery, tree],
  )
  const summary = useMemo(
    () => (tree ? buildSelectedScopeSummary(selectedScopes, tree) : null),
    [selectedScopes, tree],
  )
  const [expandedModuleId, setExpandedModuleId] = useState<string | undefined>(undefined)

  const effectiveExpandedModuleId = useMemo(() => {
    if (!filteredTree?.displayModules.length) {
      return undefined
    }

    if (
      expandedModuleId &&
      filteredTree.displayModules.some((module) => module.id === expandedModuleId)
    ) {
      return expandedModuleId
    }

    return filteredTree.displayModules[0]?.id
  }, [expandedModuleId, filteredTree])

  function handleExpandedModuleChange(value: string) {
    setExpandedModuleId(value)
  }

  const isInteractionDisabled = disabled || isLoading || readOnly || !tree

  function handleToggle(scopeType: ScopeType, scopeId: string) {
    if (!tree || isInteractionDisabled) {
      return
    }

    onChange(toggleScopeSelection(scopeType, scopeId, selectedScopes, tree))
  }

  return (
    <section className="space-y-4 rounded-[1.25rem] border border-[#ece5da] bg-white px-4 py-4 shadow-[0_14px_34px_-32px_rgba(46,72,173,0.22)]">
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-[color:var(--primary)]/10 p-2 text-[color:var(--primary)]">
            <Layers3 className="size-4" />
          </span>
          <div>
            <div className="text-sm font-semibold">Périmètre opérationnel</div>
            <div className="text-xs text-muted-foreground">
              Choisissez les zones de responsabilité de cet utilisateur.
            </div>
          </div>
        </div>
        <p className="text-sm leading-6 text-muted-foreground">
          Ce périmètre détermine ce que l&apos;utilisateur verra et pourra traiter.
        </p>
      </div>

      {!readOnly ? (
        <div className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Rechercher un module, un domaine ou un sujet…"
            disabled={isInteractionDisabled}
            className="rounded-[1rem] border-[#e7dfd1] bg-[#fffdf8] pl-10"
          />
        </div>
      ) : null}

      {isLoading ? (
        <div className="flex items-center gap-3 rounded-[1rem] border border-[#ece5da] bg-[#fffdf8] px-4 py-4 text-sm text-muted-foreground">
          <LoaderCircle className="size-4 animate-spin text-[color:var(--primary)]" />
          Chargement de la taxonomie opérationnelle…
        </div>
      ) : null}

      {errorMessage ? (
        <div className="rounded-[1rem] border border-[#f4d5d5] bg-[#fff3f2] px-4 py-3 text-sm text-[#9d3b33]">
          {errorMessage}
        </div>
      ) : null}

      {!isLoading && tree && filteredTree ? (
        filteredTree.displayModules.length === 0 ? (
          <div className="rounded-[1rem] border border-dashed border-[#ddd3c5] bg-[#fffaf2] px-4 py-3 text-sm text-muted-foreground">
            {searchQuery.trim()
              ? 'Aucun élément ne correspond à votre recherche.'
              : 'Aucune taxonomie opérationnelle active n’est disponible pour cet établissement.'}
          </div>
        ) : (
          <Accordion.Root
            className="space-y-2"
            collapsible
            type="single"
            value={effectiveExpandedModuleId}
            onValueChange={handleExpandedModuleChange}
          >
            {filteredTree.displayModules.map((moduleNode) => (
              <Accordion.Item
                key={moduleNode.id}
                className="overflow-hidden rounded-[1rem] border border-[#ebe2d5] bg-[#fffdf9]"
                value={moduleNode.id}
              >
                <Accordion.Header className="flex items-center gap-2 px-3 py-2">
                  <ScopeCheckbox
                    disabled={isInteractionDisabled}
                    label={moduleNode.label}
                    onToggle={() => handleToggle('module', moduleNode.id)}
                    selectionState={getScopeSelectionState(
                      'module',
                      moduleNode.id,
                      selectedScopes,
                      tree,
                    )}
                  />
                  <Accordion.Trigger className="group ml-auto flex min-w-0 flex-1 items-center justify-between gap-2 rounded-[0.75rem] px-2 py-1 text-left transition-colors hover:bg-[#fffaf2]">
                    <span className="truncate text-xs text-muted-foreground">
                      {moduleNode.domains.length} domaine
                      {moduleNode.domains.length === 1 ? '' : 's'}
                    </span>
                    <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
                  </Accordion.Trigger>
                </Accordion.Header>

                <Accordion.Content className="border-t border-[#ebe2d5] bg-white px-3 py-3">
                  <div className="space-y-3">
                    {moduleNode.domains.map((domainNode) => (
                      <div
                        key={domainNode.id}
                        className="rounded-[0.9rem] border border-[#f0e8dc] bg-[#fffdf9] px-3 py-3"
                      >
                        <ScopeCheckbox
                          disabled={isInteractionDisabled}
                          label={domainNode.label}
                          onToggle={() => handleToggle('domain', domainNode.id)}
                          selectionState={getScopeSelectionState(
                            'domain',
                            domainNode.id,
                            selectedScopes,
                            tree,
                          )}
                        />

                        {domainNode.subjects.length > 0 ? (
                          <div className="mt-3 space-y-2 border-l border-[#ebe2d5] pl-3">
                            {domainNode.subjects.map((subjectNode) => (
                              <ScopeCheckbox
                                key={subjectNode.id}
                                disabled={isInteractionDisabled}
                                label={subjectNode.label}
                                onToggle={() => handleToggle('subject', subjectNode.id)}
                                selectionState={getScopeSelectionState(
                                  'subject',
                                  subjectNode.id,
                                  selectedScopes,
                                  tree,
                                )}
                                compact
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
      ) : null}

      {summary ? (
        <div className="space-y-2 rounded-[1rem] border border-[#ebe2d5] bg-[#fffaf2] px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
            Sélection actuelle
          </div>
          <div className="flex flex-wrap gap-2">
            {summary.moduleLabels.length > 0 ? (
              <SummaryBadge
                count={summary.moduleLabels.length}
                kind="Modules"
                labels={summary.moduleLabels}
              />
            ) : null}
            {summary.domainLabels.length > 0 ? (
              <SummaryBadge
                count={summary.domainLabels.length}
                kind="Domaines"
                labels={summary.domainLabels}
              />
            ) : null}
            {summary.subjectLabels.length > 0 ? (
              <SummaryBadge
                count={summary.subjectLabels.length}
                kind="Sujets"
                labels={summary.subjectLabels}
              />
            ) : null}
            {summary.moduleLabels.length === 0 &&
            summary.domainLabels.length === 0 &&
            summary.subjectLabels.length === 0 ? (
              <span className="text-sm text-muted-foreground">Aucune zone sélectionnée.</span>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  )
}

function ScopeCheckbox({
  compact = false,
  disabled,
  label,
  onToggle,
  selectionState,
}: {
  compact?: boolean
  disabled: boolean
  label: string
  onToggle: () => void
  selectionState: ScopeSelectionState
}) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!inputRef.current) {
      return
    }

    inputRef.current.indeterminate = selectionState === 'indeterminate'
  }, [selectionState])

  return (
    <label
      className={cn(
        'flex cursor-pointer items-start gap-2',
        disabled && 'cursor-not-allowed opacity-60',
        compact && 'text-sm',
      )}
    >
      <input
        ref={inputRef}
        type="checkbox"
        checked={selectionState === 'checked'}
        disabled={disabled}
        onChange={onToggle}
        className="mt-0.5 size-4 rounded border-[#d9cdb8] accent-[color:var(--primary)]"
      />
      <span className={cn('font-medium', compact && 'font-normal')}>{label}</span>
    </label>
  )
}

function SummaryBadge({
  count,
  kind,
  labels,
}: {
  count: number
  kind: string
  labels: string[]
}) {
  return (
    <Badge variant="outline" className="max-w-full border-[#ebe2d5] bg-white text-left">
      <span className="font-semibold">
        {count} {kind}
      </span>
      <span className="text-muted-foreground"> · {labels.join(', ')}</span>
    </Badge>
  )
}
