import { useMemo, useState, type ReactNode } from 'react'
import { LoaderCircle, Plus } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainHubSubheader } from '@/components/layout/terrain-hub-subheader'
import { Input } from '@/components/ui/input'
import { TerrainEmptyState, TerrainErrorState } from '@/components/ui/terrain'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { ChatApiError } from '../api'
import { blockMembership } from '@/features/safety/api'
import { SafetyReportSheet } from '@/features/safety/safety-report-sheet'
import { ChatConversationActionsSheet } from '../components/chat-conversation-actions-sheet'
import { ChatCreateSheet } from '../components/chat-create-sheet'
import { ChatReconnectBanner } from '../components/chat-reconnect-banner'
import { ConversationRow } from '../components/conversation-row'
import { useOptionalChatRealtime } from '../components/chat-realtime-provider'
import { filterConversationsByQuery } from '../lib/chat-display'
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

type ChatPageProps = {
  onOpenConversation: (conversationId: string) => void
  establishmentId?: string | null
}

function ChatPageRoot({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full min-h-0 flex-col" data-testid="chat-page-root">
      {children}
    </div>
  )
}

export function ChatPage({
  onOpenConversation,
  establishmentId: establishmentIdProp,
}: ChatPageProps) {
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
  const [actionsConversation, setActionsConversation] = useState<ChatConversationListItem | null>(
    null,
  )
  const [reportPeerId, setReportPeerId] = useState<string | null>(null)

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
  const actionsPending =
    pinMutation.isPending ||
    unpinMutation.isPending ||
    hideMutation.isPending ||
    leaveMutation.isPending ||
    deleteMutation.isPending

  function closeActions() {
    setActionsConversation(null)
    pinMutation.reset()
    unpinMutation.reset()
    hideMutation.reset()
    leaveMutation.reset()
    deleteMutation.reset()
  }

  async function handlePin(conversationId: string) {
    await pinMutation.mutateAsync(conversationId)
    closeActions()
  }

  async function handleUnpin(conversationId: string) {
    await unpinMutation.mutateAsync(conversationId)
    closeActions()
  }

  async function handleHideDm(conversationId: string) {
    await hideMutation.mutateAsync(conversationId)
    closeActions()
  }

  async function handleLeaveGroup(conversationId: string) {
    await leaveMutation.mutateAsync(conversationId)
    closeActions()
  }

  async function handleDeleteGroup(conversationId: string) {
    await deleteMutation.mutateAsync(conversationId)
    closeActions()
  }

  const actionsPeerMembershipId = actionsConversation
    ? actionsConversation.participants.find((participant) => participant.membership_id !== viewerMembershipId)
        ?.membership_id ?? null
    : null

  async function handleBlockPeer() {
    if (!establishmentId || !actionsPeerMembershipId) {
      return
    }
    await blockMembership(establishmentId, actionsPeerMembershipId)
    closeActions()
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

  return (
    <ChatPageRoot>
      <div className="shrink-0">
        <ChatReconnectBanner status={connectionStatus} />
      </div>

      <TerrainHubSubheader>
        <div className="flex items-center gap-2 px-3 py-2">
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Rechercher une conversation"
            className="h-8 rounded-full border-[#E8E6DF] bg-[#F5F4F0] px-3 text-sm"
          />
          {canCreate ? (
            <button
              type="button"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full outline-none focus-visible:ring-2 focus-visible:ring-[#114660]/30 focus-visible:ring-offset-2"
              aria-label="Nouvelle conversation"
              onClick={() => setCreateOpen(true)}
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
          ) : null}
        </div>
      </TerrainHubSubheader>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain pb-3 pt-3">
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
                onOpenActions={setActionsConversation}
              />
            ))}
          </div>
        ) : null}
      </div>

      <ChatCreateSheet
        establishmentId={establishmentId}
        open={createOpen}
        canCreateDm={statusQuery.data.can_create_dm}
        canCreateGroup={statusQuery.data.can_create_group}
        onClose={() => setCreateOpen(false)}
        onConversationCreated={onOpenConversation}
      />

      <ChatConversationActionsSheet
        conversation={actionsConversation}
        open={actionsConversation !== null}
        isPending={actionsPending}
        onClose={closeActions}
        onPin={(conversationId) => {
          void handlePin(conversationId)
        }}
        onUnpin={(conversationId) => {
          void handleUnpin(conversationId)
        }}
        onHideDm={(conversationId) => {
          void handleHideDm(conversationId)
        }}
        onLeaveGroup={(conversationId) => {
          void handleLeaveGroup(conversationId)
        }}
        onDeleteGroup={(conversationId) => {
          void handleDeleteGroup(conversationId)
        }}
        onBlockPeer={
          actionsConversation?.type === 'dm' && actionsPeerMembershipId
            ? () => {
                void handleBlockPeer()
              }
            : undefined
        }
        onReportPeer={
          actionsConversation?.type === 'dm' && actionsPeerMembershipId
            ? () => {
                setReportPeerId(actionsPeerMembershipId)
                closeActions()
              }
            : undefined
        }
      />
      <SafetyReportSheet
        open={reportPeerId !== null}
        establishmentId={establishmentId}
        contentKind="user"
        targetMembershipId={reportPeerId ?? undefined}
        onClose={() => setReportPeerId(null)}
      />
    </ChatPageRoot>
  )
}
