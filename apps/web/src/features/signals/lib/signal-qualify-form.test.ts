import { describe, expect, it } from 'vitest'

import {
  applyResponsibleSelection,
  applySubjectSelection,
  buildQualifyRoutingPatch,
  createQualifyFormState,
  hasQualifyRoutingPatch,
  listAffectedBusinessUnitOptions,
  listResponsibleBusinessUnitOptions,
  listSubjectOptionsForResponsible,
  withBaselineQualifyOptions,
} from './signal-qualify-form'

/** Canonical Spa (no AS) + Hôtel (with AS) dual Lot 3 mirror fixture. */
const tree = [
  {
    id: 'bu-spa',
    specific_name: 'Spa',
    active: true,
    activity_subjects: [] as Array<{ id: string; active: boolean; label: string }>,
  },
  {
    id: 'bu-hotel',
    specific_name: 'Hôtel',
    active: true,
    activity_subjects: [
      { id: 'as-housekeeping', active: true, label: 'Housekeeping' },
      { id: 'as-inactive', active: false, label: 'Inactif' },
    ],
  },
  {
    id: 'bu-maint',
    specific_name: 'Maintenance',
    active: true,
    activity_subjects: [
      { id: 'as-light', active: true, label: 'Éclairage' },
    ],
  },
  {
    id: 'bu-kitchen',
    specific_name: 'Cuisine',
    active: true,
    activity_subjects: [{ id: 'as-stock', active: true, label: 'Stock' }],
  },
]

describe('dual Lot 3 option lists (semantic mirror)', () => {
  it('lists Spa in affected only; Hôtel in affected and responsible', () => {
    expect(listAffectedBusinessUnitOptions(tree).map((item) => item.id)).toEqual([
      'bu-spa',
      'bu-hotel',
      'bu-maint',
      'bu-kitchen',
    ])
    expect(listResponsibleBusinessUnitOptions(tree).map((item) => item.id)).toEqual([
      'bu-hotel',
      'bu-maint',
      'bu-kitchen',
    ])
  })

  it('filters subjects by responsible pole', () => {
    expect(
      listSubjectOptionsForResponsible(tree, 'bu-hotel').map((item) => item.id),
    ).toEqual(['as-housekeeping'])
  })
})

describe('withBaselineQualifyOptions', () => {
  const catalogueAffected = listAffectedBusinessUnitOptions(tree)
  const catalogueResponsible = listResponsibleBusinessUnitOptions(tree)
  const catalogueSubjects = listSubjectOptionsForResponsible(tree, 'bu-orphan-resp')

  it('injects orphan baseline options without implying a draft mutation', () => {
    const baseline = createQualifyFormState({
      affected_business_unit_id: 'bu-orphan-aff',
      responsible_business_unit_id: 'bu-orphan-resp',
      activity_subject_id: 'as-orphan',
      issue_focus: 'legacy',
    })
    const draft = { ...baseline }
    const next = withBaselineQualifyOptions({
      affectedOptions: catalogueAffected,
      responsibleOptions: catalogueResponsible,
      subjectOptions: catalogueSubjects,
      baseline,
      draft,
      labels: {
        affectedBusinessUnitLabel: 'Ancien pôle',
        responsibleBusinessUnitLabel: 'Ancien responsable',
        activitySubjectLabel: 'Ancien sujet',
      },
    })

    expect(draft).toEqual(baseline)
    expect(buildQualifyRoutingPatch(baseline, draft)).toEqual({})
    expect(next.affectedOptions.map((item) => item.id)).toContain('bu-orphan-aff')
    expect(next.responsibleOptions.map((item) => item.id)).toContain('bu-orphan-resp')
    expect(next.subjectOptions).toEqual([
      {
        id: 'as-orphan',
        label: 'Ancien sujet',
        businessUnitId: 'bu-orphan-resp',
      },
    ])
  })

  it('drops orphans after clear or replace', () => {
    const baseline = createQualifyFormState({
      affected_business_unit_id: 'bu-orphan-aff',
      responsible_business_unit_id: 'bu-orphan-resp',
      activity_subject_id: 'as-orphan',
    })
    const cleared = withBaselineQualifyOptions({
      affectedOptions: catalogueAffected,
      responsibleOptions: catalogueResponsible,
      subjectOptions: catalogueSubjects,
      baseline,
      draft: { ...baseline, affectedBusinessUnitId: null, activitySubjectId: null },
      labels: {
        affectedBusinessUnitLabel: 'Ancien pôle',
        responsibleBusinessUnitLabel: 'Ancien responsable',
        activitySubjectLabel: 'Ancien sujet',
      },
    })
    expect(cleared.affectedOptions.map((item) => item.id)).not.toContain('bu-orphan-aff')
    expect(cleared.subjectOptions.map((item) => item.id)).not.toContain('as-orphan')
    // Responsible still at baseline → orphan remains until that dim diverges.
    expect(cleared.responsibleOptions.map((item) => item.id)).toContain('bu-orphan-resp')

    const replaced = withBaselineQualifyOptions({
      affectedOptions: catalogueAffected,
      responsibleOptions: catalogueResponsible,
      subjectOptions: listSubjectOptionsForResponsible(tree, 'bu-hotel'),
      baseline,
      draft: {
        ...baseline,
        affectedBusinessUnitId: 'bu-spa',
        responsibleBusinessUnitId: 'bu-hotel',
        activitySubjectId: 'as-housekeeping',
      },
      labels: {
        affectedBusinessUnitLabel: 'Ancien pôle',
        responsibleBusinessUnitLabel: 'Ancien responsable',
        activitySubjectLabel: 'Ancien sujet',
      },
    })
    expect(replaced.affectedOptions.map((item) => item.id)).not.toContain('bu-orphan-aff')
    expect(replaced.responsibleOptions.map((item) => item.id)).not.toContain('bu-orphan-resp')
    expect(replaced.subjectOptions.map((item) => item.id)).not.toContain('as-orphan')
  })
})

describe('H2 draft mutations', () => {
  it('derives responsible from subject', () => {
    const baseline = createQualifyFormState({})
    const next = applySubjectSelection(baseline, 'as-light', 'bu-maint')
    expect(next.activitySubjectId).toBe('as-light')
    expect(next.responsibleBusinessUnitId).toBe('bu-maint')
  })

  it('clears incompatible subject when responsible changes', () => {
    const state = createQualifyFormState({
      responsible_business_unit_id: 'bu-maint',
      activity_subject_id: 'as-light',
    })
    const next = applyResponsibleSelection(state, 'bu-kitchen', 'bu-maint')
    expect(next.responsibleBusinessUnitId).toBe('bu-kitchen')
    expect(next.activitySubjectId).toBeNull()
  })

  it('clearing subject alone keeps responsible', () => {
    const state = createQualifyFormState({
      responsible_business_unit_id: 'bu-maint',
      activity_subject_id: 'as-light',
    })
    const next = applySubjectSelection(state, null, null)
    expect(next.activitySubjectId).toBeNull()
    expect(next.responsibleBusinessUnitId).toBe('bu-maint')
  })
})

describe('buildQualifyRoutingPatch Lot 7', () => {
  const baseline = createQualifyFormState({
    affected_business_unit_id: 'bu-kitchen',
    responsible_business_unit_id: 'bu-maint',
    activity_subject_id: 'as-light',
    issue_focus: 'lampe',
  })

  it('omits unchanged fields', () => {
    expect(buildQualifyRoutingPatch(baseline, baseline)).toEqual({})
    expect(hasQualifyRoutingPatch(buildQualifyRoutingPatch(baseline, baseline))).toBe(false)
  })

  it('sends null to clear and UUID to replace', () => {
    const draft = {
      ...baseline,
      affectedBusinessUnitId: null,
      responsibleBusinessUnitId: 'bu-kitchen',
      activitySubjectId: null,
      issueFocus: 'fuite',
    }
    expect(buildQualifyRoutingPatch(baseline, draft)).toEqual({
      affected_business_unit_id: null,
      responsible_business_unit_id: 'bu-kitchen',
      activity_subject_id: null,
      issue_focus: 'fuite',
    })
  })

  it('clears subject alone without touching responsible', () => {
    const draft = { ...baseline, activitySubjectId: null }
    expect(buildQualifyRoutingPatch(baseline, draft)).toEqual({
      activity_subject_id: null,
    })
  })

  it('includes derived responsible when subject selection changes it', () => {
    const empty = createQualifyFormState({})
    const draft = applySubjectSelection(empty, 'as-stock', 'bu-kitchen')
    expect(buildQualifyRoutingPatch(empty, draft)).toEqual({
      responsible_business_unit_id: 'bu-kitchen',
      activity_subject_id: 'as-stock',
    })
  })
})
