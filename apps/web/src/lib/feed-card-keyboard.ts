import type { KeyboardEvent } from 'react'

export function feedCardKeyDown(
  event: KeyboardEvent<HTMLElement>,
  onSelect: (id: string) => void,
  id: string,
): void {
  if (event.target !== event.currentTarget) {
    return
  }

  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    onSelect(id)
  }
}
