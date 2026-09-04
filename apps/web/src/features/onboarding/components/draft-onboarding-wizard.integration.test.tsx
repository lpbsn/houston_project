/** @vitest-environment jsdom */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  canCompleteOnboardingDraft,
  removeBusinessUnitFromDraft,
} from '../lib/onboarding-draft-validation'
import {
  applyCatalogBusinessUnitSelection,
  createEmptyBusinessUnit,
} from '../lib/onboarding-draft-catalog'
import {
  emptyOnboardingDraftPayload,
  parseOnboardingDraftPayload,
  stripEmptyMemberRows,
  withCurrentStep,
} from '../lib/onboarding-draft-payload'

const putMock = vi.fn()
const completeMock = vi.fn()
const navigate = vi.fn()
const fetchBootstrapMock = vi.fn()

vi.mock('@/features/onboarding/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/onboarding/api')>()
  return {
    ...actual,
    getOnboardingDraft: vi.fn(async () => ({
      id: 'draft-1',
      onboarding_session_id: 'session-1',
      updated_at: new Date().toISOString(),
      payload: emptyOnboardingDraftPayload(),
      validation: { mode: 'soft', is_ready_for_complete: false, errors: [] },
    })),
    putOnboardingDraft: (...args: unknown[]) => putMock(...args),
    completeOnboardingSession: (...args: unknown[]) => completeMock(...args),
    suggestBusinessUnits: vi.fn(async () => [
      {
        key: 'restaurant',
        label: 'Restaurant',
        description: 'Resto',
        unit_type: 'dedicated',
      },
    ]),
    suggestActivitySubjects: vi.fn(async () => [
      {
        key: 'restaurant__stock',
        label: 'Stock',
        business_unit_key: 'restaurant',
      },
    ]),
  }
})

vi.mock('@/features/auth/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/auth/api')>()
  return {
    ...actual,
    fetchBootstrap: (...args: unknown[]) => fetchBootstrapMock(...args),
  }
})

import { DraftOnboardingWizard } from '../components/draft-onboarding-wizard'

function stubLgViewport(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

function multiMembershipBootstrapWithoutActive() {
  const membership = (establishmentId: string) => ({
    id: `membership-${establishmentId}`,
    establishment_id: establishmentId,
    establishment_name: `Hotel ${establishmentId}`,
    organization_id: 'org-1',
    organization_name: 'Org',
    role: 'director' as const,
    status: 'active' as const,
    scopes: [],
    scope_summary: { business_unit_count: 0 },
  })
  return {
    authenticated: true,
    user: {
      id: '11111111-1111-1111-1111-111111111111',
      username: 'director',
      email: 'director@example.com',
      identity_type: 'human',
    },
    memberships: [membership('est-1'), membership('est-2')],
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
      can_manage_organization: false,
      can_create_establishment: false,
    },
  }
}

async function fillAndFinishWizard() {
  await screen.findByTestId('draft-onboarding-wizard')

  fireEvent.click(screen.getByRole('button', { name: /Ajouter un pôle/i }))
  fireEvent.change(screen.getByPlaceholderText(/Le Grand Hôtel Central/i), {
    target: { value: 'Hôtel Test' },
  })
  fireEvent.change(screen.getByPlaceholderText(/Décrivez votre établissement/i), {
    target: { value: 'Description assez longue pour valider le minimum requis.' },
  })

  const catalogChip = await screen.findByRole('button', { name: /Restaurant/i })
  fireEvent.click(catalogChip)

  await waitFor(() => {
    expect(screen.getByText(/Stock/i)).toBeTruthy()
  })

  const continueButton = screen.getByRole('button', { name: /Continuer/i })
  await waitFor(() => {
    expect((continueButton as HTMLButtonElement).disabled).toBe(false)
  })
  fireEvent.click(continueButton)

  await screen.findByRole('heading', { name: /Invitez votre équipe/i })
  const directorSection = screen.getByText(/Directeur \(obligatoire\)/i).parentElement!
  const inputs = directorSection.querySelectorAll('input')
  fireEvent.change(inputs[0]!, { target: { value: 'Ada' } })
  fireEvent.change(inputs[1]!, { target: { value: 'Lovelace' } })
  fireEvent.change(inputs[2]!, { target: { value: 'ada@example.com' } })

  const finishButton = screen.getByRole('button', { name: /Terminer/i })
  await waitFor(() => {
    expect((finishButton as HTMLButtonElement).disabled).toBe(false)
  })
  fireEvent.click(finishButton)
}

function renderWizard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)

  return render(
    createElement(DraftOnboardingWizard, { sessionId: 'session-1', onNavigate: navigate }),
    { wrapper },
  )
}

describe('draft onboarding integration', () => {
  beforeEach(() => {
    putMock.mockReset()
    completeMock.mockReset()
    navigate.mockReset()
    fetchBootstrapMock.mockReset()

    putMock.mockImplementation(async (_sessionId: string, payload: unknown) => ({
      id: 'draft-1',
      onboarding_session_id: 'session-1',
      updated_at: new Date().toISOString(),
      payload,
      validation: { mode: 'soft', is_ready_for_complete: true, errors: [] },
    }))
    completeMock.mockResolvedValue({
      session: { id: 'session-1', status: 'activated' },
      activation_summary: {},
      activated: true,
      idempotent: false,
    })
    fetchBootstrapMock.mockResolvedValue({
      active_membership: { id: 'm1' },
      memberships: [{ id: 'm1' }],
      pending_onboarding_memberships: [],
      permission_hints: {},
    })
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
  })

  it('supports hydrate → edit → catalog seed → continue → complete → redirect', async () => {
    renderWizard()

    await screen.findByTestId('draft-onboarding-wizard')
    expect(screen.getByTestId('onboarding-stepper')).toBeTruthy()
    expect(screen.getByTestId('onboarding-step-organization').getAttribute('data-state')).toBe(
      'done',
    )
    expect(screen.getByTestId('onboarding-step-structure').getAttribute('data-state')).toBe(
      'current',
    )
    expect(document.body.textContent).not.toMatch(/draft-[0-9a-f-]+/i)

    fireEvent.click(screen.getByRole('button', { name: /Ajouter un pôle/i }))
    fireEvent.change(screen.getByPlaceholderText(/Le Grand Hôtel Central/i), {
      target: { value: 'Hôtel Test' },
    })
    fireEvent.change(screen.getByPlaceholderText(/Décrivez votre établissement/i), {
      target: { value: 'Description assez longue pour valider le minimum requis.' },
    })

    const catalogChip = await screen.findByRole('button', { name: /Restaurant/i })
    fireEvent.click(catalogChip)

    await waitFor(() => {
      expect(screen.getByText(/Stock/i)).toBeTruthy()
    })

    const continueButton = screen.getByRole('button', { name: /Continuer/i })
    await waitFor(() => {
      expect((continueButton as HTMLButtonElement).disabled).toBe(false)
    })
    fireEvent.click(continueButton)

    await waitFor(() => {
      expect(putMock).toHaveBeenCalled()
      const lastPayload = putMock.mock.calls.at(-1)?.[1] as { current_step?: string }
      expect(lastPayload.current_step).toBe('team')
    })

    await screen.findByRole('heading', { name: /Invitez votre équipe/i })
    const directorSection = screen.getByText(/Directeur \(obligatoire\)/i).parentElement!
    const inputs = directorSection.querySelectorAll('input')
    fireEvent.change(inputs[0]!, { target: { value: 'Ada' } })
    fireEvent.change(inputs[1]!, { target: { value: 'Lovelace' } })
    fireEvent.change(inputs[2]!, { target: { value: 'ada@example.com' } })

    const finishButton = screen.getByRole('button', { name: /Terminer/i })
    await waitFor(() => {
      expect((finishButton as HTMLButtonElement).disabled).toBe(false)
    })
    fireEvent.click(finishButton)

    await waitFor(() => {
      expect(completeMock).toHaveBeenCalled()
      expect(navigate).toHaveBeenCalledWith('/reporting')
    })
  })

  it('lands native large-viewport complete on the selector, not desktop cross', async () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    stubLgViewport(true)
    fetchBootstrapMock.mockResolvedValue(multiMembershipBootstrapWithoutActive())

    renderWizard()
    await fillAndFinishWizard()

    await waitFor(() => {
      expect(completeMock).toHaveBeenCalled()
      expect(navigate).toHaveBeenCalledWith('/select-establishment')
    })
    expect(navigate).not.toHaveBeenCalledWith('/cross?period=7d')
  })

  it('blocks complete after deleting a pole that removed member scopes', () => {
    const bu = createEmptyBusinessUnit()
    let payload = emptyOnboardingDraftPayload()
    payload.establishment = {
      name: 'Hôtel',
      description: 'Description assez longue pour valider.',
    }
    payload.business_units = [
      {
        ...bu,
        catalog_key: 'restaurant',
        specific_name: 'Restaurant',
      },
    ]
    payload = applyCatalogBusinessUnitSelection(
      payload,
      bu.client_key,
      { key: 'restaurant', label: 'Restaurant', unit_type: 'dedicated' },
      [{ key: 'restaurant__stock', label: 'Stock', business_unit_key: 'restaurant' }],
    )
    payload.team.director = {
      email: 'dir@example.com',
      first_name: 'Ada',
      last_name: 'Lovelace',
    }
    payload.team.members = [
      {
        email: 'm@example.com',
        first_name: 'Sam',
        last_name: 'Staff',
        role: 'staff',
        business_unit_client_keys: [bu.client_key],
      },
    ]

    expect(canCompleteOnboardingDraft(payload).ok).toBe(true)
    payload = removeBusinessUnitFromDraft(payload, bu.client_key)
    expect(payload.team.members[0]?.business_unit_client_keys).toEqual([])
    expect(canCompleteOnboardingDraft(payload).ok).toBe(false)

    const stripped = stripEmptyMemberRows(withCurrentStep(payload, 'team'))
    expect(parseOnboardingDraftPayload(stripped).team.members).toHaveLength(1)
  })
})
