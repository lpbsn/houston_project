import { TerrainEmptyState } from '@/components/ui/terrain'

type ComingSoonPageProps = {
  title: string
  description?: string
}

export function ComingSoonPage({
  title,
  description = 'Cette fonctionnalité sera bientôt disponible.',
}: ComingSoonPageProps) {
  return (
    <div className="px-4 py-8 lg:px-8">
      <TerrainEmptyState title={title} description={description} />
    </div>
  )
}
