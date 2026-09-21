// @vitest-environment jsdom

import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { NoEstablishmentPage } from './no-establishment-page'
import type { BootstrapResponse, Membership } from '@/features/auth/types'

function membership(overrides: Partial<Membership> = {}): Membership {
  return {
    id: overrides.id ?? 'membership-1',
    establishment_id: overrides.establishment_id ?? 'est-1',
    establishment_name: overrides.establishment_name ?? 'Spore Paris',
    organization_id: overrides.organization_id ?? 'org-1',
    organization_name: overrides.organization_name ?? 'Spore',
    role: overrides.role ?? 'owner',
    status: overrides.status ?? 'active',
    chat_available: overrides.chat_available ?? true,
    scopes: [],
    scope_summary: { business_unit_count: 0 },
  }
}

function bootstrap(
  hints: Partial<BootstrapResponse['permission_hints']> = {},
): BootstrapResponse {
  return {
    authenticated: true,
    user: {
      id: 'user-1',
      username: 'marie',
      email: 'marie@example.com',
      identity_type: 'human',
      first_name: 'Marie',
      last_name: 'Renaud',
      pending_email: null,
      pending_email_expires_at: null,
      terms_version: 'cgu-v1',
      terms_accepted_at: '2026-01-01T00:00:00.000Z',
      current_terms_version: 'cgu-v1',
      needs_terms_acceptance: false,
      ai_consent_version: 'openai-v1',
      ai_processing_consented_at: '2026-01-01T00:00:00.000Z',
      current_ai_consent_version: 'openai-v1',
      needs_ai_consent: false,
      ai_consent_status: 'granted',
    },
    memberships: [membership()],
    active_membership: null,
    pending_onboarding_memberships: [],
    permission_hints: {
      chat_available: false,
      can_create_action_plan: false,
      can_create_catalog_action_plan: false,
      can_view_action_plan_catalog: false,
      can_invite: false,
      can_manage_runtime_config: false,
      can_view_team: false,
      can_manage_organization: true,
      platform_operator_active: false,
      ...hints,
    },
  }
}

afterEach(() => {
  cleanup()
})

describe('NoEstablishmentPage', () => {
  it('does not offer client establishment creation', () => {
    render(
      createElement(
        QueryClientProvider,
        { client: new QueryClient({ defaultOptions: { queries: { retry: false } } }) },
        createElement(NoEstablishmentPage, {
          bootstrap: bootstrap(),
          navigate: () => undefined,
        }),
      ),
    )

    expect(screen.queryByRole('button', { name: /Ajouter un établissement/i })).toBeNull()
  })

  it('asks a platform operator to use desktop web', () => {
    render(
      createElement(
        QueryClientProvider,
        { client: new QueryClient({ defaultOptions: { queries: { retry: false } } }) },
        createElement(NoEstablishmentPage, {
          bootstrap: bootstrap({ platform_operator_active: true }),
          navigate: () => undefined,
        }),
      ),
    )

    expect(screen.getByText(/ordinateur/i)).toBeTruthy()
  })
})
