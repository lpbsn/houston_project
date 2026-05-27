import { ArrowRight, PanelLeft, Sparkles } from 'lucide-react'
import type { PropsWithChildren, ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { cn } from '@/lib/utils'

type AppShellProps = PropsWithChildren<{
  sidebarOpen: boolean
  visualMode: 'focus' | 'calm'
  onToggleSidebar: () => void
  onCycleVisualMode: () => void
  headingBadge: string
  title: string
  description: string
  heroTitle: string
  heroDescription: string
  heroFooter: string
  actions?: ReactNode
}>

const architectureNotes = [
  'Django remains the authority for identity, sessions, permissions, and visibility.',
  'TanStack Query owns bootstrap state while the access token stays in memory only.',
  'The refresh token stays in an HttpOnly cookie and auth mutations use CSRF headers.',
]

export function AppShell({
  sidebarOpen,
  visualMode,
  onToggleSidebar,
  onCycleVisualMode,
  headingBadge,
  title,
  description,
  heroTitle,
  heroDescription,
  heroFooter,
  actions,
  children,
}: AppShellProps) {
  return (
    <div className="grid min-h-[calc(100vh-3rem)] w-full gap-4 lg:grid-cols-[18rem_minmax(0,1fr)]">
      <aside
        className={cn(
          'overflow-hidden transition-[max-width,opacity] duration-300 ease-out',
          sidebarOpen ? 'max-w-80 opacity-100' : 'max-w-0 opacity-0 lg:max-w-0',
        )}
        aria-hidden={!sidebarOpen}
      >
        <Card className="h-full border-white/60 bg-white/80 shadow-[0_24px_80px_-48px_rgba(15,59,72,0.45)] backdrop-blur">
          <CardHeader>
            <Badge variant="secondary" className="mb-2 w-fit">
              Auth contract
            </Badge>
            <CardTitle>Thin client, backend-owned authority</CardTitle>
            <CardDescription>
              This shell stays narrow on purpose. Authentication, sessions, and visibility remain
              backend-owned.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {architectureNotes.map((note) => (
              <div key={note} className="rounded-xl border border-border/70 bg-background/75 p-3 text-sm">
                {note}
              </div>
            ))}
          </CardContent>
          <CardFooter className="items-start">
            <p className="text-sm text-muted-foreground">
              Access tokens never touch durable browser storage in this shell.
            </p>
          </CardFooter>
        </Card>
      </aside>

      <section className="grid gap-4">
        <Card className="border-white/60 bg-white/80 shadow-[0_24px_80px_-48px_rgba(15,59,72,0.45)] backdrop-blur">
          <CardHeader className="gap-4 md:flex md:flex-row md:items-start md:justify-between">
            <div className="space-y-3">
              <Badge className="w-fit bg-[color:var(--primary)] text-primary-foreground">
                {headingBadge}
              </Badge>
              <div className="space-y-2">
                <CardTitle className="text-3xl tracking-tight">{title}</CardTitle>
                <CardDescription className="max-w-2xl text-base leading-7">
                  {description}
                </CardDescription>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {actions}
              <Button variant="outline" onClick={onToggleSidebar}>
                <PanelLeft className="size-4" />
                {sidebarOpen ? 'Hide notes' : 'Show notes'}
              </Button>
              <Button variant="secondary" onClick={onCycleVisualMode}>
                <Sparkles className="size-4" />
                Mode: {visualMode}
              </Button>
            </div>
          </CardHeader>

          <CardContent className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
            <Card className="border-border/70 bg-[linear-gradient(135deg,rgba(15,59,72,0.98),rgba(36,152,122,0.88))] text-primary-foreground shadow-none">
              <CardHeader>
                <Badge variant="outline" className="w-fit border-white/25 text-white">
                  Auth shell
                </Badge>
                <CardTitle className="text-2xl text-white">{heroTitle}</CardTitle>
                <CardDescription className="text-white/80">{heroDescription}</CardDescription>
              </CardHeader>
              <CardFooter className="justify-between border-white/10 bg-white/8 text-white/85">
                <span>{heroFooter}</span>
                <ArrowRight className="size-4" />
              </CardFooter>
            </Card>

            {children}
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
