// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { TerrainTopbar } from '@/components/layout/terrain-topbar'
import type { ActionPlanListItem } from '../types'

import { ActionPlanHubPage } from './action-plan-hub-page'

const navigate = vi.fn()
const catalogQueryMock = vi.fn()

const { mockAuthState } = vi.hoisted(() => ({
  mockAuthState: {
    isReady: true,
    isBootstrapping: false,
    bootstrap: {
      permission_hints: {
        chat_available: false,
        can_create_action_plan: true,
        can_create_catalog_action_plan: true,
        can_view_action_plan_catalog: true,
        can_invite: false,
        can_manage_runtime_config: false,
      },
    },
    activeMembership: {
      id: 'member-manager',
      establishment_id: 'est-1',
      role: 'manager',
    },
  },
}))

function buildListItem(
  partial: Partial<ActionPlanListItem> & Pick<ActionPlanListItem, 'id'>,
): ActionPlanListItem {
  return {
    title: 'Réassort bar hebdomadaire',
    description: 'Contrôle des stocks.',
    catalog_status: 'active',
    pilot_business_unit: {
      id: 'bu-1',
      specific_name: 'Bar',
      instance_description: '',
      active: true,
      generic: { key: 'bar', label: 'Bar', description: '', unit_type: 'dedicated' },
    },
    task_count: 3,
    involved_pole_count: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    permission_hints: {
      can_update: false,
      can_activate: false,
      can_deactivate: false,
      can_delete: false,
      can_use: true,
      can_schedule: false,
    },
    ...partial,
  }
}

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({ navigate }),
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => mockAuthState,
}))

vi.mock('@/features/auth/hooks', () => ({
  useBusinessUnitTreeQuery: () => ({
    data: { business_units: [] },
    isLoading: false,
    isError: false,
  }),
}))

vi.mock('../hooks', () => ({
  useActionPlanCatalogQuery: () => catalogQueryMock(),
  useSubmitActionPlanPlanningMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}))

vi.mock('../components/action-plan-use-sheet', () => ({
  ActionPlanUseSheet: ({ open }: { open: boolean }) =>
    open ? createElement('div', { role: 'dialog' }, 'Planification du modèle') : null,
}))

function renderHub() {
  return render(
    createElement(
      'div',
      null,
      createElement(TerrainTopbar, {
        variant: 'detail',
        title: 'Bibliothèque',
        onBack: () => undefined,
      }),
      createElement(ActionPlanHubPage),
    ),
  )
}

function enableDesktopWeb() {
  vi.stubEnv('VITE_APP_RUNTIME', 'web')
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: query.includes('1024'),
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

describe('ActionPlanHubPage', () => {
  beforeEach(() => {
    mockAuthState.isReady = true
    mockAuthState.isBootstrapping = false
    mockAuthState.activeMembership.role = 'manager'
    mockAuthState.activeMembership.id = 'member-manager'
    mockAuthState.bootstrap.permission_hints.can_view_action_plan_catalog = true
    mockAuthState.bootstrap.permission_hints.can_create_catalog_action_plan = true
    catalogQueryMock.mockReturnValue({
      data: [buildListItem({ id: 'plan-1' })],
      isLoading: false,
      isError: false,
    })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    vi.unstubAllEnvs()
    Reflect.deleteProperty(window, 'matchMedia')
  })

  it('keeps the library title in the topbar and hides the content heading', () => {
    renderHub()

    expect(screen.queryByRole('heading', { name: 'Bibliothèque' })).toBeNull()
    expect(screen.getByText('Bibliothèque')).toBeTruthy()
    expect(screen.getByTestId('action-plan-hub-frame').querySelector('h1')).toBeNull()
    expect(screen.getByText('Réassort bar hebdomadaire')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Tous les pôles' }).getAttribute('aria-pressed')).toBe(
      'true',
    )
  })

  it('navigates to catalog create from the topbar action only', () => {
    renderHub()

    const createButton = screen.getByRole('button', { name: 'Créer un plan d’action' })
    expect(screen.getByTestId('action-plan-hub-frame').contains(createButton)).toBe(false)
    fireEvent.click(createButton)
    expect(navigate).toHaveBeenCalledWith('/action-plans/new')
  })

  it('opens the launch route when using a catalog plan', () => {
    renderHub()

    fireEvent.click(screen.getByRole('button', { name: 'Utiliser ce plan' }))
    expect(navigate).toHaveBeenCalledWith('/action-plans/plan-1/use')
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('keeps the desktop library heading, content create action, filters, and use sheet', () => {
    enableDesktopWeb()
    renderHub()

    expect(screen.getByRole('heading', { name: 'Bibliothèque' })).toBeTruthy()
    const createButton = screen.getByRole('button', { name: 'Créer un plan d’action' })
    expect(screen.getByTestId('action-plan-hub-frame').contains(createButton)).toBe(true)
    expect(screen.getByRole('button', { name: 'Tous les pôles' }).hasAttribute('aria-pressed')).toBe(
      false,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Utiliser ce plan' }))
    expect(screen.getByRole('dialog')).toBeTruthy()
    expect(navigate).not.toHaveBeenCalledWith('/action-plans/plan-1/use')
  })

  it('blocks catalog access when the viewer cannot see the library', () => {
    mockAuthState.bootstrap.permission_hints.can_view_action_plan_catalog = false
    mockAuthState.activeMembership.role = 'staff'

    render(createElement(ActionPlanHubPage))

    expect(
      screen.getByText("Vous n'avez pas accès à la bibliothèque de plans d'action."),
    ).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Bibliothèque' })).toBeNull()
  })

  it('shows staff empty copy when no catalog plans are available', () => {
    mockAuthState.activeMembership.role = 'staff'
    mockAuthState.bootstrap.permission_hints.can_create_catalog_action_plan = false
    catalogQueryMock.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    })

    render(createElement(ActionPlanHubPage))

    expect(screen.getByText('Aucun modèle actif disponible pour votre pôle.')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Créer un plan d’action' })).toBeNull()
  })

  it('keeps a single catalog column and an iconic create action on wide native', () => {
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: true,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })

    renderHub()

    expect(screen.getByTestId('action-plan-catalog-grid').className).not.toContain('lg:grid-cols-2')
    expect(screen.getByTestId('action-plan-catalog-grid').className).not.toContain('xl:grid-cols-3')
    const createButton = screen.getByRole('button', { name: 'Créer un plan d’action' })
    expect(screen.getByTestId('action-plan-hub-frame').contains(createButton)).toBe(false)
    expect(createButton.className).not.toContain('lg:w-auto')
    expect(createButton.querySelector('span')).toBeNull()
    expect(screen.getByTestId('action-plan-hub-pole-filters').className).toContain('overflow-x-auto')
    expect(screen.getByTestId('action-plan-hub-pole-filters').className).not.toContain('lg:flex-wrap')
    expect(screen.getByRole('button', { name: 'Utiliser ce plan' }).className).not.toContain('lg:h-9')
  })
})
