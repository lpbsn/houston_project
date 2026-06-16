import { describe, expect, it } from 'vitest'

import {
  buildInitialAssigneeFromMembership,
  buildTemplateCreatePayload,
} from './checklist-create-submit'

describe('checklist-create-submit', () => {
  const baseInput = {
    title: '  To do ouverture  ',
    description: '  Vérifications matinales  ',
    businessUnitId: 'bu-1',
    tasks: ['Désactiver l’alarme', 'Vérifier la terrasse'],
  }

  it('builds template payload with assign_now false explicit', () => {
    expect(buildTemplateCreatePayload(baseInput)).toEqual({
      title: 'To do ouverture',
      description: 'Vérifications matinales',
      business_unit_id: 'bu-1',
      tasks: [{ task: 'Désactiver l’alarme' }, { task: 'Vérifier la terrasse' }],
      assign_now: false,
    })
  })

  it('prefills assignee with Moi for active membership', () => {
    const result = buildInitialAssigneeFromMembership({
      membershipId: 'member-1',
      username: 'staff.user',
      role: 'staff',
    })

    expect(result.assignedTo).toBe('member-1')
    expect(result.selectedUser.display_name).toBe('Moi')
  })

  it('keeps membership id on assignee prefill', () => {
    const result = buildInitialAssigneeFromMembership({
      membershipId: 'member-1',
      displayName: 'Jean Dupont',
      username: 'jean',
      role: 'manager',
    })

    expect(result.selectedUser.display_name).toBe('Moi')
  })
})
