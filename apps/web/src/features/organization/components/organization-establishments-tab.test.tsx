// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { OrganizationEstablishmentsTab } from './organization-establishments-tab'
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
  onManage: vi.fn(),
  onAccessApp: vi.fn(),
  pendingAccessEstablishmentId: null as string | null,
  accessError: null as string | null,
  accessErrorEstablishmentId: null as string | null,
  onResume: vi.fn(),
}

describe('OrganizationEstablishmentsTab create action slot', () => {
  it('renders a provided create action', () => {
    render(
      <OrganizationEstablishmentsTab
        {...baseProps}
        establishments={[]}
        createAction={<button type="button">Ajouter un établissement</button>}
      />,
    )
    expect(screen.getByRole('button', { name: /Ajouter un établissement/i })).toBeTruthy()
  })

  it('hides create when no action is provided', () => {
    render(<OrganizationEstablishmentsTab {...baseProps} establishments={[]} />)
    expect(screen.queryByRole('button', { name: /Ajouter un établissement/i })).toBeNull()
  })
})

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

  it('shows a neutral label when the draft name is empty', () => {
    render(
      <OrganizationEstablishmentsTab
        {...baseProps}
        organizationName="Spore"
        establishments={[
          establishment({
            name: '',
            status: 'draft',
            can_continue_onboarding: true,
            onboarding_session_id: 'session-1',
          }),
        ]}
      />,
    )
    expect(screen.getByText('Spore')).toBeTruthy()
  })
})
