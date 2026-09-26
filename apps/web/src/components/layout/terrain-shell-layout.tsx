import { createContext, useContext, type ReactNode } from 'react'

type TerrainShellLayoutValue = {
  showBottomNav: boolean
}

const TerrainShellLayoutContext = createContext<TerrainShellLayoutValue>({
  showBottomNav: false,
})

export function TerrainShellLayoutProvider({
  showBottomNav,
  children,
}: {
  showBottomNav: boolean
  children: ReactNode
}) {
  return (
    <TerrainShellLayoutContext.Provider value={{ showBottomNav }}>
      {children}
    </TerrainShellLayoutContext.Provider>
  )
}

export function useTerrainShellLayout(): TerrainShellLayoutValue {
  return useContext(TerrainShellLayoutContext)
}
