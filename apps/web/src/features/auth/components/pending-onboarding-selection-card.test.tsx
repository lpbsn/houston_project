// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { PendingOnboardingSelectionCard } from './pending-onboarding-selection-card'

afterEach(() => {
  cleanup()
})

describe('PendingOnboardingSelectionCard', () => {
  it('does not display draft-* technical establishment names', () => {
    render(
      createElement(PendingOnboardingSelectionCard, {
        pendingMemberships: [
          {
            id: 'm1',
            establishment_id: 'est-1',
            establishment_name: 'draft-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
            establishment_status: 'draft',
            organization_id: 'org-1',
            organization_name: 'Northwind Group',
            role: 'owner',
            onboarding_session_id: 'sess-1',
            can_continue_onboarding: true,
          },
        ],
        onContinueOnboarding: vi.fn(),
        onShowWaiting: vi.fn(),
      }),
    )

    expect(screen.getByText('Northwind Group')).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/draft-aaaaaaaa/i)
  })
})
