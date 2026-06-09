import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type ChecklistAssignmentCreateStickyFooterProps = {
  onClick: () => void
}

export function ChecklistAssignmentCreateStickyFooter({
  onClick,
}: ChecklistAssignmentCreateStickyFooterProps) {
  return (
    <footer
      className={cn(
        'sticky bottom-0 z-10 mt-auto shrink-0',
        'border-t border-[#E8E6DF] bg-[#F5F4F0]',
        'shadow-[0_-4px_12px_rgba(0,0,0,0.04)]',
        'px-3 pt-2.5 pb-[max(0.75rem,env(safe-area-inset-bottom))]',
      )}
    >
      <Button
        type="button"
        className="h-11 w-full rounded-xl bg-[#1B4FD8]"
        onClick={onClick}
      >
        Nouvelle affectation
      </Button>
    </footer>
  )
}
