import { useMemo } from 'react'
import { LoaderCircle, Pin, PinOff, LogOut, Trash2 } from 'lucide-react'

import { TerrainBottomSheet } from '@/components/ui/terrain'

import type { ChatConversationListItem } from '../types'

const HIDE_DM_CONFIRM =
  'Supprimer cette conversation pour vous ? L’historique actuel ne sera plus visible. La conversation réapparaîtra si un nouveau message est reçu ou si vous la relancez.'

const LEAVE_GROUP_CONFIRM =
  'Quitter ce groupe ? Vous n’aurez plus accès à ses messages. Un administrateur pourra vous ajouter de nouveau.'

const DELETE_GROUP_CONFIRM =
  'Supprimer définitivement ce groupe ? Tous les participants perdront immédiatement l’accès. Cette action est irréversible.'

type ChatConversationActionsSheetProps = {
  conversation: ChatConversationListItem | null
  open: boolean
  isPending: boolean
  onClose: () => void
  onPin: (conversationId: string) => void
  onUnpin: (conversationId: string) => void
  onHideDm: (conversationId: string) => void
  onLeaveGroup: (conversationId: string) => void
  onDeleteGroup: (conversationId: string) => void
}

export function ChatConversationActionsSheet({
  conversation,
  open,
  isPending,
  onClose,
  onPin,
  onUnpin,
  onHideDm,
  onLeaveGroup,
  onDeleteGroup,
}: ChatConversationActionsSheetProps) {
  const title = useMemo(() => {
    if (!conversation) {
      return 'Actions'
    }
    return conversation.type === 'group' ? 'Actions du groupe' : 'Actions de la conversation'
  }, [conversation])

  if (!conversation) {
    return (
      <TerrainBottomSheet title={title} open={open} onClose={onClose}>
        {null}
      </TerrainBottomSheet>
    )
  }

  const isGroup = conversation.type === 'group'

  function runConfirmed(message: string, action: () => void) {
    if (!window.confirm(message)) {
      return
    }
    action()
  }

  return (
    <TerrainBottomSheet title={title} open={open} onClose={onClose}>
      <ul className="flex flex-col gap-2">
        <li>
          <button
            type="button"
            disabled={isPending}
            className="flex w-full items-center gap-3 rounded-2xl border border-[#E8E6DF] bg-white px-4 py-3 text-left text-sm font-medium text-[#1a1a1a] disabled:opacity-60"
            onClick={() => {
              if (conversation.pinned) {
                onUnpin(conversation.id)
              } else {
                onPin(conversation.id)
              }
            }}
          >
            {conversation.pinned ? (
              <PinOff className="h-4 w-4 shrink-0 text-[#7D7B75]" strokeWidth={2.25} />
            ) : (
              <Pin className="h-4 w-4 shrink-0 text-[#7D7B75]" strokeWidth={2.25} />
            )}
            <span>{conversation.pinned ? 'Désépingler' : 'Épingler'}</span>
          </button>
        </li>

        {!isGroup ? (
          <li>
            <button
              type="button"
              disabled={isPending}
              className="flex w-full items-center gap-3 rounded-2xl border border-[#E8E6DF] bg-white px-4 py-3 text-left text-sm font-medium text-[#B42318] disabled:opacity-60"
              onClick={() =>
                runConfirmed(HIDE_DM_CONFIRM, () => {
                  onHideDm(conversation.id)
                })
              }
            >
              <Trash2 className="h-4 w-4 shrink-0" strokeWidth={2.25} />
              <span>Supprimer la conversation</span>
            </button>
          </li>
        ) : null}

        {isGroup ? (
          <li>
            <button
              type="button"
              disabled={isPending}
              className="flex w-full items-center gap-3 rounded-2xl border border-[#E8E6DF] bg-white px-4 py-3 text-left text-sm font-medium text-[#B42318] disabled:opacity-60"
              onClick={() =>
                runConfirmed(LEAVE_GROUP_CONFIRM, () => {
                  onLeaveGroup(conversation.id)
                })
              }
            >
              <LogOut className="h-4 w-4 shrink-0" strokeWidth={2.25} />
              <span>Quitter le groupe</span>
            </button>
          </li>
        ) : null}

        {isGroup && conversation.can_delete ? (
          <li>
            <button
              type="button"
              disabled={isPending}
              className="flex w-full items-center gap-3 rounded-2xl border border-[#E8E6DF] bg-white px-4 py-3 text-left text-sm font-medium text-[#B42318] disabled:opacity-60"
              onClick={() =>
                runConfirmed(DELETE_GROUP_CONFIRM, () => {
                  onDeleteGroup(conversation.id)
                })
              }
            >
              <Trash2 className="h-4 w-4 shrink-0" strokeWidth={2.25} />
              <span>Supprimer le groupe</span>
            </button>
          </li>
        ) : null}
      </ul>

      {isPending ? (
        <div className="mt-4 flex items-center justify-center text-[#7D7B75]">
          <LoaderCircle className="h-5 w-5 animate-spin" />
        </div>
      ) : null}
    </TerrainBottomSheet>
  )
}
