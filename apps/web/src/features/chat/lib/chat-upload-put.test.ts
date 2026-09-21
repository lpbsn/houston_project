// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

import { isExternalPresignedPutUrl } from './chat-upload-put'

describe('isExternalPresignedPutUrl', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('treats a blank put_url as the Houston filesystem PUT', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    expect(
      isExternalPresignedPutUrl(
        '',
        'http://localhost:8000/api/v1/establishments/est/chat/uploads/up/content/',
      ),
    ).toBe(false)
  })

  it('treats a Houston /content/ URL as authenticated, not presigned', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    const houston =
      'http://localhost:8000/api/v1/establishments/est/chat/uploads/up/content/'
    expect(isExternalPresignedPutUrl(houston, houston)).toBe(false)
    expect(
      isExternalPresignedPutUrl(
        '/api/v1/establishments/est/chat/uploads/up/content/',
        houston,
      ),
    ).toBe(false)
  })

  it('treats an S3 presigned URL as external', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    expect(
      isExternalPresignedPutUrl(
        'https://s3.example.test/chat/put?X-Amz-Signature=abc',
        'http://localhost:8000/api/v1/establishments/est/chat/uploads/up/content/',
      ),
    ).toBe(true)
  })
})
