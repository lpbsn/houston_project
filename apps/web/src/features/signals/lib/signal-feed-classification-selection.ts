import type { BusinessUnitNode } from '@/features/auth/lib/business-unit-scope'

import type { SignalFeedFilters } from './signal-feed-filters'

export type ClassificationKeySelection = Pick<
  SignalFeedFilters,
  'businessUnitKeys' | 'activitySubjectIds'
>

export type FeedClassificationSelectionState = 'checked' | 'indeterminate' | 'unchecked'

export function collectClassificationKeysFromTree(
  businessUnits: BusinessUnitNode[],
): ClassificationKeySelection {
  const businessUnitKeys: string[] = []
  const activitySubjectIds: string[] = []

  for (const businessUnit of businessUnits) {
    businessUnitKeys.push(businessUnit.key)
    for (const subject of businessUnit.activity_subjects) {
      activitySubjectIds.push(subject.id)
    }
  }

  return {
    businessUnitKeys: [...new Set(businessUnitKeys)].sort(),
    activitySubjectIds: [...new Set(activitySubjectIds)].sort(),
  }
}

export function mergeClassificationSelections(
  current: ClassificationKeySelection,
  addition: ClassificationKeySelection,
): ClassificationKeySelection {
  return {
    businessUnitKeys: [...new Set([...current.businessUnitKeys, ...addition.businessUnitKeys])].sort(),
    activitySubjectIds: [
      ...new Set([...current.activitySubjectIds, ...addition.activitySubjectIds]),
    ].sort(),
  }
}

export function toggleBusinessUnitKey(
  selection: ClassificationKeySelection,
  businessUnitKey: string,
  checked: boolean,
): ClassificationKeySelection {
  return {
    ...selection,
    businessUnitKeys: checked
      ? [...new Set([...selection.businessUnitKeys, businessUnitKey])].sort()
      : selection.businessUnitKeys.filter((key) => key !== businessUnitKey),
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
  if (selection.businessUnitKeys.includes(businessUnit.key)) {
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
  return selection.businessUnitKeys.length + selection.activitySubjectIds.length
}

export function buildClassificationLabelsFromTree(
  businessUnits: BusinessUnitNode[],
): {
  labelByBusinessUnitKey: Map<string, string>
  labelByActivitySubjectId: Map<string, string>
} {
  const labelByBusinessUnitKey = new Map<string, string>()
  const labelByActivitySubjectId = new Map<string, string>()

  for (const businessUnit of businessUnits) {
    labelByBusinessUnitKey.set(businessUnit.key, businessUnit.label)
    for (const subject of businessUnit.activity_subjects) {
      labelByActivitySubjectId.set(subject.id, subject.label)
    }
  }

  return { labelByBusinessUnitKey, labelByActivitySubjectId }
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
        businessUnit.label.toLowerCase().includes(normalizedQuery) ||
        businessUnit.key.toLowerCase().includes(normalizedQuery)
      const matchingSubjects = businessUnit.activity_subjects.filter(
        (subject) =>
          subject.label.toLowerCase().includes(normalizedQuery) ||
          subject.normalized_name.toLowerCase().includes(normalizedQuery),
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
