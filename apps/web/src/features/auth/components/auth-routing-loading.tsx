import { LoaderCircle } from 'lucide-react'

export function AuthRoutingLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="flex items-center gap-3 rounded-xl border border-border/70 bg-background/85 px-4 py-3 text-sm text-muted-foreground">
        <LoaderCircle className="size-4 animate-spin text-primary" />
        Chargement de votre session…
      </div>
    </div>
  )
}
