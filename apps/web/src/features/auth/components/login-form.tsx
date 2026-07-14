import { ArrowRight, Eye, EyeOff, LoaderCircle, LockKeyhole, Mail } from 'lucide-react'
import { useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

import { AuthApiError } from '@/features/auth/api'
import { useAuth } from '@/app/auth-provider'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

function getLoginErrorMessage(error: Error | null) {
  if (error instanceof AuthApiError && error.status === 401) {
    return 'Identifiants invalides.'
  }

  return error ? 'La connexion a échoué.' : null
}

export function LoginForm() {
  const { isLoggingIn, login, loginError } = useAuth()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  const errorMessage = useMemo(() => getLoginErrorMessage(loginError), [loginError])

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await login({
      identifier: identifier.trim(),
      password,
    })
  }

  return (
    <section className="w-full max-w-[346px] rounded-[22px] border border-[#E8E6DF] bg-white px-5 py-6 shadow-[0_20px_60px_-24px_rgba(15,23,42,0.12)] sm:max-w-[360px] sm:rounded-3xl">
      <form className="space-y-5" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <label className="text-sm font-semibold text-[#111827]" htmlFor="identifier">
            Email ou identifiant
          </label>
          <div className="relative">
            <Mail className="pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2 text-[#9CA3AF]" />
            <Input
              id="identifier"
              autoComplete="username"
              className="h-12 rounded-full border-[#E5E7EB] bg-white pl-11 text-base placeholder:text-[#9CA3AF] shadow-none md:text-base"
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              placeholder="vous@spore.app"
              required
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-semibold text-[#111827]" htmlFor="password">
            Mot de passe
          </label>
          <div className="relative">
            <LockKeyhole className="pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2 text-[#9CA3AF]" />
            <Input
              id="password"
              autoComplete="current-password"
              className="h-12 rounded-full border-[#E5E7EB] bg-white pr-11 pl-11 text-base placeholder:text-[#9CA3AF] shadow-none md:text-base"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
            <button
              type="button"
              className="absolute top-1/2 right-1 inline-flex size-10 -translate-y-1/2 items-center justify-center rounded-full text-[#9CA3AF] transition hover:text-[#6B7280]"
              aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
              onClick={() => setShowPassword((current) => !current)}
            >
              {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
            </button>
          </div>
        </div>

        {errorMessage ? (
          <div className="rounded-xl border border-rose-300/60 bg-rose-50 px-3 py-2 text-sm text-rose-900">
            {errorMessage}
          </div>
        ) : null}

        <Button
          className={cn(
            'h-12 w-full rounded-full text-[15px] font-semibold text-white',
            terrainBrandAction.bg,
            terrainBrandAction.hover,
          )}
          disabled={isLoggingIn}
          type="submit"
        >
          {isLoggingIn ? (
            <>
              <LoaderCircle className="size-4 animate-spin" />
              Connexion en cours…
            </>
          ) : (
            <>
              Se connecter
              <ArrowRight className="size-4" />
            </>
          )}
        </Button>
      </form>
    </section>
  )
}
