// @vitest-environment jsdom

import { describe, expect, it, vi } from 'vitest'

import { feedCardKeyDown } from './feed-card-keyboard'

function createKeyboardEvent(
  key: string,
  target: EventTarget,
  currentTarget: EventTarget,
): Parameters<typeof feedCardKeyDown>[0] {
  return {
    key,
    target,
    currentTarget,
    preventDefault: vi.fn(),
  } as unknown as Parameters<typeof feedCardKeyDown>[0]
}

describe('feedCardKeyDown', () => {
  it('triggers onSelect on Enter when target is the card', () => {
    const onSelect = vi.fn()
    const card = document.createElement('article')

    feedCardKeyDown(createKeyboardEvent('Enter', card, card), onSelect, 'signal-1')

    expect(onSelect).toHaveBeenCalledWith('signal-1')
  })

  it('triggers onSelect on Space when target is the card', () => {
    const onSelect = vi.fn()
    const card = document.createElement('article')

    feedCardKeyDown(createKeyboardEvent(' ', card, card), onSelect, 'signal-1')

    expect(onSelect).toHaveBeenCalledWith('signal-1')
  })

  it('does not trigger onSelect when event originates from nested button', () => {
    const onSelect = vi.fn()
    const card = document.createElement('article')
    const button = document.createElement('button')
    card.appendChild(button)

    feedCardKeyDown(createKeyboardEvent('Enter', button, card), onSelect, 'signal-1')

    expect(onSelect).not.toHaveBeenCalled()
  })

  it('ignores other keys', () => {
    const onSelect = vi.fn()
    const card = document.createElement('article')

    feedCardKeyDown(createKeyboardEvent('Tab', card, card), onSelect, 'signal-1')

    expect(onSelect).not.toHaveBeenCalled()
  })
})
