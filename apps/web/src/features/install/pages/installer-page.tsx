import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { InstallFrame } from '@/features/install/components/install-frame'
import { iosAppStoreUrl } from '@/features/install/distribution'
import { buildLoginRedirectHref } from '@/lib/app-open-target'

export function InstallerPage() {
  const { navigate } = useAppRoute()
  const { isAuthenticated } = useAuth()

  function openAndroid() {
    const href = '/acces?destination=android'
    navigate(isAuthenticated ? href : buildLoginRedirectHref({ href }))
  }

  return (
    <InstallFrame>
      <Card className="rounded-[1.75rem] border-[#dce8e2] bg-white text-[#172e27] shadow-xl">
        <CardHeader className="gap-2">
          <CardTitle className="text-2xl font-bold">Où souhaitez-vous installer SPORE ?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button asChild className="h-12 w-full rounded-2xl bg-[#004d3b] text-white hover:bg-[#003b2d]">
            <a href={iosAppStoreUrl} target="_blank" rel="noopener noreferrer">
              Télécharger sur l’App Store
            </a>
          </Button>
          <Button type="button" variant="outline" className="h-12 w-full rounded-2xl" onClick={openAndroid}>
            Télécharger sur Android
          </Button>
          <p className="text-sm leading-6 text-[#40564d]">
            Une fois l’application installée, connectez-vous avec votre compte SPORE.
          </p>
        </CardContent>
      </Card>
    </InstallFrame>
  )
}
