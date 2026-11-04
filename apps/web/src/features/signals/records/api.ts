import { apiClient, withAuthRetry } from '@/api/client'
import type { components } from '@/api/generated/types'
import { parseStandardApiError } from '@/lib/api-errors'

export type FieldRecord = components['schemas']['FieldRecord']
export type RecordUpdate = components['schemas']['PatchedFieldRecordUpdate'] & {
  expected_updated_at: string
}
export type RecordCommand = components['schemas']['FieldRecordCommand']
export type RecordCreate = components['schemas']['FieldRecordCreate']
export type RecordStage = FieldRecord['stage']
export type RecordFilters = {
  day?: boolean
  stage?: RecordStage
  mine?: boolean
  q?: string
  pole?: string
  from?: string
  to?: string
}
export const recordKeys = {
  all: (site: string) => ['field-records', site] as const,
  detail: (site: string, id: string) =>
    ['field-records', site, 'detail', id] as const,
}
const headers = (token: string | null) =>
  token ? { Authorization: `Bearer ${token}` } : undefined
function result<T>(response: {
  response: Response
  data?: T
  error?: unknown
}): T {
  if (response.response.ok && response.data) return response.data
  throw new Error(
    parseStandardApiError(response.response, response.error).detail,
  )
}
export async function listRecords(
  site: string,
  filters: RecordFilters,
  offset = 0,
) {
  return result(
    await withAuthRetry(
      (token) =>
        apiClient.GET('/api/v1/establishments/{establishment_id}/records/', {
          params: {
            path: { establishment_id: site },
            query: { ...filters, offset },
          },
          headers: headers(token),
        }),
      { refreshable: true },
    ),
  )
}
export async function getRecord(site: string, id: string) {
  return result(
    await withAuthRetry(
      (token) =>
        apiClient.GET(
          '/api/v1/establishments/{establishment_id}/records/{record_id}/',
          {
            params: { path: { establishment_id: site, record_id: id } },
            headers: headers(token),
          },
        ),
      { refreshable: true },
    ),
  )
}
export async function updateRecord(
  site: string,
  id: string,
  body: RecordUpdate,
) {
  return result(
    await withAuthRetry(
      (token) =>
        apiClient.PATCH(
          '/api/v1/establishments/{establishment_id}/records/{record_id}/',
          {
            params: { path: { establishment_id: site, record_id: id } },
            body,
            headers: headers(token),
          },
        ),
      { refreshable: true },
    ),
  )
}
export async function commandRecord(
  site: string,
  id: string,
  body: RecordCommand,
) {
  return result(
    await withAuthRetry(
      (token) =>
        apiClient.POST(
          '/api/v1/establishments/{establishment_id}/records/{record_id}/commands/',
          {
            params: { path: { establishment_id: site, record_id: id } },
            body,
            headers: headers(token),
          },
        ),
      { refreshable: true },
    ),
  )
}
export async function createRecord(site: string, body: RecordCreate) {
  return result(
    await withAuthRetry(
      (token) =>
        apiClient.POST('/api/v1/establishments/{establishment_id}/records/', {
          params: { path: { establishment_id: site } },
          body,
          headers: headers(token),
        }),
      { refreshable: true },
    ),
  )
}
export async function recordOptions(site: string, q = '') {
  return result(
    await withAuthRetry(
      (token) =>
        apiClient.GET(
          '/api/v1/establishments/{establishment_id}/record-options/',
          {
            params: { path: { establishment_id: site }, query: { q } },
            headers: headers(token),
          },
        ),
      { refreshable: true },
    ),
  )
}
export async function recordSection(
  site: string,
  id: string,
  section: 'sources' | 'work' | 'history' | 'objectives',
  offset = 0,
) {
  return result(
    await withAuthRetry(
      (token) =>
        apiClient.GET(
          '/api/v1/establishments/{establishment_id}/records/{record_id}/sections/',
          {
            params: {
              path: { establishment_id: site, record_id: id },
              query: { section, offset },
            },
            headers: headers(token),
          },
        ),
      { refreshable: true },
    ),
  )
}
