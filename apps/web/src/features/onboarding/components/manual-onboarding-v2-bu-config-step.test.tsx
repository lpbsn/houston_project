// @vitest-environment jsdom

import { createElement, useState } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ManualOnboardingV2BuConfigStep } from '@/features/onboarding/components/manual-onboarding-v2-bu-config-step'
import {
  buildManualV2Payload,
  createDraftActivitySubject,
  createDraftBusinessUnit,
  updateBusinessUnitLabel,
  type DraftActivitySubject,
  type DraftBusinessUnit,
} from '@/features/onboarding/lib/manual-v2-proposal'

vi.mock('@/features/onboarding/hooks', () => ({
  useActivitySubjectSuggestions: () => ({
    data: [],
    isFetching: false,
  }),
}))

afterEach(() => {
  cleanup()
})

function ConfigStepHarness({
  initialBusinessUnits,
  initialActivitySubjects,
  onPayload,
}: {
  initialBusinessUnits: DraftBusinessUnit[]
  initialActivitySubjects: DraftActivitySubject[]
  onPayload: (payload: ReturnType<typeof buildManualV2Payload>) => void
}) {
  const [businessUnits, setBusinessUnits] = useState(initialBusinessUnits)
  const [activitySubjects, setActivitySubjects] = useState(initialActivitySubjects)

  return createElement(ManualOnboardingV2BuConfigStep, {
    businessUnits,
    activitySubjects,
    onBusinessUnitDescriptionChange: () => undefined,
    onBusinessUnitLabelChange: (clientKey, label) => {
      const next = updateBusinessUnitLabel(businessUnits, clientKey, label)
      setBusinessUnits(next)
      onPayload(buildManualV2Payload(next, activitySubjects))
    },
    onBusinessUnitTypeChange: () => undefined,
    onChange: setActivitySubjects,
    onExcludeCatalogSubject: () => undefined,
  })
}

describe('ManualOnboardingV2BuConfigStep specific_name', () => {
  it('exposes an editable Nom d’instance field that feeds payload specific_name', () => {
    const businessUnit = createDraftBusinessUnit({
      label: 'Restaurant',
      catalog_key: 'restaurant',
    })
    const subject = createDraftActivitySubject({
      label: 'Stock',
      business_unit_client_key: businessUnit.client_key,
      catalog_key: 'restaurant__stock',
    })
    const onPayload = vi.fn()

    render(
      createElement(ConfigStepHarness, {
        initialBusinessUnits: [businessUnit],
        initialActivitySubjects: [subject],
        onPayload,
      }),
    )

    const input = screen.getByLabelText('Nom d’instance') as HTMLInputElement
    expect(input.value).toBe('Restaurant')

    fireEvent.change(input, { target: { value: 'Food Court' } })

    expect(input.value).toBe('Food Court')
    expect(onPayload).toHaveBeenCalled()
    expect(onPayload.mock.calls.at(-1)?.[0]).toMatchObject({
      schema_version: 'onboarding_proposal_v4',
      business_units: [
        expect.objectContaining({
          catalog_key: 'restaurant',
          specific_name: 'Food Court',
        }),
      ],
    })
  })
})
