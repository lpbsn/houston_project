import { useRef } from 'react'
import { LoaderCircle } from 'lucide-react'

import { TerrainCard, TerrainErrorState, TerrainFieldLabel } from '@/components/ui/terrain'
import { resolveApiErrorMessage } from '@/lib/error-message'

import { CommentsApiError } from '../api'
import {
  useActionCommentsQuery,
  useCreateActionCommentMutation,
  useCreateSignalCommentMutation,
  useSignalCommentsQuery,
} from '../hooks'
import { CommentComposer, type CommentComposerHandle } from './comment-composer'
import { CommentList } from './comment-list'

type CommentSectionProps = {
  establishmentId: string
  targetType: 'signal' | 'action'
  targetId: string
}

export function CommentSection({ establishmentId, targetType, targetId }: CommentSectionProps) {
  const composerRef = useRef<CommentComposerHandle>(null)
  const signalQuery = useSignalCommentsQuery(
    targetType === 'signal' ? establishmentId : null,
    targetType === 'signal' ? targetId : null,
  )
  const actionQuery = useActionCommentsQuery(
    targetType === 'action' ? establishmentId : null,
    targetType === 'action' ? targetId : null,
  )
  const createSignalMutation = useCreateSignalCommentMutation(
    targetType === 'signal' ? establishmentId : null,
    targetType === 'signal' ? targetId : null,
  )
  const createActionMutation = useCreateActionCommentMutation(
    targetType === 'action' ? establishmentId : null,
    targetType === 'action' ? targetId : null,
  )

  const commentsQuery = targetType === 'signal' ? signalQuery : actionQuery
  const createMutation = targetType === 'signal' ? createSignalMutation : createActionMutation

  return (
    <TerrainCard>
      <TerrainFieldLabel>Commentaires</TerrainFieldLabel>

      {commentsQuery.isLoading ? (
        <div className="mt-4 flex items-center justify-center py-6 text-[#7D7B75]">
          <LoaderCircle className="h-5 w-5 animate-spin" aria-label="Chargement des commentaires" />
        </div>
      ) : null}

      {commentsQuery.isError ? (
        <TerrainErrorState
          className="mt-3"
          message={resolveApiErrorMessage(
            commentsQuery.error,
            CommentsApiError,
            'Impossible de charger les commentaires.',
          )}
          onRetry={() => void commentsQuery.refetch()}
        />
      ) : null}

      {commentsQuery.isSuccess ? (
        <CommentList
          comments={commentsQuery.data}
          showOrigin={targetType === 'action'}
        />
      ) : null}

      <CommentComposer
        ref={composerRef}
        establishmentId={establishmentId}
        disabled={createMutation.isPending || commentsQuery.isLoading || commentsQuery.isError}
        errorMessage={
          createMutation.error
            ? resolveApiErrorMessage(
                createMutation.error,
                CommentsApiError,
                'Impossible d’envoyer le commentaire.',
              )
            : null
        }
        onSubmit={({ body, mentionedMembershipIds }) => {
          createMutation.mutate(
            {
              body,
              mentioned_membership_ids: mentionedMembershipIds,
            },
            {
              onSuccess: () => {
                composerRef.current?.reset()
              },
            },
          )
        }}
      />
    </TerrainCard>
  )
}
