export const ACTION_PLAN_RECURRENCE_DAYS = [
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday',
] as const

export type ActionPlanRecurrenceDay = (typeof ACTION_PLAN_RECURRENCE_DAYS)[number]

export const ACTION_PLAN_RECURRENCE_DAY_LABELS: Record<ActionPlanRecurrenceDay, string> = {
  monday: 'Lundi',
  tuesday: 'Mardi',
  wednesday: 'Mercredi',
  thursday: 'Jeudi',
  friday: 'Vendredi',
  saturday: 'Samedi',
  sunday: 'Dimanche',
}
