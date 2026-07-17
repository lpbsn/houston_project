// @vitest-environment jsdom

import { createElement } from 'react'
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useMembershipInviteForm } from './use-membership-invite-form'

const inviteMembership = vi.fn()
const invalidateMembershipWorkspaceQueries = vi.fn()
const invalidateQueries = vi.fn()

vi.mock('@/features/auth/api', () => ({
  inviteMembership: (...args: unknown[]) => inviteMembership(...args),
  invalidateMembershipWorkspaceQueries: (...args: unknown[]) =>
    invalidateMembershipWorkspaceQueries(...args),
  membershipListQueryKey: (establishmentId: string) =>
    ['workspace', 'memberships', establishmentId] as const,
}))

vi.mock('@/lib/query-client', () => ({
  queryClient: {
    invalidateQueries: (...args: unknown[]) => invalidateQueries(...args),
  },
}))

vi.mock('@/features/auth/hooks', () => ({
  useBusinessUnitTreeQuery: () => ({
    data: null,
    isPending: false,
    error: null,
  }),
}))

function InviteFormProbe({
  establishmentId,
  allowedTargetRoles,
}: {
  establishmentId: string
  allowedTargetRoles?: ('staff' | 'manager' | 'owner' | 'director')[]
}) {
  const {
    form,
    setForm,
    setRole,
    selectedBusinessUnitScopes,
    setSelectedBusinessUnitScopes,
    invitationLink,
    invitedEmail,
    errorMessage,
    requiresScopes,
    handleSubmit,
  } = useMembershipInviteForm({ establishmentId, allowedTargetRoles })

  return createElement(
    'form',
    { onSubmit: handleSubmit },
    createElement('input', {
      'aria-label': 'Email',
      value: form.email,
      onChange: (event: React.ChangeEvent<HTMLInputElement>) =>
        setForm((current) => ({ ...current, email: event.target.value })),
    }),
    createElement('input', {
      'aria-label': 'First name',
      value: form.first_name,
      onChange: (event: React.ChangeEvent<HTMLInputElement>) =>
        setForm((current) => ({ ...current, first_name: event.target.value })),
    }),
    createElement('input', {
      'aria-label': 'Last name',
      value: form.last_name,
      onChange: (event: React.ChangeEvent<HTMLInputElement>) =>
        setForm((current) => ({ ...current, last_name: event.target.value })),
    }),
    createElement(
      'div',
      { 'data-testid': 'scopes-count' },
      String(selectedBusinessUnitScopes.length),
    ),
    createElement('div', { 'data-testid': 'requires-scopes' }, String(requiresScopes)),
    createElement(
      'button',
      {
        type: 'button',
        onClick: () =>
          setSelectedBusinessUnitScopes([{ scope_type: 'business_unit', scope_id: 'bu-1' }]),
      },
      'Select scope',
    ),
    createElement(
      'button',
      { type: 'button', onClick: () => setRole('owner') },
      'Select owner',
    ),
    createElement('button', { type: 'submit' }, 'Submit'),
    createElement('div', { 'data-testid': 'invited-email' }, invitedEmail ?? ''),
    createElement('div', { 'data-testid': 'invitation-link' }, invitationLink ?? ''),
    createElement('div', { 'data-testid': 'error-message' }, errorMessage ?? ''),
  )
}

function fillInviteForm(email = 'staff@example.com') {
  fireEvent.change(screen.getByLabelText('Email'), {
    target: { value: email },
  })
  fireEvent.change(screen.getByLabelText('First name'), {
    target: { value: 'Alex' },
  })
  fireEvent.change(screen.getByLabelText('Last name'), {
    target: { value: 'Martin' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Select scope' }))
}

function createDeferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((res) => {
    resolve = res
  })

  return { promise, resolve }
}

beforeEach(() => {
  inviteMembership.mockReset()
  invalidateMembershipWorkspaceQueries.mockReset()
  invalidateQueries.mockReset()
  invalidateMembershipWorkspaceQueries.mockResolvedValue(undefined)
  invalidateQueries.mockResolvedValue(undefined)
})

afterEach(() => {
  cleanup()
})

describe('useMembershipInviteForm', () => {
  it('stores invitedEmail and invitationLink after successful submit', async () => {
    inviteMembership.mockResolvedValue({
      invitation_accept_path: '/invitations/token-abc',
    })

    render(
      createElement(InviteFormProbe, {
        establishmentId: 'est-1',
      }),
    )

    fillInviteForm('staff@example.com')

    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: 'Submit' }))
    })

    await waitFor(() => {
      expect(screen.getByTestId('invited-email').textContent).toBe('staff@example.com')
    })

    expect(screen.getByTestId('invitation-link').textContent).toBe(
      `${window.location.origin}/invitations/token-abc`,
    )
    expect(invalidateQueries).toHaveBeenCalled()
    expect(invalidateMembershipWorkspaceQueries).not.toHaveBeenCalled()
  })

  it('submits owner invites without scopes and invalidates workspace memberships root', async () => {
    inviteMembership.mockResolvedValue({
      invitation_accept_path: '/invitations/token-owner',
    })

    render(
      createElement(InviteFormProbe, {
        establishmentId: 'est-1',
        allowedTargetRoles: ['owner', 'director', 'manager', 'staff'],
      }),
    )

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'owner@example.com' },
    })
    fireEvent.change(screen.getByLabelText('First name'), {
      target: { value: 'Pat' },
    })
    fireEvent.change(screen.getByLabelText('Last name'), {
      target: { value: 'Owner' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Select scope' }))
    fireEvent.click(screen.getByRole('button', { name: 'Select owner' }))

    expect(screen.getByTestId('requires-scopes').textContent).toBe('false')
    expect(screen.getByTestId('scopes-count').textContent).toBe('0')

    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: 'Submit' }))
    })

    await waitFor(() => {
      expect(inviteMembership).toHaveBeenCalledWith('est-1', {
        email: 'owner@example.com',
        first_name: 'Pat',
        last_name: 'Owner',
        role: 'owner',
      })
    })

    expect(invalidateMembershipWorkspaceQueries).toHaveBeenCalledWith({
      includeBootstrap: true,
    })
  })

  it('maps invitation API error codes', async () => {
    inviteMembership.mockRejectedValue({
      name: 'AuthApiError',
      status: 409,
      code: 'membership_invitation_user_exists',
      message: 'A Houston account with this email already exists.',
    })

    render(
      createElement(InviteFormProbe, {
        establishmentId: 'est-1',
      }),
    )

    fillInviteForm('dup@example.com')

    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: 'Submit' }))
    })

    await waitFor(() => {
      expect(screen.getByTestId('error-message').textContent).toContain('existe déjà')
    })
    expect(screen.getByTestId('error-message').textContent).not.toMatch(/réactiv/i)
  })

  it('exposes invitedEmail from hook state', async () => {
    inviteMembership.mockResolvedValue({
      invitation_accept_path: '/invitations/token-abc',
    })

    const { result } = renderHook(() =>
      useMembershipInviteForm({ establishmentId: 'est-1' }),
    )

    act(() => {
      result.current.setForm({
        email: 'manager@example.com',
        first_name: 'Jamie',
        last_name: 'Lee',
        role: 'staff',
      })
      result.current.setSelectedBusinessUnitScopes([
        { scope_type: 'business_unit', scope_id: 'bu-1' },
      ])
    })

    await act(async () => {
      await result.current.handleSubmit({
        preventDefault: vi.fn(),
      } as unknown as React.FormEvent<HTMLFormElement>)
    })

    await waitFor(() => {
      expect(result.current.invitedEmail).toBe('manager@example.com')
    })

    expect(result.current.invitationLink).toBe(`${window.location.origin}/invitations/token-abc`)
  })

  it('clears invitation success state when a new submit starts', async () => {
    inviteMembership
      .mockResolvedValueOnce({
        invitation_accept_path: '/invitations/token-first',
      })
      .mockImplementationOnce(() => {
        const deferred = createDeferred<{ invitation_accept_path: string }>()
        return deferred.promise
      })

    render(
      createElement(InviteFormProbe, {
        establishmentId: 'est-1',
      }),
    )

    fillInviteForm('first@example.com')

    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: 'Submit' }))
    })

    await waitFor(() => {
      expect(screen.getByTestId('invited-email').textContent).toBe('first@example.com')
    })

    fillInviteForm('second@example.com')

    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: 'Submit' }))
    })

    expect(screen.getByTestId('invited-email').textContent).toBe('')
    expect(screen.getByTestId('invitation-link').textContent).toBe('')
  })

  it('clears invitation success state when a retry fails', async () => {
    inviteMembership
      .mockResolvedValueOnce({
        invitation_accept_path: '/invitations/token-first',
      })
      .mockRejectedValueOnce(new Error('Invitation could not be created.'))

    render(
      createElement(InviteFormProbe, {
        establishmentId: 'est-1',
      }),
    )

    fillInviteForm('first@example.com')

    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: 'Submit' }))
    })

    await waitFor(() => {
      expect(screen.getByTestId('invited-email').textContent).toBe('first@example.com')
    })

    fillInviteForm('second@example.com')

    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: 'Submit' }))
    })

    await waitFor(() => {
      expect(screen.getByTestId('invited-email').textContent).toBe('')
    })

    expect(screen.getByTestId('invitation-link').textContent).toBe('')
  })
})
