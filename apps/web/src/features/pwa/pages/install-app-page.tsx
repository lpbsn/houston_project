import { useState, type ComponentType } from 'react'
import { Sun } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { HoustonBadge, TerrainCard } from '@/components/ui/terrain'
import {
  INSTALL_APP_FOOTER_NOTE,
  INSTALL_APP_GUIDES,
  INSTALL_APP_HERO_ICON,
  INSTALL_PLATFORM_TABS,
  type InstallBrowserGuide,
  type InstallPlatform,
  type InstallStep,
} from '@/features/pwa/content/install-app-guides'
import { terrain, terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type InstallAppPageProps = {
  onNavigate: (pathname: string, options?: { replace?: boolean }) => void
}

type InstallPlatformTabsProps = {
  activePlatform: InstallPlatform
  onChange: (platform: InstallPlatform) => void
}

function InstallPlatformTabs({ activePlatform, onChange }: InstallPlatformTabsProps) {
  return (
    <div
      role="tablist"
      aria-label="Plateforme d'installation"
      className="grid w-full grid-cols-2 gap-1 rounded-xl bg-[#F5F4F0] p-1"
    >
      {INSTALL_PLATFORM_TABS.map(({ value, label, icon: Icon }) => {
        const isActive = activePlatform === value

        return (
          <button
            key={value}
            type="button"
            role="tab"
            id={`install-app-tab-${value}`}
            aria-selected={isActive}
            aria-controls={`install-app-panel-${value}`}
            className={cn(
              'flex min-h-11 items-center justify-center gap-1.5 rounded-lg px-3 text-[13px] font-semibold transition',
              isActive
                ? cn(terrainBrandAction.bg, 'text-white shadow-sm')
                : 'bg-transparent text-[#888]',
            )}
            onClick={() => onChange(value)}
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden />
            {label}
          </button>
        )
      })}
    </div>
  )
}

type InstallStepRowProps = {
  step: InstallStep
  showNumbers: boolean
}

function InstallStepRow({ step, showNumbers }: InstallStepRowProps) {
  const StepIcon = step.icon

  return (
    <li className="flex items-center gap-2.5 rounded-full border border-[#E8E6DF] bg-[#F5F4F0] px-3 py-2.5">
      {showNumbers && step.number != null ? (
        <span
          className={cn(
            'flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white',
            terrainBrandAction.bg,
          )}
          aria-hidden
        >
          {step.number}
        </span>
      ) : (
        <span
          className="flex h-6 w-6 shrink-0 items-center justify-center text-[#1a1a1a]"
          aria-hidden
        >
          <StepIcon className="h-4 w-4" />
        </span>
      )}
      <span className="min-w-0 flex-1 text-sm leading-snug text-[#1a1a1a]">{step.text}</span>
      {showNumbers && step.number != null ? (
        <span className="flex h-6 w-6 shrink-0 items-center justify-center text-[#1a1a1a]" aria-hidden>
          <StepIcon className="h-4 w-4" />
        </span>
      ) : null}
    </li>
  )
}

type InstallBrowserSectionProps = {
  guide: InstallBrowserGuide
  showStepNumbers: boolean
}

function InstallBrowserSection({ guide, showStepNumbers }: InstallBrowserSectionProps) {
  const SectionIcon = guide.icon

  return (
    <section className="rounded-[14px] border border-[#E8E6DF] bg-white p-3">
      <div className="mb-2.5 flex items-center gap-2">
        {SectionIcon ? (
          <span
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#F5F4F0] text-[#1a1a1a]"
            aria-hidden
          >
            <SectionIcon className="h-4 w-4" />
          </span>
        ) : null}
        <h3 className="text-sm font-semibold text-[#1a1a1a]">{guide.title}</h3>
      </div>
      <ol className="space-y-2">
        {guide.steps.map((step) => (
          <InstallStepRow key={step.id} step={step} showNumbers={showStepNumbers} />
        ))}
      </ol>
      {guide.footnote ? (
        <p className={cn('mt-2.5 px-1 text-xs leading-relaxed', terrain.muted)}>{guide.footnote}</p>
      ) : null}
    </section>
  )
}

type InstallPlatformPanelProps = {
  platform: InstallPlatform
}

function InstallPlatformPanel({ platform }: InstallPlatformPanelProps) {
  const guides = INSTALL_APP_GUIDES[platform]

  return (
    <div
      role="tabpanel"
      id={`install-app-panel-${platform}`}
      aria-labelledby={`install-app-tab-${platform}`}
      className="space-y-3"
    >
      {guides.map((guide) => (
        <InstallBrowserSection
          key={guide.id}
          guide={guide}
          showStepNumbers={guide.id === 'safari' || guide.id === 'chrome-android'}
        />
      ))}
    </div>
  )
}

export function InstallAppPage({ onNavigate }: InstallAppPageProps) {
  const [activePlatform, setActivePlatform] = useState<InstallPlatform>('ios')
  const HeroIcon = INSTALL_APP_HERO_ICON as ComponentType<{ className?: string }>

  return (
    <div className="flex min-h-0 flex-1 flex-col px-3">
      <header className="space-y-3 border-b border-[#E8E6DF] pb-4 pt-[max(0.75rem,env(safe-area-inset-top))]">
        <HoustonBadge variant="gray" className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] tracking-[0.12em]">
          <Sun className="h-3 w-3" aria-hidden />
          APPLICATION
        </HoustonBadge>
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-[#1a1a1a]">Installer Spore</h1>
          <p className={cn('text-sm', terrain.muted)}>
            Ajoutez Spore à votre écran d&apos;accueil pour un accès rapide.
          </p>
        </div>
      </header>

      <TerrainCard className="relative mt-4 overflow-hidden p-4">
        <div
          className="pointer-events-none absolute inset-x-0 top-0 h-16 bg-gradient-to-b from-[#E8F0FF]/80 to-transparent"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-[#F3EFFF]/60 to-transparent"
          aria-hidden
        />

        <div className="relative space-y-4">
          <div className="flex flex-col items-center text-center">
            <span
              className={cn(
                'flex h-14 w-14 items-center justify-center rounded-2xl text-white',
                terrainBrandAction.bg,
              )}
              aria-hidden
            >
              <HeroIcon className="h-7 w-7" />
            </span>
            <h2 className="mt-3 text-base font-semibold text-[#1a1a1a]">
              Installez Spore sur votre téléphone
            </h2>
            <p className={cn('mt-1 max-w-sm text-sm leading-relaxed', terrain.muted)}>
              Ajoutez Spore à votre écran d&apos;accueil pour y accéder comme à une application.
              L&apos;installation ne prend que quelques secondes.
            </p>
          </div>

          <InstallPlatformTabs activePlatform={activePlatform} onChange={setActivePlatform} />

          <InstallPlatformPanel platform={activePlatform} />

          <p className={cn('text-center text-xs leading-relaxed', terrain.muted)}>
            {INSTALL_APP_FOOTER_NOTE}
          </p>
        </div>
      </TerrainCard>

      <div className="mt-5 flex justify-center pb-[max(1.5rem,env(safe-area-inset-bottom))]">
        <Button
          type="button"
          variant="outline"
          className="h-11 min-w-[12rem] rounded-full border-[#E8E6DF] bg-white px-6 text-sm font-medium text-[#1a1a1a] hover:bg-[#F5F4F0]"
          onClick={() => onNavigate('/general')}
        >
          Retour à l&apos;application
        </Button>
      </div>
    </div>
  )
}
