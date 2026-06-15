import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type ChecklistCreateFormHeaderProps = {
  onCancel: () => void
  isPending?: boolean
}

export function ChecklistCreateFormHeader({
  onCancel,
  isPending = false,
}: ChecklistCreateFormHeaderProps) {
  return (
    <header
      className={cn(
        'sticky top-0 z-10 shrink-0 border-b border-[#E8E6DF] bg-[#F5F4F0]',
        'pt-[max(0.75rem,env(safe-area-inset-top))] pb-3',
      )}
    >
      <div className="flex items-center justify-between gap-3 px-4">
        <Button
          type="button"
          variant="ghost"
          className="h-auto min-w-16 px-0 text-left text-sm font-medium text-[#1B4FD8] hover:bg-transparent hover:text-[#1B4FD8]/90"
          disabled={isPending}
          onClick={onCancel}
        >
          Annuler
        </Button>
        <h1 className="text-sm font-semibold text-[#1a1a1a]">Nouvelle liste</h1>
        <span className="min-w-16" aria-hidden />
      </div>
    </header>
  )
}
