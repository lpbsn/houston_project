import { useEffect, useRef, useState } from 'react'
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAppRoute } from '@/app/app-routes'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

import {
  confirmBrainPeriod,
  fetchActiveBrainWork,
  fetchBrainAnalysis,
  isBrainAccessLoss,
  launchBrainAnalysis,
  listBrainAnalyses,
  listBrainObjectives,
  listBrainReportings,
  listBrainSources,
  uploadBrainReporting,
  brainQueryKeys,
  type BrainReporting,
} from '../api'
import { errorDetail, workStatusLabel, type ReanalysisProposal } from '../display'
import { brainPollInterval } from '../polling'
import { BrainAnalysisPanel } from './brain-analysis-panel'
import { BrainDecisions } from './brain-decisions'

type BrainWorkspaceProps = {
  establishmentId: string
  analysisId: string | null
}

export function BrainWorkspace({ establishmentId, analysisId }: BrainWorkspaceProps) {
  const { navigate } = useAppRoute()
  const queryClient = useQueryClient()
  const [selectedReportingId, setSelectedReportingId] = useState<string | null>(null)
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')
  const [reanalysisNote, setReanalysisNote] = useState<string | null>(null)
  const [requireNewReporting, setRequireNewReporting] = useState(false)
  const launchKey = useRef<string | null>(null)

  const reportings = useInfiniteQuery({
    queryKey: brainQueryKeys.reportings(establishmentId),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => listBrainReportings(establishmentId, pageParam),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    retry: (failureCount, error) => !isBrainAccessLoss(error) && failureCount < 1,
  })
  const analyses = useInfiniteQuery({
    queryKey: brainQueryKeys.analyses(establishmentId),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => listBrainAnalyses(establishmentId, pageParam),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    retry: (failureCount, error) => !isBrainAccessLoss(error) && failureCount < 1,
  })
  const objectives = useInfiniteQuery({
    queryKey: brainQueryKeys.objectives(establishmentId),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => listBrainObjectives(establishmentId, pageParam),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    retry: (failureCount, error) => !isBrainAccessLoss(error) && failureCount < 1,
  })
  const work = useQuery({
    queryKey: brainQueryKeys.work(establishmentId),
    queryFn: () => fetchActiveBrainWork(establishmentId),
    retry: (failureCount, error) => !isBrainAccessLoss(error) && failureCount < 1,
    refetchInterval: (query) =>
      brainPollInterval({
        visible: true,
        accessLost: isBrainAccessLoss(query.state.error),
        statuses: [query.state.data?.work?.status],
      }),
  })
  const analysis = useQuery({
    queryKey: analysisId
      ? brainQueryKeys.analysis(establishmentId, analysisId)
      : ['brain', establishmentId, 'analysis', 'none'],
    queryFn: () => fetchBrainAnalysis(establishmentId, analysisId ?? ''),
    enabled: Boolean(analysisId),
    retry: (failureCount, error) => !isBrainAccessLoss(error) && failureCount < 1,
    refetchInterval: (query) =>
      brainPollInterval({
        visible: true,
        accessLost: isBrainAccessLoss(query.state.error),
        statuses: [
          query.state.data?.status,
          ...(query.state.data?.messages ?? []).map((message) => message.status),
        ],
      }),
  })
  const analysisStatus = analysis.data?.status
  useEffect(() => {
    if (!analysisId || !analysisStatus) {
      return
    }
    if (analysisStatus === 'queued' || analysisStatus === 'running') {
      return
    }
    void queryClient.invalidateQueries({
      queryKey: brainQueryKeys.analyses(establishmentId),
    })
  }, [analysisId, analysisStatus, establishmentId, queryClient])

  const sources = useQuery({
    queryKey: analysisId
      ? brainQueryKeys.sources(establishmentId, analysisId)
      : ['brain', establishmentId, 'sources', 'none'],
    queryFn: () => listBrainSources(establishmentId, analysisId ?? ''),
    enabled: Boolean(analysisId) && analysis.data?.status === 'completed',
    retry: (failureCount, error) => !isBrainAccessLoss(error) && failureCount < 1,
  })

  const reportingRows = reportings.data?.pages.flatMap((page) => page.results) ?? []
  const selectedReporting = requireNewReporting
    ? null
    : selectedReportingId
      ? reportingRows.find((item) => item.id === selectedReportingId) ?? null
      : reportingRows[0] ?? null

  function prepareReanalysis(proposal: ReanalysisProposal) {
    if (proposal.requiresNewReporting) {
      setRequireNewReporting(true)
      setSelectedReportingId(null)
      setReanalysisNote('Un nouveau fichier de reporting est nécessaire. La réanalyse n’est pas lancée.')
      document.getElementById('brain-import')?.scrollIntoView({ block: 'start' })
      return
    }
    if (proposal.reportingId) {
      setSelectedReportingId(proposal.reportingId)
    }
    setPeriodStart(proposal.periodStart ?? '')
    setPeriodEnd(proposal.periodEnd ?? '')
    setReanalysisNote('La réanalyse est préparée. Elle démarre seulement avec Analyser.')
    document.getElementById('brain-launch')?.scrollIntoView({ block: 'start' })
  }

  function openAnalysis(nextAnalysisId: string) {
    navigate(`/e/${establishmentId}/brain/${nextAnalysisId}`)
  }

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ['brain', establishmentId] })
  }

  const upload = useMutation({
    mutationFn: (file: File) => uploadBrainReporting(establishmentId, file),
    onSuccess: (reporting) => {
      setRequireNewReporting(false)
      setReanalysisNote(null)
      setSelectedReportingId(reporting.id)
      setPeriodStart(reporting.period_start ?? '')
      setPeriodEnd(reporting.period_end ?? '')
      refresh()
    },
  })
  const confirmPeriod = useMutation({
    mutationFn: (reporting: BrainReporting) =>
      confirmBrainPeriod(establishmentId, reporting.id, {
        period_start: periodStart,
        period_end: periodEnd,
      }),
    onSuccess: (reporting) => {
      setSelectedReportingId(reporting.id)
      refresh()
    },
  })
  const launch = useMutation({
    mutationFn: (input: { reportingId: string; idempotencyKey: string }) =>
      launchBrainAnalysis(establishmentId, {
        reporting_id: input.reportingId,
        idempotency_key: input.idempotencyKey,
      }),
    onSuccess: (result) => {
      launchKey.current = null
      setReanalysisNote(null)
      refresh()
      openAnalysis(result.work.analysis_id)
    },
  })

  if (isBrainAccessLoss(work.error) || isBrainAccessLoss(reportings.error)) {
    return <p className="px-4 py-8 text-sm">Cette page est introuvable.</p>
  }

  const activeWork = work.data?.work ?? null

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6" data-testid="brain-workspace">
      <section className="rounded-xl border border-border p-4" id="brain-import">
        <h2 className="text-base font-semibold">Reporting</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Le fichier est conservé. L&apos;analyse ne démarre qu&apos;après confirmation de la
          période et un lancement explicite.
        </p>
        <form
          className="mt-3 flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault()
            const input = event.currentTarget.elements.namedItem('file')
            const file = input instanceof HTMLInputElement ? input.files?.[0] : undefined
            if (file) {
              upload.mutate(file)
            }
          }}
        >
          <label className="flex flex-col gap-1 text-sm">
            Fichier de reporting
            <Input name="file" type="file" data-testid="brain-file" required />
          </label>
          {reanalysisNote ? <p className="text-sm">{reanalysisNote}</p> : null}
          {upload.error ? <p className="text-sm">{errorDetail(upload.error)}</p> : null}
          <Button type="submit" disabled={upload.isPending}>
            Importer
          </Button>
        </form>
      </section>

      {selectedReporting ? (
        <section className="rounded-xl border border-border p-4" id="brain-launch">
          <h2 className="text-base font-semibold">{selectedReporting.original_filename}</h2>
          <p className="mt-2 text-sm">
            Extraction : {selectedReporting.extraction.coverage || 'couverture non précisée'} —{' '}
            {selectedReporting.extraction.measure_count} mesures,{' '}
            {selectedReporting.extraction.qualitative_count} éléments qualitatifs.
          </p>
          {selectedReporting.extraction.warnings.map((notice) => (
            <p key={`${notice.code}-${notice.message}`} className="mt-1 text-sm">
              {notice.message}
            </p>
          ))}
          {selectedReporting.extraction.limits.map((notice) => (
            <p key={`${notice.code}-${notice.message}`} className="mt-1 text-sm">
              Limite : {notice.message}
            </p>
          ))}
          {selectedReporting.period_confirmed ? (
            <p className="mt-2 text-sm">
              Période confirmée : {selectedReporting.period_start} → {selectedReporting.period_end}{' '}
              (fin exclue).
            </p>
          ) : (
            <form
              className="mt-3 flex flex-col gap-3"
              onSubmit={(event) => {
                event.preventDefault()
                confirmPeriod.mutate(selectedReporting)
              }}
            >
              <label className="flex flex-col gap-1 text-sm">
                Début de période
                <Input type="date" value={periodStart} onChange={(event) => setPeriodStart(event.target.value)} required />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                Fin de période, exclue
                <Input type="date" value={periodEnd} onChange={(event) => setPeriodEnd(event.target.value)} required />
              </label>
              {confirmPeriod.error ? <p className="text-sm">{errorDetail(confirmPeriod.error)}</p> : null}
              <Button type="submit" disabled={confirmPeriod.isPending}>
                Confirmer la période
              </Button>
            </form>
          )}
          {selectedReporting.period_confirmed ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <Button
                type="button"
                data-testid="brain-analyze"
                disabled={launch.isPending}
                onClick={() => {
                  const idempotencyKey = crypto.randomUUID()
                  launchKey.current = idempotencyKey
                  launch.mutate({ reportingId: selectedReporting.id, idempotencyKey })
                }}
              >
                Analyser
              </Button>
              {launch.error ? (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() =>
                    launch.mutate({
                      reportingId: selectedReporting.id,
                      idempotencyKey: launchKey.current ?? crypto.randomUUID(),
                    })
                  }
                >
                  Réessayer
                </Button>
              ) : null}
            </div>
          ) : null}
          {launch.error ? <p className="mt-2 text-sm">{errorDetail(launch.error)}</p> : null}
          {selectedReporting.preview_url ? (
            <a className="mt-3 inline-block text-sm underline" href={selectedReporting.preview_url}>
              Voir le fichier importé
            </a>
          ) : null}
        </section>
      ) : null}

      {activeWork && activeWork.analysis_id !== analysisId ? (
        <section className="rounded-xl border border-border p-4">
          <p className="text-sm">
            Un travail est suivi sur cet établissement : {workStatusLabel(activeWork.status)}.
          </p>
          <Button type="button" className="mt-3" variant="outline" onClick={() => openAnalysis(activeWork.analysis_id)}>
            Ouvrir le travail en cours
          </Button>
        </section>
      ) : null}

      {analysis.data ? (
        <BrainAnalysisPanel
          establishmentId={establishmentId}
          analysis={analysis.data}
          sources={sources.data?.results ?? []}
          onChanged={refresh}
          onOpenAnalysis={openAnalysis}
          onPrepareReanalysis={(proposal) => prepareReanalysis(proposal)}
        />
      ) : null}
      {analysisId && isBrainAccessLoss(analysis.error) ? (
        <p className="text-sm">Cette analyse est introuvable.</p>
      ) : null}

      <BrainDecisions
        establishmentId={establishmentId}
        analysis={analysis.data ?? null}
        objectives={objectives.data?.pages.flatMap((page) => page.results) ?? []}
        onChanged={refresh}
      />

      <section className="rounded-xl border border-border p-4">
        <h2 className="text-base font-semibold">Historique</h2>
        <ul className="mt-3 flex flex-col gap-2 text-sm">
          {(analyses.data?.pages.flatMap((page) => page.results) ?? []).map((item) => (
            <li key={item.id}>
              <button type="button" className="underline" onClick={() => openAnalysis(item.id)}>
                {item.reporting.original_filename} — {workStatusLabel(item.status)} —{' '}
                {item.reporting.period_start ?? 'période non confirmée'}
              </button>
            </li>
          ))}
        </ul>
        {analyses.hasNextPage ? (
          <Button type="button" className="mt-3" variant="outline" onClick={() => void analyses.fetchNextPage()}>
            Analyses plus anciennes
          </Button>
        ) : null}
        {reportings.hasNextPage ? (
          <Button
            type="button"
            className="mt-3"
            variant="outline"
            onClick={() => void reportings.fetchNextPage()}
          >
            Reportings plus anciens
          </Button>
        ) : null}
      </section>
    </div>
  )
}
