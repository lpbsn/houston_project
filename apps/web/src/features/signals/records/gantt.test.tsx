// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { getAppRuntime } from '@/lib/runtime'
import { listRecords, recordOptions, type FieldRecord } from './api'
import { RecordFeedPage } from './feed'
import { RecordGantt } from './gantt'
import { dateInZone, ganttSpan, ganttWindow, shiftGanttMonth } from './gantt-layout'

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({ memberships: [{ establishment_id: 'site', role: 'director' }] }),
}))
vi.mock('@/lib/lg-viewport', () => ({ useLgViewport: () => true }))
vi.mock('@/lib/runtime', async (original) => ({
  ...(await original<typeof import('@/lib/runtime')>()),
  getAppRuntime: vi.fn(() => 'web'),
}))
vi.mock('./api', async (original) => ({
  ...(await original<typeof import('./api')>()),
  listRecords: vi.fn(),
  recordOptions: vi.fn(),
}))
beforeEach(() => {
  vi.mocked(getAppRuntime).mockReturnValue('web')
  vi.mocked(recordOptions).mockResolvedValue({ poles: [], members: [] })
  vi.mocked(listRecords).mockResolvedValue({ items: [], next_offset: null, timezone: 'Europe/Paris' })
})
afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function record(start: string, end: string, due = end): FieldRecord {
  return {
    id: 'fiche', title: 'Renforcer le service du déjeuner', summary: '',
    kind: 'observation', stage: 'doing', closure_reason: '', is_pinned: false,
    pole: 'Restaurant', pole_id: null, color_index: 0,
    owner: { id: 'owner', name: 'Nora Garcia' }, waiting_for: null,
    due_on: due, blocked_reason: '', created_at: `${start}T12:00:00Z`,
    updated_at: `${end}T12:00:00Z`, observation_count: 2,
    calendar: { start, end, due, overdue: due < end },
    can_manage: true, can_progress: true, can_use_brain: true,
  }
}

describe('dates du Gantt', () => {
  it('respecte les mois calendaires, les années bissextiles et la limite serveur', () => {
    expect(ganttWindow('2028-02', 'month').days).toHaveLength(29)
    expect(ganttWindow('2026-03', 'month').days).toHaveLength(31)
    expect(ganttWindow('2026-11', 'quarter')).toMatchObject({ from: '2026-11-01', to: '2027-01-31' })
    for (let month = 1; month <= 12; month++) {
      expect(ganttWindow(`2026-${String(month).padStart(2, '0')}`, 'quarter').days.length).toBeLessThanOrEqual(92)
    }
    expect(shiftGanttMonth('2026-11', 3)).toBe('2027-02')
    expect(shiftGanttMonth('2026-01', -1)).toBe('2025-12')
  })
  it('repère aujourd’hui dans le fuseau du site', () => {
    const instant = new Date('2026-10-31T23:30:00Z')
    expect(dateInZone('Europe/Paris', instant)).toBe('2026-11-01')
    expect(dateInZone('America/New_York', instant)).toBe('2026-10-31')
  })
  it('conserve une barre continue sur les frontières du mois et borne le retard visible', () => {
    const spanning = record('2026-10-20', '2026-12-04', '2026-11-12')
    expect(ganttSpan(spanning, '2026-11-01', '2026-11-30')).toEqual({
      start: 0, end: 29, due: 11, lateStart: 12,
      continuesBefore: true, continuesAfter: true,
    })
    const alreadyLate = record('2026-10-20', '2026-11-04', '2026-10-30')
    expect(ganttSpan(alreadyLate, '2026-11-01', '2026-11-30')).toMatchObject({
      start: 0, end: 3, due: null, lateStart: 0,
    })
  })
  it('garde la clôture effective et l’échéance distinctes, sans prolonger une fiche close', () => {
    const closed = { ...record('2026-11-02', '2026-11-04', '2026-11-20'), stage: 'closed' as const }
    expect(ganttSpan(closed, '2026-11-01', '2026-11-30')).toMatchObject({
      start: 1, end: 3, due: 19, lateStart: null,
    })
    const closedLate = { ...record('2026-11-02', '2026-11-10', '2026-11-05'), stage: 'closed' as const }
    closedLate.calendar!.overdue = false
    expect(ganttSpan(closedLate, '2026-11-01', '2026-11-30')?.lateStart).toBeNull()
  })
  it('exclut les fiches sans échéance et celles hors de la fenêtre', () => {
    const old = record('2026-10-02', '2026-10-20')
    expect(ganttSpan(old, '2026-11-01', '2026-11-30')).toBeNull()
    expect(ganttSpan({ ...old, due_on: null, calendar: null }, '2026-10-01', '2026-10-31')).toBeNull()
  })
})

describe('présentation du Gantt', () => {
  it('ouvre la même fiche par le titre ou la barre et affiche responsable, blocage et échéance', () => {
    const onOpen = vi.fn()
    render(<RecordGantt records={[{ ...record('2026-11-01', '2026-11-04', '2026-11-02'), blocked_reason: 'Attente du fournisseur' }]} month="2026-11" zoom="month" timeZone="Europe/Paris" onOpen={onOpen} />)
    expect(screen.getByText('Nora Garcia')).toBeTruthy()
    expect(screen.getByText('Bloqué').title).toBe('Attente du fournisseur')
    expect(screen.getByText(/En retard · Éch\./)).toBeTruthy()
    expect(screen.getByRole('img', { name: /Échéance de Renforcer/ })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Renforcer le service du déjeuner' }))
    fireEvent.click(screen.getByRole('button', { name: /Ouvrir Renforcer/ }))
    expect(onOpen.mock.calls).toEqual([['fiche'], ['fiche']])
  })
  it('explique une période vide sans afficher les fiches non datées', () => {
    render(<RecordGantt records={[{ ...record('2026-11-01', '2026-11-04'), due_on: null, calendar: null }]} month="2026-11" zoom="quarter" timeZone="UTC" onOpen={vi.fn()} />)
    expect(screen.getByText('Aucune fiche avec échéance sur cette période.')).toBeTruthy()
    expect(screen.queryByRole('button')).toBeNull()
  })
})

function feed() {
  const onNavigate = vi.fn()
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  render(<QueryClientProvider client={client}><RecordFeedPage establishmentId="site" onNavigate={onNavigate} /></QueryClientProvider>)
  return onNavigate
}

describe('Gantt dans les fiches terrain', () => {
  it('réutilise filtres, pagination et navigation, puis charge trois mois sans dépasser la limite', async () => {
    vi.mocked(recordOptions).mockResolvedValue({ poles: [{ id: 'restaurant', name: 'Restaurant' }], members: [] })
    vi.mocked(listRecords).mockImplementation(async (_site, filters, offset) => ({
      items: filters.from && !offset ? [record('2026-11-01', '2026-11-12')] : [],
      next_offset: filters.from && !offset ? 30 : null,
      timezone: 'Europe/Paris',
    }))
    const navigate = feed()
    await screen.findByRole('option', { name: 'Restaurant' })
    fireEvent.change(screen.getByLabelText('Filtrer par pôle'), { target: { value: 'restaurant' } })
    fireEvent.change(screen.getByLabelText('Filtrer par étape'), { target: { value: 'doing' } })
    fireEvent.change(screen.getByLabelText('Rechercher une fiche'), { target: { value: 'déjeuner' } })
    fireEvent.click(screen.getByLabelText('Mes fiches et mes observations'))
    fireEvent.click(screen.getByRole('button', { name: 'Gantt' }))
    fireEvent.change(screen.getByLabelText('Mois'), { target: { value: '2026-11' } })
    const filter = { mine: true, q: 'déjeuner', pole: 'restaurant', stage: 'doing', from: '2026-11-01', to: '2026-11-30' }
    await waitFor(() => expect(listRecords).toHaveBeenCalledWith('site', filter, 0))
    expect(await screen.findByText('Vue partielle : d’autres fiches restent à charger.')).toBeTruthy()
    fireEvent.click(await screen.findByRole('button', { name: /Ouvrir Renforcer/ }))
    expect(navigate).toHaveBeenCalledWith('/e/site/signals/fiche')
    fireEvent.click(screen.getByRole('button', { name: 'Afficher davantage de fiches dans le Gantt' }))
    await waitFor(() => expect(listRecords).toHaveBeenCalledWith('site', filter, 30))
    await waitFor(() => expect(screen.queryByText('Vue partielle : d’autres fiches restent à charger.')).toBeNull())
    fireEvent.click(screen.getByRole('button', { name: '3 mois' }))
    await waitFor(() => expect(listRecords).toHaveBeenCalledWith('site', { ...filter, to: '2027-01-31' }, 0))
    fireEvent.click(screen.getByRole('button', { name: 'Période suivante' }))
    await waitFor(() => expect(listRecords).toHaveBeenCalledWith('site', { ...filter, from: '2027-02-01', to: '2027-04-30' }, 0))
    fireEvent.click(screen.getByRole('button', { name: 'Période précédente' }))
    expect((screen.getByLabelText('Mois') as HTMLInputElement).value).toBe('2026-11')
    fireEvent.click(screen.getByRole('button', { name: 'Calendrier' }))
    await waitFor(() => expect(listRecords).toHaveBeenCalledWith('site', { ...filter, from: '2026-10-26', to: '2026-12-06' }, 0))
  })
  it('ne propose pas le Gantt sur le runtime natif, même avec un grand écran', async () => {
    vi.mocked(getAppRuntime).mockReturnValue('native')
    feed()
    await screen.findByText('Aucune fiche ici.')
    expect(screen.queryByRole('button', { name: 'Gantt' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Kanban' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Calendrier' })).toBeTruthy()
  })
  it('conserve le message d’échec serveur et ne présente pas un Gantt vide comme chargé', async () => {
    vi.mocked(listRecords).mockRejectedValue(new Error('Impossible de charger les fiches.'))
    feed()
    fireEvent.click(screen.getByRole('button', { name: 'Gantt' }))
    expect(await screen.findByText('Impossible de charger les fiches.')).toBeTruthy()
    expect(screen.queryByText('Aucune fiche avec échéance sur cette période.')).toBeNull()
  })
})
