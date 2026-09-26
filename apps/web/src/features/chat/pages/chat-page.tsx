import { useMemo, useState, type ReactNode } from 'react'
import { LoaderCircle, PanelLeftClose, PanelLeftOpen, Plus } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainHubSubheader } from '@/components/layout/terrain-hub-subheader'
import { Input } from '@/components/ui/input'
import { TerrainEmptyState, TerrainErrorState } from '@/components/ui/terrain'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { useLgViewport } from '@/lib/lg-viewport'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ChatApiError } from '../api'
import { blockMembership } from '@/features/safety/api'
import { SafetyReportSheet } from '@/features/safety/safety-report-sheet'
import {
  ChatConversationActionsSheet,
  type ChatConversationActionsHandlers,
} from '../components/chat-conversation-actions-sheet'
import { ChatCreateSheet } from '../components/chat-create-sheet'
import { ChatReconnectBanner } from '../components/chat-reconnect-banner'
import {
  ConversationAvatarButton,
  ConversationRow,
} from '../components/conversation-row'
import { useOptionalChatRealtime } from '../components/chat-realtime-provider'
import { filterConversationsByQuery } from '../lib/chat-display'
import { chatDesktopColumnHeaderClassName } from '../lib/chat-desktop-surface'
import {
  useChatConversationsQuery,
  useChatStatusQuery,
  useDeleteGroupMutation,
  useHideDmMutation,
  useLeaveGroupMutation,
  usePinConversationMutation,
  useUnpinConversationMutation,
} from '../hooks'
import type { ChatConversationListItem } from '../types'
import { ChatConversationPage } from './chat-conversation-page'

type ChatPageProps = {
  onOpenConversation: (conversationId: string) => void
  establishmentId?: string | null
  selectedConversationId?: string | null
}

function ChatPageRoot({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full min-h-0 flex-col" data-testid="chat-page-root">
      {children}
    </div>
  )
}

function CreateConversationButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full outline-none focus-visible:ring-2 focus-visible:ring-[#114660]/30 focus-visible:ring-offset-2"
      aria-label="Nouvelle conversation"
      title="Nouvelle conversation"
      onClick={onClick}
    >
      <span
        className={cn(
          'flex h-8 w-8 items-center justify-center rounded-full text-white',
          terrainBrandAction.bg,
        )}
      >
        <Plus className="h-4 w-4" strokeWidth={2.5} />
      </span>
    </button>
  )
}

export function ChatPage({
  onOpenConversation,
  establishmentId: establishmentIdProp,
  selectedConversationId = null,
}: ChatPageProps) {
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const auth = useAuth()
  const establishmentId =
    establishmentIdProp ?? auth.bootstrap?.active_membership?.establishment_id ?? null
  const fromList = (auth.bootstrap?.memberships ?? []).find(
    (membership) =>
      membership.establishment_id === establishmentId && membership.status === 'active',
  )?.id
  const active = auth.bootstrap?.active_membership
  const viewerMembershipId =
    fromList ?? (active?.establishment_id === establishmentId ? active.id : null) ?? null
  const [search, setSearch] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [listCollapsed, setListCollapsed] = useState(false)
  const [actionsConversation, setActionsConversation] = useState<ChatConversationListItem | null>(
    null,
  )
  const [reportPeerId, setReportPeerId] = useState<string | null>(null)
  const [blockPending, setBlockPending] = useState(false)
  /** Conversation that owns the in-flight action and any failure shown in the menu. */
  const [actionOwnerConversationId, setActionOwnerConversationId] = useState<string | null>(null)
  const [actionFailure, setActionFailure] = useState<{
    conversationId: string
    error: unknown
  } | null>(null)

  const statusQuery = useChatStatusQuery(establishmentId)
  const conversationsQuery = useChatConversationsQuery(establishmentId, {
    enabled: Boolean(statusQuery.data?.can_access),
  })
  const realtime = useOptionalChatRealtime()
  const connectionStatus = realtime?.connectionStatus ?? 'idle'
  const clearLocalMessages = realtime?.clearLocalMessagesForConversation

  const pinMutation = usePinConversationMutation(establishmentId)
  const unpinMutation = useUnpinConversationMutation(establishmentId)
  const hideMutation = useHideDmMutation(establishmentId, {
    clearLocalMessages,
  })
  const leaveMutation = useLeaveGroupMutation(establishmentId, {
    clearLocalMessages,
  })
  const deleteMutation = useDeleteGroupMutation(establishmentId, {
    clearLocalMessages,
  })

  const isActionOwnerMenuOpen =
    actionsConversation !== null && actionsConversation.id === actionOwnerConversationId
  const ownerActionInFlight =
    pinMutation.isPending ||
    unpinMutation.isPending ||
    hideMutation.isPending ||
    leaveMutation.isPending ||
    deleteMutation.isPending ||
    blockPending
  const actionsPending = isActionOwnerMenuOpen && ownerActionInFlight
  const actionsErrorMessage =
    actionFailure && actionsConversation?.id === actionFailure.conversationId
      ? resolveApiErrorMessage(actionFailure.error, ChatApiError, 'Une erreur est survenue.')
      : null

  function isActionInFlightFor(conversationId: string): boolean {
    return actionOwnerConversationId === conversationId && ownerActionInFlight
  }

  function resetActionMutations() {
    pinMutation.reset()
    unpinMutation.reset()
    hideMutation.reset()
    leaveMutation.reset()
    deleteMutation.reset()
    setBlockPending(false)
    setActionOwnerConversationId(null)
    setActionFailure(null)
  }

  function closeActions() {
    setActionsConversation(null)
    resetActionMutations()
  }

  /** Close + reset only when the open menu is still this conversation (stale settles leave B alone). */
  function closeActionsIfCurrent(conversationId: string) {
    let didClose = false
    setActionsConversation((current) => {
      if (current?.id !== conversationId) {
        return current
      }
      didClose = true
      return null
    })
    if (didClose) {
      resetActionMutations()
    }
  }

  function beginAction(conversationId: string) {
    setActionOwnerConversationId(conversationId)
    setActionFailure((current) =>
      current?.conversationId === conversationId ? null : current,
    )
  }

  async function handlePin(conversationId: string) {
    beginAction(conversationId)
    try {
      await pinMutation.mutateAsync(conversationId)
      closeActionsIfCurrent(conversationId)
    } catch (error) {
      // Record against the launcher; display is gated by open menu id (stale A must not paint on B).
      setActionFailure({ conversationId, error })
    }
  }

  async function handleUnpin(conversationId: string) {
    beginAction(conversationId)
    try {
      await unpinMutation.mutateAsync(conversationId)
      closeActionsIfCurrent(conversationId)
    } catch (error) {
      setActionFailure({ conversationId, error })
    }
  }

  async function handleHideDm(conversationId: string) {
    beginAction(conversationId)
    try {
      await hideMutation.mutateAsync(conversationId)
      closeActionsIfCurrent(conversationId)
    } catch (error) {
      setActionFailure({ conversationId, error })
    }
  }

  async function handleLeaveGroup(conversationId: string) {
    beginAction(conversationId)
    try {
      await leaveMutation.mutateAsync(conversationId)
      closeActionsIfCurrent(conversationId)
    } catch (error) {
      setActionFailure({ conversationId, error })
    }
  }

  async function handleDeleteGroup(conversationId: string) {
    beginAction(conversationId)
    try {
      await deleteMutation.mutateAsync(conversationId)
      closeActionsIfCurrent(conversationId)
    } catch (error) {
      setActionFailure({ conversationId, error })
    }
  }

  function openActionsFor(conversation: ChatConversationListItem) {
    if (actionsConversation?.id !== conversation.id) {
      resetActionMutations()
    }
    setActionsConversation(conversation)
  }

  function buildActionHandlers(
    conversation: ChatConversationListItem,
  ): ChatConversationActionsHandlers {
    const peerMembershipId =
      conversation.participants.find(
        (participant) => participant.membership_id !== viewerMembershipId,
      )?.membership_id ?? null

    return {
      onPin: (conversationId: string) => {
        void handlePin(conversationId)
      },
      onUnpin: (conversationId: string) => {
        void handleUnpin(conversationId)
      },
      onHideDm: (conversationId: string) => {
        void handleHideDm(conversationId)
      },
      onLeaveGroup: (conversationId: string) => {
        void handleLeaveGroup(conversationId)
      },
      onDeleteGroup: (conversationId: string) => {
        void handleDeleteGroup(conversationId)
      },
      onBlockPeer:
        conversation.type === 'dm' && peerMembershipId && establishmentId
          ? () => {
              void (async () => {
                beginAction(conversation.id)
                setBlockPending(true)
                try {
                  await blockMembership(establishmentId, peerMembershipId)
                  closeActionsIfCurrent(conversation.id)
                } catch (error) {
                  setActionFailure({ conversationId: conversation.id, error })
                } finally {
                  setBlockPending(false)
                }
              })()
            }
          : undefined,
      onReportPeer:
        conversation.type === 'dm' && peerMembershipId
          ? () => {
              setReportPeerId(peerMembershipId)
              closeActions()
            }
          : undefined,
    }
  }

  const allConversations = useMemo(
    () => conversationsQuery.data?.items ?? [],
    [conversationsQuery.data?.items],
  )
  const filteredConversations = useMemo(() => {
    return filterConversationsByQuery(allConversations, search, viewerMembershipId)
  }, [allConversations, search, viewerMembershipId])

  const searchActive = search.trim().length > 0
  const showGlobalEmpty =
    conversationsQuery.isSuccess && allConversations.length === 0
  const showSearchEmpty =
    conversationsQuery.isSuccess &&
    allConversations.length > 0 &&
    searchActive &&
    filteredConversations.length === 0

  if (!establishmentId) {
    return (
      <ChatPageRoot>
        <p className="px-3 py-4 text-sm text-[#6b5f52]">Établissement non sélectionné.</p>
      </ChatPageRoot>
    )
  }

  if (statusQuery.isLoading) {
    return (
      <ChatPageRoot>
        <div className="flex min-h-0 flex-1 items-center justify-center text-[#7D7B75]">
          <LoaderCircle className="h-6 w-6 animate-spin" />
        </div>
      </ChatPageRoot>
    )
  }

  if (statusQuery.isError) {
    return (
      <ChatPageRoot>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain">
          <TerrainErrorState
            className="mx-3 mt-3"
            message={resolveApiErrorMessage(statusQuery.error, ChatApiError, 'Une erreur est survenue.')}
            onRetry={() => void statusQuery.refetch()}
          />
        </div>
      </ChatPageRoot>
    )
  }

  if (!statusQuery.data?.can_access || !statusQuery.data.chat_enabled) {
    return (
      <ChatPageRoot>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain">
          <TerrainEmptyState
            className="mx-3 mt-6"
            title="Chat indisponible"
            description="Le chat n'est pas activé pour cet établissement ou vous n'y avez pas accès."
          />
        </div>
      </ChatPageRoot>
    )
  }

  const canCreate = statusQuery.data.can_create_dm || statusQuery.data.can_create_group
  const collapseLabel = listCollapsed
    ? 'Développer les discussions'
    : 'Réduire les discussions'
  const CollapseIcon = listCollapsed ? PanelLeftOpen : PanelLeftClose

  const searchHeader = (
    <TerrainHubSubheader className="border-b border-[#E8E6DF]">
      <div className="flex items-center gap-2 px-3 py-2">
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Rechercher une conversation"
          className="h-8 rounded-full border-[#E8E6DF] bg-[#F5F4F0] px-3 text-sm"
          data-testid="chat-list-search"
        />
        {canCreate ? <CreateConversationButton onClick={() => setCreateOpen(true)} /> : null}
      </div>
    </TerrainHubSubheader>
  )

  const listBody = (
    <>
      {conversationsQuery.isLoading ? (
        <div className="flex items-center justify-center py-16 text-[#7D7B75]">
          <LoaderCircle className="h-6 w-6 animate-spin" />
        </div>
      ) : null}

      {conversationsQuery.isError ? (
        <TerrainErrorState
          className="mx-3 mt-3"
          message={resolveApiErrorMessage(conversationsQuery.error, ChatApiError, 'Une erreur est survenue.')}
          onRetry={() => void conversationsQuery.refetch()}
        />
      ) : null}

      {showGlobalEmpty ? (
        <TerrainEmptyState
          className="mx-3 mt-6"
          title="Aucune conversation"
          description="Démarrez un message direct ou créez un groupe pour commencer."
        />
      ) : null}

      {showSearchEmpty ? (
        <TerrainEmptyState
          className="mx-3 mt-6"
          title="Aucun résultat"
          description="Aucune conversation ne correspond à cette recherche."
        />
      ) : null}

      {conversationsQuery.isSuccess && filteredConversations.length > 0 ? (
        <div className="flex flex-col gap-[6px] px-3">
          {filteredConversations.map((conversation) => (
            <ConversationRow
              key={conversation.id}
              conversation={conversation}
              viewerMembershipId={viewerMembershipId}
              onSelect={onOpenConversation}
              onOpenActions={isDesktopWeb ? undefined : openActionsFor}
              selected={selectedConversationId === conversation.id}
              actionsMode={isDesktopWeb ? 'popover' : 'sheet'}
              actionsOpen={isDesktopWeb && actionsConversation?.id === conversation.id}
              onActionsOpenChange={
                isDesktopWeb
                  ? (open) => {
                      if (open) {
                        openActionsFor(conversation)
                        return
                      }
                      // Ignore dismiss while this row owns an in-flight action (disabling the
                      // focused menuitem can otherwise close the controlled popover).
                      if (isActionInFlightFor(conversation.id)) {
                        return
                      }
                      closeActionsIfCurrent(conversation.id)
                    }
                  : undefined
              }
              actionsPending={actionsPending}
              actionsErrorMessage={
                actionsConversation?.id === conversation.id ? actionsErrorMessage : null
              }
              actionHandlers={isDesktopWeb ? buildActionHandlers(conversation) : undefined}
            />
          ))}
        </div>
      ) : null}
    </>
  )

  const collapsedListBody = (
    <>
      {conversationsQuery.isLoading ? (
        <div className="flex items-center justify-center py-8 text-[#7D7B75]">
          <LoaderCircle className="h-5 w-5 animate-spin" />
        </div>
      ) : null}

      {conversationsQuery.isError ? (
        <div className="px-1 pt-2">
          <button
            type="button"
            className="w-full rounded-lg px-1 py-2 text-[11px] font-semibold text-[#E24B4A]"
            onClick={() => void conversationsQuery.refetch()}
          >
            Réessayer
          </button>
        </div>
      ) : null}

      {conversationsQuery.isSuccess && allConversations.length > 0 ? (
        <div className="flex flex-col items-center gap-2 px-1">
          {allConversations.map((conversation) => (
            <ConversationAvatarButton
              key={conversation.id}
              conversation={conversation}
              viewerMembershipId={viewerMembershipId}
              selected={selectedConversationId === conversation.id}
              onSelect={onOpenConversation}
            />
          ))}
        </div>
      ) : null}
    </>
  )

  const overlays = (
    <>
      <ChatCreateSheet
        establishmentId={establishmentId}
        open={createOpen}
        presentation={isDesktopWeb ? 'dialog' : 'sheet'}
        canCreateDm={statusQuery.data.can_create_dm}
        canCreateGroup={statusQuery.data.can_create_group}
        onClose={() => setCreateOpen(false)}
        onConversationCreated={onOpenConversation}
      />

      {!isDesktopWeb && actionsConversation ? (
        <ChatConversationActionsSheet
          conversation={actionsConversation}
          open
          isPending={actionsPending}
          errorMessage={actionsErrorMessage}
          onClose={closeActions}
          {...buildActionHandlers(actionsConversation)}
        />
      ) : null}
      <SafetyReportSheet
        open={reportPeerId !== null}
        establishmentId={establishmentId}
        contentKind="user"
        targetMembershipId={reportPeerId ?? undefined}
        onClose={() => setReportPeerId(null)}
      />
    </>
  )

  if (isDesktopWeb) {
    return (
      <ChatPageRoot>
        <div className="shrink-0">
          <ChatReconnectBanner status={connectionStatus} />
        </div>
        <div className="flex min-h-0 flex-1" data-testid="chat-desktop-split">
          <div
            className={cn(
              'flex shrink-0 flex-col border-r border-[#E8E6DF]',
              listCollapsed ? 'w-28' : 'w-[22rem]',
            )}
            data-testid="chat-discussions-rail"
            data-collapsed={listCollapsed ? 'true' : 'false'}
          >
            <div
              className={cn(
                chatDesktopColumnHeaderClassName,
                listCollapsed ? 'relative justify-center px-0' : 'gap-2',
              )}
            >
              {listCollapsed ? null : (
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Rechercher une conversation"
                  className="h-8 min-w-0 flex-1 rounded-full border-[#E8E6DF] bg-[#F5F4F0] px-3 text-sm"
                  data-testid="chat-list-search"
                />
              )}
              {canCreate ? (
                <CreateConversationButton onClick={() => setCreateOpen(true)} />
              ) : null}
              <button
                type="button"
                className={cn(
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[#7D7B75] outline-none hover:bg-[#F5F4F0] hover:text-[#1a1a1a] focus-visible:ring-2 focus-visible:ring-[#114660]/30',
                  listCollapsed && 'absolute right-0 top-1/2 -translate-y-1/2',
                )}
                aria-label={collapseLabel}
                title={collapseLabel}
                aria-pressed={listCollapsed}
                data-testid="chat-discussions-collapse"
                onClick={() => setListCollapsed((current) => !current)}
              >
                <CollapseIcon className="h-4 w-4" aria-hidden />
              </button>
            </div>
            <div
              className={cn(
                'min-h-0 flex-1 overflow-y-auto overscroll-y-contain pb-3 pt-3',
                listCollapsed && 'px-0',
              )}
              data-testid="chat-list-scroll"
            >
              {listCollapsed ? collapsedListBody : listBody}
            </div>
          </div>
          <div className="relative flex min-h-0 min-w-0 flex-1 flex-col">
            {selectedConversationId ? (
              <ChatConversationPage
                key={selectedConversationId}
                conversationId={selectedConversationId}
                embedded
              />
            ) : (
              <>
                <div
                  className={chatDesktopColumnHeaderClassName}
                  data-testid="chat-desktop-empty-header"
                  aria-hidden="true"
                />
                <div
                  className="flex flex-1 items-center justify-center px-6"
                  data-testid="chat-desktop-empty"
                >
                  <TerrainEmptyState
                    title="Sélectionnez une conversation"
                    description="Choisissez une discussion dans la liste pour lire et écrire des messages."
                  />
                </div>
              </>
            )}
          </div>
        </div>
        {overlays}
      </ChatPageRoot>
    )
  }

  return (
    <ChatPageRoot>
      <div className="shrink-0">
        <ChatReconnectBanner status={connectionStatus} />
      </div>

      {searchHeader}

      <div
        className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain pb-3 pt-3"
        data-testid="chat-list-scroll"
      >
        {listBody}
      </div>

      {overlays}
    </ChatPageRoot>
  )
}
