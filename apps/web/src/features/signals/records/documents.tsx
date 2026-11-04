import { useInfiniteQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { FileText, MessageSquare } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { CommentAttachmentTiles } from '@/features/comments/components/comment-attachment-tiles'
import { CommentAttachmentPreviewDialog } from '@/features/comments/components/comment-attachment-preview-dialog'
import { isCommentPdfAttachment } from '@/features/comments/lib/comment-media'
import {
  commentPdfAlertMessage,
  openCommentPdfAttachment,
} from '@/features/comments/lib/comment-pdf'
import { buildCommentDeepLinkPath } from '@/features/comments/lib/detail-deep-link'
import type { CommentAttachment } from '@/features/comments/types'
import { listRecordDocuments, recordKeys, type FieldRecord } from './api'
import { ErrorNote, inputClass } from './shared'

export function RecordDocuments({
  site,
  record,
  onNavigate,
  onWork,
}: {
  site: string
  record: FieldRecord
  onNavigate: (path: string) => void
  onWork: () => void
}) {
  const [search, setSearch] = useState('')
  const [preview, setPreview] = useState<CommentAttachment | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const query = useInfiniteQuery({
    queryKey: [...recordKeys.detail(site, record.id), 'documents', search],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      listRecordDocuments(site, record.id, pageParam, search),
    getNextPageParam: (page) => page.next_offset ?? undefined,
  })
  const rows = query.data?.pages.flatMap((page) => page.items) ?? []
  const open = (attachment: CommentAttachment) => {
    setError(null)
    if (
      isCommentPdfAttachment({
        kind: attachment.kind,
        contentType: attachment.content_type,
      })
    ) {
      void openCommentPdfAttachment({
        src: attachment.preview_url,
        filename: attachment.original_filename,
        id: attachment.id,
      })
        .then((result) => {
          if (!result.ok)
            setError(
              new Error(
                commentPdfAlertMessage(result.reason) ??
                  'Impossible d’ouvrir ce document. Actualisez puis réessayez.',
              ),
            )
        })
        .catch(() =>
          setError(
            new Error(
              'Impossible d’ouvrir ce document. Actualisez puis réessayez.',
            ),
          ),
        )
    } else setPreview(attachment)
  }
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 font-semibold">
            <FileText size={18} /> Documents des plans
          </h2>
          <p className="mt-1 max-w-xl text-sm leading-relaxed text-[#45564A]">
            Les photos et PDF partagés dans les plans rattachés, avec leur
            discussion d’origine. Les règles de conservation restent celles des
            plans.
          </p>
        </div>
        <Button variant="outline" onClick={onWork}>
          Partager dans un plan
        </Button>
      </div>
      <input
        className={`${inputClass} max-w-sm`}
        aria-label="Rechercher un document"
        placeholder="Nom du document…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <ErrorNote error={error ?? query.error} />
      {query.isPending && <p role="status">Chargement des documents…</p>}
      <div className="grid gap-3 sm:grid-cols-2">
        {rows.map((file) => (
          <article
            key={file.id}
            className="rounded-xl border border-[#DADFD8] bg-white p-4 text-[#17251F]"
          >
            <CommentAttachmentTiles attachments={[file]} onOpen={open} />
            <p className="mt-3 text-xs text-[#45564A]">
              {file.author_display_name} ·{' '}
              {new Date(file.created_at).toLocaleDateString('fr-FR')}
            </p>
            <button
              className="mt-2 flex items-start gap-2 text-left text-sm font-medium text-[#075940] underline underline-offset-2"
              onClick={() =>
                onNavigate(
                  buildCommentDeepLinkPath(
                    `/e/${site}/execution/${file.execution_id}`,
                    file.comment_id,
                  ),
                )
              }
            >
              <MessageSquare size={15} className="mt-0.5 shrink-0" />
              {file.execution_title} · voir le message
            </button>
          </article>
        ))}
      </div>
      {!rows.length && !query.isPending && !query.isError && (
        <p className="rounded-xl border border-dashed border-[#BCCDBD] p-5 text-sm text-[#45564A]">
          {search
            ? 'Aucun document ne correspond à cette recherche.'
            : 'Aucun document disponible. Ouvrez la discussion d’un plan dans Travail pour joindre une photo ou un PDF.'}
        </p>
      )}
      {query.hasNextPage && (
        <Button
          variant="outline"
          disabled={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          Afficher la suite
        </Button>
      )}
      <CommentAttachmentPreviewDialog
        attachment={preview}
        onClose={() => setPreview(null)}
      />
    </div>
  )
}
