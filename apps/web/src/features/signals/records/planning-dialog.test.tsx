// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { planRecord, type FieldRecord, type PlanningResponse } from './api'
import { PlanningDialog } from './planning-dialog'
import { RecordGantt } from './gantt'
import { ganttSpan } from './gantt-layout'

vi.mock('./api', async (original) => ({
  ...(await original<typeof import('./api')>()),
  planRecord: vi.fn(),
}))
afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})
const record = {
  id: 'r',
  title: 'Installation',
  stage: 'doing',
  pole: 'Jardin',
  kind: 'project',
  owner: null,
  can_manage: true,
  updated_at: '2026-11-04T10:00:00Z',
  due_on: '2026-11-12',
  calendar: {
    start: '2026-11-04',
    end: '2026-11-12',
    due: '2026-11-12',
    overdue: false,
  },
  planned_start_on: '2026-11-10',
} as FieldRecord
const preview: PlanningResponse = {
  applied: false,
  changes: [
    {
      id: 'r',
      title: 'Installation',
      before_start: '2026-11-10',
      before_due: '2026-11-12',
      start_on: '2026-11-11',
      due_on: '2026-11-13',
    },
  ],
  versions: [{ id: 'r', updated_at: record.updated_at }],
}
function dialog() {
  const close = vi.fn()
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { mutations: { retry: false } } })
      }
    >
      <PlanningDialog
        site="site"
        draft={{ record, start: '2026-11-11', due: '2026-11-13' }}
        onClose={close}
      />
    </QueryClientProvider>,
  )
  return close
}
it('montre les changements puis confirme avec les versions, sans écriture initiale', async () => {
  vi.mocked(planRecord)
    .mockResolvedValueOnce(preview)
    .mockResolvedValueOnce({ ...preview, applied: true })
  const close = dialog()
  expect(planRecord).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Vérifier l’impact' }))
  await screen.findByText('1 fiche à modifier')
  expect(planRecord).toHaveBeenLastCalledWith('site', 'r', {
    expected_updated_at: record.updated_at,
    start_on: '2026-11-11',
    due_on: '2026-11-13',
    apply: false,
  })
  expect(close).not.toHaveBeenCalled()
  fireEvent.click(
    screen.getByRole('button', { name: 'Confirmer les modifications' }),
  )
  await waitFor(() => expect(close).toHaveBeenCalledOnce())
  expect(planRecord).toHaveBeenLastCalledWith(
    'site',
    'r',
    expect.objectContaining({
      apply: true,
      expected_versions: preview.versions,
    }),
  )
})
it('annule une prévisualisation si les dates changent et ne ferme pas après un échec', async () => {
  vi.mocked(planRecord)
    .mockResolvedValueOnce(preview)
    .mockRejectedValueOnce(new Error('Une fiche a changé.'))
  const close = dialog()
  fireEvent.click(screen.getByRole('button', { name: 'Vérifier l’impact' }))
  await screen.findByRole('button', { name: 'Confirmer les modifications' })
  fireEvent.change(screen.getByLabelText('Échéance'), {
    target: { value: '2026-11-14' },
  })
  expect(
    screen.queryByRole('button', { name: 'Confirmer les modifications' }),
  ).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Vérifier l’impact' }))
  await screen.findByText('Une fiche a changé.')
  expect(close).not.toHaveBeenCalled()
})
it('planifie au clavier et ne modifie pas le calendrier historique', () => {
  const plan = vi.fn()
  render(
    <RecordGantt
      records={[record]}
      month="2026-11"
      zoom="month"
      timeZone="UTC"
      onOpen={vi.fn()}
      onPlan={plan}
    />,
  )
  fireEvent.click(
    screen.getByRole('button', { name: 'Planifier Installation' }),
  )
  expect(plan).toHaveBeenCalledWith({
    record,
    start: '2026-11-10',
    due: '2026-11-12',
  })
  expect(ganttSpan(record, '2026-11-01', '2026-11-30')?.start).toBe(9)
  expect(record.calendar?.start).toBe('2026-11-04')
})
it('un glisser propose le décalage sans ouvrir la fiche ni appeler le serveur', () => {
  const plan = vi.fn(),
    open = vi.fn()
  // jsdom has no PointerEvent; retain mouse coordinates for the pointer lifecycle.
  vi.stubGlobal('PointerEvent', MouseEvent)
  render(
    <RecordGantt
      records={[record]}
      month="2026-11"
      zoom="month"
      timeZone="UTC"
      onOpen={open}
      onPlan={plan}
    />,
  )
  const bar = screen.getByRole('button', { name: /Ouvrir Installation/ })
  bar.setPointerCapture = vi.fn()
  fireEvent.pointerDown(bar, { clientX: 100, button: 0, pointerId: 1 })
  fireEvent.pointerMove(bar, { clientX: 172, pointerId: 1 })
  fireEvent.pointerUp(bar, { clientX: 172, pointerId: 1 })
  fireEvent.click(bar)
  expect(plan).toHaveBeenCalledWith({
    record,
    start: '2026-11-12',
    due: '2026-11-14',
  })
  expect(planRecord).not.toHaveBeenCalled()
  expect(open).not.toHaveBeenCalled()
  vi.unstubAllGlobals()
})
it('ne propose aucune modification pour une fiche close', () => {
  render(
    <RecordGantt
      records={[{ ...record, stage: 'closed' }]}
      month="2026-11"
      zoom="month"
      timeZone="UTC"
      onOpen={vi.fn()}
      onPlan={vi.fn()}
    />,
  )
  expect(
    screen.queryByRole('button', { name: 'Planifier Installation' }),
  ).toBeNull()
})
