import { resolveApiUrl } from '@/lib/runtime'

export type NativeDocumentOpenReason = 'fetch' | 'write' | 'viewer'

export type NativeDocumentOpenResult =
  | { ok: true }
  | { ok: false; reason: NativeDocumentOpenReason }

export async function openNativeDocument(url: string): Promise<NativeDocumentOpenResult> {
  try {
    const { FileViewer } = await import('@capacitor/file-viewer')
    await FileViewer.openDocumentFromUrl({ url: resolveApiUrl(url) })
    return { ok: true }
  } catch (error) {
    return { ok: false, reason: nativeDocumentOpenReason(error) }
  }
}

export function nativeDocumentOpenReason(error: unknown): NativeDocumentOpenReason {
  const text = pluginErrorText(error)
  if (text.includes('0013')) {
    return 'write'
  }
  if (text.includes('0010') || text.includes('0008') || /could not open/i.test(text)) {
    return 'viewer'
  }
  return 'fetch'
}

function pluginErrorText(error: unknown): string {
  if (typeof error === 'string') {
    return error
  }
  if (error instanceof Error) {
    const code = 'code' in error ? String(error.code) : ''
    return `${code} ${error.message}`
  }
  if (error && typeof error === 'object') {
    const record = error as { code?: unknown; message?: unknown }
    return `${record.code ?? ''} ${record.message ?? ''}`
  }
  return ''
}
