export function formatCommentRelativeTime(iso: string): string {
  const date = new Date(iso)
  const diffMs = Date.now() - date.getTime()
  const minutes = Math.floor(diffMs / 60000)
  if (minutes < 60) {
    return `il y a ${Math.max(minutes, 1)} min`
  }
  const hours = Math.floor(minutes / 60)
  if (hours < 24) {
    return `il y a ${hours} h`
  }
  const days = Math.floor(hours / 24)
  return `il y a ${days} j`
}

export function getDisplayNameInitials(displayName: string): string {
  const parts = displayName.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) {
    return '?'
  }
  if (parts.length === 1) {
    return parts[0]!.slice(0, 2).toUpperCase()
  }
  return `${parts[0]![0] ?? ''}${parts[1]![0] ?? ''}`.toUpperCase()
}
