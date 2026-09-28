/**
 * Bounded hydrated window for one feed collection.
 *
 * Page 1 of the current generation stays available for a return to the top.
 * The focus holds the pages around the viewport, including at most one
 * preloaded page. Evicting a slot drops its items and cursors. The single
 * `behindCursor` is replaced, never stacked.
 */

/** Pages kept around the viewport, excluding the dedicated first page. */
export const FEED_FOCUS_PAGE_LIMIT = 2

export type FeedPageSlot<TItem> = {
  requestCursor: string | null
  nextCursor: string | null
  hasMore: boolean
  items: TItem[]
}

export type FeedReadingWindow<TItem> = {
  generation: number
  pageOne: FeedPageSlot<TItem> | null
  focus: FeedPageSlot<TItem>[]
  behindCursor: string | null
  stalled: boolean
}

export type FeedContinuationPage = {
  items: readonly unknown[]
  nextCursor: string | null
  hasMore: boolean
}

export function emptyFeedReadingWindow<TItem>(): FeedReadingWindow<TItem> {
  return {
    generation: 0,
    pageOne: null,
    focus: [],
    behindCursor: null,
    stalled: false,
  }
}

export function continuationPageStalled(
  requestedCursor: string,
  page: FeedContinuationPage,
): boolean {
  if (page.items.length === 0 && page.hasMore) {
    return true
  }
  return page.hasMore && page.nextCursor === requestedCursor
}

function pageChainsFrom<TItem>(
  previous: FeedPageSlot<TItem>,
  next: FeedPageSlot<TItem>,
): boolean {
  return previous.nextCursor != null && previous.nextCursor === next.requestCursor
}

function focusIsContiguous<TItem>(focus: readonly FeedPageSlot<TItem>[]): boolean {
  for (let index = 1; index < focus.length; index += 1) {
    if (!pageChainsFrom(focus[index - 1]!, focus[index]!)) {
      return false
    }
  }
  return true
}

export function focusContinuesPageOne<TItem>(window: FeedReadingWindow<TItem>): boolean {
  if (!window.pageOne) {
    return false
  }
  if (window.focus.length === 0) {
    return true
  }
  return pageChainsFrom(window.pageOne, window.focus[0]!) && focusIsContiguous(window.focus)
}

export function renderedSlots<TItem>(
  window: FeedReadingWindow<TItem>,
): FeedPageSlot<TItem>[] {
  if (!window.pageOne) {
    return window.focus
  }
  if (focusContinuesPageOne(window)) {
    return [window.pageOne, ...window.focus]
  }
  return window.focus
}

export function windowHead<TItem>(
  window: FeedReadingWindow<TItem>,
): FeedPageSlot<TItem> | null {
  const slots = renderedSlots(window)
  return slots[slots.length - 1] ?? null
}

export function renderedItems<TItem>(
  window: FeedReadingWindow<TItem>,
  itemId: (item: TItem) => string,
): TItem[] {
  const order: string[] = []
  const byId = new Map<string, TItem>()
  for (const slot of renderedSlots(window)) {
    for (const item of slot.items) {
      const id = itemId(item)
      if (!byId.has(id)) {
        order.push(id)
      }
      byId.set(id, item)
    }
  }
  return order.map((id) => byId.get(id)!)
}

export function hydratedItems<TItem>(window: FeedReadingWindow<TItem>): TItem[] {
  const items = window.pageOne ? [...window.pageOne.items] : []
  for (const slot of window.focus) {
    items.push(...slot.items)
  }
  return items
}

function withoutId<TItem>(items: readonly TItem[], id: string, itemId: (item: TItem) => string) {
  return items.filter((item) => itemId(item) !== id)
}

export function replaceWithFirstPage<TItem>(
  window: FeedReadingWindow<TItem>,
  page: FeedPageSlot<TItem>,
  generation?: number,
): FeedReadingWindow<TItem> {
  return {
    generation: generation ?? window.generation + 1,
    pageOne: { ...page, requestCursor: null },
    focus: [],
    behindCursor: null,
    stalled: false,
  }
}

export function showRetainedPageOne<TItem>(
  window: FeedReadingWindow<TItem>,
): FeedReadingWindow<TItem> {
  return {
    ...window,
    focus: [],
    behindCursor: null,
    stalled: false,
  }
}

export function placeResumePage<TItem>(
  window: FeedReadingWindow<TItem>,
  slot: FeedPageSlot<TItem>,
): FeedReadingWindow<TItem> {
  if (slot.requestCursor == null) {
    return {
      ...window,
      pageOne: slot,
      focus: [],
      behindCursor: null,
      stalled: false,
    }
  }
  return {
    ...window,
    focus: [slot],
    behindCursor: null,
    stalled: false,
  }
}

function replaceHydratedItem<TItem>(
  window: FeedReadingWindow<TItem>,
  id: string,
  nextItem: TItem,
  itemId: (item: TItem) => string,
): FeedReadingWindow<TItem> | null {
  let found = false
  const mapItems = (items: TItem[]) =>
    items.map((item) => {
      if (itemId(item) !== id) {
        return item
      }
      found = true
      return nextItem
    })
  const pageOne = window.pageOne
    ? { ...window.pageOne, items: mapItems(window.pageOne.items) }
    : null
  const focus = window.focus.map((slot) => ({ ...slot, items: mapItems(slot.items) }))
  if (!found) {
    return null
  }
  return { ...window, pageOne, focus }
}

/** Later payload wins and stays on the slot that already holds the id. */
function absorbIncomingItems<TItem>(
  window: FeedReadingWindow<TItem>,
  incoming: readonly TItem[],
  itemId: (item: TItem) => string,
): { window: FeedReadingWindow<TItem>; fresh: TItem[] } {
  let next = window
  const fresh: TItem[] = []
  const seen = new Set<string>()
  for (const item of incoming) {
    const id = itemId(item)
    if (seen.has(id)) {
      continue
    }
    seen.add(id)
    const replaced = replaceHydratedItem(next, id, item, itemId)
    if (replaced) {
      next = replaced
    } else {
      fresh.push(item)
    }
  }
  return { window: next, fresh }
}

export function appendForwardPage<TItem>(
  window: FeedReadingWindow<TItem>,
  requestedCursor: string,
  page: FeedContinuationPage & { items: readonly TItem[] },
  itemId: (item: TItem) => string,
): { window: FeedReadingWindow<TItem>; stalled: boolean; ignored: boolean } {
  const head = windowHead(window)
  if (!head?.hasMore || head.nextCursor !== requestedCursor) {
    return { window, stalled: false, ignored: true }
  }
  if (continuationPageStalled(requestedCursor, page)) {
    return {
      window: { ...window, stalled: true },
      stalled: true,
      ignored: false,
    }
  }
  const absorbed = absorbIncomingItems(window, page.items, itemId)
  const slot: FeedPageSlot<TItem> = {
    requestCursor: requestedCursor,
    nextCursor: page.nextCursor,
    hasMore: page.hasMore,
    items: absorbed.fresh,
  }
  let focus = [...absorbed.window.focus, slot]
  let behindCursor = window.behindCursor
  while (focus.length > FEED_FOCUS_PAGE_LIMIT) {
    const evicted = focus[0]!
    behindCursor = evicted.requestCursor
    focus = focus.slice(1)
  }
  return {
    window: {
      ...absorbed.window,
      focus,
      behindCursor,
      stalled: false,
    },
    stalled: false,
    ignored: false,
  }
}

export function prependBehindPage<TItem>(
  window: FeedReadingWindow<TItem>,
  page: FeedContinuationPage & { items: readonly TItem[] },
  itemId: (item: TItem) => string,
): { window: FeedReadingWindow<TItem>; stalled: boolean; ignored: boolean } {
  if (!window.behindCursor) {
    return { window, stalled: false, ignored: true }
  }
  const requestedCursor = window.behindCursor
  if (continuationPageStalled(requestedCursor, page)) {
    return {
      window: { ...window, stalled: true },
      stalled: true,
      ignored: false,
    }
  }
  const successor = window.focus[0]
  if (successor && page.nextCursor !== successor.requestCursor) {
    return {
      window: { ...window, stalled: true },
      stalled: true,
      ignored: false,
    }
  }
  const absorbed = absorbIncomingItems(window, page.items, itemId)
  const slot: FeedPageSlot<TItem> = {
    requestCursor: requestedCursor,
    nextCursor: page.nextCursor,
    hasMore: page.hasMore,
    items: absorbed.fresh,
  }
  let focus = [slot, ...absorbed.window.focus]
  if (focus.length > FEED_FOCUS_PAGE_LIMIT) {
    focus = focus.slice(0, FEED_FOCUS_PAGE_LIMIT)
  }
  return {
    window: {
      ...absorbed.window,
      focus,
      behindCursor: null,
      stalled: false,
    },
    stalled: false,
    ignored: false,
  }
}

export function mapHydratedItems<TItem>(
  window: FeedReadingWindow<TItem>,
  mapItem: (item: TItem) => TItem,
): FeedReadingWindow<TItem> {
  return {
    ...window,
    pageOne: window.pageOne
      ? { ...window.pageOne, items: window.pageOne.items.map(mapItem) }
      : null,
    focus: window.focus.map((slot) => ({ ...slot, items: slot.items.map(mapItem) })),
  }
}

export function removeHydratedItem<TItem>(
  window: FeedReadingWindow<TItem>,
  id: string,
  itemId: (item: TItem) => string,
): { window: FeedReadingWindow<TItem>; removed: boolean; neighborId: string | null } {
  const visible = renderedItems(window, itemId)
  const index = visible.findIndex((item) => itemId(item) === id)
  const neighbor =
    index < 0
      ? null
      : visible[index + 1] ?? visible[index - 1] ?? null
  const drop = (items: TItem[]) => withoutId(items, id, itemId)
  const next: FeedReadingWindow<TItem> = {
    ...window,
    pageOne: window.pageOne
      ? { ...window.pageOne, items: drop(window.pageOne.items) }
      : null,
    focus: window.focus.map((slot) => ({ ...slot, items: drop(slot.items) })),
  }
  return {
    window: next,
    removed: index >= 0 || hydratedItems(window).some((item) => itemId(item) === id),
    neighborId: neighbor ? itemId(neighbor) : null,
  }
}

export function slotRequestCursorForItem<TItem>(
  window: FeedReadingWindow<TItem>,
  id: string,
  itemId: (item: TItem) => string,
): string | null | undefined {
  if (window.pageOne?.items.some((item) => itemId(item) === id)) {
    return null
  }
  const slot = window.focus.find((entry) => entry.items.some((item) => itemId(item) === id))
  return slot ? slot.requestCursor : undefined
}
