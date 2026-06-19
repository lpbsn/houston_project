export type OperationalRealtimeAuthOkEvent = {
  type: 'auth.ok'
  membership_id: string
  session_id: string
}

export type OperationalRealtimeInvalidateEvent = {
  type: 'invalidate'
  subject_type: 'signal' | 'action' | 'checklist' | 'execution' | 'comment'
  reason: string
  establishment_id: string
  entity_id: string
  occurred_at: string
}

export type OperationalRealtimeAccessReason =
  | 'session.revoked'
  | 'establishment.switched'
  | 'membership.deactivated'
  | 'membership.updated'

export type OperationalRealtimeAccessEvent = {
  type: 'access'
  reason: OperationalRealtimeAccessReason
  establishment_id?: string
  membership_id?: string
  occurred_at: string
}

export type OperationalRealtimeServerEvent =
  | OperationalRealtimeAuthOkEvent
  | OperationalRealtimeInvalidateEvent
  | OperationalRealtimeAccessEvent

export type OperationalRealtimeWsTicketResponse = {
  ticket: string
  expires_in: number
}

export type OperationalRealtimeConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'disconnected'
