import { useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TerrainBottomSheet } from '@/components/ui/terrain'

import { useCreateDmMutation, useCreateGroupMutation, useEligibleChatMembershipsQuery } from '../hooks'
import type { ChatEligibleMembership } from '../types'

type ChatCreateSheetProps = {
  establishmentId: string
  open: boolean
  canCreateDm: boolean
  canCreateGroup: boolean
  onClose: () => void
  onConversationCreated: (conversationId: string) => void
}

type CreateMode = 'menu' | 'dm' | 'group'

export function ChatCreateSheet({
  establishmentId,
  open,
  canCreateDm,
  canCreateGroup,
  onClose,
  onConversationCreated,
}: ChatCreateSheetProps) {
  const [mode, setMode] = useState<CreateMode>('menu')
  const [search, setSearch] = useState('')
  const [groupTitle, setGroupTitle] = useState('')
  const [selectedMembershipIds, setSelectedMembershipIds] = useState<string[]>([])

  const eligibleQuery = useEligibleChatMembershipsQuery(establishmentId, search, {
    enabled: open && (mode === 'dm' || mode === 'group'),
  })
  const createDmMutation = useCreateDmMutation(establishmentId)
  const createGroupMutation = useCreateGroupMutation(establishmentId)

  const memberships = eligibleQuery.data?.items ?? []
  const isSubmitting = createDmMutation.isPending || createGroupMutation.isPending
  const errorMessage =
    (createDmMutation.error instanceof Error ? createDmMutation.error.message : null) ||
    (createGroupMutation.error instanceof Error ? createGroupMutation.error.message : null)

  const sheetTitle = useMemo(() => {
    if (mode === 'dm') {
      return 'Nouveau message direct'
    }
    if (mode === 'group') {
      return 'Nouveau groupe'
    }
    return 'Nouvelle conversation'
  }, [mode])

  function resetState() {
    setMode('menu')
    setSearch('')
    setGroupTitle('')
    setSelectedMembershipIds([])
    createDmMutation.reset()
    createGroupMutation.reset()
  }

  function handleClose() {
    resetState()
    onClose()
  }

  function toggleMembership(membership: ChatEligibleMembership) {
    setSelectedMembershipIds((current) =>
      current.includes(membership.membership_id)
        ? current.filter((id) => id !== membership.membership_id)
        : [...current, membership.membership_id],
    )
  }

  async function handleCreateDm(membershipId: string) {
    const response = await createDmMutation.mutateAsync(membershipId)
    onConversationCreated(response.conversation.id)
    handleClose()
  }

  async function handleCreateGroup() {
    const response = await createGroupMutation.mutateAsync({
      title: groupTitle.trim(),
      membershipIds: selectedMembershipIds,
    })
    onConversationCreated(response.conversation.id)
    handleClose()
  }

  return (
    <TerrainBottomSheet title={sheetTitle} open={open} onClose={handleClose}>
      {mode === 'menu' ? (
        <ul className="flex flex-col gap-2">
          {canCreateDm ? (
            <li>
              <button
                type="button"
                className="flex min-h-11 w-full items-center rounded-lg border border-[#E8E6DF] bg-[#F5F4F0] px-3 py-2.5 text-left text-sm font-medium text-[#1a1a1a]"
                onClick={() => setMode('dm')}
              >
                Message direct
              </button>
            </li>
          ) : null}
          {canCreateGroup ? (
            <li>
              <button
                type="button"
                className="flex min-h-11 w-full items-center rounded-lg border border-[#E8E6DF] bg-[#F5F4F0] px-3 py-2.5 text-left text-sm font-medium text-[#1a1a1a]"
                onClick={() => setMode('group')}
              >
                Groupe
              </button>
            </li>
          ) : null}
        </ul>
      ) : null}

      {mode === 'dm' || mode === 'group' ? (
        <div className="flex flex-col gap-3">
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Rechercher un membre"
          />

          {mode === 'group' ? (
            <Input
              value={groupTitle}
              onChange={(event) => setGroupTitle(event.target.value)}
              placeholder="Nom du groupe"
            />
          ) : null}

          <ul className="flex max-h-56 flex-col gap-2 overflow-y-auto">
            {memberships.map((membership) => {
              const selected = selectedMembershipIds.includes(membership.membership_id)
              return (
                <li key={membership.membership_id}>
                  <button
                    type="button"
                    className="flex min-h-11 w-full items-center justify-between rounded-lg border border-[#E8E6DF] bg-white px-3 py-2.5 text-left"
                    onClick={() => {
                      if (mode === 'dm') {
                        void handleCreateDm(membership.membership_id)
                        return
                      }
                      toggleMembership(membership)
                    }}
                    disabled={isSubmitting}
                  >
                    <span className="text-sm font-medium text-[#1a1a1a]">
                      {membership.display_name}
                    </span>
                    <span className="text-[11px] uppercase text-[#7D7B75]">{membership.role}</span>
                    {mode === 'group' && selected ? (
                      <span className="ml-2 text-[11px] font-semibold text-[#1B4FD8]">Sélectionné</span>
                    ) : null}
                  </button>
                </li>
              )
            })}
          </ul>

          {mode === 'group' ? (
            <Button
              type="button"
              className="h-11 rounded-2xl bg-[#1B4FD8] text-white hover:bg-[#1B4FD8]/95"
              disabled={
                isSubmitting ||
                !groupTitle.trim() ||
                selectedMembershipIds.length === 0
              }
              onClick={() => void handleCreateGroup()}
            >
              Créer le groupe
            </Button>
          ) : null}

          {errorMessage ? (
            <p className="text-sm text-destructive" role="alert">
              {errorMessage}
            </p>
          ) : null}
        </div>
      ) : null}
    </TerrainBottomSheet>
  )
}
