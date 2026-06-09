import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const featureDir = dirname(fileURLToPath(import.meta.url))
const pagesDir = join(featureDir, '../pages')

function readPage(filename: string): string {
  return readFileSync(join(pagesDir, filename), 'utf8')
}

describe('chat-page', () => {
  const source = readPage('chat-page.tsx')

  it('uses websocket reconnect banner and conversation list', () => {
    expect(source).toContain('ChatReconnectBanner')
    expect(source).toContain('ConversationRow')
    expect(source).toContain('onOpenConversation')
  })

  it('gates the page when chat is unavailable', () => {
    expect(source).toContain('Chat indisponible')
    expect(source).toContain('chat_enabled')
  })
})

describe('chat-conversation-page', () => {
  const source = readPage('chat-conversation-page.tsx')

  it('sends messages through websocket helper and shows retention notice', () => {
    expect(source).toContain('sendChatMessage')
    expect(source).toContain('7 jours')
    expect(source).toContain('ChatComposer')
  })

  it('marks conversation seen through REST mutation', () => {
    expect(source).toContain('useMarkConversationSeenMutation')
    expect(source).toContain('markConversationSeen')
  })
})
