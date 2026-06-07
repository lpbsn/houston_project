import { LoaderCircle, Plus, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { CatalogBusinessUnitSuggestion } from '@/features/onboarding/types'
import { useBusinessUnitSuggestions } from '@/features/onboarding/hooks'

type BusinessUnitAutocompleteProps = {
  disabled?: boolean
  onAddFreeText: (label: string) => void
  onSelectSuggestion: (suggestion: CatalogBusinessUnitSuggestion) => void
}

export function BusinessUnitAutocomplete({
  disabled = false,
  onAddFreeText,
  onSelectSuggestion,
}: BusinessUnitAutocompleteProps) {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setDebouncedQuery(query.trim())
    }, 250)

    return () => {
      window.clearTimeout(timeout)
    }
  }, [query])

  const suggestionsQuery = useBusinessUnitSuggestions(debouncedQuery, {
    enabled: debouncedQuery.length >= 2,
  })

  const suggestions = useMemo(
    () => suggestionsQuery.data ?? [],
    [suggestionsQuery.data],
  )

  const trimmedQuery = query.trim()

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          disabled={disabled}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Rechercher un pôle dans le catalogue…"
          className="h-11 rounded-[1rem] border-[#e7dfd1] bg-white pl-10"
        />
      </div>

      {suggestionsQuery.isFetching ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <LoaderCircle className="size-4 animate-spin" />
          Recherche en cours…
        </div>
      ) : null}

      {debouncedQuery.length >= 2 && suggestions.length > 0 ? (
        <ul className="space-y-2">
          {suggestions.map((suggestion) => (
            <li key={suggestion.key}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => {
                  onSelectSuggestion(suggestion)
                  setQuery('')
                  setDebouncedQuery('')
                }}
                className="flex w-full items-center justify-between rounded-[1rem] border border-[#ece5da] bg-white px-4 py-3 text-left transition hover:border-[color:var(--primary)]"
              >
                <span>
                  <span className="block font-medium">{suggestion.label}</span>
                  <span className="text-xs text-muted-foreground">{suggestion.key}</span>
                </span>
                <Plus className="size-4 text-[color:var(--primary)]" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {trimmedQuery.length > 0 ? (
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          onClick={() => {
            onAddFreeText(trimmedQuery)
            setQuery('')
            setDebouncedQuery('')
          }}
          className="h-11 w-full rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
        >
          <Plus className="size-4" />
          Ajouter « {trimmedQuery} » comme pôle libre
        </Button>
      ) : null}
    </div>
  )
}
