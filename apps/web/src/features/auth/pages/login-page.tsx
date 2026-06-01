import { LoaderCircle } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { LoginForm } from '@/features/auth/components/login-form'

export function LoginPage() {
  const { isReady } = useAuth()

  if (!isReady) {
    return (
      <div className="flex min-h-[22rem] items-center justify-center">
        <div className="flex items-center gap-3 rounded-xl border border-border/70 bg-background/85 px-4 py-3 text-sm">
          <LoaderCircle className="size-4 animate-spin text-primary" />
          Restoring your session...
        </div>
      </div>
    )
  }

  return <LoginForm />
}
