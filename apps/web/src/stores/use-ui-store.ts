import { create } from 'zustand'

type VisualMode = 'focus' | 'calm'

type UiStore = {
  sidebarOpen: boolean
  visualMode: VisualMode
  toggleSidebar: () => void
  cycleVisualMode: () => void
}

export const useUiStore = create<UiStore>((set) => ({
  sidebarOpen: true,
  visualMode: 'focus',
  toggleSidebar: () => {
    set((state) => ({ sidebarOpen: !state.sidebarOpen }))
  },
  cycleVisualMode: () => {
    set((state) => ({
      visualMode: state.visualMode === 'focus' ? 'calm' : 'focus',
    }))
  },
}))
