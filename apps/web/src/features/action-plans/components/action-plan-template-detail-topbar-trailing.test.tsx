// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanDetail } from '@/features/action-plans/types'
import { notifySuccess } from '@/lib/success-toast'

import {
  ActionPlanTemplateDetailTopbarTrailing,
  DELETE_TEMPLATE_CONFIRM,
} from './action-plan-template-detail-topbar-trailing'

vi.mock('@/lib/success-toast', async () => {
  const actual = await vi.importActual<typeof import('@/lib/success-toast')>('@/lib/success-toast')
  return {
    ...actual,
    notifySuccess: vi.fn(),
  }
})

const detailQueryMock = vi.fn()
const navigateMock = vi.fn()
const deleteMutateAsyncMock = vi.fn()
const deleteMutationMock = vi.fn()

function buildPlan(overrides: Partial<ActionPlanDetail> = {}): ActionPlanDetail {
  return {
    id: 'plan-1',
    title: 'Plan catalogue',
    description: 'Description',
    catalog_status: 'active',
    pilot_business_unit: { id: 'bu-1', specific_name: 'Restaurant', instance_description: '', active: true, generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' } },
    task_count: 1,
    involved_pole_count: 1,
    created_at: '2026-06-30T08:00:00Z',
    updated_at: '2026-06-30T10:00:00Z',
    created_by_id: 'member-1',
    created_by_display_name: 'Alice',
    requires_validation: false,
    is_reusable: true,
    tasks: [],
    permission_hints: {
      can_update: true,
      can_activate: false,
      can_deactivate: false,
      can_delete: true,
      can_use: true,
      can_schedule: true,
    },
    ...overrides,
  }
}

function renderTrailing(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(createElement(QueryClientProvider, { client: queryClient }, ui))
}

vi.mock('../hooks', () => ({
  useActionPlanDetailQuery: () => detailQueryMock(),
  useDeleteActionPlanMutation: () => deleteMutationMock(),
}))

describe('ActionPlanTemplateDetailTopbarTrailing', () => {
  beforeEach(() => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan(),
      refetch: vi.fn(),
    })
    deleteMutateAsyncMock.mockResolvedValue(undefined)
    deleteMutationMock.mockReturnValue({
      mutateAsync: deleteMutateAsyncMock,
      isPending: false,
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    vi.restoreAllMocks()
  })

  it('shows edit pencil when can_update is granted', () => {
    renderTrailing(
      createElement(ActionPlanTemplateDetailTopbarTrailing, {
        establishmentId: 'est-1',
        actionPlanId: 'plan-1',
        onNavigate: navigateMock,
      }),
    )

    expect(screen.getByRole('button', { name: 'Modifier' })).toBeTruthy()
  })

  it('shows trash immediately to the right of pencil when can_delete is granted', () => {
    renderTrailing(
      createElement(ActionPlanTemplateDetailTopbarTrailing, {
        establishmentId: 'est-1',
        actionPlanId: 'plan-1',
        onNavigate: navigateMock,
      }),
    )

    const pencil = screen.getByRole('button', { name: 'Modifier' })
    const trash = screen.getByRole('button', { name: 'Supprimer' })
    expect(pencil.compareDocumentPosition(trash) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('hides trash when can_delete is false', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan({
        permission_hints: {
          can_update: true,
          can_activate: false,
          can_deactivate: false,
          can_delete: false,
          can_use: true,
          can_schedule: true,
        },
      }),
      refetch: vi.fn(),
    })

    renderTrailing(
      createElement(ActionPlanTemplateDetailTopbarTrailing, {
        establishmentId: 'est-1',
        actionPlanId: 'plan-1',
        onNavigate: navigateMock,
      }),
    )

    expect(screen.getByRole('button', { name: 'Modifier' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Supprimer' })).toBeNull()
  })

  it('hides edit pencil when can_update is false but keeps trash when can_delete', () => {
    detailQueryMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: buildPlan({
        permission_hints: {
          can_update: false,
          can_activate: false,
          can_deactivate: false,
          can_delete: true,
          can_use: true,
          can_schedule: true,
        },
      }),
      refetch: vi.fn(),
    })

    renderTrailing(
      createElement(ActionPlanTemplateDetailTopbarTrailing, {
        establishmentId: 'est-1',
        actionPlanId: 'plan-1',
        onNavigate: navigateMock,
      }),
    )

    expect(screen.queryByRole('button', { name: 'Modifier' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Supprimer' })).toBeTruthy()
  })

  it('navigates to edit route when pencil is clicked', () => {
    renderTrailing(
      createElement(ActionPlanTemplateDetailTopbarTrailing, {
        establishmentId: 'est-1',
        actionPlanId: 'plan-1',
        onNavigate: navigateMock,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Modifier' }))

    expect(navigateMock).toHaveBeenCalledWith('/action-plans/plan-1/edit')
  })

  it('opens confirmation and cancels without calling DELETE', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)

    renderTrailing(
      createElement(ActionPlanTemplateDetailTopbarTrailing, {
        establishmentId: 'est-1',
        actionPlanId: 'plan-1',
        onNavigate: navigateMock,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Supprimer' }))

    expect(window.confirm).toHaveBeenCalledWith(DELETE_TEMPLATE_CONFIRM)
    expect(deleteMutateAsyncMock).not.toHaveBeenCalled()
    expect(navigateMock).not.toHaveBeenCalled()
  })

  it('calls DELETE after confirmation then navigates to catalog', async () => {
    renderTrailing(
      createElement(ActionPlanTemplateDetailTopbarTrailing, {
        establishmentId: 'est-1',
        actionPlanId: 'plan-1',
        onNavigate: navigateMock,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Supprimer' }))

    expect(window.confirm).toHaveBeenCalledWith(DELETE_TEMPLATE_CONFIRM)
    await vi.waitFor(() => {
      expect(deleteMutateAsyncMock).toHaveBeenCalledTimes(1)
      expect(notifySuccess).toHaveBeenCalledWith({
        message: 'Modèle supprimé.',
        kind: 'deleted',
      })
      expect(navigateMock).toHaveBeenCalledWith('/action-plans')
    })
  })

  it('disables trash while delete is pending', () => {
    deleteMutationMock.mockReturnValue({
      mutateAsync: deleteMutateAsyncMock,
      isPending: true,
    })

    renderTrailing(
      createElement(ActionPlanTemplateDetailTopbarTrailing, {
        establishmentId: 'est-1',
        actionPlanId: 'plan-1',
        onNavigate: navigateMock,
      }),
    )

    expect(
      (screen.getByRole('button', { name: 'Supprimer' }) as HTMLButtonElement).disabled,
    ).toBe(true)
  })

  it('keeps user on page when DELETE fails', async () => {
    deleteMutateAsyncMock.mockRejectedValueOnce(new Error('Observation blocks delete'))

    renderTrailing(
      createElement(ActionPlanTemplateDetailTopbarTrailing, {
        establishmentId: 'est-1',
        actionPlanId: 'plan-1',
        onNavigate: navigateMock,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Supprimer' }))

    await vi.waitFor(() => {
      expect(deleteMutateAsyncMock).toHaveBeenCalledTimes(1)
    })
    expect(navigateMock).not.toHaveBeenCalled()
  })
})
