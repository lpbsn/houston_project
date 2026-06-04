/** Max tiles shown when API only exposes media_count (no signed URLs yet). */
export const MAX_VISIBLE_PHOTO_TILES = 6

export function resolveVisiblePhotoTileCount(mediaCount: number): number {
  return Math.min(Math.max(mediaCount, 0), MAX_VISIBLE_PHOTO_TILES)
}
