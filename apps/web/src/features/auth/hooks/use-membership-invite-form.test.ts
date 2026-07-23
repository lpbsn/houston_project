// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { useMembershipInviteForm } from './use-membership-invite-form'

const inviteMembership = vi.fn()
const invalidateMembershipListQueries = vi.fn()

vi.mock('@/features/auth/api', () => ({
  inviteMembership: (...args: unknown[]) => inviteMembership(...args),
  invalidateMembershipListQueries: (...args: unknown[]) =>
    invalidateMembershipListQueries(...args),
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
  allowedTargetRoles?: ('staff' | 'manager' | 'director')[]
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
      { type: 'button', onClick: () => setRole('director') },
      'Select director',
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

function renderWithQueryClient(ui: ReactNode) {
  const queryClient = createTestQueryClient()
  return render(
    createElement(QueryClientProvider, { client: queryClient }, ui),
  )
}

function renderHookWithQueryClient<T>(callback: () => T) {
  const queryClient = createTestQueryClient()
  return renderHook(callback, {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: queryClient }, children),
  })
}

beforeEach(() => {
  inviteMembership.mockReset()
  invalidateMembershipListQueries.mockReset()
  invalidateMembershipListQueries.mockResolvedValue(undefined)
})

afterEach(() => {
  cleanup()
})

describe('useMembershipInviteForm', () => {
  it('stores invitedEmail and invitationLink after successful submit', async () => {
    inviteMembership.mockResolvedValue({
      invitation_accept_path: '/invitations/token-abc',
    })

    renderWithQueryClient(
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
    expect(invalidateMembershipListQueries).toHaveBeenCalledWith('est-1', expect.anything())
  })

  it('shows success UI when list invalidation is still pending', async () => {
    inviteMembership.mockResolvedValue({
      invitation_accept_path: '/invitations/token-abc',
    })
    const deferred = createDeferred<void>()
    invalidateMembershipListQueries.mockReturnValue(deferred.promise)

    renderWithQueryClient(
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
    expect(screen.getByTestId('error-message').textContent).toBe('')
    expect(invalidateMembershipListQueries).toHaveBeenCalled()
  })

  it('keeps invite success when list invalidation rejects', async () => {
    inviteMembership.mockResolvedValue({
      invitation_accept_path: '/invitations/token-director',
    })
    invalidateMembershipListQueries.mockRejectedValue(new Error('cache refresh failed'))

    renderWithQueryClient(
      createElement(InviteFormProbe, {
        establishmentId: 'est-1',
        allowedTargetRoles: ['director', 'manager', 'staff'],
      }),
    )

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'director@example.com' },
    })
    fireEvent.change(screen.getByLabelText('First name'), {
      target: { value: 'Pat' },
    })
    fireEvent.change(screen.getByLabelText('Last name'), {
      target: { value: 'Director' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Select director' }))

    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: 'Submit' }))
    })

    await waitFor(() => {
      expect(screen.getByTestId('invited-email').textContent).toBe('director@example.com')
    })
    expect(screen.getByTestId('error-message').textContent).toBe('')
    expect(invalidateMembershipListQueries).toHaveBeenCalledWith('est-1', expect.anything())
  })

  it('submits director invites without scopes and invalidates membership list', async () => {
    inviteMembership.mockResolvedValue({
      invitation_accept_path: '/invitations/token-director',
    })

    renderWithQueryClient(
      createElement(InviteFormProbe, {
        establishmentId: 'est-1',
        allowedTargetRoles: ['director', 'manager', 'staff'],
      }),
    )

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'director@example.com' },
    })
    fireEvent.change(screen.getByLabelText('First name'), {
      target: { value: 'Pat' },
    })
    fireEvent.change(screen.getByLabelText('Last name'), {
      target: { value: 'Director' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Select scope' }))
    fireEvent.click(screen.getByRole('button', { name: 'Select director' }))

    expect(screen.getByTestId('requires-scopes').textContent).toBe('false')
    expect(screen.getByTestId('scopes-count').textContent).toBe('0')

    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: 'Submit' }))
    })

    await waitFor(() => {
      expect(inviteMembership).toHaveBeenCalledWith('est-1', {
        email: 'director@example.com',
        first_name: 'Pat',
        last_name: 'Director',
        role: 'director',
      })
    })

    expect(invalidateMembershipListQueries).toHaveBeenCalledWith('est-1', expect.anything())
  })

  it('maps invitation API error codes', async () => {
    inviteMembership.mockRejectedValue({
      name: 'AuthApiError',
      status: 409,
      code: 'membership_invitation_user_exists',
      message: 'A Houston account with this email already exists.',
    })

    renderWithQueryClient(
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

    const { result } = renderHookWithQueryClient(() =>
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

    renderWithQueryClient(
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

    renderWithQueryClient(
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
