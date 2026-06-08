import { Button } from '@/components/ui/button'
import { TerrainEmptyState } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

type NotFoundPageProps = {
  fallbackPath: string
  backLabel: string
  onNavigate: (pathname: string) => void
  className?: string
}

export function NotFoundPage({
  fallbackPath,
  backLabel,
  onNavigate,
  className,
}: NotFoundPageProps) {
  return (
    <div className={cn('flex flex-col gap-4', className)}>
      <TerrainEmptyState
        title="Page introuvable"
        description="Cette adresse ne correspond à aucune page Houston."
      />
      <Button
        type="button"
        variant="outline"
        className="w-fit rounded-xl border-[#E8E6DF]"
        onClick={() => onNavigate(fallbackPath)}
      >
        {backLabel}
      </Button>
    </div>
  )
}
