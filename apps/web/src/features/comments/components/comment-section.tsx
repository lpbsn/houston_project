import { useRef, useState, type ReactNode } from 'react'
import { LoaderCircle } from 'lucide-react'

import { TerrainCard, TerrainErrorState, TerrainFieldLabel } from '@/components/ui/terrain'
import { resolveApiErrorMessage } from '@/lib/error-message'
import { terrainCardClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { CommentsApiError } from '../api'
import {
  commentExistsInExecutionList,
  commentExistsInSignalList,
} from '../lib/comment-highlight'
import {
  useCreateExecutionCommentMutation,
  useCreateSignalCommentMutation,
  useExecutionCommentsQuery,
  useResolveExecutionCommentMutation,
  useSignalCommentsQuery,
  useUnresolveExecutionCommentMutation,
} from '../hooks'
import { CommentComposer, type CommentComposerHandle } from './comment-composer'
import { CommentList } from './comment-list'

type CommentSectionProps = {
  establishmentId: string
  targetType: 'signal' | 'action-plan-execution'
  targetId: string
  highlightCommentId?: string | null
  readOnly?: boolean
}

function CommentUnavailableMessage() {
  return (
    <p
      className="mt-3 rounded-[12px] border border-[#E8E6DF] bg-[#FAFAF8] px-3 py-3 text-[13px] text-[#65676B]"
      role="status"
    >
      Ce commentaire n&apos;est plus disponible.
    </p>
  )
}

function OperationalCommentsLayout({
  list,
  composer,
}: {
  list: ReactNode
  composer: ReactNode
}) {
  return (
    <div
      data-testid="comment-section"
      className="flex min-h-0 flex-1 flex-col gap-2.5 lg:gap-4"
    >
      <TerrainCard className="flex min-h-0 flex-1 flex-col lg:contents">
        <div
          className={cn(
            'flex min-h-0 flex-1 flex-col lg:min-h-[min(28rem,55vh)]',
            terrainCardClassName(
              'p-4 max-lg:rounded-none max-lg:border-0 max-lg:bg-transparent max-lg:p-0',
            ),
          )}
        >
          {list}
        </div>
        {composer ? (
          <div
            className={cn(
              'shrink-0',
              terrainCardClassName(
                'p-4 max-lg:rounded-none max-lg:border-0 max-lg:bg-transparent max-lg:p-0',
              ),
            )}
          >
            {composer}
          </div>
        ) : null}
      </TerrainCard>
    </div>
  )
}

export function CommentSection({
  establishmentId,
  targetType,
  targetId,
  highlightCommentId = null,
  readOnly = false,
}: CommentSectionProps) {
  const composerRef = useRef<CommentComposerHandle>(null)
  const [replyErrorCommentId, setReplyErrorCommentId] = useState<string | null>(null)
  const [pendingReplyCommentId, setPendingReplyCommentId] = useState<string | null>(null)

  const isSignal = targetType === 'signal'
  const isExecution = targetType === 'action-plan-execution'

  const signalQuery = useSignalCommentsQuery(
    isSignal ? establishmentId : null,
    isSignal ? targetId : null,
  )
  const executionQuery = useExecutionCommentsQuery(
    isExecution ? establishmentId : null,
    isExecution ? targetId : null,
  )
  const createSignalMutation = useCreateSignalCommentMutation(
    isSignal ? establishmentId : null,
    isSignal ? targetId : null,
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

  const commentsQuery = isSignal ? signalQuery : executionQuery
  const createMutation = isSignal ? createSignalMutation : createExecutionRootMutation
  const isThreadPending = isExecution
    ? createExecutionRootMutation.isPending ||
      createExecutionReplyMutation.isPending ||
      resolveExecutionMutation.isPending ||
      unresolveExecutionMutation.isPending
    : false

  const isHighlightMissing =
    highlightCommentId != null &&
    commentsQuery.isSuccess &&
    (isSignal
      ? !commentExistsInSignalList(signalQuery.data, highlightCommentId)
      : !commentExistsInExecutionList(executionQuery.data, highlightCommentId))

  const threadListProps = {
    establishmentId,
    disabled: isThreadPending || commentsQuery.isLoading || commentsQuery.isError,
    replyErrorCommentId,
    pendingReplyCommentId,
    highlightCommentId,
  }

  const list = (
    <>
      <TerrainFieldLabel className="lg:hidden">Commentaires</TerrainFieldLabel>

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

      {isHighlightMissing ? <CommentUnavailableMessage /> : null}

      {commentsQuery.isSuccess && isSignal ? (
        <CommentList
          mode="signal"
          comments={commentsQuery.data}
          highlightCommentId={highlightCommentId}
        />
      ) : null}

      {executionQuery.isSuccess && isExecution ? (
        <CommentList
          mode="execution"
          comments={executionQuery.data}
          {...threadListProps}
          disabled={readOnly || threadListProps.disabled}
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
            if (readOnly) {
              return
            }
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
            if (readOnly) {
              return
            }
            resolveExecutionMutation.mutate(commentId)
          }}
          onUnresolve={(commentId) => {
            if (readOnly) {
              return
            }
            unresolveExecutionMutation.mutate(commentId)
          }}
        />
      ) : null}
    </>
  )

  const composer = readOnly ? null : (
    <CommentComposer
      ref={composerRef}
      establishmentId={establishmentId}
      compactOnLg
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
  )

  return <OperationalCommentsLayout list={list} composer={composer} />
}
