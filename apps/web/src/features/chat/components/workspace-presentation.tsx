import type { ReactNode } from 'react'
import { ChevronRight, ClipboardList, ExternalLink, MessageCircle } from 'lucide-react'

import { getDisplayNameInitials } from '@/lib/display-names'
import { terrainFeedAvatar } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { formatChatRelativeTime } from '../lib/chat-display'
import type { WorkspaceItem } from '../workspace-api'

export function workspaceItemKey(item: WorkspaceItem): string {
  return `${item.kind}-${item.id}`
}

function kindLabel(kind: WorkspaceItem['kind']): 'Équipe' | 'Plan' {
  return kind === 'plan' ? 'Plan' : 'Équipe'
}

function itemExcerpt(item: WorkspaceItem): string {
  const body = item.body?.trim()
  return body ? body : 'Pièce jointe'
}

export function WorkspaceSectionHeader({
  eyebrow,
  title,
  description,
  hint,
}: {
  eyebrow: string
  title: string
  description: string
  hint?: string
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <p className="text-[10px] font-semibold tracking-[0.14em] text-[#779681] uppercase">
          {eyebrow}
        </p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight text-[#1a1a1a]">{title}</h2>
        <p className="mt-1 max-w-xl text-[13px] leading-snug text-[#6d7c72]">{description}</p>
      </div>
      {hint ? (
        <p className="inline-flex max-w-xs items-center rounded-lg bg-[#e8f0e9] px-3 py-2 text-[11px] font-medium text-[#547360]">
          {hint}
        </p>
      ) : null}
    </div>
  )
}

export function WorkspaceFilterChips({
  unresolved,
  onChange,
}: {
  unresolved: boolean
  onChange: (unresolved: boolean) => void
}) {
  return (
    <div className="flex gap-1.5" role="group" aria-label="Filtrer les discussions de plans">
      {(
        [
          [false, 'Toutes'],
          [true, 'Non résolues'],
        ] as const
      ).map(([value, label]) => {
        const active = unresolved === value
        return (
          <button
            key={label}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(value)}
            className={cn(
              'rounded-full px-3 py-1.5 text-xs font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[#265d4c]/40',
              active
                ? 'bg-[#e7f2ec] text-[#1d5949]'
                : 'bg-white text-[#5c6b62] ring-1 ring-[#E8E6DF]',
            )}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}

function RowShell({
  selected,
  onClick,
  children,
  testId,
}: {
  selected?: boolean
  onClick: () => void
  children: ReactNode
  testId: string
}) {
  return (
    <button
      type="button"
      data-testid={testId}
      aria-current={selected ? 'true' : undefined}
      onClick={onClick}
      className={cn(
        'flex w-full gap-3 px-4 py-3 text-left outline-none transition focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#265d4c]/40',
        selected ? 'bg-[#e7f2ec]' : 'hover:bg-[#f7f8f6]',
      )}
    >
      {children}
    </button>
  )
}

export function PlanDiscussionRow({
  item,
  selected = false,
  onActivate,
}: {
  item: WorkspaceItem
  selected?: boolean
  onActivate: () => void
}) {
  return (
    <li className="border-b border-[#eef2ee] last:border-b-0">
      <RowShell
        selected={selected}
        onClick={onActivate}
        testId={`workspace-row-${item.kind}-${item.id}`}
      >
        <span
          className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#e8f0e9] text-[#245d4a]"
          aria-hidden="true"
        >
          <ClipboardList className="h-4 w-4" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-start justify-between gap-2">
            <span className="flex min-w-0 items-center gap-1.5">
              <span className="truncate text-sm font-semibold text-[#1a1a1a]">{item.title}</span>
              {item.unread ? (
                <>
                  <span className="sr-only">Non lu</span>
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#245d4a]" aria-hidden="true" />
                </>
              ) : null}
            </span>
          </span>
          <span className="mt-0.5 block truncate text-xs text-[#6d7c72]">
            {item.author} · {formatChatRelativeTime(item.created_at)}
          </span>
          <span className="mt-1 line-clamp-2 block text-[13px] leading-snug text-[#3d4f45]">
            {itemExcerpt(item)}
          </span>
          {item.unresolved ? (
            <span className="mt-2 inline-flex rounded-full bg-[#f3ebe3] px-2 py-0.5 text-[11px] font-medium text-[#8a5a32]">
              Commentaire non résolu
            </span>
          ) : null}
        </span>
        <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-[#8aa094]" aria-hidden="true" />
      </RowShell>
    </li>
  )
}

export function MentionRow({
  item,
  selected = false,
  onActivate,
}: {
  item: WorkspaceItem
  selected?: boolean
  onActivate: () => void
}) {
  const initials = getDisplayNameInitials(item.author || item.title || '?')
  return (
    <li className="border-b border-[#eef2ee] last:border-b-0">
      <RowShell
        selected={selected}
        onClick={onActivate}
        testId={`workspace-row-${item.kind}-${item.id}`}
      >
        <span
          className={cn(
            'mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold',
            terrainFeedAvatar,
          )}
          aria-hidden="true"
        >
          {initials}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm leading-snug text-[#1a1a1a]">
            <span className="font-semibold">{item.author}</span> vous a mentionné dans{' '}
            <span className="font-semibold">{item.title}</span>
          </span>
          <span className="mt-1 line-clamp-2 block text-[13px] leading-snug text-[#4d5c53]">
            {itemExcerpt(item)}
          </span>
          <span className="mt-2 flex items-center gap-2 text-[11px] text-[#6d7c72]">
            <span className="inline-flex items-center gap-1 rounded-full bg-[#f4f7f3] px-2 py-0.5 font-medium text-[#3d5348]">
              {item.kind === 'plan' ? (
                <ClipboardList className="h-3 w-3" aria-hidden="true" />
              ) : (
                <MessageCircle className="h-3 w-3" aria-hidden="true" />
              )}
              {kindLabel(item.kind)}
            </span>
            <span>{formatChatRelativeTime(item.created_at)}</span>
          </span>
        </span>
        <ExternalLink className="mt-1 h-3.5 w-3.5 shrink-0 text-[#8aa094]" aria-hidden="true" />
      </RowShell>
    </li>
  )
}

export function SearchResultRow({
  item,
  onActivate,
}: {
  item: WorkspaceItem
  onActivate: () => void
}) {
  return (
    <li>
      <button
        type="button"
        data-testid={`workspace-row-${item.kind}-${item.id}`}
        onClick={onActivate}
        className="w-full rounded-2xl border border-[#E8E6DF] bg-white p-4 text-left outline-none hover:bg-[#f7f8f6] focus-visible:ring-2 focus-visible:ring-[#265d4c]/40"
      >
        <span className="block font-semibold text-[#1a1a1a]">{item.title}</span>
        <span className="mt-1 block text-xs text-[#6d7c72]">
          {item.author} · {formatChatRelativeTime(item.created_at)} · {kindLabel(item.kind)}
        </span>
        <span className="mt-2 line-clamp-3 block whitespace-pre-wrap text-sm text-[#1a1a1a]">
          {itemExcerpt(item)}
        </span>
      </button>
    </li>
  )
}

export function WorkspacePreview({
  item,
  onOpen,
}: {
  item: WorkspaceItem | null
  onOpen: (item: WorkspaceItem) => void
}) {
  if (!item) {
    return (
      <section
        aria-label="Aperçu"
        data-testid="workspace-preview"
        className="flex min-h-0 items-center justify-center rounded-2xl border border-[#e1e9e0] bg-white p-6 text-center"
      >
        <p className="max-w-xs text-sm text-[#6d7c72]">
          Sélectionnez un échange pour l’afficher ici. La sélection ne modifie pas son état.
        </p>
      </section>
    )
  }

  const isPlan = item.kind === 'plan'
  const openLabel = isPlan ? 'Ouvrir dans le plan' : 'Ouvrir la conversation'
  return (
    <section
      aria-label="Aperçu"
      data-testid="workspace-preview"
      className="min-h-0 overflow-y-auto rounded-2xl border border-[#e1e9e0] bg-white p-5"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-[10px] font-semibold tracking-[0.14em] text-[#779681] uppercase">
          Aperçu
        </p>
        <span className="inline-flex items-center gap-1 rounded-full bg-[#f4f7f3] px-2 py-0.5 text-[11px] font-medium text-[#3d5348]">
          {isPlan ? 'Plan d’action' : 'Équipe'}
        </span>
      </div>
      <h3 className="mt-3 text-lg font-semibold tracking-tight text-[#1a1a1a]">{item.title}</h3>
      <p className="mt-2 text-xs text-[#6d7c72]">
        {item.author} · {formatChatRelativeTime(item.created_at)}
      </p>
      {item.unresolved ? (
        <p className="mt-3 inline-flex rounded-full bg-[#f3ebe3] px-2 py-0.5 text-[11px] font-medium text-[#8a5a32]">
          Commentaire non résolu
        </p>
      ) : null}
      <blockquote className="mt-4 border-l-[3px] border-[#7cac8b] bg-[#f4f7f3] px-3 py-3 text-[13px] leading-relaxed whitespace-pre-wrap text-[#35513d]">
        {itemExcerpt(item)}
      </blockquote>
      <p className="mt-4 text-xs leading-relaxed text-[#6d7c72]">
        {isPlan
          ? 'Pour répondre ou traiter ce commentaire, ouvrez la discussion dans son plan.'
          : 'La réponse se fait dans la conversation d’origine.'}
      </p>
      <button
        type="button"
        onClick={() => onOpen(item)}
        className="mt-4 inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-[#245d4a] px-4 text-sm font-semibold text-white outline-none hover:bg-[#1e4e3e] focus-visible:ring-2 focus-visible:ring-[#245d4a]/40"
      >
        {openLabel}
        <ExternalLink className="h-4 w-4" aria-hidden="true" />
      </button>
    </section>
  )
}
