import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

export function AccessWebLink({ onClick }: { onClick: () => void }) {
  return (
    <div className="border-t border-[#dce8e2] pt-4 text-center">
      <button
        type="button"
        className={cn('text-sm underline underline-offset-4', terrain.success)}
        onClick={onClick}
      >
        Accéder au site web
      </button>
    </div>
  )
}
