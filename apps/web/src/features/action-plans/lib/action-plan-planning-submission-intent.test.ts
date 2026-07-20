// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  applyPlanningSubmissionIntent,
  buildPlanningBusinessFingerprint,
  buildPlanningSubmissionStorageKey,
  clearAllPlanningSubmissionIntents,
  clearPlanningSubmissionIntent,
  readPlanningSubmissionIntent,
  resolvePlanningSubmissionIntent,
  writePlanningSubmissionIntent,
} from './action-plan-planning-submission-intent'

const establishmentId = 'est-1'
const actionPlanId = 'plan-1'

describe('action-plan-planning-submission-intent', () => {
  let uuidCounter = 0

  beforeEach(() => {
    sessionStorage.clear()
    uuidCounter = 0
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn(() => {
        uuidCounter += 1
        return `uuid-${uuidCounter}`
      }),
      subtle: {
        digest: vi.fn(async (_algorithm: string, data: BufferSource) => {
          const bytes = new Uint8Array(data as ArrayBuffer)
          let hash = 0
          for (let index = 0; index < bytes.length; index += 1) {
            hash = (Math.imul(hash, 31) + (bytes[index] ?? 0)) >>> 0
          }
          const out = new Uint8Array(4)
          out[0] = (hash >>> 24) & 0xff
          out[1] = (hash >>> 16) & 0xff
          out[2] = (hash >>> 8) & 0xff
          out[3] = hash & 0xff
          return out.buffer
        }),
      },
    })
  })

  afterEach(() => {
    sessionStorage.clear()
    vi.unstubAllGlobals()
  })

  it('builds storage key', () => {
    expect(buildPlanningSubmissionStorageKey(establishmentId, actionPlanId)).toBe(
      `houston:planning-submission:${establishmentId}:${actionPlanId}`,
    )
  })

  it('returns null for missing or invalid intents', () => {
    expect(readPlanningSubmissionIntent(establishmentId, actionPlanId)).toBeNull()
    sessionStorage.setItem(
      buildPlanningSubmissionStorageKey(establishmentId, actionPlanId),
      '{bad',
    )
    expect(readPlanningSubmissionIntent(establishmentId, actionPlanId)).toBeNull()
    sessionStorage.setItem(
      buildPlanningSubmissionStorageKey(establishmentId, actionPlanId),
      JSON.stringify({ submissionId: 's1', requestHash: 'h1' }),
    )
    expect(readPlanningSubmissionIntent(establishmentId, actionPlanId)).toBeNull()
  })

  it('fingerprint ignores submission_id and item_id', () => {
    const left = buildPlanningBusinessFingerprint({
      submission_id: 'sub-a',
      use_shared_chronology: false,
      items: [{ item_id: 'i1', kind: 'execution', primary_membership_id: 'm1' }],
    })
    const right = buildPlanningBusinessFingerprint({
      submission_id: 'sub-b',
      use_shared_chronology: false,
      items: [{ item_id: 'i2', kind: 'execution', primary_membership_id: 'm1' }],
    })
    expect(left).toBe(right)
  })

  it('reuses submission id and item ids when business fingerprint matches', async () => {
    const first = await resolvePlanningSubmissionIntent({
      establishmentId,
      actionPlanId,
      body: {
        use_shared_chronology: false,
        items: [{ item_id: 'throwaway-1', kind: 'execution', primary_membership_id: 'm1' }],
      },
    })
    const second = await resolvePlanningSubmissionIntent({
      establishmentId,
      actionPlanId,
      body: {
        use_shared_chronology: false,
        items: [{ item_id: 'throwaway-2', kind: 'execution', primary_membership_id: 'm1' }],
      },
    })
    expect(second).toEqual(first)
    expect(first.itemIds).toHaveLength(1)

    const payloadA = applyPlanningSubmissionIntent(
      {
        use_shared_chronology: false,
        items: [{ item_id: 'a', kind: 'execution', primary_membership_id: 'm1' }],
      },
      first,
    )
    const payloadB = applyPlanningSubmissionIntent(
      {
        use_shared_chronology: false,
        items: [{ item_id: 'b', kind: 'execution', primary_membership_id: 'm1' }],
      },
      second,
    )
    expect(payloadA).toEqual(payloadB)
    expect(payloadA.submission_id).toBe(first.submissionId)
    expect(payloadA.items[0]?.item_id).toBe(first.itemIds[0])
  })

  it('rotates submission id and item ids when business content changes', async () => {
    const first = await resolvePlanningSubmissionIntent({
      establishmentId,
      actionPlanId,
      body: {
        use_shared_chronology: false,
        items: [{ item_id: 'a', kind: 'execution', primary_membership_id: 'm1' }],
      },
    })
    const second = await resolvePlanningSubmissionIntent({
      establishmentId,
      actionPlanId,
      body: {
        use_shared_chronology: false,
        items: [{ item_id: 'a', kind: 'execution', primary_membership_id: 'm2' }],
      },
    })
    expect(second.submissionId).not.toBe(first.submissionId)
    expect(second.itemIds).not.toEqual(first.itemIds)
    expect(second.requestHash).not.toBe(first.requestHash)
  })

  it('clears stored intents', async () => {
    writePlanningSubmissionIntent(establishmentId, actionPlanId, {
      submissionId: 's1',
      requestHash: 'h1',
      itemIds: ['i1'],
    })
    clearPlanningSubmissionIntent(establishmentId, actionPlanId)
    expect(readPlanningSubmissionIntent(establishmentId, actionPlanId)).toBeNull()

    await resolvePlanningSubmissionIntent({
      establishmentId,
      actionPlanId,
      body: { use_shared_chronology: true, items: [{ kind: 'execution' }] },
    })
    await resolvePlanningSubmissionIntent({
      establishmentId: 'est-2',
      actionPlanId: 'plan-2',
      body: { use_shared_chronology: true, items: [{ kind: 'execution' }] },
    })
    clearAllPlanningSubmissionIntents()
    expect(sessionStorage.length).toBe(0)
  })

  it('clearAllPlanningSubmissionIntents does not throw without sessionStorage', () => {
    const originalDescriptor = Object.getOwnPropertyDescriptor(window, 'sessionStorage')
    try {
      Object.defineProperty(window, 'sessionStorage', {
        configurable: true,
        value: undefined,
      })
      expect(() => clearAllPlanningSubmissionIntents()).not.toThrow()
    } finally {
      if (originalDescriptor) {
        Object.defineProperty(window, 'sessionStorage', originalDescriptor)
      }
    }
  })
})
