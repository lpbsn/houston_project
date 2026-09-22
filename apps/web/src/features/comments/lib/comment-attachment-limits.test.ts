import { describe, expect, it } from 'vitest'

import {
  describeCommentAttachmentSelectionError,
  validateCommentAttachmentFile,
} from './comment-attachment-limits'

function file(name: string, type: string, size: number) {
  return new File([new Uint8Array(size)], name, { type })
}

describe('comment attachment limits', () => {
  it('accepts supported image and pdf files', () => {
    expect(validateCommentAttachmentFile(file('a.png', 'image/png', 12))).toBeNull()
    expect(validateCommentAttachmentFile(file('b.pdf', 'application/pdf', 12))).toBeNull()
    expect(validateCommentAttachmentFile(file('c.heic', 'image/heic', 12))).toBeNull()
  })

  it('rejects oversized and unsupported files', () => {
    expect(validateCommentAttachmentFile(file('big.png', 'image/png', 11 * 1024 * 1024))).toBe(
      'too_large',
    )
    expect(validateCommentAttachmentFile(file('note.txt', 'text/plain', 12))).toBe(
      'unsupported_type',
    )
    expect(describeCommentAttachmentSelectionError('too_many')).toMatch(/4 fichiers/)
  })
})
