// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanDetail } from '@/features/action-plans/types'

import { ActionPlanTemplateDetailPage } from './action-plan-template-detail-page'

const detailQueryMock = vi.fn()
const navigateMock = vi.fn()
const useMutationMock = vi.fn()
const scheduleMutationMock = vi.fn()

function buildPlan(overrides: Partial<ActionPlanDetail> = {}): ActionPlanDetail {
  return {
    id: 'plan-1',
    title: 'Plan catalogue',
    description: 'Description',
    catalog_status: 'active',
    pilot_business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
    task_count: 1,
    involved_pole_count: 1,
    created_at: '2026-06-30T08:00:00Z',
    updated_at: '2026-06-30T10:00:00Z',
    created_by_id: 'member-1',
    created_by_display_name: 'Alice',
    requires_validation: true,
    is_reusable: true,
    tasks: [
      {
        id: 'task-1',
        task: 'Contrôler la température',
        description: 'Frigo',
        deadline_at: '2026-07-08T10:00:00Z',
        assigned_membership_id: 'member-2',
        assigned_display_name: 'Bob',
        position: 1,
        business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
      },
    ],
    permission_hints: {
      can_update: true,
      can_activate: false,
      can_deactivate: true,
      can_use: true,
      can_schedule: true,
    },
    ...overrides,
  }
}

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({
    navigate: navigateMock,
    route: { kind: 'action-plan-template-detail', actionPlanId: 'plan-1' },
  }),
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    activeMembership: {
      establishment_id: 'est-1',
      id: 'membership-1',
      role: 'manager',
    },
    bootstrap: {
      user: { username: 'manager_user' },
    },
  }),
}))

vi.mock('../hooks', () => ({
  useActionPlanDetailQuery: () => detailQueryMock(),
  useActivateActionPlanMutation: () => useMutationMock(),
  useDeactivateActionPlanMutation: () => useMutationMock(),
  useUseActionPlanMutation: () => useMutationMock(),
  useCreateActionPlanScheduleMutation: () => scheduleMutationMock(),
}))

describe('ActionPlanTemplateDetailPage', () => {
  beforeEach(() => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan(),
      refetch: vi.fn(),
    })
    useMutationMock.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    })
    scheduleMutationMock.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders read-only template detail with modifier action', () => {
    render(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    expect(screen.getByRole('heading', { name: 'Plan catalogue' })).toBeTruthy()
    expect(screen.getByText('Contrôler la température')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Modifier' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Exécution' })).toBeTruthy()
    expect(screen.queryByRole('textbox')).toBeNull()
  })

  it('renders catalog actions in sticky footer when panel is closed', () => {
    render(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    const modifierButton = screen.getByRole('button', { name: 'Modifier' })
    const executionButton = screen.getByRole('button', { name: 'Exécution' })

    expect(modifierButton.closest('footer')).toBeTruthy()
    expect(executionButton.closest('footer')).toBeTruthy()
  })

  it('opens planning panel and sticky launch actions', () => {
    render(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    fireEvent.click(screen.getByRole('button', { name: 'Exécution' }))

    expect(screen.getByRole('button', { name: 'Annuler' })).toBeTruthy()
    expect(screen.getByRole('button', { name: "Lancer l'exécution" })).toBeTruthy()
    expect(screen.getByText('Répéter')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Exécution' })).toBeNull()
  })

  it('hides repeat toggle when schedule is not allowed', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan({
        permission_hints: {
          can_update: true,
          can_activate: false,
          can_deactivate: true,
          can_use: true,
          can_schedule: false,
        },
      }),
      refetch: vi.fn(),
    })

    render(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    fireEvent.click(screen.getByRole('button', { name: 'Exécution' }))

    expect(screen.queryByText('Répéter')).toBeNull()
  })

  it('shows launch actions in sticky footer when execution panel is open', () => {
    render(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    fireEvent.click(screen.getByRole('button', { name: 'Exécution' }))

    const cancelButton = screen.getByRole('button', { name: 'Annuler' })
    const launchButton = screen.getByRole('button', { name: "Lancer l'exécution" })

    expect(cancelButton.closest('footer')).toBeTruthy()
    expect(launchButton.closest('footer')).toBeTruthy()
    expect(screen.getByText('Planification')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Modifier' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Exécution' })).toBeNull()
  })

  it('navigates to edit route from modifier button', () => {
    render(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    fireEvent.click(screen.getByRole('button', { name: 'Modifier' }))

    expect(navigateMock).toHaveBeenCalledWith('/action-plans/plan-1/edit')
  })

  it('hides primary launch action when per-assignee chronology is enabled', () => {
    render(createElement(ActionPlanTemplateDetailPage, { actionPlanId: 'plan-1' }))

    fireEvent.click(screen.getByRole('button', { name: 'Exécution' }))
    fireEvent.click(screen.getByRole('switch', { name: 'Chronologie par assigné' }))

    expect(screen.getByRole('button', { name: 'Annuler' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: "Lancer l'exécution" })).toBeNull()
  })
})
