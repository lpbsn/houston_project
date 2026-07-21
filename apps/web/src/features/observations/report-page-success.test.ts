import { describe, expect, it } from 'vitest'

import {
  formatProgressBannerLabel,
  formatTerminalBannerLabel,
  resolveTerminalBannerNavigation,
} from './lib/observation-processing-banner-copy'

describe('observation processing banner outcomes', () => {
  it('formats create / update / mixed / empty / failed', () => {
    expect(
      formatTerminalBannerLabel({
        status: 'processed',
        uxStatus: 'signal_created',
        processedAt: null,
        sortAt: 'a',
        createdCount: 1,
        updatedCount: 0,
        signalIds: ['s1'],
      }),
    ).toBe('1 observation créée')

    expect(
      formatTerminalBannerLabel({
        status: 'processed',
        uxStatus: 'signal_updated',
        processedAt: null,
        sortAt: 'a',
        createdCount: 0,
        updatedCount: 2,
        signalIds: ['s1', 's2'],
      }),
    ).toBe('2 observations existantes mises à jour')

    expect(
      formatTerminalBannerLabel({
        status: 'processed',
        uxStatus: 'signal_created',
        processedAt: null,
        sortAt: 'a',
        createdCount: 2,
        updatedCount: 1,
        signalIds: ['a', 'b', 'c'],
      }),
    ).toBe('2 observations créées · 1 observation existante mise à jour')

    expect(
      formatTerminalBannerLabel({
        status: 'processed',
        uxStatus: 'no_signal_created',
        processedAt: null,
        sortAt: 'a',
        createdCount: 0,
        updatedCount: 0,
        signalIds: [],
      }),
    ).toBe('Observation enregistrée — aucun élément opérationnel détecté')

    expect(
      formatTerminalBannerLabel({
        status: 'failed',
        uxStatus: 'analysis_failed',
        processedAt: null,
        sortAt: 'a',
        createdCount: 0,
        updatedCount: 0,
        signalIds: [],
      }),
    ).toBe('Observation enregistrée, mais son analyse a échoué')
  })

  it('resolves navigation targets', () => {
    expect(
      resolveTerminalBannerNavigation({
        status: 'processed',
        uxStatus: 'signal_created',
        processedAt: null,
        sortAt: 'a',
        createdCount: 1,
        updatedCount: 0,
        signalIds: ['sig-1'],
      }),
    ).toBe('/signals/sig-1')

    expect(
      resolveTerminalBannerNavigation({
        status: 'processed',
        uxStatus: 'signal_created',
        processedAt: null,
        sortAt: 'a',
        createdCount: 2,
        updatedCount: 0,
        signalIds: ['a', 'b'],
      }),
    ).toBe('/signals')

    expect(
      resolveTerminalBannerNavigation({
        status: 'processed',
        uxStatus: 'no_signal_created',
        processedAt: null,
        sortAt: 'a',
        createdCount: 0,
        updatedCount: 0,
        signalIds: [],
      }),
    ).toBeNull()

    expect(
      resolveTerminalBannerNavigation({
        status: 'failed',
        uxStatus: 'analysis_failed',
        processedAt: null,
        sortAt: 'a',
        createdCount: 0,
        updatedCount: 0,
        signalIds: [],
      }),
    ).toBe('/reporting')
  })

  it('formats multi progress label', () => {
    expect(formatProgressBannerLabel('processing', 3)).toBe(
      '3 observations en cours d’analyse',
    )
    expect(formatProgressBannerLabel('queued', 1)).toBe('Analyse en attente')
    expect(formatProgressBannerLabel('retrying', 1)).toBe('Nouvelle tentative d’analyse')
  })
})
