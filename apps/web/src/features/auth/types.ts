import type { components } from '@/api/generated/types'

export type AuthResponse = components['schemas']['AuthResponse']
export type BootstrapResponse = components['schemas']['BootstrapResponse']
export type EstablishmentMembershipResponse = components['schemas']['EstablishmentMembershipResponse']
export type EstablishmentMembershipDetailResponse =
  components['schemas']['EstablishmentMembershipDetailResponse']
export type MembershipReinviteResponse = components['schemas']['MembershipReinviteResponse']
export type LoginRequest = Omit<
  components['schemas']['LoginRequest'],
  'refresh_token_transport'
>
export type RegistrationOwnerValidateRequest =
  components['schemas']['RegistrationOwnerValidateRequest']
export type RegistrationRequest = Omit<
  components['schemas']['RegistrationRequest'],
  'refresh_token_transport'
>
export type RegistrationResponse = components['schemas']['RegistrationResponse']
export type DirectorInvitationAcceptInput = Omit<
  components['schemas']['DirectorInvitationAcceptRequest'],
  'refresh_token_transport'
>
export type Membership = components['schemas']['Membership']
export type MembershipInvitationRequest = components['schemas']['MembershipInvitationRequest']
export type MembershipUpdateRequest = components['schemas']['PatchedMembershipUpdateRequest']
export type MembershipInvitationRequestRoleEnum = MembershipInvitationRequest['role']
export type RoleEnum = NonNullable<MembershipUpdateRequest['role']>
export type SwitchEstablishmentRequest = components['schemas']['SwitchEstablishmentRequest']
export type EstablishmentCreateRequest = components['schemas']['EstablishmentCreateRequest']
export type EstablishmentCreateResponse = components['schemas']['EstablishmentCreateResponse']
export type UserPublic = components['schemas']['UserPublic']
export type MembershipScopeItem = components['schemas']['EstablishmentMembershipScopeItem']
export type BusinessUnitTreeResponse = components['schemas']['BusinessUnitTreeResponse']
