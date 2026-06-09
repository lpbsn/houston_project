export const RECURRENCE_DAY_OPTIONS = [
  { value: 'monday', label: 'Lundi' },
  { value: 'tuesday', label: 'Mardi' },
  { value: 'wednesday', label: 'Mercredi' },
  { value: 'thursday', label: 'Jeudi' },
  { value: 'friday', label: 'Vendredi' },
  { value: 'saturday', label: 'Samedi' },
  { value: 'sunday', label: 'Dimanche' },
] as const

export type RecurrenceDay = (typeof RECURRENCE_DAY_OPTIONS)[number]['value']

export function formatRecurrenceDaysLabel(days: string[]): string {
  if (days.length === 0) {
    return 'Ponctuelle'
  }

  const labels = RECURRENCE_DAY_OPTIONS.filter((option) => days.includes(option.value)).map(
    (option) => option.label,
  )

  return labels.join(', ')
}

export function toggleRecurrenceDay(days: string[], day: RecurrenceDay): string[] {
  if (days.includes(day)) {
    return days.filter((value) => value !== day)
  }
  return [...days, day]
}
