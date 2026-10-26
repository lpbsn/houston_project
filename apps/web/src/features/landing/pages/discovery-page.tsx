import { useState } from 'react'

import sporeMark from '@/features/landing/assets/spore-mark.png'

export const PUBLIC_DISCOVERY_VIDEO_URL =
  'https://media.spore-os.com/spore-discovery-v1.mp4' as const

export const DISCOVERY_POSTER_PATH = '/discover/poster-v1.jpg' as const
export const DISCOVERY_CAPTIONS_PATH = '/discover/captions-v1.vtt' as const

export const DISCOVERY_TITLE = 'Découvrez Spore' as const
export const DISCOVERY_SUMMARY =
  'En 1 min 33, découvrez comment Spore aide votre équipe à partager les observations du terrain, à collaborer et à suivre les actions qui en découlent.' as const
export const DISCOVERY_UNAVAILABLE_MESSAGE =
  'La vidéo est momentanément indisponible.' as const

export function DiscoveryPage() {
  const [unavailable, setUnavailable] = useState(false)

  return (
    <div data-testid="discovery-page" className="min-h-dvh bg-white text-spore-forest">
      <main className="mx-auto max-w-3xl px-5 py-10 sm:px-8 sm:py-16">
        <p className="flex items-center gap-2.5 text-[2rem] font-bold tracking-[-0.06em] text-[#043f30]">
          <img src={sporeMark} alt="Logo Spore" width={64} height={64} className="h-16 w-16" />
          <span>spore</span>
        </p>
        <h1 className="mt-8 text-[clamp(1.75rem,4vw,2.25rem)] font-semibold tracking-tight">
          {DISCOVERY_TITLE}
        </h1>
        <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-spore-moss">
          {DISCOVERY_SUMMARY}
        </p>
        <div className="mt-8">
          <video
            className="aspect-video w-full rounded-2xl bg-[#edf5f0]"
            controls
            playsInline
            preload="none"
            poster={DISCOVERY_POSTER_PATH}
            aria-label="Présentation de Spore"
            onError={() => setUnavailable(true)}
          >
            <source src={PUBLIC_DISCOVERY_VIDEO_URL} type="video/mp4" />
            <track
              kind="captions"
              src={DISCOVERY_CAPTIONS_PATH}
              srcLang="fr"
              label="Français"
              default
            />
          </video>
          {unavailable ? (
            <p role="status" className="mt-3 text-sm leading-relaxed text-spore-moss">
              {DISCOVERY_UNAVAILABLE_MESSAGE}
            </p>
          ) : null}
        </div>
      </main>
    </div>
  )
}
