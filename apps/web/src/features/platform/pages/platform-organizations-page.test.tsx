// @vitest-environment jsdom

import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { PlatformOrganizationsPage } from './platform-organizations-page'

const listOrganizations = vi.fn()
const getOrganization = vi.fn()
const listEstablishments = vi.fn()
const listMemberships = vi.fn()
const deleteOrganization = vi.fn()
const routeState = vi.hoisted(() => ({
  search: '',
  navigate: vi.fn(),
}))

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({
    search: routeState.search,
    navigate: routeState.navigate,
  }),
}))

vi.mock('@/features/platform/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/platform/api')>()
  return {
    ...actual,
    listPlatformOrganizations: (...args: unknown[]) => listOrganizations(...args),
    getPlatformOrganization: (...args: unknown[]) => getOrganization(...args),
    listPlatformEstablishments: (...args: unknown[]) => listEstablishments(...args),
    listPlatformMemberships: (...args: unknown[]) => listMemberships(...args),
    deletePlatformOrganization: (...args: unknown[]) => deleteOrganization(...args),
  }
})

function renderPage(resourceId?: string) {
  const queryClient = createTestQueryClient()
  const wrap = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
  return render(createElement(PlatformOrganizationsPage, { resourceId }), { wrapper: wrap })
}

function installDialogPolyfill() {
  if (typeof HTMLDialogElement === 'undefined') {
    return
  }
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute('open', '')
  }
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute('open')
    this.dispatchEvent(new Event('close'))
  }
}

describe('PlatformOrganizationsPage', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    installDialogPolyfill()
    routeState.search = '?q=acme'
    routeState.navigate.mockReset()
    listOrganizations.mockReset()
    getOrganization.mockReset()
    listEstablishments.mockReset()
    listMemberships.mockReset()
    deleteOrganization.mockReset()
    listMemberships.mockResolvedValue({ next_cursor: null, results: [] })
  })

  it('preserves q on list resource links', async () => {
    listOrganizations.mockResolvedValue({
      next_cursor: null,
      results: [{ id: 'org-1', name: 'Acme', status: 'active' }],
    })
    renderPage()
    expect((await screen.findByRole('link', { name: 'Acme' })).getAttribute('href')).toBe(
      '/platform/organizations/org-1?q=acme',
    )
  })

  it('loads relational establishments by organization_id instead of embedded detail.establishments', async () => {
    getOrganization.mockResolvedValue({
      id: 'org-1',
      name: 'Acme',
      status: 'active',
      has_been_operational: false,
      created_at: '2026-01-01T00:00:00.000Z',
      updated_at: '2026-01-01T00:00:00.000Z',
      can_delete: false,
      blocking_reasons: ['has_active_membership'],
      establishments: [{ id: 'embedded', name: 'Should not render', status: 'draft' }],
    })
    listEstablishments.mockResolvedValue({
      next_cursor: 'e2',
      results: [{ id: 'est-1', name: 'From list', status: 'draft' }],
    })
    renderPage('org-1')

    expect(await screen.findByRole('link', { name: 'From list' })).toBeTruthy()
    expect(screen.queryByText('Should not render')).toBeNull()
    expect(listEstablishments).toHaveBeenCalledWith('', {
      cursor: undefined,
      organization_id: 'org-1',
    })
    expect(screen.getByRole('button', { name: 'Charger plus' })).toBeTruthy()
    expect((screen.getByRole('link', { name: 'Organisations' }) as HTMLAnchorElement).href).toContain(
      '/platform/organizations?q=acme',
    )
  })

  it('shows blocking reasons without a delete action', async () => {
    getOrganization.mockResolvedValue({
      id: 'org-1',
      name: 'Acme',
      status: 'active',
      has_been_operational: true,
      created_at: '2026-01-01T00:00:00.000Z',
      updated_at: '2026-01-01T00:00:00.000Z',
      can_delete: false,
      blocking_reasons: ['has_been_operational'],
      establishments: [],
    })
    listEstablishments.mockResolvedValue({ next_cursor: null, results: [] })
    renderPage('org-1')

    expect(await screen.findByTestId('platform-delete-blocked')).toBeTruthy()
    expect(screen.getByText('has_been_operational')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Supprimer l’organisation' })).toBeNull()
  })

  it('opens a delete dialog, blocks close while pending, then returns to the list', async () => {
    getOrganization.mockResolvedValue({
      id: 'org-1',
      name: 'Acme',
      status: 'active',
      has_been_operational: false,
      created_at: '2026-01-01T00:00:00.000Z',
      updated_at: '2026-01-01T00:00:00.000Z',
      can_delete: true,
      blocking_reasons: [],
      establishments: [],
    })
    listEstablishments.mockResolvedValue({ next_cursor: null, results: [] })
    let resolveDelete: (value?: unknown) => void = () => undefined
    deleteOrganization.mockReturnValue(
      new Promise((resolve) => {
        resolveDelete = resolve
      }),
    )
    renderPage('org-1')

    fireEvent.click(await screen.findByRole('button', { name: 'Supprimer l’organisation' }))
    expect(await screen.findByRole('dialog')).toBeTruthy()
    fireEvent.change(screen.getByPlaceholderText('Justification'), {
      target: { value: 'abandon' },
    })
    fireEvent.click(screen.getAllByRole('button', { name: 'Supprimer l’organisation' })[1])

    await waitFor(() => {
      expect((screen.getByRole('button', { name: 'Annuler' }) as HTMLButtonElement).disabled).toBe(
        true,
      )
    })
    resolveDelete()
    await waitFor(() => {
      expect(deleteOrganization.mock.calls[0]?.slice(0, 2)).toEqual(['org-1', 'abandon'])
    })
    await waitFor(() => {
      expect(routeState.navigate).toHaveBeenCalledWith('/platform/organizations?q=acme')
    })
  })
})
