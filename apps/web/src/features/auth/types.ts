import type { components } from '@/api/generated/types'

export type AuthResponse = components['schemas']['AuthResponse']
export type BootstrapResponse = components['schemas']['BootstrapResponse']
export type EstablishmentMembershipResponse = components['schemas']['EstablishmentMembershipResponse']
export type LoginRequest = components['schemas']['LoginRequest']
export type RegistrationOwnerValidateRequest =
  components['schemas']['RegistrationOwnerValidateRequest']
export type RegistrationRequest = components['schemas']['RegistrationRequest']
export type RegistrationResponse = components['schemas']['RegistrationResponse']
export type Membership = components['schemas']['Membership']
export type MembershipInvitationRequest = components['schemas']['MembershipInvitationRequest']
export type MembershipUpdateRequest = components['schemas']['PatchedMembershipUpdateRequest']
export type MembershipInvitationRequestRoleEnum =
  Extract<MembershipInvitationRequest['role'], 'staff' | 'manager'>
export type RoleEnum = NonNullable<MembershipUpdateRequest['role']>
export type SwitchEstablishmentRequest = components['schemas']['SwitchEstablishmentRequest']
export type UserPublic = components['schemas']['UserPublic']
export type WorkspaceSummaryResponse = components['schemas']['WorkspaceSummaryResponse']
export type OperationalTaxonomyResponse = components['schemas']['OperationalTaxonomyResponse']
export type MembershipScopeItem = components['schemas']['EstablishmentMembershipScopeItem']
