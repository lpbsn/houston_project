import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

type TerrainHubHeaderActionContextValue = {
  action: ReactNode | null
  setAction: (action: ReactNode | null) => void
}

const TerrainHubHeaderActionContext = createContext<TerrainHubHeaderActionContextValue | null>(
  null,
)

export function TerrainHubHeaderActionProvider({ children }: { children: ReactNode }) {
  const [action, setAction] = useState<ReactNode | null>(null)
  const value = useMemo(
    () => ({
      action,
      setAction,
    }),
    [action],
  )

  return (
    <TerrainHubHeaderActionContext.Provider value={value}>
      {children}
    </TerrainHubHeaderActionContext.Provider>
  )
}

export function useTerrainHubHeaderAction(): ReactNode | null {
  const context = useContext(TerrainHubHeaderActionContext)
  return context?.action ?? null
}

export function useSetTerrainHubHeaderAction(action: ReactNode | null): void {
  const context = useContext(TerrainHubHeaderActionContext)

  useEffect(() => {
    if (!context) {
      return
    }

    context.setAction(action)
    return () => {
      context.setAction(null)
    }
  }, [action, context])
}
