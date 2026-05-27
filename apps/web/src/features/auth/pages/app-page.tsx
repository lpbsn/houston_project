import { Building2, LoaderCircle, LogOut, ShieldCheck, Users } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
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

export function AppPage() {
  const {
    activeMembership,
    isAuthenticated,
    isBootstrapping,
    isLoggingOut,
    logout,
    memberships,
    user,
  } = useAuth()

  if (isBootstrapping) {
    return (
      <Card className="border-border/70 bg-background/85 shadow-none">
        <CardContent className="flex items-center gap-3 py-8">
          <LoaderCircle className="size-4 animate-spin text-primary" />
          <span>Loading your authenticated workspace...</span>
        </CardContent>
      </Card>
    )
  }

  if (!isAuthenticated || !user) {
    return (
      <Card className="border-border/70 bg-background/85 shadow-none">
        <CardContent className="py-8 text-sm text-muted-foreground">
          Redirecting you to sign in...
        </CardContent>
      </Card>
    )
  }

  const userIdentifier = user.email ?? user.username

  return (
    <div className="grid gap-4">
      <Card className="border-white/60 bg-white/90 shadow-[0_24px_80px_-48px_rgba(15,59,72,0.45)] backdrop-blur">
        <CardHeader className="gap-4 md:flex md:flex-row md:items-start md:justify-between">
          <div className="space-y-3">
            <Badge className="w-fit bg-[color:var(--primary)] text-primary-foreground">
              Authenticated
            </Badge>
            <div className="space-y-2">
              <CardTitle className="text-2xl tracking-tight">{userIdentifier}</CardTitle>
              <CardDescription>
                This shell only exposes bootstrap data the backend already approved for the
                current session.
              </CardDescription>
            </div>
          </div>

          <Button variant="outline" onClick={() => void logout()} disabled={isLoggingOut}>
            <LogOut className="size-4" />
            {isLoggingOut ? 'Signing out...' : 'Logout'}
          </Button>
        </CardHeader>

        <CardContent className="grid gap-4 md:grid-cols-3">
          <Card className="border-border/70 bg-background/85 shadow-none">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="size-4 text-primary" />
                Identity
              </CardTitle>
              <CardDescription>The backend owns the authenticated session state.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="text-sm font-medium">{user.username}</div>
              <div className="text-sm text-muted-foreground">{user.email ?? 'No email on file'}</div>
            </CardContent>
          </Card>

          <Card className="border-border/70 bg-background/85 shadow-none">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="size-4 text-primary" />
                Active establishment
              </CardTitle>
              <CardDescription>
                Populated only when exactly one active membership exists.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="text-sm font-medium">
                {activeMembership?.establishment_name ?? 'Not selected'}
              </div>
              <div className="text-sm text-muted-foreground">
                {activeMembership?.organization_name ?? 'Multiple or zero active memberships'}
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/70 bg-background/85 shadow-none">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="size-4 text-primary" />
                Memberships
              </CardTitle>
              <CardDescription>
                Backend-filtered memberships available to this session.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="text-2xl font-medium">{memberships.length}</div>
              <div className="text-sm text-muted-foreground">
                {memberships.length === 1 ? '1 active membership' : `${memberships.length} active memberships`}
              </div>
            </CardContent>
          </Card>
        </CardContent>

        <CardFooter className="justify-between text-sm text-muted-foreground">
          <span>Permissions and visibility remain backend-enforced.</span>
          <span>{user.identity_type}</span>
        </CardFooter>
      </Card>
    </div>
  )
}
