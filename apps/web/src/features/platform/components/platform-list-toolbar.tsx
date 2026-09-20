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
    <div className="mb-6 flex flex-wrap items-end gap-3">
      <label className="min-w-64 flex-1 text-sm">
        <span className="mb-1 block text-slate-600">Recherche</span>
        <Input
          value={q}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder={placeholder}
        />
      </label>
    </div>
  )
}
