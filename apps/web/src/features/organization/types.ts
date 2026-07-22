import type { components } from '@/api/generated/types'

export type OrganizationAdminOverview = components['schemas']['OrganizationAdminOverview']
export type OrganizationAdminEstablishment =
  components['schemas']['OrganizationAdminEstablishment']
export type OrganizationAdminEstablishmentList =
  components['schemas']['OrganizationAdminEstablishmentList']
export type OrganizationAdminMember = components['schemas']['OrganizationAdminMember']
export type OrganizationAdminMemberList = components['schemas']['OrganizationAdminMemberList']
export type OrganizationAdminMemberFilterOptions =
  components['schemas']['OrganizationAdminMemberFilterOptions']
export type OrganizationAdminOwner = components['schemas']['OrganizationAdminOwner']
export type OrganizationAdminOwnerList = components['schemas']['OrganizationAdminOwnerList']
export type OrganizationAdminOwnerInvitationRequest =
  components['schemas']['OrganizationAdminOwnerInvitationRequest']
export type DirectorInvitationResponse = components['schemas']['DirectorInvitationResponse']

export type OrganizationMemberListFilters = {
  q?: string
  establishment_id?: string
  business_unit_id?: string
  role?: string
  status?: string
}

export type OrganizationTab = 'establishments' | 'members' | 'owners'
