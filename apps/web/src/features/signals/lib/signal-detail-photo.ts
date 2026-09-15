/** Upper bound on signal-detail photo tiles rendered from `media_items`. */
export const MAX_VISIBLE_PHOTO_TILES = 6

export function resolveVisiblePhotoTileCount(mediaCount: number): number {
  return Math.min(Math.max(mediaCount, 0), MAX_VISIBLE_PHOTO_TILES)
}
