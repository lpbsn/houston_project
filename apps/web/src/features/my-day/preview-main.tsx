import './preview-api'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import type { AppRoute } from '@/app/app-routes'
import { getTerrainContentKey, getTerrainRouteConfig } from '@/app/terrain-routes'
import { TerrainShell } from '@/components/layout/terrain-shell'
import { TerrainTopbar } from '@/components/layout/terrain-topbar'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import type { BootstrapResponse } from '@/features/auth/types'
import { NotificationCenter } from '@/features/notifications/components/notification-center'
import { useLgViewport } from '@/lib/lg-viewport'
import '@/styles/globals.css'

import { MyDayPage } from './my-day-page'

const ESTABLISHMENT_ID = '11111111-1111-4111-8111-111111111111'

const membership: BootstrapResponse['memberships'][number] = {
  id: '44444444-4444-4444-8444-444444444444',
  establishment_id: ESTABLISHMENT_ID,
  establishment_name: 'Les Terrasses',
  organization_id: '22222222-2222-4222-8222-222222222222',
  organization_name: 'Séjours',
  role: 'staff',
  status: 'active',
  chat_available: true,
  scopes: [],
  scope_summary: { business_unit_count: 2 },
}

const bootstrap: BootstrapResponse = {
  authenticated: true,
  user: {
    id: '33333333-3333-4333-8333-333333333333',
    username: 'camille.bernard',
    email: 'camille.bernard@example.com',
    identity_type: 'email',
    first_name: 'Camille',
    last_name: 'Bernard',
    pending_email: null,
    pending_email_expires_at: null,
    terms_version: '1',
    terms_accepted_at: '2026-01-01T00:00:00Z',
    current_terms_version: '1',
    needs_terms_acceptance: false,
    ai_consent_version: null,
    ai_processing_consented_at: null,
    current_ai_consent_version: '1',
    needs_ai_consent: false,
    ai_consent_status: 'granted',
  },
  memberships: [membership],
  active_membership: membership,
  pending_onboarding_memberships: [],
  permission_hints: {
    chat_available: true,
    can_create_action_plan: false,
    can_create_catalog_action_plan: false,
    can_view_action_plan_catalog: false,
    can_invite: false,
    can_manage_runtime_config: false,
    can_view_team: false,
    can_manage_organization: false,
    platform_operator_active: false,
  },
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, refetchOnWindowFocus: false },
  },
})

function noopNavigate() {}

function Preview() {
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const route: AppRoute = isDesktopWeb
    ? {
        kind: 'scoped-terrain',
        scope: { type: 'establishment', establishmentId: ESTABLISHMENT_ID },
        page: 'my-day',
      }
    : { kind: 'static', path: '/my-day' }
  const config = getTerrainRouteConfig(route)

  return (
    <TerrainShell
      contentKey={getTerrainContentKey(route)}
      topbar={
        <TerrainTopbar
          variant={config.topbarVariant}
          pageTitle={config.pageTitle}
          showBottomBorder={false}
          trailing={
            <NotificationCenter establishmentId={ESTABLISHMENT_ID} onNavigate={noopNavigate} />
          }
        />
      }
      showBottomNav={config.showBottomNav}
      bootstrap={bootstrap}
      route={route}
      mainScroll={config.mainScroll}
      navigate={noopNavigate}
    >
      <MyDayPage establishmentId={ESTABLISHMENT_ID} onNavigate={noopNavigate} />
    </TerrainShell>
  )
}

const root = document.getElementById('root')
if (root) {
  createRoot(root).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <Preview />
      </QueryClientProvider>
    </StrictMode>,
  )
}
