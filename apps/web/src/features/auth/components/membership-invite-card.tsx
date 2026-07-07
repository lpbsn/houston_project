import { CheckCircle2, Copy, LoaderCircle, UserPlus } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { BusinessUnitScopeSelector } from '@/components/domain/business-unit-scope-selector'
import { useMembershipInviteForm } from '@/features/auth/hooks/use-membership-invite-form'
import type { MembershipInvitationRequestRoleEnum } from '@/features/auth/types'

type MembershipInviteCardProps = {
  establishmentId: string
  allowedTargetRoles?: MembershipInvitationRequestRoleEnum[]
}

export function MembershipInviteCard({
  establishmentId,
  allowedTargetRoles,
}: MembershipInviteCardProps) {
  const {
    form,
    setForm,
    selectedBusinessUnitScopes,
    setSelectedBusinessUnitScopes,
    invitationLink,
    copyMessage,
    errorMessage,
    isSubmitting,
    businessUnitQuery,
    roleOptions,
    hasRoleOptions,
    selectedRole,
    isManagerRestrictedToStaff,
    canSubmit,
    handleSubmit,
    handleCopyLink,
  } = useMembershipInviteForm({ establishmentId, allowedTargetRoles })

  return (
    <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
      <CardHeader className="gap-3">
        <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
          Invitations
        </Badge>
        <div className="space-y-2">
          <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
            Invite a team member
          </CardTitle>
          <CardDescription className="text-sm leading-6">
            Send a staff or manager invitation link. Houston does not send email in MVP; copy and
            share the link manually.
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {!hasRoleOptions ? (
          <div className="rounded-[1rem] border border-[#e7dfd1] bg-[#fffaf2] px-4 py-3 text-sm text-[#5f574d]">
            Aucun rôle invitable pour votre profil.
          </div>
        ) : null}

        {isManagerRestrictedToStaff ? (
          <div className="rounded-[1rem] border border-[#e7dfd1] bg-[#fffaf2] px-4 py-3 text-sm text-[#5f574d]">
            Vous pouvez inviter uniquement un membre Staff dans votre périmètre opérationnel.
          </div>
        ) : null}

        {hasRoleOptions ? (
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field
              label="First name"
              value={form.first_name}
              onChange={(value) => setForm((current) => ({ ...current, first_name: value }))}
            />
            <Field
              label="Last name"
              value={form.last_name}
              onChange={(value) => setForm((current) => ({ ...current, last_name: value }))}
            />
          </div>

          <Field
            label="Email"
            type="email"
            value={form.email}
            onChange={(value) => setForm((current) => ({ ...current, email: value }))}
          />

          <div className="space-y-2">
            <div className="text-sm font-semibold">Role</div>
            {roleOptions.length === 1 ? (
              <Button type="button" className="h-11 rounded-[1rem] capitalize" disabled>
                {roleOptions[0]}
              </Button>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {roleOptions.map((role) => (
                  <Button
                    key={role}
                    type="button"
                    variant={selectedRole === role ? 'default' : 'outline'}
                    className="h-11 rounded-[1rem] capitalize"
                    onClick={() => setForm((current) => ({ ...current, role }))}
                  >
                    {role}
                  </Button>
                ))}
              </div>
            )}
          </div>

          <BusinessUnitScopeSelector
            tree={businessUnitQuery.data ?? null}
            selectedScopes={selectedBusinessUnitScopes}
            onChange={setSelectedBusinessUnitScopes}
            isLoading={businessUnitQuery.isPending}
            errorMessage={
              businessUnitQuery.error
                ? businessUnitQuery.error instanceof Error
                  ? businessUnitQuery.error.message
                  : 'Les pôles d’activité sont indisponibles.'
                : null
            }
            disabled={isSubmitting}
          />

          {errorMessage ? (
            <div className="rounded-[1rem] border border-[#f4d5d5] bg-[#fff3f2] px-4 py-3 text-sm text-[#9d3b33]">
              {errorMessage}
            </div>
          ) : null}

          <Button type="submit" disabled={!canSubmit || isSubmitting} className="h-11 rounded-[1rem]">
            {isSubmitting ? (
              <>
                <LoaderCircle className="size-4 animate-spin" />
                Creating invitation...
              </>
            ) : (
              <>
                <UserPlus className="size-4" />
                Create invitation
              </>
            )}
          </Button>
        </form>
        ) : null}

        {invitationLink ? (
          <div className="space-y-3 rounded-[1.35rem] border border-[#dce8d0] bg-[#f7fbf2] px-4 py-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-[#3f6d2d]">
              <CheckCircle2 className="size-4" />
              Invitation ready
            </div>
            <div className="break-all text-sm text-muted-foreground">{invitationLink}</div>
            <Button type="button" variant="outline" className="h-10 rounded-[1rem]" onClick={handleCopyLink}>
              <Copy className="size-4" />
              Copy invitation link
            </Button>
            {copyMessage ? <div className="text-sm text-muted-foreground">{copyMessage}</div> : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

function Field({
  label,
  onChange,
  type = 'text',
  value,
}: {
  label: string
  onChange: (value: string) => void
  type?: string
  value: string
}) {
  return (
    <div className="space-y-2">
      <div className="text-sm font-semibold">{label}</div>
      <Input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="rounded-[1rem] border-[#e7dfd1] bg-[#fffdf8]"
      />
    </div>
  )
}
