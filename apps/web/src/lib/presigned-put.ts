import { fetchWithAuthRetry } from '@/api/client'

import { getApiBaseUrl } from '@/lib/runtime'

export class PresignedPutError extends Error {
  readonly status: number
  readonly response: Response | null

  constructor(status: number, detail: string, response: Response | null = null) {
    super(detail)
    this.name = 'PresignedPutError'
    this.status = status
    this.response = response
  }
}

function resolveUrl(value: string): URL | null {
  try {
    if (/^[a-z][a-z0-9+.-]*:/i.test(value)) {
      return new URL(value)
    }
    const base =
      getApiBaseUrl() ||
      (typeof window !== 'undefined' && window.location?.origin
        ? window.location.origin
        : 'http://same-origin.test')
    return new URL(value, `${base.replace(/\/+$/, '')}/`)
  } catch {
    return null
  }
}

function normalizePath(pathname: string): string {
  if (pathname.length > 1 && pathname.endsWith('/')) {
    return pathname.slice(0, -1)
  }
  return pathname
}

/** True when put_url is an external presigned PUT (S3). Empty or Houston /content/ is not. */
export function isExternalPresignedPutUrl(putUrl: string, houstonContentUrl: string): boolean {
  const trimmed = putUrl.trim()
  if (!trimmed) {
    return false
  }
  const put = resolveUrl(trimmed)
  const houston = resolveUrl(houstonContentUrl)
  if (!put || !houston) {
    return true
  }
  return put.origin !== houston.origin || normalizePath(put.pathname) !== normalizePath(houston.pathname)
}

export async function putPresignedBytes(options: {
  putUrl: string
  houstonContentUrl: string
  blob: Blob
  contentType: string
  signal?: AbortSignal
  onProgress?: (ratio: number) => void
}): Promise<void> {
  if (isExternalPresignedPutUrl(options.putUrl, options.houstonContentUrl)) {
    await putExternalPresignedBytes(options)
    return
  }

  const response = await fetchWithAuthRetry(options.houstonContentUrl, {
    method: 'PUT',
    headers: {
      'Content-Type': options.contentType,
    },
    body: options.blob,
    signal: options.signal,
  })
  if (!response.ok) {
    throw new PresignedPutError(response.status, 'Upload failed.', response)
  }
  options.onProgress?.(1)
}

function putExternalPresignedBytes(options: {
  putUrl: string
  blob: Blob
  contentType: string
  signal?: AbortSignal
  onProgress?: (ratio: number) => void
}): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open('PUT', options.putUrl)
    request.setRequestHeader('Content-Type', options.contentType)
    const abort = () => {
      request.abort()
      reject(new PresignedPutError(0, 'Upload cancelled.'))
    }
    if (options.signal?.aborted) {
      abort()
      return
    }
    options.signal?.addEventListener('abort', abort, { once: true })
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        options.onProgress?.(event.loaded / event.total)
      }
    }
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        options.onProgress?.(1)
        resolve()
        return
      }
      reject(new PresignedPutError(request.status, 'Upload failed.'))
    }
    request.onerror = () => reject(new PresignedPutError(0, 'Upload failed.'))
    request.onabort = () => reject(new PresignedPutError(0, 'Upload cancelled.'))
    request.send(options.blob)
  })
}
