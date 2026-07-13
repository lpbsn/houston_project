import { Bell } from 'lucide-react'

import { Button } from '@/components/ui/button'

type NotificationBellButtonProps = {
  hasUnread: boolean
  onClick: () => void
}

export function NotificationBellButton({ hasUnread, onClick }: NotificationBellButtonProps) {
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="relative h-10 w-10 min-h-10 min-w-10 shrink-0 rounded-xl"
      aria-label="Notifications"
      onClick={onClick}
    >
      <Bell className="h-5 w-5" />
      {hasUnread ? (
        <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-[#1B4FD8]" />
      ) : null}
    </Button>
  )
}
