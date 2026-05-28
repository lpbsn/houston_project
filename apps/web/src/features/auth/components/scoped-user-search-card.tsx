import { LoaderCircle, Search, UsersRound } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { ScopedUserSearchResult } from '@/features/auth/types'

type ScopedUserSearchCardProps = {
  errorMessage: string | null
  hint: string
  isSearching: boolean
  query: string
  results: ScopedUserSearchResult[]
  onQueryChange: (value: string) => void
}

export function ScopedUserSearchCard({
  errorMessage,
  hint,
  isSearching,
  query,
  results,
  onQueryChange,
}: ScopedUserSearchCardProps) {
  const hasRunnableQuery = query.trim().length >= 2

  return (
    <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
      <CardHeader className="gap-3">
        <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
          User search
        </Badge>
        <div className="space-y-2">
          <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
            Scoped people lookup
          </CardTitle>
          <CardDescription className="text-sm leading-6">
            Search only active users who already hold an active membership in the current
            establishment.
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Search by name, username, or email"
            className="rounded-[1.15rem] border-[#e7dfd1] bg-white pl-11"
          />
        </div>

        <div className="rounded-[1.1rem] border border-[#ebe2d5] bg-[#fbf7f0] px-4 py-3 text-sm text-muted-foreground">
          {hint}
        </div>

        {errorMessage ? (
          <div className="rounded-[1rem] border border-[#f4d5d5] bg-[#fff3f2] px-4 py-3 text-sm text-[#9d3b33]">
            {errorMessage}
          </div>
        ) : null}

        {isSearching ? (
          <div className="flex items-center gap-3 rounded-[1.2rem] border border-[#ece5da] bg-white px-4 py-4 text-sm text-muted-foreground">
            <LoaderCircle className="size-4 animate-spin text-[color:var(--primary)]" />
            Searching current-establishment users...
          </div>
        ) : !hasRunnableQuery ? (
          <div className="rounded-[1.2rem] border border-dashed border-[#ddd3c5] bg-[#fffaf2] px-4 py-5 text-sm text-muted-foreground">
            Search starts after two characters and stays inside the current establishment.
          </div>
        ) : results.length === 0 ? (
          <div className="rounded-[1.2rem] border border-dashed border-[#ddd3c5] bg-[#fffaf2] px-4 py-5 text-sm text-muted-foreground">
            No users matched this scoped search yet.
          </div>
        ) : (
          <div className="space-y-3">
            {results.map((result) => (
              <div
                key={result.membership_id}
                className="flex items-start gap-3 rounded-[1.3rem] border border-[#ece5da] bg-white px-4 py-4 shadow-[0_16px_36px_-30px_rgba(46,72,173,0.22)]"
              >
                <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-[color:var(--primary)]/10 text-sm font-bold text-[color:var(--primary)]">
                  {getInitials(result.display_name)}
                </span>

                <div className="min-w-0 flex-1 space-y-2">
                  <div>
                    <div className="truncate text-base font-bold tracking-[-0.03em]">
                      {result.display_name}
                    </div>
                    <div className="truncate text-sm text-muted-foreground">
                      @{result.username}
                      {result.email ? ` · ${result.email}` : ''}
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Badge className="bg-[color:var(--primary)] text-primary-foreground">
                      {result.role}
                    </Badge>
                    <Badge variant="outline" className="border-[#ebe2d5] bg-[#fbf7f0]">
                      {result.membership_id.slice(0, 8)}
                    </Badge>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-muted-foreground">
          <UsersRound className="size-4" />
          Tenant-filtered before serialization
        </div>
      </CardContent>
    </Card>
  )
}

function getInitials(displayName: string) {
  const parts = displayName
    .split(/\s+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 2)

  if (parts.length === 0) {
    return 'U'
  }

  return parts.map((part) => part[0]!.toUpperCase()).join('')
}
