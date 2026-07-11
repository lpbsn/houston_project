// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  buildMixedSubmissionStorageKey,
  clearAllMixedSubmissionIntents,
  clearMixedSubmissionIntent,
  readMixedSubmissionIntent,
  resolveMixedSubmissionIntent,
  writeMixedSubmissionIntent,
} from './action-plan-mixed-submission-intent'

const SUBMISSION_ID_1 = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1'
const SUBMISSION_ID_2 = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2'
const SUBMISSION_ID_3 = 'cccccccc-cccc-4ccc-8ccc-ccccccccccc3'

const establishmentId = '11111111-1111-4111-8111-111111111111'
const actionPlanId = '22222222-2222-4222-8222-222222222222'
const otherEstablishmentId = '33333333-3333-4333-8333-333333333333'
const otherActionPlanId = '44444444-4444-4444-8444-444444444444'

const scheduleBody = {
  recurrence_days: ['monday'],
  assignees: [{ membership_id: 'm1', business_unit_id: 'bu1' }],
}
const useBody = {
  use_shared_chronology: false,
  assignees: [{ membership_id: 'm2', business_unit_id: 'bu1' }],
}

function resolveOptions(overrides?: {
  establishmentId?: string
  actionPlanId?: string
  scheduleBody?: unknown
  useBody?: unknown
}) {
  return {
    establishmentId: overrides?.establishmentId ?? establishmentId,
    actionPlanId: overrides?.actionPlanId ?? actionPlanId,
    scheduleBody: overrides?.scheduleBody ?? scheduleBody,
    useBody: overrides?.useBody ?? useBody,
  }
}

function storageKey(
  estId = establishmentId,
  planId = actionPlanId,
): string {
  return buildMixedSubmissionStorageKey(estId, planId)
}

beforeEach(() => {
  sessionStorage.clear()
  vi.spyOn(crypto, 'randomUUID').mockReturnValue(SUBMISSION_ID_1)
})

afterEach(() => {
  sessionStorage.clear()
  vi.restoreAllMocks()
})

describe('action-plan-mixed-submission-intent', () => {
  describe('buildMixedSubmissionStorageKey', () => {
    it('scopes sessionStorage keys by establishment and action plan', () => {
      expect(storageKey()).toBe(
        `houston:mixed-submission:${establishmentId}:${actionPlanId}`,
      )
      expect(storageKey(otherEstablishmentId, actionPlanId)).not.toBe(storageKey())
      expect(storageKey(establishmentId, otherActionPlanId)).not.toBe(storageKey())
    })
  })

  describe('readMixedSubmissionIntent', () => {
    it('returns null when storage is absent', () => {
      expect(readMixedSubmissionIntent(establishmentId, actionPlanId)).toBeNull()
    })

    it('returns null for invalid JSON without throwing', () => {
      sessionStorage.setItem(storageKey(), '{broken')
      expect(readMixedSubmissionIntent(establishmentId, actionPlanId)).toBeNull()
    })

    it('returns null for empty or incomplete payloads', () => {
      sessionStorage.setItem(storageKey(), '{}')
      expect(readMixedSubmissionIntent(establishmentId, actionPlanId)).toBeNull()

      sessionStorage.setItem(storageKey(), JSON.stringify({ submissionId: '', payloadHash: 'abc' }))
      expect(readMixedSubmissionIntent(establishmentId, actionPlanId)).toBeNull()

      sessionStorage.setItem(
        storageKey(),
        JSON.stringify({ submissionId: SUBMISSION_ID_1, payloadHash: '' }),
      )
      expect(readMixedSubmissionIntent(establishmentId, actionPlanId)).toBeNull()
    })

    it('round-trips a valid intent via write and read', () => {
      const intent = { submissionId: SUBMISSION_ID_1, payloadHash: 'hash-abc' }
      writeMixedSubmissionIntent(establishmentId, actionPlanId, intent)
      expect(readMixedSubmissionIntent(establishmentId, actionPlanId)).toEqual(intent)
    })
  })

  describe('resolveMixedSubmissionIntent', () => {
    it('reuses submissionId for same establishment, plan, and payload hash', async () => {
      const randomUUID = vi.mocked(crypto.randomUUID)

      const first = await resolveMixedSubmissionIntent(resolveOptions())
      const second = await resolveMixedSubmissionIntent(resolveOptions())

      expect(first.submissionId).toBe(SUBMISSION_ID_1)
      expect(second.submissionId).toBe(SUBMISSION_ID_1)
      expect(randomUUID).toHaveBeenCalledTimes(1)
    })

    it('generates a new submissionId when payload hash changes', async () => {
      vi.spyOn(crypto, 'randomUUID')
        .mockReturnValueOnce(SUBMISSION_ID_1)
        .mockReturnValueOnce(SUBMISSION_ID_2)

      const first = await resolveMixedSubmissionIntent(resolveOptions())
      const second = await resolveMixedSubmissionIntent(
        resolveOptions({
          scheduleBody: {
            ...scheduleBody,
            recurrence_days: ['tuesday'],
          },
        }),
      )

      expect(first.submissionId).toBe(SUBMISSION_ID_1)
      expect(second.submissionId).toBe(SUBMISSION_ID_2)

      const stored = JSON.parse(sessionStorage.getItem(storageKey())!)
      expect(stored.submissionId).toBe(SUBMISSION_ID_2)
    })

    it('does not reuse submissionId across different establishments', async () => {
      vi.spyOn(crypto, 'randomUUID')
        .mockReturnValueOnce(SUBMISSION_ID_1)
        .mockReturnValueOnce(SUBMISSION_ID_2)

      await resolveMixedSubmissionIntent(resolveOptions())
      const otherEstablishment = await resolveMixedSubmissionIntent(
        resolveOptions({ establishmentId: otherEstablishmentId }),
      )

      expect(otherEstablishment.submissionId).toBe(SUBMISSION_ID_2)
    })

    it('does not reuse submissionId across different action plans', async () => {
      vi.spyOn(crypto, 'randomUUID')
        .mockReturnValueOnce(SUBMISSION_ID_1)
        .mockReturnValueOnce(SUBMISSION_ID_2)

      await resolveMixedSubmissionIntent(resolveOptions())
      const otherPlan = await resolveMixedSubmissionIntent(
        resolveOptions({ actionPlanId: otherActionPlanId }),
      )

      expect(otherPlan.submissionId).toBe(SUBMISSION_ID_2)
    })

    it('restores intent from sessionStorage after a simulated reload', async () => {
      const randomUUID = vi.mocked(crypto.randomUUID)

      const beforeReload = await resolveMixedSubmissionIntent(resolveOptions())
      expect(sessionStorage.getItem(storageKey())).not.toBeNull()

      const afterReload = await resolveMixedSubmissionIntent(resolveOptions())

      expect(afterReload).toEqual(beforeReload)
      expect(afterReload.submissionId).toBe(SUBMISSION_ID_1)
      expect(randomUUID).toHaveBeenCalledTimes(1)
    })

    it('recovers from corrupted storage without crashing', async () => {
      vi.spyOn(crypto, 'randomUUID')
        .mockReturnValueOnce(SUBMISSION_ID_1)
        .mockReturnValueOnce(SUBMISSION_ID_2)

      sessionStorage.setItem(storageKey(), '{not-json')

      const intent = await resolveMixedSubmissionIntent(resolveOptions())

      expect(intent.submissionId).toBe(SUBMISSION_ID_1)
      expect(readMixedSubmissionIntent(establishmentId, actionPlanId)).toEqual(intent)
    })

    it('stores only submissionId and payloadHash, not full business payloads', async () => {
      await resolveMixedSubmissionIntent(resolveOptions())

      const raw = sessionStorage.getItem(storageKey())
      expect(raw).not.toBeNull()

      const parsed = JSON.parse(raw!) as Record<string, unknown>
      expect(Object.keys(parsed).sort()).toEqual(['payloadHash', 'submissionId'])
      expect(parsed).not.toHaveProperty('schedule')
      expect(parsed).not.toHaveProperty('use')
      expect(parsed).not.toHaveProperty('assignees')
    })
  })

  describe('clearMixedSubmissionIntent', () => {
    it('purges stored intent and allows a new submissionId on next resolve', async () => {
      vi.spyOn(crypto, 'randomUUID')
        .mockReturnValueOnce(SUBMISSION_ID_1)
        .mockReturnValueOnce(SUBMISSION_ID_2)

      await resolveMixedSubmissionIntent(resolveOptions())
      clearMixedSubmissionIntent(establishmentId, actionPlanId)

      expect(readMixedSubmissionIntent(establishmentId, actionPlanId)).toBeNull()

      const next = await resolveMixedSubmissionIntent(resolveOptions())
      expect(next.submissionId).toBe(SUBMISSION_ID_2)
    })
  })

  describe('clearAllMixedSubmissionIntents', () => {
    it('removes all mixed-submission keys from sessionStorage', async () => {
      vi.spyOn(crypto, 'randomUUID')
        .mockReturnValueOnce(SUBMISSION_ID_1)
        .mockReturnValueOnce(SUBMISSION_ID_2)
        .mockReturnValueOnce(SUBMISSION_ID_3)

      await resolveMixedSubmissionIntent(resolveOptions())
      await resolveMixedSubmissionIntent(
        resolveOptions({ actionPlanId: otherActionPlanId }),
      )
      sessionStorage.setItem('unrelated-key', 'keep')

      clearAllMixedSubmissionIntents()

      expect(sessionStorage.getItem(storageKey())).toBeNull()
      expect(sessionStorage.getItem(storageKey(establishmentId, otherActionPlanId))).toBeNull()
      expect(sessionStorage.getItem('unrelated-key')).toBe('keep')
    })
  })
})
