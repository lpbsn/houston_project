export const COMMENT_ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024
export const COMMENT_ATTACHMENTS_MAX_PER_COMMENT = 4
export const COMMENT_ATTACHMENT_ACCEPT =
  'image/jpeg,image/png,image/webp,image/heic,image/heif,application/pdf'

export const COMMENT_ATTACHMENT_ALLOWED_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/heic',
  'image/heif',
  'application/pdf',
])

export const COMMENT_ATTACHMENT_LIMITS_LABEL =
  'JPEG, PNG, WebP, HEIC/HEIF ou PDF · 10 Mo max · 4 fichiers'

export type CommentAttachmentSelectionError =
  | 'too_many'
  | 'too_large'
  | 'unsupported_type'

export function describeCommentAttachmentSelectionError(
  error: CommentAttachmentSelectionError,
): string {
  if (error === 'too_many') {
    return 'Un commentaire accepte au plus 4 fichiers.'
  }
  if (error === 'too_large') {
    return 'Le fichier dépasse la taille maximale de 10 Mo.'
  }
  return 'Ce type de fichier n’est pas supporté.'
}

export function validateCommentAttachmentFile(file: File): CommentAttachmentSelectionError | null {
  const type = (file.type || '').toLowerCase()
  if (type && !COMMENT_ATTACHMENT_ALLOWED_TYPES.has(type)) {
    const name = file.name.toLowerCase()
    const allowedByName =
      name.endsWith('.heic') ||
      name.endsWith('.heif') ||
      name.endsWith('.pdf') ||
      name.endsWith('.jpg') ||
      name.endsWith('.jpeg') ||
      name.endsWith('.png') ||
      name.endsWith('.webp')
    if (!allowedByName) {
      return 'unsupported_type'
    }
  }
  if (file.size > COMMENT_ATTACHMENT_MAX_BYTES) {
    return 'too_large'
  }
  return null
}
