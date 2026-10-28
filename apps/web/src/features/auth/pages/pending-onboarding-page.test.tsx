// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PendingOnboardingMembership } from '@/features/auth/lib/pending-onboarding'
import type { Membership } from '@/features/auth/types'
import { PendingOnboardingPage } from '@/features/auth/pages/pending-onboarding-page'

function pending(id: string, name: string): PendingOnboardingMembership {
  return {
    id,
    establishment_id: id,
    establishment_name: name,
    establishment_status: 'draft',
    organization_id: 'org-1',
    organization_name: 'Org',
    role: 'owner',
    onboarding_session_id: null,
  }
}

afterEach(() => {
  cleanup()
})

describe('PendingOnboardingPage', () => {
  it('opens install from a single pending establishment', () => {
    const onNavigate = vi.fn()
    render(
      createElement(PendingOnboardingPage, {
        pendingMemberships: [pending('est-1', 'Hôtel des Mésanges')],
        memberships: [],
        onNavigate,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: /options d.installation/i }))
    expect(onNavigate).toHaveBeenCalledWith('/acces')
  })

  it('shows the same install step after choosing one of several establishments', () => {
    const onNavigate = vi.fn()
    render(
      createElement(PendingOnboardingPage, {
        pendingMemberships: [pending('est-1', 'Hôtel des Mésanges'), pending('est-2', 'Maison Blanche')],
        memberships: [],
        onNavigate,
      }),
    )

    expect(screen.getByText('Choisissez un établissement')).toBeTruthy()
    fireEvent.click(screen.getAllByRole('button', { name: /voir le statut/i })[0]!)
    fireEvent.click(screen.getByRole('button', { name: /options d.installation/i }))
    expect(onNavigate).toHaveBeenCalledWith('/acces')
  })

  it('keeps the empty states', () => {
    const { unmount } = render(
      createElement(PendingOnboardingPage, {
        pendingMemberships: [],
        memberships: [],
        onNavigate: vi.fn(),
      }),
    )
    expect(screen.getByText(/Aucun établissement en attente/)).toBeTruthy()
    unmount()

    render(
      createElement(PendingOnboardingPage, {
        pendingMemberships: [],
        memberships: [{} as Membership],
        onNavigate: vi.fn(),
      }),
    )
    expect(screen.getByText(/Aucun établissement en cours de configuration/)).toBeTruthy()
  })
})
