import { Building2, LoaderCircle, ShieldCheck, UserRound } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { EstablishmentMembershipResponse, RoleEnum } from '@/features/auth/types'
import { cn } from '@/lib/utils'

const ROLE_OPTIONS: RoleEnum[] = ['owner', 'director', 'manager', 'staff']

type MembershipManagementCardProps = {
  domainDraft: string
  errorMessage: string | null
  isDeactivating: boolean
  isLoadingList: boolean
  isLoadingMembership: boolean
  isSaving: boolean
  memberships: EstablishmentMembershipResponse[]
  onDeactivate: () => void
  onDomainDraftChange: (value: string) => void
  onRoleChange: (role: RoleEnum) => void
  onSave: () => void
  onSelectMembership: (membershipId: string) => void
  roleDraft: RoleEnum
  selectedMembership: EstablishmentMembershipResponse | null
  selectedMembershipId: string | null
}

export function MembershipManagementCard({
  domainDraft,
  errorMessage,
  isDeactivating,
  isLoadingList,
  isLoadingMembership,
  isSaving,
  memberships,
  onDeactivate,
  onDomainDraftChange,
  onRoleChange,
  onSave,
  onSelectMembership,
  roleDraft,
  selectedMembership,
  selectedMembershipId,
}: MembershipManagementCardProps) {
  return (
    <Card className="rounded-[1.75rem] border-[#ece5da] bg-[#fffdf9] shadow-[0_22px_48px_-38px_rgba(59,90,184,0.28)]">
      <CardHeader className="gap-3">
        <Badge className="w-fit bg-[color:var(--primary)]/12 text-[color:var(--primary)]">
          Memberships
        </Badge>
        <div className="space-y-2">
          <CardTitle className="text-[1.55rem] font-black tracking-[-0.05em]">
            Membership workspace
          </CardTitle>
          <CardDescription className="text-sm leading-6">
            Owners and directors can review memberships, update role and domain assignments, and
            deactivate accounts inside the currently selected establishment.
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {isLoadingList ? (
          <MembershipCardPlaceholder label="Loading memberships..." />
        ) : memberships.length === 0 ? (
          <EmptyState message="No memberships were returned for this establishment." />
        ) : (
          <div className="space-y-3">
            {memberships.map((membership) => {
              const isSelected = membership.id === selectedMembershipId

              return (
                <button
                  key={membership.id}
                  type="button"
                  onClick={() => onSelectMembership(membership.id)}
                  className={cn(
                    'w-full rounded-[1.35rem] border px-4 py-4 text-left shadow-[0_16px_36px_-30px_rgba(46,72,173,0.22)] transition',
                    isSelected
                      ? 'border-[color:var(--primary)]/40 bg-[color:var(--primary)]/5'
                      : 'border-[#ece5da] bg-white hover:border-[color:var(--primary)]/25',
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="rounded-full bg-[color:var(--primary)]/10 p-2 text-[color:var(--primary)]">
                          <UserRound className="size-4" />
                        </span>
                        <div className="min-w-0">
                          <div className="truncate text-base font-bold tracking-[-0.03em]">
                            {membership.user.display_name}
                          </div>
                          <div className="truncate text-sm text-muted-foreground">
                            @{membership.user.username}
                            {membership.user.email ? ` · ${membership.user.email}` : ''}
                          </div>
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <Badge className="bg-[color:var(--primary)] text-primary-foreground">
                          {membership.role}
                        </Badge>
                        <Badge variant="outline" className="border-[#ebe2d5] bg-[#fbf7f0]">
                          {membership.status}
                        </Badge>
                        <Badge variant="outline" className="border-[#ebe2d5] bg-white">
                          {membership.operational_domains.length} domains
                        </Badge>
                      </div>
                    </div>

                    {isSelected ? (
                      <span className="rounded-full bg-[color:var(--primary)] px-2 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-primary-foreground">
                        Editing
                      </span>
                    ) : null}
                  </div>
                </button>
              )
            })}
          </div>
        )}

        <div className="rounded-[1.45rem] border border-[#ece5da] bg-white p-4 shadow-[0_18px_38px_-32px_rgba(46,72,173,0.2)]">
          {isLoadingMembership ? (
            <MembershipCardPlaceholder label="Loading membership details..." />
          ) : !selectedMembership ? (
            <EmptyState message="Select a membership to review or edit its role and operational domains." />
          ) : (
            <div className="space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Building2 className="size-4 text-[color:var(--primary)]" />
                    {selectedMembership.establishment_name}
                  </div>
                  <div className="text-xl font-black tracking-[-0.05em]">
                    {selectedMembership.user.display_name}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {selectedMembership.user.email ?? `@${selectedMembership.user.username}`}
                  </div>
                </div>

                <Badge variant="outline" className="border-[#ebe2d5] bg-[#fbf7f0]">
                  {selectedMembership.status}
                </Badge>
              </div>

              <div className="space-y-2">
                <div className="text-sm font-semibold">Role</div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {ROLE_OPTIONS.map((role) => (
                    <Button
                      key={role}
                      type="button"
                      variant={roleDraft === role ? 'default' : 'outline'}
                      className={cn(
                        'h-11 rounded-[1rem]',
                        roleDraft === role
                          ? 'shadow-[0_14px_28px_-20px_rgba(46,72,173,0.45)]'
                          : 'border-[#e7dfd1] bg-[#fffdf8]',
                      )}
                      onClick={() => onRoleChange(role)}
                    >
                      {role}
                    </Button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-sm font-semibold">Operational domains</div>
                <Input
                  value={domainDraft}
                  onChange={(event) => onDomainDraftChange(event.target.value)}
                  placeholder="housekeeping, maintenance"
                  className="rounded-[1rem] border-[#e7dfd1] bg-[#fffdf8]"
                />
                <div className="text-xs leading-5 text-muted-foreground">
                  Comma-separated active domain keys for this establishment.
                </div>
              </div>

              {errorMessage ? (
                <div className="rounded-[1rem] border border-[#f4d5d5] bg-[#fff3f2] px-4 py-3 text-sm text-[#9d3b33]">
                  {errorMessage}
                </div>
              ) : null}

              <div className="flex flex-col gap-3 sm:flex-row">
                <Button
                  type="button"
                  className="h-11 flex-1 rounded-[1rem]"
                  disabled={isSaving}
                  onClick={onSave}
                >
                  {isSaving ? (
                    <>
                      <LoaderCircle className="size-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="size-4" />
                      Save membership
                    </>
                  )}
                </Button>

                <Button
                  type="button"
                  variant="outline"
                  className="h-11 rounded-[1rem] border-[#efc4c4] bg-[#fff6f6] text-[#9d3b33] hover:bg-[#ffe8e6] hover:text-[#8d3129]"
                  disabled={isDeactivating}
                  onClick={onDeactivate}
                >
                  {isDeactivating ? (
                    <>
                      <LoaderCircle className="size-4 animate-spin" />
                      Deactivating...
                    </>
                  ) : (
                    'Deactivate membership'
                  )}
                </Button>
              </div>
            </div>
          )}
        </div>

        <div className="rounded-[1.15rem] border border-[#ebe2d5] bg-[#fbf7f0] px-4 py-3 text-sm text-muted-foreground">
          Role-based access stays backend-owned. This card only renders the API contract the
          current workspace exposes.
        </div>
      </CardContent>
    </Card>
  )
}

function MembershipCardPlaceholder({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 rounded-[1.2rem] border border-[#ece5da] bg-white px-4 py-4 text-sm text-muted-foreground">
      <LoaderCircle className="size-4 animate-spin text-[color:var(--primary)]" />
      {label}
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-[1.2rem] border border-dashed border-[#ddd3c5] bg-[#fffaf2] px-4 py-5 text-sm text-muted-foreground">
      {message}
    </div>
  )
}
