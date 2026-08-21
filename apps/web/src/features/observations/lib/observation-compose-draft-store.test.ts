// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { MAX_OBSERVATION_PHOTOS } from '@/features/observations/types'

import {
  __resetObservationComposeDraftStoreForTests,
  addReportingComposePhoto,
  clearObservationComposeDrafts,
  clearReportingComposeDraft,
  clearTaskComposeDraft,
  getObservationComposeDraftSnapshot,
  getReportingComposeDraft,
  getTaskComposeDraft,
  removeReportingComposePhoto,
  setReportingComposeText,
  setTaskComposeText,
} from './observation-compose-draft-store'

const EST_A = 'est-a'
const EST_B = 'est-b'

function makeFile(name: string) {
  return new File(['bytes'], name, { type: 'image/jpeg' })
}

describe('observation-compose-draft-store', () => {
  beforeEach(() => {
    let previewCount = 0
    vi.spyOn(URL, 'createObjectURL').mockImplementation(() => {
      previewCount += 1
      return `blob:preview-${previewCount}`
    })
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
  })

  afterEach(() => {
    __resetObservationComposeDraftStoreForTests()
    window.localStorage.clear()
    window.sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it('keeps reporting text and local photos across snapshot reads (process-alive remount)', () => {
    setReportingComposeText(EST_A, 'Tache visible sur le mur.')
    expect(addReportingComposePhoto(EST_A, makeFile('photo.jpg'))).toBe(true)

    const first = getReportingComposeDraft(EST_A)
    const second = getReportingComposeDraft(EST_A)

    expect(second.text).toBe('Tache visible sur le mur.')
    expect(second.photos).toHaveLength(1)
    expect(second.photos[0]?.file.name).toBe('photo.jpg')
    expect(second.photos[0]?.previewUrl).toBe(first.photos[0]?.previewUrl)
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1)
  })

  it('does not write compose drafts to localStorage or sessionStorage', () => {
    setReportingComposeText(EST_A, 'Tache visible sur le mur.')
    addReportingComposePhoto(EST_A, makeFile('photo.jpg'))
    setTaskComposeText(EST_A, 'task-1', 'Observation depuis la tâche.')

    expect(window.localStorage.length).toBe(0)
    expect(window.sessionStorage.length).toBe(0)
  })

  it('clears reporting photos and revokes preview urls', () => {
    addReportingComposePhoto(EST_A, makeFile('photo.jpg'))
    const previewUrl = getReportingComposeDraft(EST_A).photos[0]?.previewUrl
    expect(previewUrl).toBe('blob:preview-1')

    removeReportingComposePhoto(getReportingComposeDraft(EST_A).photos[0]!.localId)

    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:preview-1')
    expect(getReportingComposeDraft(EST_A).photos).toHaveLength(0)
  })

  it('rejects a fourth photo without mutating the draft', () => {
    expect(addReportingComposePhoto(EST_A, makeFile('a.jpg'))).toBe(true)
    expect(addReportingComposePhoto(EST_A, makeFile('b.jpg'))).toBe(true)
    expect(addReportingComposePhoto(EST_A, makeFile('c.jpg'))).toBe(true)
    expect(addReportingComposePhoto(EST_A, makeFile('d.jpg'))).toBe(false)
    expect(getReportingComposeDraft(EST_A).photos).toHaveLength(MAX_OBSERVATION_PHOTOS)
  })

  it('isolates task drafts by taskExecutionId', () => {
    setTaskComposeText(EST_A, 'task-1', 'Première tâche.')
    setTaskComposeText(EST_A, 'task-2', 'Deuxième tâche.')

    expect(getTaskComposeDraft(EST_A, 'task-1').text).toBe('Première tâche.')
    expect(getTaskComposeDraft(EST_A, 'task-2').text).toBe('Deuxième tâche.')

    clearTaskComposeDraft('task-1')

    expect(getTaskComposeDraft(EST_A, 'task-1').text).toBe('')
    expect(getTaskComposeDraft(EST_A, 'task-2').text).toBe('Deuxième tâche.')
  })

  it('does not expose a task draft from another establishment', () => {
    setTaskComposeText(EST_A, 'task-1', 'Texte établissement A.')

    expect(getTaskComposeDraft(EST_B, 'task-1').text).toBe('')
    expect(getTaskComposeDraft(EST_A, 'task-1').text).toBe('Texte établissement A.')
  })

  it('clears reporting after successful submit helper', () => {
    setReportingComposeText(EST_A, 'Tache visible sur le mur.')
    addReportingComposePhoto(EST_A, makeFile('photo.jpg'))

    clearReportingComposeDraft()

    expect(getReportingComposeDraft(EST_A).text).toBe('')
    expect(getReportingComposeDraft(EST_A).photos).toHaveLength(0)
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:preview-1')
  })

  it('clears all drafts on logout or establishment switch', () => {
    setReportingComposeText(EST_A, 'Tache visible sur le mur.')
    addReportingComposePhoto(EST_A, makeFile('photo.jpg'))
    setTaskComposeText(EST_A, 'task-1', 'Observation depuis la tâche.')

    clearObservationComposeDrafts()

    expect(getObservationComposeDraftSnapshot()).toEqual({
      reporting: null,
      tasks: {},
    })
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:preview-1')
  })
})
