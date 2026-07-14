// @vitest-environment jsdom

import { createElement } from 'react'
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useMembershipInviteForm } from './use-membership-invite-form'

const inviteMembership = vi.fn()

vi.mock('@/features/auth/api', () => ({
  inviteMembership: (...args: unknown[]) => inviteMembership(...args),
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
  allowedTargetRoles?: ('staff' | 'manager')[]
}) {
  const {
    form,
    setForm,
    selectedBusinessUnitScopes,
    setSelectedBusinessUnitScopes,
    invitationLink,
    invitedEmail,
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
    createElement('button', {
      type: 'button',
      onClick: () =>
        setSelectedBusinessUnitScopes([
          { scope_type: 'business_unit', scope_id: 'bu-1' },
        ]),
    }, 'Select scope'),
    createElement('button', { type: 'submit' }, 'Submit'),
    createElement('div', { 'data-testid': 'invited-email' }, invitedEmail ?? ''),
    createElement('div', { 'data-testid': 'invitation-link' }, invitationLink ?? ''),
  )
}

afterEach(() => {
  cleanup()
  inviteMembership.mockReset()
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

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'staff@example.com' },
    })
    fireEvent.change(screen.getByLabelText('First name'), {
      target: { value: 'Alex' },
    })
    fireEvent.change(screen.getByLabelText('Last name'), {
      target: { value: 'Martin' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Select scope' }))

    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: 'Submit' }))
    })

    await waitFor(() => {
      expect(screen.getByTestId('invited-email').textContent).toBe('staff@example.com')
    })

    expect(screen.getByTestId('invitation-link').textContent).toBe(
      `${window.location.origin}/invitations/token-abc`,
    )
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
})
