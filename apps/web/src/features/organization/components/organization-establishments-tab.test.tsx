// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
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

describe('OrganizationEstablishmentsTab resume CTA', () => {
  it('shows resume only when can continue and session exists', () => {
    const onResume = vi.fn()
    render(
      <OrganizationEstablishmentsTab
        establishments={[
          establishment({
            can_continue_onboarding: true,
            onboarding_session_id: 'session-1',
          }),
        ]}
        canCreate={false}
        onManage={vi.fn()}
        onResume={onResume}
        onCreate={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: /Reprendre la configuration/i })).toBeTruthy()
  })

  it('hides resume when session is missing', () => {
    render(
      <OrganizationEstablishmentsTab
        establishments={[
          establishment({
            can_continue_onboarding: true,
            onboarding_session_id: null,
          }),
        ]}
        canCreate={false}
        onManage={vi.fn()}
        onResume={vi.fn()}
        onCreate={vi.fn()}
      />,
    )
    expect(screen.queryByRole('button', { name: /Reprendre la configuration/i })).toBeNull()
  })
})
