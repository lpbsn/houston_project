import { TerrainFilterSlot } from '@/components/ui/terrain'

/**
 * Visual placeholders for future Signal Feed filters.
 * UI labels: « État » (maps to status), « Catégorie » (maps to operational subject / subject_key).
 * Disabled until signal-feed API exposes status/subject query params.
 */
export function SignalFeedFiltersPlaceholder() {
  return (
    <div
      className="flex shrink-0 gap-2 border-t border-[#E8E6DF] bg-white px-3 py-2 pb-3"
      aria-label="Filtres des signaux"
    >
      <div className="flex flex-1 pointer-events-none" data-filter-kind="status">
        <TerrainFilterSlot label="État" value="Tous ▾" disabled />
      </div>
      <div className="flex flex-1 pointer-events-none" data-filter-kind="subject">
        <TerrainFilterSlot label="Catégorie" value="Tous ▾" disabled />
      </div>
    </div>
  )
}
