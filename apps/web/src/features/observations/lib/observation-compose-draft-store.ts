import { MAX_OBSERVATION_PHOTOS } from '@/features/observations/types'

export type ObservationComposePhotoDraft = {
  localId: string
  file: File
  previewUrl: string
}

export type ReportingComposeDraft = {
  establishmentId: string
  text: string
  photos: ObservationComposePhotoDraft[]
}

export type TaskComposeDraft = {
  establishmentId: string
  text: string
}

export type ObservationComposeDraftState = {
  reporting: ReportingComposeDraft | null
  tasks: Record<string, TaskComposeDraft>
}

type Listener = () => void

const listeners = new Set<Listener>()

const emptyState: ObservationComposeDraftState = {
  reporting: null,
  tasks: {},
}

let state: ObservationComposeDraftState = emptyState

function emit(): void {
  for (const listener of listeners) {
    listener()
  }
}

function setState(next: ObservationComposeDraftState): void {
  state = next
  emit()
}

function revokePreviewUrl(url: string): void {
  URL.revokeObjectURL(url)
}

function revokeReportingPhotos(draft: ReportingComposeDraft | null): void {
  if (!draft) {
    return
  }
  for (const photo of draft.photos) {
    revokePreviewUrl(photo.previewUrl)
  }
}

export function subscribeObservationComposeDraft(listener: Listener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function getObservationComposeDraftSnapshot(): ObservationComposeDraftState {
  return state
}

export function getReportingComposeDraft(establishmentId: string): ReportingComposeDraft {
  const draft = state.reporting
  if (draft && draft.establishmentId === establishmentId) {
    return draft
  }

  return {
    establishmentId,
    text: '',
    photos: [],
  }
}

export function getTaskComposeDraft(
  establishmentId: string,
  taskExecutionId: string,
): TaskComposeDraft {
  const draft = state.tasks[taskExecutionId]
  if (draft && draft.establishmentId === establishmentId) {
    return draft
  }

  return {
    establishmentId,
    text: '',
  }
}

export function setReportingComposeText(establishmentId: string, text: string): void {
  const current =
    state.reporting?.establishmentId === establishmentId ? state.reporting : null
  if (!current) {
    revokeReportingPhotos(state.reporting)
    setState({
      ...state,
      reporting: {
        establishmentId,
        text,
        photos: [],
      },
    })
    return
  }

  if (current.text === text) {
    return
  }

  setState({
    ...state,
    reporting: {
      ...current,
      text,
    },
  })
}

export function addReportingComposePhoto(establishmentId: string, file: File): boolean {
  const current =
    state.reporting?.establishmentId === establishmentId
      ? state.reporting
      : { establishmentId, text: '', photos: [] }

  if (current.photos.length >= MAX_OBSERVATION_PHOTOS) {
    return false
  }

  if (state.reporting && state.reporting.establishmentId !== establishmentId) {
    revokeReportingPhotos(state.reporting)
  }

  const photo: ObservationComposePhotoDraft = {
    localId: crypto.randomUUID(),
    file,
    previewUrl: URL.createObjectURL(file),
  }

  setState({
    ...state,
    reporting: {
      ...current,
      photos: [...current.photos, photo],
    },
  })
  return true
}

export function removeReportingComposePhoto(localId: string): void {
  const current = state.reporting
  if (!current) {
    return
  }

  const photo = current.photos.find((item) => item.localId === localId)
  if (!photo) {
    return
  }

  revokePreviewUrl(photo.previewUrl)
  setState({
    ...state,
    reporting: {
      ...current,
      photos: current.photos.filter((item) => item.localId !== localId),
    },
  })
}

export function clearReportingComposeDraft(): void {
  if (!state.reporting) {
    return
  }
  revokeReportingPhotos(state.reporting)
  setState({
    ...state,
    reporting: null,
  })
}

export function setTaskComposeText(
  establishmentId: string,
  taskExecutionId: string,
  text: string,
): void {
  const current = state.tasks[taskExecutionId]
  if (current?.establishmentId === establishmentId && current.text === text) {
    return
  }

  setState({
    ...state,
    tasks: {
      ...state.tasks,
      [taskExecutionId]: {
        establishmentId,
        text,
      },
    },
  })
}

export function clearTaskComposeDraft(taskExecutionId: string): void {
  if (!(taskExecutionId in state.tasks)) {
    return
  }

  const tasks = { ...state.tasks }
  delete tasks[taskExecutionId]
  setState({
    ...state,
    tasks,
  })
}

export function clearObservationComposeDrafts(): void {
  revokeReportingPhotos(state.reporting)
  setState({
    reporting: null,
    tasks: {},
  })
}

/** Test helper */
export function __resetObservationComposeDraftStoreForTests(): void {
  revokeReportingPhotos(state.reporting)
  listeners.clear()
  state = {
    reporting: null,
    tasks: {},
  }
}
