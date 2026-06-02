import { Card } from '@/components/ui/card'

type ComingSoonPageProps = {
  featureLabel: string
}

export function ComingSoonPage({ featureLabel }: ComingSoonPageProps) {
  return (
    <Card className="rounded-2xl border-[#E8E6DF] bg-white p-5">
      <h2 className="text-base font-semibold text-[#1a1a1a]">{featureLabel}</h2>
      <p className="mt-2 text-sm text-[#5f574d]">Fonctionnalite bientot disponible.</p>
    </Card>
  )
}
