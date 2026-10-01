// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

const { fetchWithAuthRetry } = vi.hoisted(() => ({
  fetchWithAuthRetry: vi.fn(),
}))

vi.mock('@/api/client', () => ({
  fetchWithAuthRetry: (...args: unknown[]) => fetchWithAuthRetry(...args),
}))

import { isExternalPresignedPutUrl, PresignedPutError, putPresignedBytes } from './presigned-put'

const HOUSTON = 'http://localhost:8000/api/v1/establishments/est/chat/uploads/up/content/'

function installXhr(options: {
  status?: number
  error?: boolean
  abort?: boolean
  lengthComputable?: boolean
}) {
  const instances: Array<{
    method: string
    url: string
    headers: Record<string, string>
    aborted: boolean
  }> = []

  class FakeXhr {
    status = options.status ?? 200
    upload = { onprogress: null as ((event: ProgressEvent) => void) | null }
    onload: (() => void) | null = null
    onerror: (() => void) | null = null
    onabort: (() => void) | null = null
    method = ''
    url = ''
    headers: Record<string, string> = {}
    aborted = false

    open(method: string, url: string) {
      this.method = method
      this.url = url
    }

    setRequestHeader(name: string, value: string) {
      this.headers[name] = value
    }

    send() {
      instances.push({
        method: this.method,
        url: this.url,
        headers: { ...this.headers },
        aborted: false,
      })
      if (options.lengthComputable) {
        this.upload.onprogress?.({ lengthComputable: true, loaded: 1, total: 2 } as ProgressEvent)
      }
      if (options.abort) {
        this.aborted = true
        instances[instances.length - 1]!.aborted = true
        this.onabort?.()
        return
      }
      if (options.error) {
        this.onerror?.()
        return
      }
      this.onload?.()
    }

    abort() {
      this.aborted = true
      this.onabort?.()
    }
  }

  vi.stubGlobal('XMLHttpRequest', FakeXhr)
  return instances
}

describe('isExternalPresignedPutUrl', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('treats a blank put_url as the Houston filesystem PUT', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    expect(isExternalPresignedPutUrl('', HOUSTON)).toBe(false)
  })

  it('treats a Houston /content/ URL as authenticated, not presigned', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    expect(isExternalPresignedPutUrl(HOUSTON, HOUSTON)).toBe(false)
    expect(
      isExternalPresignedPutUrl('/api/v1/establishments/est/chat/uploads/up/content/', HOUSTON),
    ).toBe(false)
  })

  it('treats an S3 presigned URL as external', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    expect(
      isExternalPresignedPutUrl('https://s3.example.test/chat/put?X-Amz-Signature=abc', HOUSTON),
    ).toBe(true)
  })
})

describe('putPresignedBytes', () => {
  afterEach(() => {
    fetchWithAuthRetry.mockReset()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('PUTs an external URL with XHR and reports progress', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    const opens = installXhr({ status: 200, lengthComputable: true })
    const onProgress = vi.fn()

    await putPresignedBytes({
      putUrl: 'https://s3.example.test/chat/put?X-Amz-Signature=abc',
      houstonContentUrl: HOUSTON,
      blob: new Blob(['abc']),
      contentType: 'image/jpeg',
      onProgress,
    })

    expect(opens).toEqual([
      {
        method: 'PUT',
        url: 'https://s3.example.test/chat/put?X-Amz-Signature=abc',
        headers: { 'Content-Type': 'image/jpeg' },
        aborted: false,
      },
    ])
    expect(onProgress).toHaveBeenCalledWith(0.5)
    expect(onProgress).toHaveBeenCalledWith(1)
    expect(fetchWithAuthRetry).not.toHaveBeenCalled()
  })

  it('preserves an HTTP status from the bucket', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    installXhr({ status: 403 })

    await expect(
      putPresignedBytes({
        putUrl: 'https://s3.example.test/chat/put',
        houstonContentUrl: HOUSTON,
        blob: new Blob(['abc']),
        contentType: 'image/jpeg',
      }),
    ).rejects.toMatchObject({ name: 'PresignedPutError', status: 403, response: null })
  })

  it('reports status 0 when XHR has no HTTP response', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    installXhr({ error: true })

    await expect(
      putPresignedBytes({
        putUrl: 'https://s3.example.test/chat/put',
        houstonContentUrl: HOUSTON,
        blob: new Blob(['abc']),
        contentType: 'image/jpeg',
      }),
    ).rejects.toMatchObject({ status: 0, message: 'Upload failed.' })
  })

  it('rejects an aborted external PUT with status 0', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    installXhr({ status: 200 })
    const controller = new AbortController()
    controller.abort()

    await expect(
      putPresignedBytes({
        putUrl: 'https://s3.example.test/chat/put',
        houstonContentUrl: HOUSTON,
        blob: new Blob(['abc']),
        contentType: 'image/jpeg',
        signal: controller.signal,
      }),
    ).rejects.toMatchObject({ status: 0, message: 'Upload cancelled.' })
  })

  it('uses the authenticated Houston PUT when the URL is empty or /content/', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    installXhr({ status: 500 })
    fetchWithAuthRetry.mockResolvedValue({ ok: true })
    const blob = new Blob(['abc'])

    await putPresignedBytes({
      putUrl: '',
      houstonContentUrl: HOUSTON,
      blob,
      contentType: 'image/png',
    })

    expect(fetchWithAuthRetry).toHaveBeenCalledWith(HOUSTON, {
      method: 'PUT',
      headers: { 'Content-Type': 'image/png' },
      body: blob,
      signal: undefined,
    })
  })

  it('keeps the Houston response on a non-OK content PUT', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    const response = { ok: false, status: 400 }
    fetchWithAuthRetry.mockResolvedValue(response)

    try {
      await putPresignedBytes({
        putUrl: HOUSTON,
        houstonContentUrl: HOUSTON,
        blob: new Blob(['abc']),
        contentType: 'image/png',
      })
      throw new Error('expected rejection')
    } catch (error) {
      expect(error).toBeInstanceOf(PresignedPutError)
      expect(error).toMatchObject({ status: 400, response })
    }
  })
})
