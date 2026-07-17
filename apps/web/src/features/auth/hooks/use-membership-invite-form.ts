import { useMemo, useState } from 'react'

import {
  inviteMembership,
  invalidateMembershipWorkspaceQueries,
  membershipListQueryKey,
} from '@/features/auth/api'
import { useBusinessUnitTreeQuery } from '@/features/auth/hooks'
import { type BusinessUnitScopeSelection } from '@/features/auth/lib/business-unit-scope'
import { resolveInvitationErrorMessage } from '@/features/auth/lib/invitation-errors'
import { requiresInviteScopes } from '@/features/auth/lib/invitation-rbac'
import type { MembershipInvitationRequestRoleEnum } from '@/features/auth/types'
import { queryClient } from '@/lib/query-client'

export type MembershipInviteFormState = {
  email: string
  first_name: string
  last_name: string
  role: MembershipInvitationRequestRoleEnum
}

const emptyForm: MembershipInviteFormState = {
  email: '',
  first_name: '',
  last_name: '',
  role: 'staff',
}

const DEFAULT_TARGET_ROLES: MembershipInvitationRequestRoleEnum[] = ['staff', 'manager']

export function buildInvitationAcceptUrl(acceptPath: string) {
  if (acceptPath.startsWith('http://') || acceptPath.startsWith('https://')) {
    return acceptPath
  }

  return `${window.location.origin}${acceptPath.startsWith('/') ? acceptPath : `/${acceptPath}`}`
}

type UseMembershipInviteFormOptions = {
  establishmentId: string
  allowedTargetRoles?: MembershipInvitationRequestRoleEnum[]
}

export function useMembershipInviteForm({
  establishmentId,
  allowedTargetRoles,
}: UseMembershipInviteFormOptions) {
  const [form, setForm] = useState<MembershipInviteFormState>(emptyForm)
  const [selectedBusinessUnitScopes, setSelectedBusinessUnitScopes] = useState<
    BusinessUnitScopeSelection[]
  >([])
  const [invitationLink, setInvitationLink] = useState<string | null>(null)
  const [invitedEmail, setInvitedEmail] = useState<string | null>(null)
  const [copyMessage, setCopyMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const businessUnitQuery = useBusinessUnitTreeQuery(establishmentId, { staleTime: 60_000 })

  const roleOptions = useMemo(() => {
    if (allowedTargetRoles) {
      const seen = new Set<MembershipInvitationRequestRoleEnum>()
      const deduped: MembershipInvitationRequestRoleEnum[] = []
      for (const role of allowedTargetRoles) {
        if (!seen.has(role)) {
          deduped.push(role)
          seen.add(role)
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
  const requiresScopes = requiresInviteScopes(selectedRole)

  const canSubmit = useMemo(() => {
    if (!hasRoleOptions || !isRoleAllowed || !selectedRole) {
      return false
    }

    if (!form.email.trim() || !form.first_name.trim() || !form.last_name.trim()) {
      return false
    }

    if (requiresScopes) {
      return selectedBusinessUnitScopes.length > 0
    }

    return true
  }, [
    form,
    hasRoleOptions,
    isRoleAllowed,
    requiresScopes,
    selectedBusinessUnitScopes.length,
    selectedRole,
  ])

  function setRole(role: MembershipInvitationRequestRoleEnum) {
    setForm((current) => ({ ...current, role }))
    if (!requiresInviteScopes(role)) {
      setSelectedBusinessUnitScopes([])
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrorMessage(null)
    setCopyMessage(null)
    setInvitedEmail(null)
    setInvitationLink(null)
    setIsSubmitting(true)

    try {
      if (!hasRoleOptions) {
        throw new Error('Aucun rôle invitable pour votre profil.')
      }

      if (!selectedRole || !roleOptions.includes(selectedRole)) {
        throw new Error('Le rôle sélectionné n’est pas autorisé pour votre profil.')
      }

      if (requiresInviteScopes(selectedRole) && selectedBusinessUnitScopes.length === 0) {
        throw new Error('Sélectionnez au moins un pôle d’activité.')
      }

      const submittedEmail = form.email.trim()
      const scopes = requiresInviteScopes(selectedRole) ? selectedBusinessUnitScopes : []

      const result = await inviteMembership(establishmentId, {
        email: submittedEmail,
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        role: selectedRole,
        ...(scopes.length > 0 ? { scopes } : {}),
      })

      if (selectedRole === 'owner') {
        await invalidateMembershipWorkspaceQueries({ includeBootstrap: true })
      } else {
        await queryClient.invalidateQueries({
          queryKey: membershipListQueryKey(establishmentId),
        })
      }

      setInvitedEmail(submittedEmail)
      setInvitationLink(buildInvitationAcceptUrl(result.invitation_accept_path))
      setForm(emptyForm)
      setSelectedBusinessUnitScopes([])
    } catch (error) {
      setErrorMessage(
        resolveInvitationErrorMessage(error, 'L’invitation n’a pas pu être créée.'),
      )
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

  return {
    form,
    setForm,
    setRole,
    selectedBusinessUnitScopes,
    setSelectedBusinessUnitScopes,
    invitationLink,
    invitedEmail,
    copyMessage,
    errorMessage,
    isSubmitting,
    businessUnitQuery,
    roleOptions,
    hasRoleOptions,
    selectedRole,
    requiresScopes,
    isManagerRestrictedToStaff,
    canSubmit,
    handleSubmit,
    handleCopyLink,
  }
}
