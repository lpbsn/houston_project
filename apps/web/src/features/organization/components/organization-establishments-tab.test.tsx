// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { OrganizationEstablishmentsTab } from '../components/organization-establishments-tab'
import type { OrganizationAdminEstablishment } from '../types'

afterEach(() => {
  cleanup()
})

function establishment(
  overrides: Partial<OrganizationAdminEstablishment>,
): OrganizationAdminEstablishment {
  return {
    id: 'est-1',
    name: 'Draft Hotel',
    status: 'draft',
    directors: [],
    active_member_count: 1,
    business_unit_count: 0,
    onboarding_session_id: null,
    onboarding_current_step: '',
    can_continue_onboarding: false,
    ...overrides,
  }
}

const baseProps = {
  canCreate: false,
  onManage: vi.fn(),
  onAccessApp: vi.fn(),
  pendingAccessEstablishmentId: null as string | null,
  accessError: null as string | null,
  accessErrorEstablishmentId: null as string | null,
  onResume: vi.fn(),
  onCreate: vi.fn(),
}

describe('OrganizationEstablishmentsTab resume CTA', () => {
  it('shows resume only when can continue and session exists', () => {
    const onResume = vi.fn()
    render(
      <OrganizationEstablishmentsTab
        {...baseProps}
        establishments={[
          establishment({
            can_continue_onboarding: true,
            onboarding_session_id: 'session-1',
          }),
        ]}
        onResume={onResume}
      />,
    )
    expect(screen.getByRole('button', { name: /Reprendre la configuration/i })).toBeTruthy()
  })

  it('hides resume when session is missing', () => {
    render(
      <OrganizationEstablishmentsTab
        {...baseProps}
        establishments={[
          establishment({
            can_continue_onboarding: true,
            onboarding_session_id: null,
          }),
        ]}
      />,
    )
    expect(screen.queryByRole('button', { name: /Reprendre la configuration/i })).toBeNull()
  })
})

describe('OrganizationEstablishmentsTab access app CTA', () => {
  it('shows access app for active establishments and calls onAccessApp', () => {
    const onAccessApp = vi.fn()
    render(
      <OrganizationEstablishmentsTab
        {...baseProps}
        establishments={[
          establishment({
            id: 'est-active',
            name: 'Active Hotel',
            status: 'active',
          }),
        ]}
        onAccessApp={onAccessApp}
      />,
    )

    const button = screen.getByRole('button', { name: /Accéder à l'application/i })
    fireEvent.click(button)
    expect(onAccessApp).toHaveBeenCalledWith('est-active')
  })

  it('hides access app for draft establishments', () => {
    render(
      <OrganizationEstablishmentsTab
        {...baseProps}
        establishments={[
          establishment({
            status: 'draft',
            can_continue_onboarding: true,
            onboarding_session_id: 'session-1',
          }),
        ]}
      />,
    )
    expect(screen.queryByRole('button', { name: /Accéder à l'application/i })).toBeNull()
  })
})
