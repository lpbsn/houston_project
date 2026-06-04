import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import { TerrainCard, TerrainFieldLabel, TerrainSectionLabel } from '@/components/ui/terrain'
import { getOperationalTaxonomy, operationalTaxonomyQueryKey } from '@/features/auth/api'

type ActionCreateTaxonomySectionProps = {
  establishmentId: string
  moduleKey: string
  domainKey: string
  subjectKey: string
  onModuleKeyChange: (key: string) => void
  onDomainKeyChange: (key: string) => void
  onSubjectKeyChange: (key: string) => void
}

export function ActionCreateTaxonomySection({
  establishmentId,
  moduleKey,
  domainKey,
  subjectKey,
  onModuleKeyChange,
  onDomainKeyChange,
  onSubjectKeyChange,
}: ActionCreateTaxonomySectionProps) {
  const taxonomyQuery = useQuery({
    queryKey: operationalTaxonomyQueryKey(establishmentId),
    queryFn: () => getOperationalTaxonomy(establishmentId),
    enabled: Boolean(establishmentId),
  })

  const domains = useMemo(() => {
    const modules = taxonomyQuery.data?.modules ?? []
    const mod = modules.find((m) => m.key === moduleKey)
    return mod?.domains ?? []
  }, [moduleKey, taxonomyQuery.data?.modules])

  const subjects = useMemo(() => {
    const domain = domains.find((d) => d.key === domainKey)
    return domain?.subjects ?? []
  }, [domainKey, domains])

  return (
    <section className="flex flex-col gap-1.5">
      <TerrainSectionLabel>Classification</TerrainSectionLabel>
      <TerrainCard className="flex flex-col gap-3">
        <div>
          <TerrainFieldLabel>Module</TerrainFieldLabel>
          <select
            className="mt-1 h-10 w-full rounded-md border border-[#E8E6DF] bg-white px-3 text-sm"
            value={moduleKey}
            onChange={(e) => {
              onModuleKeyChange(e.target.value)
              onDomainKeyChange('')
              onSubjectKeyChange('')
            }}
            required
          >
            <option value="">Choisir…</option>
            {(taxonomyQuery.data?.modules ?? []).map((m) => (
              <option key={m.id} value={m.key}>
                {m.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <TerrainFieldLabel>Domaine</TerrainFieldLabel>
          <select
            className="mt-1 h-10 w-full rounded-md border border-[#E8E6DF] bg-white px-3 text-sm"
            value={domainKey}
            onChange={(e) => {
              onDomainKeyChange(e.target.value)
              onSubjectKeyChange('')
            }}
            required
            disabled={!moduleKey}
          >
            <option value="">Choisir…</option>
            {domains.map((d) => (
              <option key={d.id} value={d.key}>
                {d.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <TerrainFieldLabel>Sujet</TerrainFieldLabel>
          <select
            className="mt-1 h-10 w-full rounded-md border border-[#E8E6DF] bg-white px-3 text-sm"
            value={subjectKey}
            onChange={(e) => onSubjectKeyChange(e.target.value)}
            required
            disabled={!domainKey}
          >
            <option value="">Choisir…</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.key}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </TerrainCard>
    </section>
  )
}
