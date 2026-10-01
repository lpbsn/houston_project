// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type { ActionPlanExecutionDetail } from '@/features/action-plans/types'

import { ActionPlanExecutionDetailDeadlineSection } from './action-plan-execution-detail-deadline-section'
import { ActionPlanExecutionDetailHeader } from './action-plan-execution-detail-header'
import { ActionPlanExecutionDetailMobileContext } from './action-plan-execution-detail-mobile-context'

function buildExecution(
  overrides: Partial<ActionPlanExecutionDetail> = {},
): ActionPlanExecutionDetail {
  return {
    id: 'exec-1',
    action_plan_id: 'plan-1',
    status: 'done',
    title: 'Plan nettoyage terrasse',
    description: '',
    requires_validation: true,
    pilot_business_unit: {
      id: 'bu-1',
      specific_name: 'Restaurant',
      instance_description: '',
      active: true,
      generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' },
    },
    affected_business_unit: null,
    responsible_business_unit: null,
    activity_subject: null,
    signal_summary: null,
    created_by_id: 'user-1',
    created_by_display_name: 'Alice',
    use_shared_chronology: true,
    start_at: null,
    all_day: false,
    visible_from: null,
    end_at: null,
    occurrence_date: null,
    last_activity_at: '2026-06-30T10:00:00Z',
    marked_done_by_membership_id: null,
    marked_done_by_display_name: null,
    marked_done_at: null,
    validated_by_membership_id: null,
    validated_by_display_name: null,
    validated_at: null,
    canceled_by_membership_id: null,
    canceled_by_display_name: null,
    canceled_at: null,
    cancel_origin: null,
    reopened_by_membership_id: null,
    reopened_by_display_name: null,
    reopened_at: null,
    started_by_membership_id: null,
    started_by_display_name: null,
    started_at: null,
    reactivated_by_membership_id: null,
    reactivated_by_display_name: null,
    reactivated_at: null,
    created_at: '2026-06-30T08:00:00Z',
    updated_at: '2026-06-30T10:00:00Z',
    assignees_by_pole: [],
    involved_poles: [],
    task_executions: [],
    permission_hints: {
      can_mark_done: false,
      can_validate: false,
      can_reopen: false,
      can_cancel: false,
      can_update: false,
      is_pilot_pole_assignee: true,
      can_pin: false,
    },
    active_review: null,
    ...overrides,
  }
}

afterEach(() => {
  cleanup()
})

describe('ActionPlanExecutionDetailHeader', () => {
  it('keeps the title card to the title, and shows review only once validated', () => {
    const { unmount } = render(
      <ActionPlanExecutionDetailHeader
        execution={buildExecution({
          active_review: { stars: 2, comment: 'À améliorer' },
          description: 'Vérifier le disjoncteur.',
          start_at: '2026-07-01T10:00:00.000Z',
          end_at: '2026-07-02T10:00:00.000Z',
        })}
        isOverdue
      />,
    )

    const title = screen.getByRole('heading', { name: 'Plan nettoyage terrasse' })
    expect(title.parentElement?.textContent).not.toContain('Terminé')
    expect(screen.queryByText('Note')).toBeNull()
    expect(screen.queryByText('À améliorer')).toBeNull()
    expect(screen.getByText('Échéance')).toBeTruthy()
    expect(screen.getByText('Début')).toBeTruthy()
    expect(screen.getByText('Fin')).toBeTruthy()
    expect(screen.queryByText('Échéance dépassée')).toBeNull()
    expect(screen.queryByRole('progressbar')).toBeNull()
    unmount()

    render(
      <ActionPlanExecutionDetailHeader
        execution={buildExecution({
          validated_at: '2026-07-02T16:30:00.000Z',
          active_review: { stars: 2, comment: 'À améliorer' },
        })}
        isOverdue={false}
      />,
    )

    const validatedTitle = screen.getByRole('heading', { name: 'Plan nettoyage terrasse' })
    expect(screen.queryByText('Note')).toBeNull()
    expect(screen.getByRole('img', { name: 'Note : 2 sur 5' })).toBeTruthy()
    expect(validatedTitle.parentElement?.textContent).toContain('À améliorer')
    expect(screen.queryByText('Validée')).toBeNull()
  })

  it('shows the feed start and end pattern with a brand progress bar while in progress', () => {
    render(
      <ActionPlanExecutionDetailHeader
        execution={buildExecution({
          status: 'in_progress',
          start_at: '2026-06-30T08:00:00Z',
          end_at: '2026-07-01T18:00:00Z',
        })}
        isOverdue
      />,
    )

    expect(screen.getByText('Échéance')).toBeTruthy()
    expect(screen.getByText('Début')).toBeTruthy()
    expect(screen.getByText('Fin')).toBeTruthy()
    expect(screen.getByText('Échéance dépassée')).toBeTruthy()
    const progress = screen.getByRole('progressbar', { name: 'Progression temporelle' })
    expect(progress.querySelector('.bg-\\[\\#E24B4A\\]')).toBeNull()
    expect(progress.querySelector('.bg-\\[\\#114660\\]')).toBeTruthy()
  })

  it('hides the active temporal bar outside in_progress', () => {
    for (const status of ['scheduled', 'pending_validation', 'canceled'] as const) {
      const { unmount } = render(
        <ActionPlanExecutionDetailHeader
          execution={buildExecution({
            status,
            start_at: '2026-06-30T08:00:00Z',
            end_at: '2026-07-01T18:00:00Z',
          })}
          isOverdue
        />,
      )
      expect(screen.queryByRole('progressbar')).toBeNull()
      expect(screen.getByText('Échéance')).toBeTruthy()
      expect(screen.getByText('Fin')).toBeTruthy()
      unmount()
    }
  })
})

describe('ActionPlanExecutionDetailMobileContext', () => {
  it('groups status, pilot, assignees, creator, and lifecycle lines', () => {
    render(
      <ActionPlanExecutionDetailMobileContext
        execution={buildExecution({
          status: 'pending_validation',
          activity_subject: {
            id: 'sub-1',
            catalog_key: 'maintenance__climatisation',
            label: 'Climatisation',
            description: '',
            source: 'catalog_suggestion',
            active: true,
            is_generic: true,
          },
          affected_business_unit: {
            id: 'bu-2',
            specific_name: 'Maintenance',
            instance_description: '',
            active: true,
            generic: {
              key: 'maintenance',
              label: 'Maintenance',
              description: '',
              unit_type: 'dedicated',
            },
          },
          all_day: true,
          start_at: '2026-07-01T10:00:00.000Z',
          end_at: '2026-07-02T10:00:00.000Z',
          marked_done_at: '2026-07-04T11:00:00.000Z',
          marked_done_by_display_name: 'Jean D.',
          assignees_by_pole: [
            {
              business_unit: {
                id: 'bu-1',
                specific_name: 'Restaurant',
                instance_description: '',
                active: true,
                generic: {
                  key: 'restaurant',
                  label: 'Restaurant',
                  description: '',
                  unit_type: 'dedicated',
                },
              },
              assignees: [
                {
                  membership_id: 'membership-1',
                  display_name: 'Jean D.',
                  start_at: '2026-07-07T09:00:00.000Z',
                  visible_from: '2026-07-07T09:00:00.000Z',
                  end_at: '2026-07-07T10:15:00.000Z',
                },
                {
                  membership_id: 'm-4',
                  display_name: 'Nora E.',
                  start_at: '2026-07-07T09:00:00.000Z',
                  visible_from: '2026-07-07T09:00:00.000Z',
                  end_at: '2026-07-07T10:15:00.000Z',
                },
              ],
            },
          ],
        })}
        currentMembershipId="membership-1"
      />,
    )

    const context = screen.getByTestId('execution-detail-mobile-context')
    expect(context.textContent).toContain('Contexte')
    expect(context.textContent).toContain('En attente de validation')
    expect(context.textContent).toContain('Restaurant')
    expect(context.textContent).not.toContain('Maintenance')
    expect(context.textContent).not.toContain('Climatisation')
    expect(context.textContent).not.toContain('Planification')
    expect(screen.getByText('Créateur')).toBeTruthy()
    expect(context.textContent).toMatch(/Alice le \d{2}\/\d{2}\/\d{4} à \d{2}:\d{2}/)
    expect((context.textContent ?? '').indexOf('Créateur')).toBeLessThan(
      (context.textContent ?? '').indexOf('Alice le'),
    )
    expect(screen.queryByText('Pôle concerné')).toBeNull()
    const markedDone = screen.getByText(/Marqué comme terminé le .+ par Jean D\./)
    expect(markedDone.className).toContain('italic')
    const assignees = screen.getByRole('list', { name: 'Assignés' })
    expect(context.contains(assignees)).toBe(true)
    expect(assignees.textContent).toContain('Jean D.')
    expect(assignees.textContent).toContain('(vous)')
    expect(assignees.textContent).toContain('Nora E.')
    expect(screen.queryByText('+1')).toBeNull()
  })

  it('bounds assignee columns and scrolls them inside the context card', () => {
    const longName = 'Alexandrine Montmorency-Beauregard'
    render(
      <ActionPlanExecutionDetailMobileContext
        execution={buildExecution({
          assignees_by_pole: [
            {
              business_unit: {
                id: 'bu-1',
                specific_name: 'Restaurant',
                instance_description: '',
                active: true,
                generic: {
                  key: 'restaurant',
                  label: 'Restaurant',
                  description: '',
                  unit_type: 'dedicated',
                },
              },
              assignees: [longName, 'Paul B.', 'Nora E.', 'Luc F.', 'Inès G.'].map(
                (displayName, index) => ({
                  membership_id: `m-${index + 1}`,
                  display_name: displayName,
                  start_at: '2026-07-07T09:00:00.000Z',
                  visible_from: '2026-07-07T09:00:00.000Z',
                  end_at: '2026-07-07T10:15:00.000Z',
                }),
              ),
            },
          ],
        })}
      />,
    )

    const context = screen.getByTestId('execution-detail-mobile-context')
    const assignees = screen.getByRole('list', { name: 'Assignés' })
    const scroller = assignees.parentElement
    const longNameNode = screen.getByText(longName)

    expect(context.contains(assignees)).toBe(true)
    expect(context.parentElement?.className).toContain('min-w-0')
    expect(scroller?.className).toContain('overflow-x-auto')
    expect(scroller?.className).toContain('min-w-0')
    expect(assignees.className).toContain('grid-flow-col')
    expect(assignees.style.gridTemplateRows).toBe('repeat(4, auto)')
    expect(assignees.style.gridAutoColumns).toBe('11rem')
    expect(longNameNode.className).toContain('min-w-0')
    expect(longNameNode.closest('li')?.className).toContain('min-w-0')
    expect(screen.getByText('Inès G.')).toBeTruthy()
  })

  it('shows the validation and cancellation lines from the feed helpers', () => {
    const { unmount } = render(
      <ActionPlanExecutionDetailMobileContext
        execution={buildExecution({
          status: 'done',
          marked_done_at: '2026-07-02T12:00:00.000Z',
          marked_done_by_display_name: 'Jean D.',
          validated_at: '2026-07-02T16:30:00.000Z',
          validated_by_display_name: 'Camille Bernard',
        })}
      />,
    )
    const markedDone = screen.getByText(/Marqué comme terminé le .+ par Jean D\./)
    const validated = screen.getByText(/Validé le .+ par Camille Bernard/)
    expect(markedDone.className).toContain('italic')
    expect(validated.className).toContain('italic')
    expect(markedDone.compareDocumentPosition(validated) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    unmount()

    render(
      <ActionPlanExecutionDetailMobileContext
        execution={buildExecution({
          status: 'canceled',
          canceled_at: '2026-07-03T09:15:00.000Z',
          canceled_by_display_name: 'Camille Bernard',
        })}
      />,
    )
    expect(screen.getByText(/Annulé le .+ par Camille Bernard/).className).toContain('italic')
  })
})

describe('ActionPlanExecutionDetailDeadlineSection planification', () => {
  it('groups start and end_at once without repeating Deadline', () => {
    render(
      <ActionPlanExecutionDetailDeadlineSection
        execution={buildExecution({
          status: 'in_progress',
          start_at: '2026-06-30T08:00:00Z',
          end_at: '2026-07-01T18:00:00Z',
        })}
        isOverdue={false}
        isTerminal={false}
        variant="planification"
      />,
    )

    expect(screen.getByText('Planification')).toBeTruthy()
    expect(screen.getByText('Début')).toBeTruthy()
    expect(screen.getByText('Échéance')).toBeTruthy()
    expect(screen.queryByText('Deadline')).toBeNull()
    expect(screen.getAllByText(/01\/07\/2026/).length).toBe(1)
  })
})
