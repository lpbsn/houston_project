import { useSyncExternalStore } from 'react'

import {
  addReportingComposePhoto,
  clearReportingComposeDraft,
  clearTaskComposeDraft,
  getObservationComposeDraftSnapshot,
  removeReportingComposePhoto,
  setReportingComposeText,
  setTaskComposeText,
  subscribeObservationComposeDraft,
  type ObservationComposePhotoDraft,
} from './observation-compose-draft-store'

const emptyReporting = {
  text: '',
  photos: [] as ObservationComposePhotoDraft[],
}

export function useReportingComposeDraft(establishmentId: string | null) {
  const snapshot = useSyncExternalStore(
    subscribeObservationComposeDraft,
    getObservationComposeDraftSnapshot,
    getObservationComposeDraftSnapshot,
  )
  const draft =
    establishmentId && snapshot.reporting?.establishmentId === establishmentId
      ? snapshot.reporting
      : emptyReporting

  return {
    text: draft.text,
    photos: draft.photos,
    setText: (text: string) => {
      if (!establishmentId) {
        return
      }
      setReportingComposeText(establishmentId, text)
    },
    addPhoto: (file: File) => {
      if (!establishmentId) {
        return false
      }
      return addReportingComposePhoto(establishmentId, file)
    },
    removePhoto: (localId: string) => {
      removeReportingComposePhoto(localId)
    },
    clear: () => {
      clearReportingComposeDraft()
    },
  }
}

export function useTaskObservationComposeDraft(
  establishmentId: string | null,
  taskExecutionId: string | null,
) {
  const snapshot = useSyncExternalStore(
    subscribeObservationComposeDraft,
    getObservationComposeDraftSnapshot,
    getObservationComposeDraftSnapshot,
  )
  const stored =
    taskExecutionId && establishmentId ? snapshot.tasks[taskExecutionId] : undefined
  const draft =
    stored && stored.establishmentId === establishmentId ? stored : { text: '' }

  return {
    text: draft.text,
    setText: (text: string) => {
      if (!establishmentId || !taskExecutionId) {
        return
      }
      setTaskComposeText(establishmentId, taskExecutionId, text)
    },
    clear: () => {
      if (!taskExecutionId) {
        return
      }
      clearTaskComposeDraft(taskExecutionId)
    },
  }
}
