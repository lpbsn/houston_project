import { X } from 'lucide-react'

import { Input } from '@/components/ui/input'

type PlatformListToolbarProps = {
  q: string
  onQueryChange: (value: string) => void
  placeholder: string
}

export function PlatformListToolbar({
  q,
  onQueryChange,
  placeholder,
}: PlatformListToolbarProps) {
  return (
    <div className="mb-6 max-w-md">
      <label className="block text-sm">
        <span className="mb-1 block text-[var(--platform-muted)]">Recherche</span>
        <span className="relative block">
          <Input
            value={q}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder={placeholder}
            className="h-10 pr-10"
          />
          {q ? (
            <button
              type="button"
              className="absolute inset-y-0 right-1 inline-flex items-center justify-center rounded-md px-2 text-[var(--platform-muted)] hover:text-[var(--platform-text)]"
              aria-label="Effacer la recherche"
              onClick={() => onQueryChange('')}
            >
              <X className="size-4" aria-hidden />
            </button>
          ) : null}
        </span>
      </label>
    </div>
  )
}
