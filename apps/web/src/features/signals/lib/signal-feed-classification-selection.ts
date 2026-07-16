import type { BusinessUnitNode } from '@/features/auth/lib/business-unit-scope'

import type { SignalFeedFilters } from './signal-feed-filters'

export type ClassificationKeySelection = Pick<
  SignalFeedFilters,
  'businessUnitIds' | 'activitySubjectIds'
>

export type FeedClassificationSelectionState = 'checked' | 'indeterminate' | 'unchecked'

export function collectClassificationKeysFromTree(
  businessUnits: BusinessUnitNode[],
): ClassificationKeySelection {
  const businessUnitIds: string[] = []
  const activitySubjectIds: string[] = []

  for (const businessUnit of businessUnits) {
    businessUnitIds.push(businessUnit.id)
    for (const subject of businessUnit.activity_subjects) {
      activitySubjectIds.push(subject.id)
    }
  }

  return {
    businessUnitIds: [...new Set(businessUnitIds)].sort(),
    activitySubjectIds: [...new Set(activitySubjectIds)].sort(),
  }
}

export function mergeClassificationSelections(
  current: ClassificationKeySelection,
  addition: ClassificationKeySelection,
): ClassificationKeySelection {
  return {
    businessUnitIds: [...new Set([...current.businessUnitIds, ...addition.businessUnitIds])].sort(),
    activitySubjectIds: [
      ...new Set([...current.activitySubjectIds, ...addition.activitySubjectIds]),
    ].sort(),
  }
}

export function toggleBusinessUnitKey(
  selection: ClassificationKeySelection,
  businessUnitId: string,
  checked: boolean,
): ClassificationKeySelection {
  return {
    ...selection,
    businessUnitIds: checked
      ? [...new Set([...selection.businessUnitIds, businessUnitId])].sort()
      : selection.businessUnitIds.filter((id) => id !== businessUnitId),
  }
}

export function toggleActivitySubjectId(
  selection: ClassificationKeySelection,
  activitySubjectId: string,
  checked: boolean,
): ClassificationKeySelection {
  return {
    ...selection,
    activitySubjectIds: checked
      ? [...new Set([...selection.activitySubjectIds, activitySubjectId])].sort()
      : selection.activitySubjectIds.filter((id) => id !== activitySubjectId),
  }
}

export function getBusinessUnitSelectionState(
  businessUnit: BusinessUnitNode,
  selection: ClassificationKeySelection,
): FeedClassificationSelectionState {
  if (selection.businessUnitIds.includes(businessUnit.id)) {
    return 'checked'
  }

  const hasChildSelection = businessUnit.activity_subjects.some((subject) =>
    selection.activitySubjectIds.includes(subject.id),
  )

  return hasChildSelection ? 'indeterminate' : 'unchecked'
}

export function getActivitySubjectSelectionState(
  activitySubjectId: string,
  selection: ClassificationKeySelection,
): FeedClassificationSelectionState {
  return selection.activitySubjectIds.includes(activitySubjectId) ? 'checked' : 'unchecked'
}

export function countClassificationSelections(selection: ClassificationKeySelection): number {
  return selection.businessUnitIds.length + selection.activitySubjectIds.length
}

export function buildClassificationLabelsFromTree(
  businessUnits: BusinessUnitNode[],
): {
  labelByBusinessUnitId: Map<string, string>
  labelByActivitySubjectId: Map<string, string>
} {
  const labelByBusinessUnitId = new Map<string, string>()
  const labelByActivitySubjectId = new Map<string, string>()

  for (const businessUnit of businessUnits) {
    labelByBusinessUnitId.set(businessUnit.id, businessUnit.specific_name)
    for (const subject of businessUnit.activity_subjects) {
      labelByActivitySubjectId.set(subject.id, subject.label)
    }
  }

  return { labelByBusinessUnitId, labelByActivitySubjectId }
}

export function filterBusinessUnitsBySearch(
  businessUnits: BusinessUnitNode[],
  query: string,
): BusinessUnitNode[] {
  const normalizedQuery = query.trim().toLowerCase()
  if (!normalizedQuery) {
    return businessUnits
  }

  return businessUnits
    .map((businessUnit) => {
      const businessUnitMatches =
        businessUnit.specific_name.toLowerCase().includes(normalizedQuery) ||
        businessUnit.generic.label.toLowerCase().includes(normalizedQuery) ||
        businessUnit.generic.key.toLowerCase().includes(normalizedQuery)
      const matchingSubjects = businessUnit.activity_subjects.filter((subject) =>
        subject.label.toLowerCase().includes(normalizedQuery),
      )

      if (businessUnitMatches) {
        return businessUnit
      }
      if (matchingSubjects.length > 0) {
        return { ...businessUnit, activity_subjects: matchingSubjects }
      }
      return null
    })
    .filter((businessUnit): businessUnit is BusinessUnitNode => businessUnit !== null)
}
