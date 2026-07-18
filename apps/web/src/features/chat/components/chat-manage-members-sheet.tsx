import { useMemo, useState } from 'react'
import { LoaderCircle, UserPlus, UserMinus, Shield } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TerrainBottomSheet } from '@/components/ui/terrain'

import {
  invalidateConversationStructureQueries,
  useAddGroupParticipantMutation,
  useEligibleChatMembershipsQuery,
  usePromoteGroupParticipantMutation,
  useRemoveGroupParticipantMutation,
} from '../hooks'
import {
  formatMembershipOpsSummary,
  runSequentialMembershipOps,
  type MembershipOpTarget,
} from '../lib/run-membership-ops'
import type { ChatConversationDetail, ChatParticipantSummary } from '../types'

const PROMOTE_CONFIRM =
  'Promouvoir cette personne administrateur ? Elle pourra gérer les membres et supprimer le groupe pour tous.'

type ChatManageMembersSheetProps = {
  establishmentId: string
  conversation: ChatConversationDetail
  viewerMembershipId: string
  open: boolean
  onClose: () => void
}

type SheetMode = 'members' | 'add'

function establishmentRoleLabel(role: string): string {
  switch (role) {
    case 'owner':
      return 'Owner'
    case 'director':
      return 'Directeur'
    case 'manager':
      return 'Manager'
    case 'staff':
      return 'Staff'
    default:
      return role
  }
}

function participantRoleLabel(role: ChatParticipantSummary['participant_role']): string {
  return role === 'admin' ? 'Administrateur' : 'Membre'
}

export function ChatManageMembersSheet({
  establishmentId,
  conversation,
  viewerMembershipId,
  open,
  onClose,
}: ChatManageMembersSheetProps) {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<SheetMode>('members')
  const [search, setSearch] = useState('')
  const [selectedToAdd, setSelectedToAdd] = useState<string[]>([])
  const [selectedToRemove, setSelectedToRemove] = useState<string[]>([])
  const [isBatchPending, setIsBatchPending] = useState(false)
  const [summary, setSummary] = useState<string | null>(null)

  const eligibleQuery = useEligibleChatMembershipsQuery(establishmentId, search, {
    enabled: open && mode === 'add',
    conversationId: conversation.id,
  })
  const addMutation = useAddGroupParticipantMutation(establishmentId, conversation.id)
  const removeMutation = useRemoveGroupParticipantMutation(establishmentId, conversation.id)
  const promoteMutation = usePromoteGroupParticipantMutation(establishmentId, conversation.id)

  const participants = conversation.participants
  const removableParticipants = useMemo(
    () => participants.filter((participant) => participant.membership_id !== viewerMembershipId),
    [participants, viewerMembershipId],
  )
  const eligibleMemberships = eligibleQuery.data?.items ?? []
  const isPending = isBatchPending || promoteMutation.isPending

  const participantById = useMemo(() => {
    const map = new Map<string, ChatParticipantSummary>()
    for (const participant of participants) {
      map.set(participant.membership_id, participant)
    }
    return map
  }, [participants])

  function resetTransientState() {
    setMode('members')
    setSearch('')
    setSelectedToAdd([])
    setSelectedToRemove([])
    setSummary(null)
    addMutation.reset()
    removeMutation.reset()
    promoteMutation.reset()
  }

  function handleClose() {
    if (isPending) {
      return
    }
    resetTransientState()
    onClose()
  }

  async function refreshConversation() {
    invalidateConversationStructureQueries(queryClient, establishmentId, conversation.id)
  }

  function toggleId(current: string[], membershipId: string): string[] {
    return current.includes(membershipId)
      ? current.filter((id) => id !== membershipId)
      : [...current, membershipId]
  }

  async function handleAddSelected() {
    const targets: MembershipOpTarget[] = selectedToAdd.map((membershipId) => {
      const membership = eligibleMemberships.find((item) => item.membership_id === membershipId)
      return {
        membershipId,
        displayName: membership?.display_name ?? membershipId,
      }
    })
    if (targets.length === 0) {
      return
    }

    setIsBatchPending(true)
    setSummary(null)
    try {
      const result = await runSequentialMembershipOps({
        targets,
        run: (membershipId) => addMutation.mutateAsync(membershipId),
      })
      setSelectedToAdd(result.failures.map((failure) => failure.membershipId))
      setSummary(
        formatMembershipOpsSummary(result, {
          successSingular: 'membre ajouté',
          successPlural: 'membres ajoutés',
        }),
      )
      await refreshConversation()
      if (result.failures.length === 0) {
        setMode('members')
        setSearch('')
      }
    } finally {
      setIsBatchPending(false)
    }
  }

  async function handleRemoveSelected() {
    const targets: MembershipOpTarget[] = selectedToRemove.map((membershipId) => {
      const participant = participantById.get(membershipId)
      return {
        membershipId,
        displayName: participant?.display_name ?? membershipId,
      }
    })
    if (targets.length === 0) {
      return
    }

    setIsBatchPending(true)
    setSummary(null)
    try {
      const result = await runSequentialMembershipOps({
        targets,
        run: (membershipId) => removeMutation.mutateAsync(membershipId),
      })
      setSelectedToRemove(result.failures.map((failure) => failure.membershipId))
      setSummary(
        formatMembershipOpsSummary(result, {
          successSingular: 'membre retiré',
          successPlural: 'membres retirés',
        }),
      )
      await refreshConversation()
    } finally {
      setIsBatchPending(false)
    }
  }

  async function handlePromote(participant: ChatParticipantSummary) {
    if (participant.participant_role === 'admin') {
      return
    }
    if (!window.confirm(PROMOTE_CONFIRM)) {
      return
    }
    setSummary(null)
    try {
      await promoteMutation.mutateAsync(participant.membership_id)
      setSummary(`${participant.display_name} est maintenant administrateur.`)
      await refreshConversation()
    } catch (error) {
      setSummary(error instanceof Error ? error.message : 'Promotion impossible.')
    }
  }

  return (
    <TerrainBottomSheet title="Gérer les membres" open={open} onClose={handleClose}>
      <div className="flex flex-col gap-3">
        {mode === 'members' ? (
          <>
            <ul className="flex max-h-64 flex-col gap-2 overflow-y-auto">
              {participants.map((participant) => {
                const isSelf = participant.membership_id === viewerMembershipId
                const selected = selectedToRemove.includes(participant.membership_id)
                return (
                  <li
                    key={participant.membership_id}
                    className="rounded-2xl border border-[#E8E6DF] bg-white px-3 py-2.5"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-[#1a1a1a]">
                          {participant.display_name}
                          {isSelf ? ' (vous)' : ''}
                        </p>
                        <p className="text-[11px] text-[#7D7B75]">
                          {establishmentRoleLabel(participant.role)} ·{' '}
                          {participantRoleLabel(participant.participant_role)}
                        </p>
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-1">
                        {!isSelf ? (
                          <button
                            type="button"
                            disabled={isPending}
                            className="text-xs font-semibold text-[#1B4FD8] disabled:opacity-60"
                            onClick={() =>
                              setSelectedToRemove((current) =>
                                toggleId(current, participant.membership_id),
                              )
                            }
                          >
                            {selected ? 'Sélectionné' : 'Sélectionner'}
                          </button>
                        ) : null}
                        {!isSelf && participant.participant_role === 'member' ? (
                          <button
                            type="button"
                            disabled={isPending}
                            className="inline-flex items-center gap-1 text-xs font-semibold text-[#1a1a1a] disabled:opacity-60"
                            onClick={() => void handlePromote(participant)}
                          >
                            <Shield className="h-3.5 w-3.5" aria-hidden="true" />
                            Promouvoir
                          </button>
                        ) : null}
                      </div>
                    </div>
                  </li>
                )
              })}
            </ul>

            <div className="flex flex-col gap-2">
              <Button
                type="button"
                variant="outline"
                className="h-11 rounded-2xl"
                disabled={isPending}
                onClick={() => {
                  setMode('add')
                  setSummary(null)
                }}
              >
                <UserPlus className="mr-2 h-4 w-4" aria-hidden="true" />
                Ajouter des membres
              </Button>
              <Button
                type="button"
                className="h-11 rounded-2xl bg-[#1B4FD8] text-white hover:bg-[#1B4FD8]/95"
                disabled={isPending || selectedToRemove.length === 0}
                onClick={() => void handleRemoveSelected()}
              >
                {isBatchPending ? (
                  <LoaderCircle className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <UserMinus className="mr-2 h-4 w-4" aria-hidden="true" />
                )}
                Retirer la sélection
              </Button>
              {removableParticipants.length === 0 ? (
                <p className="text-xs text-[#7D7B75]">
                  Pour quitter le groupe, utilisez l’action « Quitter le groupe ».
                </p>
              ) : null}
            </div>
          </>
        ) : (
          <>
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Rechercher un membre"
              disabled={isPending}
            />
            <ul className="flex max-h-56 flex-col gap-2 overflow-y-auto">
              {eligibleQuery.isLoading ? (
                <li className="flex justify-center py-6 text-[#7D7B75]">
                  <LoaderCircle className="h-5 w-5 animate-spin" />
                </li>
              ) : null}
              {!eligibleQuery.isLoading && eligibleMemberships.length === 0 ? (
                <li className="py-4 text-center text-sm text-[#7D7B75]">
                  Aucun membre éligible.
                </li>
              ) : null}
              {eligibleMemberships.map((membership) => {
                const selected = selectedToAdd.includes(membership.membership_id)
                return (
                  <li key={membership.membership_id}>
                    <button
                      type="button"
                      disabled={isPending}
                      className="flex min-h-11 w-full items-center justify-between rounded-lg border border-[#E8E6DF] bg-white px-3 py-2.5 text-left disabled:opacity-60"
                      onClick={() =>
                        setSelectedToAdd((current) => toggleId(current, membership.membership_id))
                      }
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium text-[#1a1a1a]">
                          {membership.display_name}
                        </span>
                        <span className="text-[11px] uppercase text-[#7D7B75]">
                          {establishmentRoleLabel(membership.role)}
                        </span>
                      </span>
                      {selected ? (
                        <span className="ml-2 text-[11px] font-semibold text-[#1B4FD8]">
                          Sélectionné
                        </span>
                      ) : null}
                    </button>
                  </li>
                )
              })}
            </ul>
            <div className="flex flex-col gap-2">
              <Button
                type="button"
                className="h-11 rounded-2xl bg-[#1B4FD8] text-white hover:bg-[#1B4FD8]/95"
                disabled={isPending || selectedToAdd.length === 0}
                onClick={() => void handleAddSelected()}
              >
                {isBatchPending ? (
                  <LoaderCircle className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                ) : null}
                Ajouter la sélection
              </Button>
              <Button
                type="button"
                variant="outline"
                className="h-11 rounded-2xl"
                disabled={isPending}
                onClick={() => {
                  setMode('members')
                  setSearch('')
                }}
              >
                Retour aux membres
              </Button>
            </div>
          </>
        )}

        {summary ? (
          <p className="text-sm text-[#1a1a1a]" role="status">
            {summary}
          </p>
        ) : null}
      </div>
    </TerrainBottomSheet>
  )
}
