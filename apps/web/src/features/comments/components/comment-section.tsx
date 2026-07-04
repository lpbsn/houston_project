import { useRef, useState } from 'react'
import { LoaderCircle } from 'lucide-react'

import { TerrainCard, TerrainErrorState, TerrainFieldLabel } from '@/components/ui/terrain'
import { resolveApiErrorMessage } from '@/lib/error-message'

import { CommentsApiError } from '../api'
import {
  useActionCommentsQuery,
  useCreateActionCommentMutation,
  useCreateExecutionCommentMutation,
  useCreateSignalCommentMutation,
  useExecutionCommentsQuery,
  useResolveActionCommentMutation,
  useResolveExecutionCommentMutation,
  useSignalCommentsQuery,
  useUnresolveActionCommentMutation,
  useUnresolveExecutionCommentMutation,
} from '../hooks'
import { CommentComposer, type CommentComposerHandle } from './comment-composer'
import { CommentList } from './comment-list'

type CommentSectionProps = {
  establishmentId: string
  targetType: 'signal' | 'action' | 'action-plan-execution'
  targetId: string
}

export function CommentSection({ establishmentId, targetType, targetId }: CommentSectionProps) {
  const composerRef = useRef<CommentComposerHandle>(null)
  const [replyErrorCommentId, setReplyErrorCommentId] = useState<string | null>(null)
  const [pendingReplyCommentId, setPendingReplyCommentId] = useState<string | null>(null)

  const isSignal = targetType === 'signal'
  const isAction = targetType === 'action'
  const isExecution = targetType === 'action-plan-execution'

  const signalQuery = useSignalCommentsQuery(
    isSignal ? establishmentId : null,
    isSignal ? targetId : null,
  )
  const actionQuery = useActionCommentsQuery(
    isAction ? establishmentId : null,
    isAction ? targetId : null,
  )
  const executionQuery = useExecutionCommentsQuery(
    isExecution ? establishmentId : null,
    isExecution ? targetId : null,
  )
  const createSignalMutation = useCreateSignalCommentMutation(
    isSignal ? establishmentId : null,
    isSignal ? targetId : null,
  )
  const createRootCommentMutation = useCreateActionCommentMutation(
    isAction ? establishmentId : null,
    isAction ? targetId : null,
  )
  const createReplyMutation = useCreateActionCommentMutation(
    isAction ? establishmentId : null,
    isAction ? targetId : null,
  )
  const resolveMutation = useResolveActionCommentMutation(
    isAction ? establishmentId : null,
    isAction ? targetId : null,
  )
  const unresolveMutation = useUnresolveActionCommentMutation(
    isAction ? establishmentId : null,
    isAction ? targetId : null,
  )
  const createExecutionRootMutation = useCreateExecutionCommentMutation(
    isExecution ? establishmentId : null,
    isExecution ? targetId : null,
  )
  const createExecutionReplyMutation = useCreateExecutionCommentMutation(
    isExecution ? establishmentId : null,
    isExecution ? targetId : null,
  )
  const resolveExecutionMutation = useResolveExecutionCommentMutation(
    isExecution ? establishmentId : null,
    isExecution ? targetId : null,
  )
  const unresolveExecutionMutation = useUnresolveExecutionCommentMutation(
    isExecution ? establishmentId : null,
    isExecution ? targetId : null,
  )

  const commentsQuery = isSignal ? signalQuery : isAction ? actionQuery : executionQuery
  const createMutation = isSignal
    ? createSignalMutation
    : isAction
      ? createRootCommentMutation
      : createExecutionRootMutation
  const isThreadPending = isAction
    ? createRootCommentMutation.isPending ||
      createReplyMutation.isPending ||
      resolveMutation.isPending ||
      unresolveMutation.isPending
    : isExecution
      ? createExecutionRootMutation.isPending ||
        createExecutionReplyMutation.isPending ||
        resolveExecutionMutation.isPending ||
        unresolveExecutionMutation.isPending
      : false

  const threadListProps = {
    establishmentId,
    disabled: isThreadPending || commentsQuery.isLoading || commentsQuery.isError,
    replyErrorCommentId,
    pendingReplyCommentId,
  }

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

      {commentsQuery.isSuccess && isSignal ? (
        <CommentList mode="signal" comments={commentsQuery.data} />
      ) : null}

      {actionQuery.isSuccess && isAction ? (
        <CommentList
          mode="action"
          comments={actionQuery.data}
          {...threadListProps}
          replyErrorMessage={
            replyErrorCommentId && createReplyMutation.error
              ? resolveApiErrorMessage(
                  createReplyMutation.error,
                  CommentsApiError,
                  'Impossible d’envoyer la réponse.',
                )
              : null
          }
          isResolvePending={resolveMutation.isPending || unresolveMutation.isPending}
          onReply={(payload, callbacks) => {
            const parentCommentId = payload.parent_comment_id ?? null
            setPendingReplyCommentId(parentCommentId)
            setReplyErrorCommentId(parentCommentId)
            createReplyMutation.mutate(payload, {
              onSuccess: () => {
                setPendingReplyCommentId(null)
                setReplyErrorCommentId(null)
                callbacks?.onSuccess?.()
              },
              onError: () => {
                setPendingReplyCommentId(null)
              },
            })
          }}
          onResolve={(commentId) => {
            resolveMutation.mutate(commentId)
          }}
          onUnresolve={(commentId) => {
            unresolveMutation.mutate(commentId)
          }}
        />
      ) : null}

      {executionQuery.isSuccess && isExecution ? (
        <CommentList
          mode="execution"
          comments={executionQuery.data}
          {...threadListProps}
          replyErrorMessage={
            replyErrorCommentId && createExecutionReplyMutation.error
              ? resolveApiErrorMessage(
                  createExecutionReplyMutation.error,
                  CommentsApiError,
                  'Impossible d’envoyer la réponse.',
                )
              : null
          }
          isResolvePending={
            resolveExecutionMutation.isPending || unresolveExecutionMutation.isPending
          }
          onReply={(payload, callbacks) => {
            const parentCommentId = payload.parent_comment_id ?? null
            setPendingReplyCommentId(parentCommentId)
            setReplyErrorCommentId(parentCommentId)
            createExecutionReplyMutation.mutate(payload, {
              onSuccess: () => {
                setPendingReplyCommentId(null)
                setReplyErrorCommentId(null)
                callbacks?.onSuccess?.()
              },
              onError: () => {
                setPendingReplyCommentId(null)
              },
            })
          }}
          onResolve={(commentId) => {
            resolveExecutionMutation.mutate(commentId)
          }}
          onUnresolve={(commentId) => {
            unresolveExecutionMutation.mutate(commentId)
          }}
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
