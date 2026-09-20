export const CHAT_MESSAGE_BODY_MAX_LENGTH = 2000
export const CHAT_MESSAGE_RETENTION_DAYS = 30
export const CHAT_UPLOAD_TTL_MS = 24 * 60 * 60 * 1000
export const CHAT_ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024
export const CHAT_ATTACHMENTS_MAX_PER_MESSAGE = 4

export const CHAT_ALLOWED_ATTACHMENT_TYPES = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/heic',
  'image/heif',
  'application/pdf',
] as const

export function formatChatRetentionNotice(
  days: number = CHAT_MESSAGE_RETENTION_DAYS,
): string {
  return `Les messages de plus de ${days} jours sont automatiquement supprimés.`
}

export function isAllowedChatAttachmentType(contentType: string): boolean {
  return (CHAT_ALLOWED_ATTACHMENT_TYPES as readonly string[]).includes(contentType)
}
