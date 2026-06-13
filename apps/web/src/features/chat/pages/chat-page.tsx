import { useMemo, useState } from 'react'
import { LoaderCircle, Plus } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainHubSubheader } from '@/components/layout/terrain-hub-subheader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TerrainEmptyState, TerrainErrorState } from '@/components/ui/terrain'
import { resolveApiErrorMessage } from '@/lib/error-message'

import { ChatApiError } from '../api'
import { ChatCreateSheet } from '../components/chat-create-sheet'
import { ChatReconnectBanner } from '../components/chat-reconnect-banner'
import { ConversationRow } from '../components/conversation-row'
import { useOptionalChatRealtime } from '../components/chat-realtime-provider'
import { filterConversationsByQuery } from '../lib/chat-display'
import { useChatConversationsQuery, useChatStatusQuery } from '../hooks'

type ChatPageProps = {
  onOpenConversation: (conversationId: string) => void
}

export function ChatPage({ onOpenConversation }: ChatPageProps) {
  const auth = useAuth()
  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const viewerMembershipId = auth.bootstrap?.active_membership?.id ?? null
  const [search, setSearch] = useState('')
  const [createOpen, setCreateOpen] = useState(false)

  const statusQuery = useChatStatusQuery(establishmentId)
  const conversationsQuery = useChatConversationsQuery(establishmentId, {
    enabled: Boolean(statusQuery.data?.can_access),
  })
  const realtime = useOptionalChatRealtime()
  const connectionStatus = realtime?.connectionStatus ?? 'idle'

  const filteredConversations = useMemo(() => {
    const items = conversationsQuery.data?.items ?? []
    return filterConversationsByQuery(items, search, viewerMembershipId)
  }, [conversationsQuery.data?.items, search, viewerMembershipId])

  if (!establishmentId) {
    return <p className="px-3 py-4 text-sm text-[#6b5f52]">Établissement non sélectionné.</p>
  }

  if (statusQuery.isLoading) {
    return (
      <div className="flex items-center justify-center py-16 text-[#7D7B75]">
        <LoaderCircle className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  if (statusQuery.isError) {
    return (
      <TerrainErrorState
        className="mx-3 mt-3"
        message={resolveApiErrorMessage(statusQuery.error, ChatApiError, 'Une erreur est survenue.')}
        onRetry={() => void statusQuery.refetch()}
      />
    )
  }

  if (!statusQuery.data?.can_access || !statusQuery.data.chat_enabled) {
    return (
      <TerrainEmptyState
        className="mx-3 mt-6"
        title="Chat indisponible"
        description="Le chat n'est pas activé pour cet établissement ou vous n'y avez pas accès."
      />
    )
  }

  const canCreate = statusQuery.data.can_create_dm || statusQuery.data.can_create_group

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ChatReconnectBanner status={connectionStatus} />

      <TerrainHubSubheader>
        <div className="flex items-center gap-2 px-3 py-2">
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Rechercher une conversation"
            className="h-10 rounded-xl border-[#E8E6DF] bg-[#F5F4F0]"
          />
          {canCreate ? (
            <Button
              type="button"
              size="icon"
              className="h-10 w-10 shrink-0 rounded-xl bg-[#1B4FD8] text-white hover:bg-[#1B4FD8]/95"
              aria-label="Nouvelle conversation"
              onClick={() => setCreateOpen(true)}
            >
              <Plus className="h-5 w-5" />
            </Button>
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

        {conversationsQuery.isSuccess && filteredConversations.length === 0 ? (
          <TerrainEmptyState
            className="mx-3 mt-6"
            title="Aucune conversation"
            description="Démarrez un message direct ou créez un groupe pour commencer."
          />
        ) : null}

        {conversationsQuery.isSuccess && filteredConversations.length > 0 ? (
          <div className="flex flex-col gap-3 px-3">
            {filteredConversations.map((conversation) => (
              <ConversationRow
                key={conversation.id}
                conversation={conversation}
                viewerMembershipId={viewerMembershipId}
                onSelect={onOpenConversation}
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
    </div>
  )
}
