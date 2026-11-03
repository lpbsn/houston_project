import type { MyDayCard, MyDaySectionKey } from './api'

export type MyDaySectionSlot = {
  count: number
  nextCursor: string | null
  items: MyDayCard[]
  stalled: boolean
  continuationError: boolean
}

export type MyDayWindow = {
  generation: number
  updatedAt: number
  establishmentId: string | null
  sections: Record<MyDaySectionKey, MyDaySectionSlot>
}

export type MyDayContinuation = {
  section: MyDaySectionKey
  next_cursor: string | null
  items: MyDayCard[]
}

const sectionKeys: MyDaySectionKey[] = ['action', 'follow', 'upcoming']

function emptySlot(): MyDaySectionSlot {
  return {
    count: 0,
    nextCursor: null,
    items: [],
    stalled: false,
    continuationError: false,
  }
}

export function emptyMyDayWindow(establishmentId: string | null = null): MyDayWindow {
  return {
    generation: 0,
    updatedAt: 0,
    establishmentId,
    sections: {
      action: emptySlot(),
      follow: emptySlot(),
      upcoming: emptySlot(),
    },
  }
}

export function applyMyDayInitial(
  window: MyDayWindow,
  sections: Record<MyDaySectionKey, { count: number, next_cursor: string | null, items: MyDayCard[] }>,
  updatedAt: number,
): MyDayWindow {
  return {
    generation: window.generation + 1,
    updatedAt,
    establishmentId: window.establishmentId,
    sections: Object.fromEntries(
      sectionKeys.map((key) => [
        key,
        {
          count: sections[key].count,
          nextCursor: sections[key].next_cursor,
          items: sections[key].items,
          stalled: false,
          continuationError: false,
        },
      ]),
    ) as MyDayWindow['sections'],
  }
}

export function applyMyDayContinuation(
  window: MyDayWindow,
  generation: number,
  establishmentId: string,
  section: MyDaySectionKey,
  requestCursor: string,
  page: MyDayContinuation,
): { window: MyDayWindow, ignored: boolean, stalled: boolean } {
  if (
    generation !== window.generation
    || establishmentId !== window.establishmentId
    || page.section !== section
  ) {
    return { window, ignored: true, stalled: false }
  }
  if (page.next_cursor === requestCursor) {
    return {
      window: {
        ...window,
        sections: {
          ...window.sections,
          [section]: { ...window.sections[section], stalled: true, continuationError: false },
        },
      },
      ignored: false,
      stalled: true,
    }
  }
  const seen = new Set(window.sections[section].items.map((item) => item.execution_id))
  const added = page.items.filter((item) => !seen.has(item.execution_id))
  return {
    window: {
      ...window,
      sections: {
        ...window.sections,
        [section]: {
          ...window.sections[section],
          nextCursor: page.next_cursor,
          items: [...window.sections[section].items, ...added],
          stalled: false,
          continuationError: false,
        },
      },
    },
    ignored: false,
    stalled: false,
  }
}

export function markMyDayContinuationError(
  window: MyDayWindow,
  generation: number,
  establishmentId: string,
  section: MyDaySectionKey,
): MyDayWindow {
  if (generation !== window.generation || establishmentId !== window.establishmentId) return window
  return {
    ...window,
    sections: {
      ...window.sections,
      [section]: { ...window.sections[section], continuationError: true },
    },
  }
}
