import { Profiler, StrictMode, useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'

import { ActionPlanExecutionFeedCard } from '@/features/execution/components/action-plan-execution-feed-card'
import { SignalCard } from '@/features/signals/components/signal-card'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'
import type { SignalFeedItem } from '@/features/signals/types'
import '@/styles/globals.css'

const REFERENCE_COMMIT = import.meta.env.VITE_FEED_BASELINE_REFERENCE_COMMIT
if (!REFERENCE_COMMIT) {
  throw new Error('VITE_FEED_BASELINE_REFERENCE_COMMIT is required.')
}
const ITERATIONS = 20
const HYDRATED_ITEMS = 50
const ANCHOR_MS = Date.now()

function relativeIso(hours: number) {
  return new Date(ANCHOR_MS + hours * 60 * 60 * 1000).toISOString()
}

type CommitSample = {
  phase: 'mount' | 'update' | 'nested-update'
  actualDuration: number
  baseDuration: number
  commitTime: number
}

declare global {
  interface Window {
    __FEED_BROWSER_BASELINE__?: Record<string, unknown>
  }
}

const signalCommits: CommitSample[] = []
const executionCommits: CommitSample[] = []

function signalItem(generation: number, index: number): SignalFeedItem {
  return {
    id: `signal-${generation}-${index}`,
    title: `Observation synthétique ${generation}-${index}`,
    structured_summary_short: 'Résumé sûr utilisé uniquement pour la mesure de rendu.',
    status: index % 5 === 0 ? 'interesting' : index % 3 === 0 ? 'in_progress' : 'open',
    routing_status: 'resolved',
    is_pinned: false,
    affected_business_unit_id: null,
    affected_business_unit_key: 'operations',
    affected_business_unit_label: 'Operations',
    responsible_business_unit_id: null,
    responsible_business_unit_key: 'operations',
    responsible_business_unit_label: 'Operations',
    activity_subject_id: null,
    activity_subject_normalized_name: 'feed baseline',
    activity_subject_label: 'Feed baseline',
    operational_unit_key: null,
    location_text: `Zone ${index % 8}`,
    media_count: index % 4,
    aggregation_count: 1 + (index % 5),
    last_activity_at: relativeIso(-4),
    created_at: relativeIso(-5),
    reporter_display_name: 'Baseline User',
    permission_hints: {
      can_pin: true,
      can_mark_interesting: true,
      can_cancel: true,
      can_resolve: true,
      can_create_linked_action_plan: true,
      can_qualify_routing: false,
      can_request_resolution: true,
      can_approve_resolution_request: false,
      can_reject_resolution_request: false,
      can_cancel_resolution_request: false,
    },
    resolution_request: null,
  }
}

function executionItem(generation: number, index: number): ActionPlanExecutionFeedItem {
  return {
    id: `execution-${generation}-${index}`,
    title: `Exécution synthétique ${generation}-${index}`,
    description_short: 'Description synthétique utilisée uniquement pour la mesure.',
    status: index % 4 === 0 ? 'pending_validation' : 'in_progress',
    requires_validation: index % 4 === 0,
    validated_at: null,
    validated_by_display_name: null,
    pilot_business_unit: {
      id: 'bu-baseline',
      specific_name: 'Operations',
      instance_description: '',
      active: true,
      generic: {
        key: 'operations',
        label: 'Operations',
        description: '',
        unit_type: 'dedicated',
      },
    },
    involved_poles: [],
    signal_summary: null,
    assignees: [{ membership_id: 'membership-baseline', display_name: 'Baseline User' }],
    start_at: relativeIso(-28),
    end_at: index % 3 === 0 ? relativeIso(-24) : relativeIso(24),
    all_day: false,
    visible_from: relativeIso(-48),
    is_overdue: index % 3 === 0,
    task_count: 3,
    treated_task_count: index % 4,
    task_executions: [],
    last_activity_at: relativeIso(-4),
    created_at: relativeIso(-5),
    created_by_display_name: 'Baseline User',
    marked_done_at: index % 4 === 0 ? relativeIso(-6) : null,
    marked_done_by_display_name: index % 4 === 0 ? 'Baseline User' : null,
    canceled_at: null,
    active_review: null,
    is_pinned: false,
    permission_hints: {
      can_pin: true,
      can_mark_done: true,
      can_validate: true,
      can_cancel: true,
      can_reopen: false,
      can_update: true,
      is_pilot_pole_assignee: true,
    },
  }
}

function commitSummary(samples: CommitSample[]) {
  const durations = samples.map((sample) => sample.actualDuration)
  return {
    commit_count: samples.length,
    mount_commits: samples.filter((sample) => sample.phase === 'mount').length,
    update_commits: samples.filter((sample) => sample.phase !== 'mount').length,
    actual_duration_total_ms: Number(
      durations.reduce((sum, value) => sum + value, 0).toFixed(3),
    ),
    actual_duration_mean_ms: Number(
      (durations.reduce((sum, value) => sum + value, 0) / durations.length).toFixed(3),
    ),
    actual_duration_max_ms: Number(Math.max(...durations).toFixed(3)),
    base_duration_max_ms: Number(
      Math.max(...samples.map((sample) => sample.baseDuration)).toFixed(3),
    ),
  }
}

function heapUsed(): number | null {
  const memory = (
    performance as Performance & {
      memory?: { usedJSHeapSize: number }
    }
  ).memory
  return memory?.usedJSHeapSize ?? null
}

function BaselineApp() {
  const [generation, setGeneration] = useState(0)
  const heapAtStart = useMemo(() => heapUsed(), [])
  const signals = useMemo(
    () =>
      Array.from({ length: HYDRATED_ITEMS }, (_, index) =>
        signalItem(generation, index),
      ),
    [generation],
  )
  const executions = useMemo(
    () =>
      Array.from({ length: HYDRATED_ITEMS }, (_, index) =>
        executionItem(generation, index),
      ),
    [generation],
  )

  useEffect(() => {
    if (generation >= ITERATIONS - 1) {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          window.__FEED_BROWSER_BASELINE__ = {
            schema_version: 'feed_browser_baseline_v2',
            reference_commit: REFERENCE_COMMIT,
            runtime: {
              user_agent: navigator.userAgent,
              vite_mode: import.meta.env.MODE,
              iterations: ITERATIONS,
              hydrated_items_per_feed: HYDRATED_ITEMS,
              anchor_at: new Date(ANCHOR_MS).toISOString(),
              viewport: { width: innerWidth, height: innerHeight },
              device_pixel_ratio: devicePixelRatio,
            },
            signal_render: commitSummary(signalCommits),
            execution_render: commitSummary(executionCommits),
            heap: {
              used_js_heap_start_bytes: heapAtStart,
              used_js_heap_end_bytes: heapUsed(),
            },
            dom_nodes: document.getElementsByTagName('*').length,
          }
          document.body.dataset.baselineComplete = 'true'
        })
      })
      return
    }
    const frame = requestAnimationFrame(() => setGeneration((current) => current + 1))
    return () => cancelAnimationFrame(frame)
  }, [generation, heapAtStart])

  return (
    <main className="grid grid-cols-1 gap-6 p-4 lg:grid-cols-2">
      <section aria-label="Signals baseline">
        <h1 className="mb-3 text-lg font-semibold">Signals</h1>
        <Profiler
          id="signals"
          onRender={(_id, phase, actualDuration, baseDuration, _startTime, commitTime) => {
            signalCommits.push({ phase, actualDuration, baseDuration, commitTime })
          }}
        >
          <div className="space-y-2">
            {signals.map((item) => (
              <SignalCard key={item.id} item={item} onSelect={() => undefined} />
            ))}
          </div>
        </Profiler>
      </section>
      <section aria-label="Execution baseline">
        <h1 className="mb-3 text-lg font-semibold">Exécution</h1>
        <Profiler
          id="execution"
          onRender={(_id, phase, actualDuration, baseDuration, _startTime, commitTime) => {
            executionCommits.push({ phase, actualDuration, baseDuration, commitTime })
          }}
        >
          <div className="space-y-2">
            {executions.map((item) => (
              <ActionPlanExecutionFeedCard
                key={item.id}
                item={item}
                onSelect={() => undefined}
              />
            ))}
          </div>
        </Profiler>
      </section>
    </main>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BaselineApp />
  </StrictMode>,
)
