import { useCallback, useState } from 'react'

import type { ScopedUserSearchResult } from '@/features/actions/types'
import type { AssignmentFormValues } from '@/features/checklists/lib/checklist-assignment-create-payload'
import {
  hasAssignmentFormErrors,
  validateAssignmentForm,
} from '@/features/checklists/lib/checklist-form-validation'
import type { ChecklistAssignment } from '@/features/checklists/types'

export const EMPTY_ASSIGNMENT_FORM_VALUES: AssignmentFormValues = {
  assignedTo: '',
  startDate: '',
  endDate: '',
  startAt: '',
  endAt: '',
  recurrenceDays: [],
}

export function buildInitialSelectedUser(
  assignment: ChecklistAssignment,
): ScopedUserSearchResult {
  return {
    id: assignment.assigned_to_id,
    membership_id: assignment.assigned_to_id,
    display_name: assignment.assigned_to_display_name,
    username: assignment.assigned_to_display_name,
    role: 'staff',
    email: null,
  }
}

type UseChecklistAssignmentFormOptions = {
  initialValues?: AssignmentFormValues
  initialSelectedUser?: ScopedUserSearchResult | null
}

export function useChecklistAssignmentForm({
  initialValues = EMPTY_ASSIGNMENT_FORM_VALUES,
  initialSelectedUser = null,
}: UseChecklistAssignmentFormOptions = {}) {
  const [assignedTo, setAssignedTo] = useState(initialValues.assignedTo)
  const [selectedUser, setSelectedUser] = useState<ScopedUserSearchResult | null>(
    initialSelectedUser,
  )
  const [startDate, setStartDate] = useState(initialValues.startDate)
  const [endDate, setEndDate] = useState(initialValues.endDate)
  const [startAt, setStartAt] = useState(initialValues.startAt)
  const [endAt, setEndAt] = useState(initialValues.endAt)
  const [recurrenceDays, setRecurrenceDays] = useState<string[]>(
    initialValues.recurrenceDays,
  )
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [apiError, setApiError] = useState<string | null>(null)

  const resetForm = useCallback(
    (values: AssignmentFormValues, user: ScopedUserSearchResult | null) => {
      setAssignedTo(values.assignedTo)
      setSelectedUser(user)
      setStartDate(values.startDate)
      setEndDate(values.endDate)
      setStartAt(values.startAt)
      setEndAt(values.endAt)
      setRecurrenceDays(values.recurrenceDays)
      setFieldErrors({})
      setApiError(null)
    },
    [],
  )

  const clearFieldError = useCallback((field: string) => {
    setFieldErrors((prev) => ({ ...prev, [field]: '' }))
  }, [])

  const validateForm = useCallback((): Record<string, string> => {
    return validateAssignmentForm({
      assignedTo,
      startDate,
      endDate: recurrenceDays.length > 0 ? endDate : startDate,
      startAt,
      endAt,
      recurrenceDays,
    })
  }, [assignedTo, endAt, endDate, recurrenceDays, startAt, startDate])

  const getFormValues = useCallback((): AssignmentFormValues => {
    return {
      assignedTo,
      startDate,
      endDate,
      startAt,
      endAt,
      recurrenceDays,
    }
  }, [assignedTo, endAt, endDate, recurrenceDays, startAt, startDate])

  return {
    assignedTo,
    setAssignedTo,
    selectedUser,
    setSelectedUser,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    startAt,
    setStartAt,
    endAt,
    setEndAt,
    recurrenceDays,
    setRecurrenceDays,
    fieldErrors,
    setFieldErrors,
    apiError,
    setApiError,
    resetForm,
    clearFieldError,
    validateForm,
    getFormValues,
    hasAssignmentFormErrors,
  }
}
