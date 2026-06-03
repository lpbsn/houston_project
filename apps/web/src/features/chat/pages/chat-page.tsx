import { TerrainComingSoonState } from '@/components/layout/terrain-empty-state'

export function ChatPage() {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 bg-[#F5F4F0] px-3 pb-2 pt-2">
        <p className="text-sm text-[#7D7B75]">Messagerie opérationnelle de l&apos;établissement.</p>
      </div>
      <div className="min-h-0 flex-1 pb-4">
        <TerrainComingSoonState
          title="Chat"
          description={
            <>
              Fonctionnalité en préparation. Ce module sera bientôt disponible. Aucune conversation
              ni message n&apos;est affiché pour le moment.
            </>
          }
        />
      </div>
    </div>
  )
}
