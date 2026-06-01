import { LoaderCircle, LockKeyhole, UserRound } from 'lucide-react'
import { useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

import { AuthApiError } from '@/features/auth/api'
import { useAuth } from '@/app/auth-provider'

function getLoginErrorMessage(error: Error | null) {
  if (error instanceof AuthApiError && error.status === 401) {
    return 'Invalid credentials.'
  }

  return error ? 'Sign-in failed.' : null
}

export function LoginForm() {
  const { isLoggingIn, login, loginError } = useAuth()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')

  const errorMessage = useMemo(() => getLoginErrorMessage(loginError), [loginError])

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await login({
      identifier: identifier.trim(),
      password,
    })
  }

  return (
    <Card className="border-white/60 bg-white/90 shadow-[0_24px_80px_-48px_rgba(15,59,72,0.45)] backdrop-blur">
      <CardHeader className="space-y-3">
        <CardTitle className="text-2xl">Sign in to Houston</CardTitle>
        <CardDescription>Enter your email or username and password to continue.</CardDescription>
      </CardHeader>

      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="identifier">
              Email or username
            </label>
            <div className="relative">
              <UserRound className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="identifier"
                autoComplete="username"
                className="pl-10"
                value={identifier}
                onChange={(event) => setIdentifier(event.target.value)}
                placeholder="you@example.com"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="password">
              Password
            </label>
            <div className="relative">
              <LockKeyhole className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="password"
                autoComplete="current-password"
                className="pl-10"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                required
              />
            </div>
          </div>

          {errorMessage ? (
            <div className="rounded-xl border border-rose-300/60 bg-rose-50 px-3 py-2 text-sm text-rose-900">
              {errorMessage}
            </div>
          ) : null}

          <Button className="w-full" disabled={isLoggingIn} size="lg" type="submit">
            {isLoggingIn ? (
              <>
                <LoaderCircle className="size-4 animate-spin" />
                Signing in...
              </>
            ) : (
              'Sign in'
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
