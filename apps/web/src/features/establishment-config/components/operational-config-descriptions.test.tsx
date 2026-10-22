// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { BusinessUnitTreeItem } from '@/features/establishment-config/api'
import {
  ACTIVITY_DESCRIPTION_MAX_LENGTH,
  INSTANCE_DESCRIPTION_MAX_LENGTH,
} from '@/features/onboarding/lib/onboarding-draft-payload'

import { OperationalConfigActivityDescriptionCard } from './operational-config-activity-description-card'
import { OperationalConfigBusinessUnitCard } from './operational-config-business-unit-card'

const { activityState, updateActivity, updateBusinessUnit } = vi.hoisted(() => ({
  activityState: {
    description: 'Description déjà assez longue.',
  },
  updateActivity: vi.fn(async (description: string) => ({ description })),
  updateBusinessUnit: vi.fn(async () => ({})),
}))

vi.mock('@/features/establishment-config/hooks', () => ({
  useActivityDescription: () => ({
    data: { description: activityState.description },
    isPending: false,
    error: null,
    refetch: vi.fn(),
  }),
  useUpdateActivityDescription: () => ({
    isPending: false,
    mutateAsync: updateActivity,
  }),
  useUpdateRuntimeBusinessUnit: () => ({
    isPending: false,
    mutateAsync: updateBusinessUnit,
  }),
  useDeactivateRuntimeBusinessUnit: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useReactivateRuntimeBusinessUnit: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useCreateRuntimeActivitySubject: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useDeactivateRuntimeActivitySubject: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useReactivateRuntimeActivitySubject: () => ({ isPending: false, mutateAsync: vi.fn() }),
}))

function wrap(node: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return createElement(QueryClientProvider, { client }, node)
}

function businessUnit(
  instanceDescription: string,
  overrides: Partial<BusinessUnitTreeItem> = {},
): BusinessUnitTreeItem {
  return {
    id: 'bu-1',
    specific_name: 'Hôtel',
    instance_description: instanceDescription,
    active: true,
    generic: {
      key: 'hotel',
      label: 'Hôtel',
      description: '',
      unit_type: 'dedicated',
    },
    activity_subjects: [
      {
        id: 'subject-1',
        label: 'Accueil',
        description: '',
        source: 'manual',
        active: true,
        is_generic: true,
      },
    ],
    ...overrides,
  }
}

afterEach(() => {
  cleanup()
  activityState.description = 'Description déjà assez longue.'
  updateActivity.mockClear()
  updateBusinessUnit.mockClear()
})

describe('OperationalConfigActivityDescriptionCard', () => {
  it('keeps an empty description editable and refuses text over the ceiling', () => {
    activityState.description = ''
    render(wrap(createElement(OperationalConfigActivityDescriptionCard, { establishmentId: 'est-1' })))

    const field = screen.getByLabelText('Description') as HTMLTextAreaElement
    expect(field.value).toBe('')
    expect(screen.getByRole('button', { name: 'Enregistrer' }).hasAttribute('disabled')).toBe(true)

    fireEvent.change(field, { target: { value: 'court' } })
    expect(screen.getByText('La description doit contenir au moins 10 caractères.')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Enregistrer' }).hasAttribute('disabled')).toBe(true)

    fireEvent.change(field, { target: { value: '😀'.repeat(ACTIVITY_DESCRIPTION_MAX_LENGTH + 1) } })
    expect(screen.getByText(`${ACTIVITY_DESCRIPTION_MAX_LENGTH + 1} / ${ACTIVITY_DESCRIPTION_MAX_LENGTH}`)).toBeTruthy()
    expect(screen.getByText(/dépasse 10 000 caractères/)).toBeTruthy()
    expect(field.value).toContain('😀')
    expect(screen.getByRole('button', { name: 'Enregistrer' }).hasAttribute('disabled')).toBe(true)
    expect(updateActivity).not.toHaveBeenCalled()
  })

  it('saves a valid description without touching another mutation', async () => {
    render(wrap(createElement(OperationalConfigActivityDescriptionCard, { establishmentId: 'est-1' })))
    const field = screen.getByLabelText('Description')
    fireEvent.change(field, { target: { value: '  Hôtel avec jardin et salle.  ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    expect(updateActivity).toHaveBeenCalledWith('Hôtel avec jardin et salle.')
    expect(updateBusinessUnit).not.toHaveBeenCalled()
    expect(await screen.findByText('Description enregistrée.')).toBeTruthy()
  })

  it('adopts a refreshed description and does not save it back', () => {
    const view = render(
      wrap(createElement(OperationalConfigActivityDescriptionCard, { establishmentId: 'est-1' })),
    )

    activityState.description = 'Description actualisée par un autre directeur.'
    view.rerender(
      wrap(createElement(OperationalConfigActivityDescriptionCard, { establishmentId: 'est-1' })),
    )

    const field = screen.getByLabelText('Description') as HTMLTextAreaElement
    expect(field.value).toBe('Description actualisée par un autre directeur.')
    expect(screen.getByRole('button', { name: 'Enregistrer' }).hasAttribute('disabled')).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(updateActivity).not.toHaveBeenCalled()
  })

  it('keeps an unsaved description when a newer server value arrives', () => {
    const view = render(
      wrap(createElement(OperationalConfigActivityDescriptionCard, { establishmentId: 'est-1' })),
    )
    fireEvent.change(screen.getByLabelText('Description'), {
      target: { value: 'Brouillon local encore assez long.' },
    })

    activityState.description = 'Description actualisée par un autre directeur.'
    view.rerender(
      wrap(createElement(OperationalConfigActivityDescriptionCard, { establishmentId: 'est-1' })),
    )

    const field = screen.getByLabelText('Description') as HTMLTextAreaElement
    expect(field.value).toBe('Brouillon local encore assez long.')
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(updateActivity).toHaveBeenCalledWith('Brouillon local encore assez long.')
  })

  it('drops the previous establishment draft even when the server text matches', () => {
    const view = render(
      wrap(createElement(OperationalConfigActivityDescriptionCard, { establishmentId: 'est-1' })),
    )
    fireEvent.change(screen.getByLabelText('Description'), {
      target: { value: 'Brouillon local encore assez long.' },
    })

    view.rerender(
      wrap(createElement(OperationalConfigActivityDescriptionCard, { establishmentId: 'est-2' })),
    )

    const field = screen.getByLabelText('Description') as HTMLTextAreaElement
    expect(field.value).toBe('Description déjà assez longue.')
    expect(screen.getByRole('button', { name: 'Enregistrer' }).hasAttribute('disabled')).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(updateActivity).not.toHaveBeenCalled()
  })
})

describe('OperationalConfigBusinessUnitCard', () => {
  it('renames a pole whose historical description is over the ceiling', () => {
    render(
      wrap(
        createElement(OperationalConfigBusinessUnitCard, {
          establishmentId: 'est-1',
          businessUnit: businessUnit('H'.repeat(INSTANCE_DESCRIPTION_MAX_LENGTH + 1)),
          canRemoveBusinessUnit: false,
        }),
      ),
    )

    expect(
      screen.getByText(`${INSTANCE_DESCRIPTION_MAX_LENGTH + 1} / ${INSTANCE_DESCRIPTION_MAX_LENGTH}`),
    ).toBeTruthy()
    expect(screen.getByText(/Le nom peut être enregistré/)).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Nom d’instance'), { target: { value: 'Hôtel patio' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    expect(updateBusinessUnit).toHaveBeenCalledWith({
      businessUnitId: 'bu-1',
      input: { specific_name: 'Hôtel patio' },
    })
  })

  it('sends only the name when a rename leaves the description untouched', () => {
    render(
      wrap(
        createElement(OperationalConfigBusinessUnitCard, {
          establishmentId: 'est-1',
          businessUnit: businessUnit('Description du pôle déjà en place.'),
          canRemoveBusinessUnit: false,
        }),
      ),
    )

    fireEvent.change(screen.getByLabelText('Nom d’instance'), { target: { value: 'Hôtel patio' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    expect(updateBusinessUnit).toHaveBeenCalledWith({
      businessUnitId: 'bu-1',
      input: { specific_name: 'Hôtel patio' },
    })
  })

  it('sends only the description when the name was not edited', () => {
    render(
      wrap(
        createElement(OperationalConfigBusinessUnitCard, {
          establishmentId: 'est-1',
          businessUnit: businessUnit('Description du pôle déjà en place.'),
          canRemoveBusinessUnit: false,
        }),
      ),
    )

    fireEvent.change(screen.getByLabelText('Description d’instance'), {
      target: { value: 'Nouveau périmètre du pôle.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    expect(updateBusinessUnit).toHaveBeenCalledWith({
      businessUnitId: 'bu-1',
      input: { instance_description: 'Nouveau périmètre du pôle.' },
    })
  })

  it('keeps an unsaved name when the pole description is refreshed', () => {
    const view = render(
      wrap(
        createElement(OperationalConfigBusinessUnitCard, {
          establishmentId: 'est-1',
          businessUnit: businessUnit('Description initiale du pôle.'),
          canRemoveBusinessUnit: false,
        }),
      ),
    )
    fireEvent.change(screen.getByLabelText('Nom d’instance'), { target: { value: 'Hôtel patio' } })

    view.rerender(
      wrap(
        createElement(OperationalConfigBusinessUnitCard, {
          establishmentId: 'est-1',
          businessUnit: businessUnit('Description enregistrée par un directeur.'),
          canRemoveBusinessUnit: false,
        }),
      ),
    )

    expect((screen.getByLabelText('Nom d’instance') as HTMLInputElement).value).toBe('Hôtel patio')
    expect((screen.getByLabelText('Description d’instance') as HTMLTextAreaElement).value).toBe(
      'Description enregistrée par un directeur.',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(updateBusinessUnit).toHaveBeenCalledWith({
      businessUnitId: 'bu-1',
      input: { specific_name: 'Hôtel patio' },
    })
  })

  it('drops the previous pole draft when another pole is shown', () => {
    const view = render(
      wrap(
        createElement(OperationalConfigBusinessUnitCard, {
          establishmentId: 'est-1',
          businessUnit: businessUnit('Description du premier pôle.'),
          canRemoveBusinessUnit: false,
        }),
      ),
    )
    fireEvent.change(screen.getByLabelText('Nom d’instance'), { target: { value: 'Hôtel patio' } })
    fireEvent.change(screen.getByLabelText('Description d’instance'), {
      target: { value: 'Brouillon du premier pôle.' },
    })

    view.rerender(
      wrap(
        createElement(OperationalConfigBusinessUnitCard, {
          establishmentId: 'est-2',
          businessUnit: businessUnit('Description du second pôle.', {
            id: 'bu-2',
            specific_name: 'Spa',
          }),
          canRemoveBusinessUnit: false,
        }),
      ),
    )

    expect((screen.getByLabelText('Nom d’instance') as HTMLInputElement).value).toBe('Spa')
    expect((screen.getByLabelText('Description d’instance') as HTMLTextAreaElement).value).toBe(
      'Description du second pôle.',
    )
    expect(screen.getByRole('button', { name: 'Enregistrer' }).hasAttribute('disabled')).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(updateBusinessUnit).not.toHaveBeenCalled()
  })

  it('refuses to save a description that exceeds 5000 characters', () => {
    render(
      wrap(
        createElement(OperationalConfigBusinessUnitCard, {
          establishmentId: 'est-1',
          businessUnit: businessUnit('Déjà saisi'),
          canRemoveBusinessUnit: false,
        }),
      ),
    )

    fireEvent.change(screen.getByLabelText('Description d’instance'), {
      target: { value: '😀'.repeat(INSTANCE_DESCRIPTION_MAX_LENGTH + 1) },
    })
    expect(screen.getByText(/Raccourcissez-la pour l’enregistrer/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Enregistrer' }).hasAttribute('disabled')).toBe(true)
    expect(updateBusinessUnit).not.toHaveBeenCalled()
  })
})
