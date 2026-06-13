import { useAuth } from '@/app/auth-provider'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MembershipInviteCard } from '@/features/auth/components/membership-invite-card'
import {
  canInviteFromBootstrapHints,
  getBootstrapPermissionHints,
} from '@/features/auth/lib/bootstrap-permission-hints'
import { getAllowedInviteTargetRoles } from '@/features/auth/lib/invitation-rbac'
import { toRoleEnum } from '@/features/auth/lib/role'

export function TeamInvitePage() {
  const { activeMembership, bootstrap } = useAuth()
  const permissionHints = getBootstrapPermissionHints(bootstrap)
  const role = toRoleEnum(activeMembership?.role)
  const allowedTargetRoles = getAllowedInviteTargetRoles(role)
  const canAccess = Boolean(activeMembership) && canInviteFromBootstrapHints(permissionHints)

  if (!canAccess || !activeMembership) {
    return (
      <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
        <CardHeader className="gap-3">
          <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
            Invitations
          </Badge>
          <div className="space-y-2">
            <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
              Acces non autorise
            </CardTitle>
            <CardDescription className="text-sm leading-6">
              Votre profil actuel ne vous permet pas de creer des invitations.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <Button asChild variant="outline" className="h-11 rounded-[1rem]">
            <a href="/profile">Retour au profil</a>
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <MembershipInviteCard
      establishmentId={activeMembership.establishment_id}
      allowedTargetRoles={allowedTargetRoles}
    />
  )
}
