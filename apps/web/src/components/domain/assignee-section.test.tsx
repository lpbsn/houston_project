// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'
import type { ScopedUserSearchResult } from '@/features/users/types'

import { AssigneeSection, POLE_MEMBER_SUGGESTIONS_LABEL } from './assignee-section'

const searchEstablishmentUsers = vi.fn()

vi.mock('@/features/users/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/users/api')>()
  return {
    ...actual,
    searchEstablishmentUsers: (...args: unknown[]) => searchEstablishmentUsers(...args),
  }
})

const marie: ScopedUserSearchResult = {
  id: 'user-1',
  membership_id: 'member-1',
  display_name: 'Marie Dupont',
  username: 'marie',
  email: 'marie@example.com',
  role: 'staff',
  business_unit_ids: ['bu-1'],
}

const paul: ScopedUserSearchResult = {
  id: 'user-2',
  membership_id: 'member-2',
  display_name: 'Paul Martin',
  username: 'paul',
  email: 'paul@example.com',
  role: 'manager',
  business_unit_ids: ['bu-1'],
}

function renderWithQuery(ui: ReactNode) {
  return render(
    createElement(QueryClientProvider, { client: createTestQueryClient() }, ui),
  )
}

describe('AssigneeSection', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    searchEstablishmentUsers.mockReset()
    searchEstablishmentUsers.mockImplementation((_establishmentId: string, query: string) => {
      if (!query) {
        return Promise.resolve([marie])
      }
      return Promise.resolve([paul])
    })
  })

  it('loads pole member suggestions when opted in', async () => {
    renderWithQuery(
      createElement(AssigneeSection, {
        mode: 'multiple',
        establishmentId: 'est-1',
        businessUnitId: 'bu-1',
        showPoleMemberSuggestions: true,
        assigneeIds: [],
        selectedUsers: [],
        onAssigneesChange: vi.fn(),
      }),
    )

    await waitFor(() => {
      expect(screen.getByRole('listbox', { name: POLE_MEMBER_SUGGESTIONS_LABEL })).toBeTruthy()
    })
    expect(screen.getByText(POLE_MEMBER_SUGGESTIONS_LABEL)).toBeTruthy()
    expect(screen.getByRole('option', { name: /Marie Dupont/ })).toBeTruthy()
    expect(searchEstablishmentUsers).toHaveBeenCalledWith('est-1', '', {
      businessUnitId: 'bu-1',
    })
  })

  it('switches to search results after two characters when opted in', async () => {
    renderWithQuery(
      createElement(AssigneeSection, {
        mode: 'multiple',
        establishmentId: 'est-1',
        businessUnitId: 'bu-1',
        showPoleMemberSuggestions: true,
        assigneeIds: [],
        selectedUsers: [],
        onAssigneesChange: vi.fn(),
      }),
    )

    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Marie Dupont/ })).toBeTruthy()
    })

    fireEvent.change(screen.getByPlaceholderText('Rechercher un membre…'), {
      target: { value: 'pa' },
    })

    await waitFor(() => {
      expect(screen.getByRole('listbox', { name: 'Résultats de recherche' })).toBeTruthy()
    })
    expect(screen.getByRole('option', { name: /Paul Martin/ })).toBeTruthy()
    expect(screen.queryByText(POLE_MEMBER_SUGGESTIONS_LABEL)).toBeNull()
  })

  it('does not fetch empty-query suggestions without the opt-in flag', () => {
    renderWithQuery(
      createElement(AssigneeSection, {
        mode: 'multiple',
        establishmentId: 'est-1',
        businessUnitId: 'bu-1',
        assigneeIds: [],
        selectedUsers: [],
        onAssigneesChange: vi.fn(),
      }),
    )

    expect(searchEstablishmentUsers).not.toHaveBeenCalled()
    expect(screen.queryByRole('listbox')).toBeNull()
  })
})
