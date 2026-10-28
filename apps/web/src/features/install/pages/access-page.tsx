import { useEffect, useState } from 'react'
import QRCode from 'qrcode'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { getAuthenticatedLandingPath, isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { AndroidAccess } from '@/features/install/components/android-access'
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
import { resolvePublicAppUrl } from '@/lib/runtime'
import { useLgViewport } from '@/lib/lg-viewport'

const IPHONE_FROM_ANOTHER_DEVICE =
  'Pour installer SPORE sur un iPhone depuis un autre appareil, choisissez Ordinateur et scannez le QR code. Il ouvre la page d’installation, puis cette fiche sur le téléphone.'

function destinationOf(search: string): 'android' | 'ordinateur' | null {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
  const value = params.get('destination')
  if (value === 'android' || value === 'ordinateur') {
    return value
  }
  return null
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
              onChooseAnother={() => navigate('/acces')}
            />
          ) : null}
          {destination === 'ordinateur' ? (
            <ComputerAccess
              spaceReady={copy.spaceReady}
              onOpenSpace={openSpace}
              onChooseAnother={() => navigate('/acces')}
            />
          ) : null}
          {destination === null ? (
            <ChoiceActions
              onAndroid={() => navigate('/acces?destination=android')}
              onComputer={() => navigate('/acces?destination=ordinateur')}
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
  onComputer,
  onWeb,
}: {
  onAndroid: () => void
  onComputer: () => void
  onWeb: () => void
}) {
  return (
    <div className="space-y-3">
      <Button asChild className="h-12 w-full rounded-2xl bg-[#004d3b] text-white hover:bg-[#003b2d]">
        <a href={iosAppStoreUrl} target="_blank" rel="noopener noreferrer">
          Télécharger sur l’App Store
        </a>
      </Button>
      <Button
        type="button"
        variant="outline"
        className="h-12 w-full rounded-2xl"
        onClick={onAndroid}
      >
        Préparer l’accès à Google Play
      </Button>
      <Button
        type="button"
        variant="outline"
        className="h-12 w-full rounded-2xl"
        onClick={onComputer}
      >
        Accéder à SPORE sur le Web
      </Button>
      <p className="text-sm leading-6 text-[#40564d]">
        Une fois l’application installée, connectez-vous avec votre compte SPORE.
      </p>
      <p className="text-sm leading-6 text-[#40564d]">{IPHONE_FROM_ANOTHER_DEVICE}</p>
      <Button type="button" variant="ghost" className="h-11 w-full rounded-2xl" onClick={onWeb}>
        Accéder directement au Web
      </Button>
    </div>
  )
}

function ComputerAccess({
  spaceReady,
  onOpenSpace,
  onChooseAnother,
}: {
  spaceReady: boolean
  onOpenSpace: () => void
  onChooseAnother: () => void
}) {
  const installerUrl = resolvePublicAppUrl('/installer')
  const [qrSvg, setQrSvg] = useState('')

  useEffect(() => {
    let cancelled = false
    void QRCode.toString(installerUrl, { type: 'svg', margin: 1, width: 180 }).then((svg) => {
      if (!cancelled) {
        setQrSvg(svg)
      }
    })
    return () => {
      cancelled = true
    }
  }, [installerUrl])

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-bold text-[#172e27]">
        {spaceReady ? 'Votre espace SPORE est prêt' : 'Votre établissement est encore en préparation'}
      </h2>
      <Button
        type="button"
        className="h-12 w-full rounded-2xl bg-[#004d3b] text-white hover:bg-[#003b2d]"
        onClick={onOpenSpace}
      >
        Ouvrir mon espace SPORE
      </Button>
      <div className="space-y-3 rounded-2xl bg-[#f7faf8] p-4">
        <p className="text-sm font-medium text-[#172e27]">Retrouvez SPORE sur votre téléphone</p>
        {qrSvg ? (
          <div
            className="mx-auto w-fit bg-white p-2"
            aria-label="QR code vers la page d’installation"
            dangerouslySetInnerHTML={{ __html: qrSvg }}
          />
        ) : null}
        <p className="text-sm leading-6 text-[#40564d]">
          Le QR code ouvre un choix iPhone ou Android, sans identifiant ni invitation.
        </p>
      </div>
      <Button type="button" variant="ghost" className="h-11 w-full rounded-2xl" onClick={onChooseAnother}>
        Choisir un autre appareil
      </Button>
    </div>
  )
}
