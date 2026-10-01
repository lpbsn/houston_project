// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

import { CommentsApiError, putActionPlanCommentUploadBytes } from '../api'

function installXhr(options: { status?: number; error?: boolean }) {
  class FakeXhr {
    status = options.status ?? 200
    upload = { onprogress: null as ((event: ProgressEvent) => void) | null }
    onload: (() => void) | null = null
    onerror: (() => void) | null = null
    onabort: (() => void) | null = null

    open() {}
    setRequestHeader() {}
    abort() {
      this.onabort?.()
    }
    send() {
      if (options.error) {
        this.onerror?.()
        return
      }
      this.onload?.()
    }
  }
  vi.stubGlobal('XMLHttpRequest', FakeXhr)
}

describe('putActionPlanCommentUploadBytes diagnostics', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('describes status 0 as network or bucket CORS, which XHR cannot separate', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    installXhr({ error: true })

    await expect(
      putActionPlanCommentUploadBytes({
        establishmentId: 'est',
        executionId: 'exec',
        uploadId: 'up',
        putUrl: 'https://s3.example.test/comment/put',
        blob: new Blob(['abc']),
        contentType: 'image/png',
      }),
    ).rejects.toMatchObject({
      name: 'CommentsApiError',
      status: 0,
      detail: 'Réseau ou CORS du stockage (pas de réponse HTTP).',
    })
  })

  it('includes the bucket HTTP status', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    installXhr({ status: 403 })

    const error = await putActionPlanCommentUploadBytes({
      establishmentId: 'est',
      executionId: 'exec',
      uploadId: 'up',
      putUrl: 'https://s3.example.test/comment/put',
      blob: new Blob(['abc']),
      contentType: 'image/png',
    }).catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(CommentsApiError)
    expect(error).toMatchObject({
      status: 403,
      detail: 'Échec de l’envoi du fichier (HTTP 403).',
    })
  })
})
