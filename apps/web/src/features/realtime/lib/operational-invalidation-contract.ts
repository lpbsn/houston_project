import contract from '@contracts/operational-realtime-invalidation.json'

export type OperationalInvalidationDispatch = 'by_subject_type' | 'by_reason'

export type OperationalInvalidationContractEvent = {
  subject_type: string
  reason: string
  dispatch: OperationalInvalidationDispatch
}

export type OperationalInvalidationContract = {
  version: number
  events: OperationalInvalidationContractEvent[]
}

const parsedContract = contract as OperationalInvalidationContract

export const operationalInvalidationContract: OperationalInvalidationContract = parsedContract

export const operationalInvalidationEvents: readonly OperationalInvalidationContractEvent[] =
  parsedContract.events

export const operationalInvalidationEventPairs = operationalInvalidationEvents.map(
  (event) => [event.subject_type, event.reason] as const,
)

export const reasonGatedOperationalInvalidationEvents = operationalInvalidationEvents.filter(
  (event) => event.dispatch === 'by_reason',
)

export const subjectTypeOperationalInvalidationEvents = operationalInvalidationEvents.filter(
  (event) => event.dispatch === 'by_subject_type',
)

export const notificationInvalidationReasons = new Set(
  operationalInvalidationEvents
    .filter((event) => event.subject_type === 'notification')
    .map((event) => event.reason),
)
