import { ArrowLeft, Info } from 'lucide-react'
import { useEffect, useState } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { getAuthenticatedLandingPath, isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { AccessWebLink } from '@/features/install/components/access-web-link'
import { AndroidAccess } from '@/features/install/components/android-access'
import { AndroidMark, AppleMark } from '@/features/install/components/store-marks'
import { InstallFrame } from '@/features/install/components/install-frame'
import {
  playRequestEstablishmentId,
  readAccessArrivalForDisplay,
  releaseDisplayedAccessArrival,
  resolveAccessCopy,
} from '@/features/install/arrival'
import {
  androidDistribution,
  androidPlayStoreUrl,
  iosAppStoreUrl,
  resolveAndroidChoice,
} from '@/features/install/distribution'
import { useLgViewport } from '@/lib/lg-viewport'

const installHintClassName =
  'flex items-start gap-2.5 rounded-lg bg-[#edf6f0] px-3.5 py-3 text-sm leading-5 text-[#172e27]'

function destinationOf(search: string): 'android' | null {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
  return params.get('destination') === 'android' ? 'android' : null
}

export function AccessPage() {
  const { navigate, search } = useAppRoute()
  const { bootstrap } = useAuth()
  const isDesktop = isDesktopWebLanding(useLgViewport())
  const [arrival] = useState(() => readAccessArrivalForDisplay())
  useEffect(() => {
    releaseDisplayedAccessArrival()
  }, [])

  const copy = resolveAccessCopy(bootstrap, arrival)
  const destination = destinationOf(search)
  const androidChoice = resolveAndroidChoice(androidDistribution, androidPlayStoreUrl)

  function openSpace() {
    const path = getAuthenticatedLandingPath(bootstrap, { isDesktop })
    if (path) {
      navigate(path)
    }
  }

  return (
    <InstallFrame>
      <Card className="rounded-[1.75rem] border-[#dce8e2] bg-white text-[#172e27] shadow-xl">
        <CardHeader className="gap-3">
          {destination === 'android' ? (
            <button
              type="button"
              aria-label="Retour"
              className="-ml-2 inline-flex size-8 items-center justify-center rounded-full text-[#6b8076] hover:bg-[#edf6f0] hover:text-[#172e27]"
              onClick={() => navigate('/acces')}
            >
              <ArrowLeft aria-hidden="true" className="size-4" />
            </button>
          ) : null}
          <CardTitle className="text-2xl font-bold">Bienvenue sur SPORE</CardTitle>
          {copy.lines.map((line) => (
            <p key={line} className="text-sm leading-6 text-[#40564d]">
              {line}
            </p>
          ))}
          {destination === null ? (
            <p className="text-base font-medium text-[#172e27]">{copy.question}</p>
          ) : null}
        </CardHeader>
        <CardContent className="space-y-4">
          {destination === 'android' ? (
            <AndroidAccess
              choice={androidChoice}
              establishmentId={playRequestEstablishmentId(bootstrap, arrival)}
              onContinueWeb={openSpace}
            />
          ) : null}
          {destination === null ? (
            <ChoiceActions
              onAndroid={() => navigate('/acces?destination=android')}
              onWeb={openSpace}
            />
          ) : null}
        </CardContent>
      </Card>
    </InstallFrame>
  )
}

function ChoiceActions({
  onAndroid,
  onWeb,
}: {
  onAndroid: () => void
  onWeb: () => void
}) {
  return (
    <div className="space-y-4">
      <Button asChild className="h-12 w-full gap-2 rounded-2xl bg-[#004d3b] text-white hover:bg-[#003b2d]">
        <a href={iosAppStoreUrl} target="_blank" rel="noopener noreferrer">
          <AppleMark />
          Télécharger sur iPhone
        </a>
      </Button>
      <Button
        type="button"
        variant="outline"
        className="h-12 w-full gap-2 rounded-2xl"
        onClick={onAndroid}
      >
        <AndroidMark />
        Télécharger sur Android
      </Button>
      <p className="text-sm leading-6 text-[#40564d]">
        Une fois l’application installée, connectez-vous avec votre compte SPORE.
      </p>
      <p className={installHintClassName}>
        <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <span>
          Vous pourrez retrouver cette page à tout moment dans SPORE, depuis{' '}
          <strong className="font-bold">Général → Installer SPORE</strong>.
        </span>
      </p>
      <AccessWebLink onClick={onWeb} />
    </div>
  )
}
