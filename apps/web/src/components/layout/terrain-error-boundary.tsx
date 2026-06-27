import { Component, type ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { TerrainErrorState } from '@/components/ui/terrain/terrain-error-state'

export const TERRAIN_UNEXPECTED_ERROR_MESSAGE = "Une erreur inattendue s'est produite."

type TerrainErrorBoundaryProps = {
  children: ReactNode
  resetKey: string
  navigate: (pathname: string, options?: { replace?: boolean }) => void
}

type TerrainErrorBoundaryState = {
  error: Error | null
}

type TerrainErrorBoundaryFallbackProps = {
  onRetry: () => void
  onHome: () => void
}

export function TerrainErrorBoundaryFallback({
  onRetry,
  onHome,
}: TerrainErrorBoundaryFallbackProps) {
  return (
    <div className="mx-3 mt-3 flex flex-col gap-3">
      <TerrainErrorState
        message={TERRAIN_UNEXPECTED_ERROR_MESSAGE}
        onRetry={onRetry}
      />
      <Button
        type="button"
        variant="outline"
        className="w-fit rounded-xl border-[#E8E6DF]"
        onClick={onHome}
      >
        Retour à l&apos;accueil
      </Button>
    </div>
  )
}

export class TerrainErrorBoundary extends Component<
  TerrainErrorBoundaryProps,
  TerrainErrorBoundaryState
> {
  state: TerrainErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): TerrainErrorBoundaryState {
    return { error }
  }

  componentDidUpdate(prevProps: TerrainErrorBoundaryProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null })
    }
  }

  private handleRetry = () => {
    this.setState({ error: null })
  }

  private handleHome = () => {
    this.setState({ error: null })
    this.props.navigate('/reporting', { replace: true })
  }

  render() {
    if (this.state.error) {
      return (
        <TerrainErrorBoundaryFallback
          onRetry={this.handleRetry}
          onHome={this.handleHome}
        />
      )
    }

    return this.props.children
  }
}
