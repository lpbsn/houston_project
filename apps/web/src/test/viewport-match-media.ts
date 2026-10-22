export type TestPointer = 'fine' | 'coarse'

export function installTestMatchMedia(
  viewportMatches: boolean | ((query: string) => boolean),
  pointer: TestPointer = 'coarse',
): void {
  const resolveViewport = (query: string) =>
    typeof viewportMatches === 'function' ? viewportMatches(query) : viewportMatches

  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      matches: testMediaMatches(query, resolveViewport(query), pointer),
      media: query,
      onchange: null,
      addListener() {},
      removeListener() {},
      addEventListener() {},
      removeEventListener() {},
      dispatchEvent() {
        return false
      },
    }),
  })
}

export function testMediaMatches(
  query: string,
  viewportMatches: boolean,
  pointer: TestPointer = 'coarse',
): boolean {
  if (query.includes('pointer') || query.includes('hover')) {
    return pointer === 'fine'
  }
  return viewportMatches
}
