import { TerrainComingSoonState } from '@/components/layout/terrain-empty-state'

export function ExecutionFeedPage() {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 bg-[#F5F4F0] px-3 pb-2 pt-2">
        <p className="text-sm text-[#7D7B75]">
          Suivi des plans d&apos;exécution et des tâches terrain.
        </p>
      </div>
      <div className="min-h-0 flex-1 pb-4">
        <TerrainComingSoonState
          title="Exécution"
          description={
            <>
              Fonctionnalité en préparation. Ce module sera bientôt disponible. Aucun plan
              d&apos;exécution ni checklist n&apos;est disponible pour le moment.
            </>
          }
        />
      </div>
    </div>
  )
}
