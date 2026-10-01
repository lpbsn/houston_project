export function visualKeyboardOverlap(input: {
  innerHeight: number
  visualHeight: number
  offsetTop: number
}): number {
  return Math.max(0, Math.round(input.innerHeight - input.visualHeight - input.offsetTop))
}
