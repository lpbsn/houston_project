import { CheckCircle2, Copy, LoaderCircle, UserPlus } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { BusinessUnitScopeSelector } from '@/components/domain/business-unit-scope-selector'
import {
  getBusinessUnitTree,
  inviteMembership,
  businessUnitTreeQueryKey,
} from '@/features/auth/api'
import {
  type BusinessUnitScopeSelection,
} from '@/features/auth/lib/business-unit-scope'
import type { MembershipInvitationRequestRoleEnum } from '@/features/auth/types'

type MembershipInviteCardProps = {
  establishmentId: string
  allowedTargetRoles?: MembershipInvitationRequestRoleEnum[]
}

type InviteForm = {
  email: string
  first_name: string
  last_name: string
  role: 'staff' | 'manager'
}

const emptyForm: InviteForm = {
  email: '',
  first_name: '',
  last_name: '',
  role: 'staff',
}

const DEFAULT_TARGET_ROLES: MembershipInvitationRequestRoleEnum[] = ['staff', 'manager']

function buildInvitationAcceptUrl(acceptPath: string) {
  if (acceptPath.startsWith('http://') || acceptPath.startsWith('https://')) {
    return acceptPath
  }

  return `${window.location.origin}${acceptPath.startsWith('/') ? acceptPath : `/${acceptPath}`}`
}

export function MembershipInviteCard({
  establishmentId,
  allowedTargetRoles,
}: MembershipInviteCardProps) {
  const [form, setForm] = useState<InviteForm>(emptyForm)
  const [selectedBusinessUnitScopes, setSelectedBusinessUnitScopes] = useState<
    BusinessUnitScopeSelection[]
  >([])
  const [invitationLink, setInvitationLink] = useState<string | null>(null)
  const [copyMessage, setCopyMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const businessUnitQuery = useQuery({
    queryKey: businessUnitTreeQueryKey(establishmentId),
    queryFn: () => getBusinessUnitTree(establishmentId),
    staleTime: 60_000,
  })

  const roleOptions = useMemo(() => {
    if (allowedTargetRoles) {
      const seen = new Set<MembershipInvitationRequestRoleEnum>()
      const deduped: MembershipInvitationRequestRoleEnum[] = []
      for (const role of allowedTargetRoles) {
        if (role === 'staff' || role === 'manager') {
          if (!seen.has(role)) {
            deduped.push(role)
            seen.add(role)
          }
        }
      }
      return deduped
    }
    return DEFAULT_TARGET_ROLES
  }, [allowedTargetRoles])

  const hasRoleOptions = roleOptions.length > 0
  const selectedRole = hasRoleOptions
    ? roleOptions.includes(form.role)
      ? form.role
      : roleOptions[0]
    : null
  const isRoleAllowed = selectedRole ? roleOptions.includes(selectedRole) : false
  const isManagerRestrictedToStaff =
    hasRoleOptions && roleOptions.length === 1 && roleOptions[0] === 'staff'

  const canSubmit = useMemo(() => {
    if (!hasRoleOptions || !isRoleAllowed) {
      return false
    }

    if (!form.email.trim() || !form.first_name.trim() || !form.last_name.trim()) {
      return false
    }

    return selectedBusinessUnitScopes.length > 0
  }, [form, hasRoleOptions, isRoleAllowed, selectedBusinessUnitScopes.length])

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrorMessage(null)
    setCopyMessage(null)
    setIsSubmitting(true)

    try {
      if (!hasRoleOptions) {
        throw new Error('Aucun rôle invitable pour votre profil.')
      }

      if (!selectedRole || !roleOptions.includes(selectedRole)) {
        throw new Error('Le rôle sélectionné n’est pas autorisé pour votre profil.')
      }

      if (selectedBusinessUnitScopes.length === 0) {
        throw new Error('Sélectionnez au moins un pôle d’activité.')
      }

      const result = await inviteMembership(establishmentId, {
        email: form.email.trim(),
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        role: selectedRole as MembershipInvitationRequestRoleEnum,
        scopes: selectedBusinessUnitScopes,
      })

      setInvitationLink(buildInvitationAcceptUrl(result.invitation_accept_path))
      setForm(emptyForm)
      setSelectedBusinessUnitScopes([])
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Invitation could not be created.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleCopyLink() {
    if (!invitationLink) {
      return
    }

    try {
      await navigator.clipboard.writeText(invitationLink)
      setCopyMessage('Invitation link copied.')
    } catch {
      setCopyMessage('Copy failed. Select and copy the link manually.')
    }
  }

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
