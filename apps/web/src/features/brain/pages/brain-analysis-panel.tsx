import { useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

import {
  cancelBrainAnalysis,
  cancelBrainFollowUp,
  createBrainFollowUp,
  type BrainAnalysisDetail,
  type BrainFollowUpPurpose,
} from '../api'
import {
  declarationApplied,
  errorDetail,
  isDeclarationPurpose,
  liveSourceHref,
  PURPOSE_LABELS,
  readAnalysisResult,
  readFollowUpResult,
  readFrozenSource,
  workStatusLabel,
  type FrozenSource,
  type ReanalysisProposal,
} from '../display'

const PURPOSES: BrainFollowUpPurpose[] = [
  'explain',
  'hypothesis',
  'correction',
  'new_fact',
  'new_document',
]

type BrainAnalysisPanelProps = {
  establishmentId: string
  analysis: BrainAnalysisDetail
  sources: unknown[]
  onChanged: () => void
  onOpenAnalysis: (analysisId: string) => void
  onPrepareReanalysis: (proposal: ReanalysisProposal) => void
}

export function BrainAnalysisPanel({
  establishmentId,
  analysis,
  sources,
  onChanged,
  onOpenAnalysis,
  onPrepareReanalysis,
}: BrainAnalysisPanelProps) {
  const pending = analysis.status === 'queued' || analysis.status === 'running'
  const failed = analysis.status === 'failed'
  const completed = analysis.status === 'completed'
  const result = completed ? readAnalysisResult(analysis.result) : null
  const frozenSources = sources.flatMap((item) => {
    const source = readFrozenSource(item)
    return source ? [source] : []
  })

  return (
    <div className="flex flex-col gap-4">
      <section className="rounded-xl border border-border p-4">
        <h2 className="text-base font-semibold">Suivi</h2>
        <p className="mt-2 text-sm">{workStatusLabel(analysis.status)}</p>
        {pending ? (
          <p className="mt-2 text-sm text-muted-foreground">
            Aucune conclusion n&apos;est affichée tant que l&apos;analyse n&apos;est pas terminée.
          </p>
        ) : null}
        {failed ? (
          <p className="mt-2 text-sm">
            {analysis.failure_message || "L'analyse a échoué. Aucun résultat partiel n'est publié."}
          </p>
        ) : null}
        {analysis.status === 'canceled' ? (
          <p className="mt-2 text-sm text-muted-foreground">Cette analyse est annulée.</p>
        ) : null}
        {pending ? (
          <CancelWork
            label="Annuler l'analyse"
            onCancel={() => cancelBrainAnalysis(establishmentId, analysis.id).then(onChanged)}
          />
        ) : null}
      </section>

      {completed ? (
        <ResultSection result={result} searches={analysis.searches} />
      ) : null}

      {completed ? (
        <SourcesSection establishmentId={establishmentId} sources={frozenSources} />
      ) : null}

      <FollowUps
        establishmentId={establishmentId}
        analysis={analysis}
        onChanged={onChanged}
        onOpenAnalysis={onOpenAnalysis}
        onPrepareReanalysis={onPrepareReanalysis}
      />
    </div>
  )
}

function ResultSection({
  result,
  searches,
}: {
  result: ReturnType<typeof readAnalysisResult>
  searches: BrainAnalysisDetail['searches']
}) {
  const excluded = result?.coverage.filter((item) => item.disposition === 'excluded') ?? []
  return (
    <section className="rounded-xl border border-border p-4">
      <h2 className="text-base font-semibold">Résultat</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Ce résultat porte sur les pièces retenues. Les exclusions, les limites et les recherches
        sans élément retenu en font partie. Il ne couvre pas ce qui a été écarté.
      </p>
      {!result ? (
        <p className="mt-3 text-sm">Le résultat publié ne peut pas être affiché.</p>
      ) : (
        <div className="mt-4 flex flex-col gap-4">
          {result.limits.length > 0 ? (
            <div>
              <h3 className="text-sm font-medium">Limites</h3>
              <ul className="mt-1 list-disc pl-5 text-sm">
                {result.limits.map((limit) => (
                  <li key={`${limit.code}-${limit.message}`}>{limit.message || limit.code}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {excluded.length > 0 ? (
            <div>
              <h3 className="text-sm font-medium">Pièces exclues</h3>
              <ul className="mt-1 list-disc pl-5 text-sm">
                {excluded.map((item) => (
                  <li key={item.pieceId}>
                    {item.pieceId}
                    {item.reason ? ` — ${item.reason}` : ''}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <div className="flex flex-col gap-3">
            {result.subjects.map((subject) => (
              <article key={subject.key} className="rounded-lg bg-muted/40 p-3">
                <h3 className="text-sm font-medium">{subject.statement || subject.key}</h3>
                {subject.interpretation ? (
                  <p className="mt-1 text-sm">{subject.interpretation}</p>
                ) : null}
                {subject.orientation ? (
                  <p className="mt-1 text-xs text-muted-foreground">
                    Orientation : {subject.orientation}
                  </p>
                ) : null}
                {subject.limits.map((limit) => (
                  <p key={limit} className="mt-1 text-sm">
                    Limite : {limit}
                  </p>
                ))}
                {subject.gaps.map((gap) => (
                  <p key={gap} className="mt-1 text-sm">
                    Manque : {gap}
                  </p>
                ))}
              </article>
            ))}
          </div>
        </div>
      )}
      {searches.length > 0 ? (
        <div className="mt-4">
          <h3 className="text-sm font-medium">Recherches</h3>
          <ul className="mt-1 flex flex-col gap-1 text-sm">
            {searches.map((search) => (
              <li key={search.code}>
                {search.code} : {search.retained_count} retenu
                {search.retained_count > 1 ? 's' : ''} sur {search.examined_count} examiné
                {search.examined_count > 1 ? 's' : ''}
                {search.retained_count === 0 ? ' — aucun élément retenu' : ''}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}

function SourcesSection({
  establishmentId,
  sources,
}: {
  establishmentId: string
  sources: FrozenSource[]
}) {
  return (
    <section className="rounded-xl border border-border p-4">
      <h2 className="text-base font-semibold">Preuves figées</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Ces citations sont celles de la capture. Un lien ouvre l&apos;élément actuel, qui a pu
        changer depuis.
      </p>
      {sources.length === 0 ? (
        <p className="mt-3 text-sm">Aucune preuve citable n&apos;est publiée.</p>
      ) : (
        <ul className="mt-3 flex flex-col gap-3 text-sm">
          {sources.map((source) => {
            const href = liveSourceHref(establishmentId, source.category, source.sourceId)
            return (
              <li key={source.itemId || source.title}>
                <p>{source.title || 'Preuve'}</p>
                <p className="text-muted-foreground">Citation figée à la capture</p>
                {source.periodStatusUnreconstructable ? (
                  <p>Le statut au début ou à la fin de la période n&apos;est pas reconstituable.</p>
                ) : null}
                {href ? (
                  <a className="underline" href={href}>
                    {source.category === 'execution' ? "Ouvrir l'exécution actuelle" : "Ouvrir l'observation actuelle"}
                  </a>
                ) : null}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

function FollowUps({
  establishmentId,
  analysis,
  onChanged,
  onOpenAnalysis,
  onPrepareReanalysis,
}: {
  establishmentId: string
  analysis: BrainAnalysisDetail
  onChanged: () => void
  onOpenAnalysis: (analysisId: string) => void
  onPrepareReanalysis: (proposal: ReanalysisProposal) => void
}) {
  const [purpose, setPurpose] = useState<BrainFollowUpPurpose>('explain')
  const [body, setBody] = useState('')
  const requestId = useRef<string | null>(null)
  const followUp = useMutation({
    mutationFn: (request_id: string) =>
      createBrainFollowUp(establishmentId, analysis.id, {
        request_id,
        body,
        purpose,
      }),
    onSuccess: (result) => {
      requestId.current = null
      setBody('')
      onChanged()
      if (result.work.analysis_id !== analysis.id) {
        onOpenAnalysis(result.work.analysis_id)
      }
    },
  })

  return (
    <section className="rounded-xl border border-border p-4" data-testid="brain-follow-up">
      <h2 className="text-base font-semibold">Échanges</h2>
      {analysis.older_message_count > 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">
          {analysis.older_message_count} message
          {analysis.older_message_count > 1 ? 's' : ''} plus ancien
          {analysis.older_message_count > 1 ? 's' : ''} ne {analysis.older_message_count > 1 ? 'sont' : 'est'} pas affiché
          {analysis.older_message_count > 1 ? 's' : ''}.
        </p>
      ) : null}
      <div className="mt-3 flex flex-col gap-3">
        {analysis.messages.map((message) => {
          const followUpResult = readFollowUpResult(message.result)
          const applied = declarationApplied(message.declaration)
          const proposal = followUpResult?.reanalysis
          const pending = message.status === 'queued' || message.status === 'running'
          return (
            <article key={message.id} className="rounded-lg bg-muted/40 p-3 text-sm">
              <p className="font-medium">
                {PURPOSE_LABELS[message.purpose] ?? message.purpose} — {workStatusLabel(message.status)}
              </p>
              <p className="mt-1">{message.body}</p>
              {pending ? (
                <p className="mt-1 text-muted-foreground">Réponse en attente. Aucune conclusion intermédiaire.</p>
              ) : null}
              {message.status === 'failed' && message.failure_message ? (
                <p className="mt-1">{message.failure_message}</p>
              ) : null}
              {isDeclarationPurpose(message.purpose) || applied === false ? (
                <p className="mt-1">Cette déclaration n&apos;est pas appliquée au dossier.</p>
              ) : null}
              {followUpResult?.answer ? <p className="mt-1">{followUpResult.answer}</p> : null}
              {proposal?.proposed && proposal.launched === false ? (
                <div className="mt-2">
                  <p>Proposition de réanalyse. Elle n&apos;est pas lancée.</p>
                  {proposal.requiresNewReporting ? (
                    <p>Un nouveau fichier de reporting est nécessaire.</p>
                  ) : null}
                  <Button
                    type="button"
                    variant="outline"
                    className="mt-2"
                    onClick={() => onPrepareReanalysis(proposal)}
                  >
                    Préparer la réanalyse
                  </Button>
                </div>
              ) : null}
              {pending ? (
                <CancelWork
                  label="Annuler l'échange"
                  onCancel={() => cancelBrainFollowUp(establishmentId, message.id).then(onChanged)}
                />
              ) : null}
            </article>
          )
        })}
      </div>
      {completedAnalysis(analysis.status) ? (
        <form
          className="mt-4 flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault()
            const request_id = crypto.randomUUID()
            requestId.current = request_id
            followUp.mutate(request_id)
          }}
        >
          <label className="flex flex-col gap-1 text-sm">
            Objet
            <select
              className="h-11 rounded-xl border border-border/70 bg-background px-3"
              value={purpose}
              onChange={(event) => setPurpose(event.target.value as BrainFollowUpPurpose)}
            >
              {PURPOSES.map((item) => (
                <option key={item} value={item}>
                  {PURPOSE_LABELS[item]}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Message
            <Textarea value={body} onChange={(event) => setBody(event.target.value)} required />
          </label>
          {isDeclarationPurpose(purpose) ? (
            <p className="text-sm text-muted-foreground">
              Cette déclaration sera enregistrée sans modifier le dossier.
            </p>
          ) : null}
          {followUp.error ? <p className="text-sm">{errorDetail(followUp.error)}</p> : null}
          <div className="flex gap-2">
            <Button type="submit" disabled={followUp.isPending || body.trim().length === 0}>
              Envoyer
            </Button>
            {followUp.error ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => followUp.mutate(requestId.current ?? crypto.randomUUID())}
              >
                Réessayer
              </Button>
            ) : null}
          </div>
        </form>
      ) : (
        <p className="mt-3 text-sm text-muted-foreground">
          L&apos;échange s&apos;ouvre quand l&apos;analyse est terminée.
        </p>
      )}
    </section>
  )
}

function completedAnalysis(status: string): boolean {
  return status === 'completed'
}

function CancelWork({ label, onCancel }: { label: string; onCancel: () => Promise<unknown> }) {
  const cancel = useMutation({ mutationFn: onCancel })
  return (
    <div className="mt-3">
      <Button type="button" variant="outline" disabled={cancel.isPending} onClick={() => cancel.mutate()}>
        {label}
      </Button>
      {cancel.error ? <p className="mt-2 text-sm">{errorDetail(cancel.error)}</p> : null}
    </div>
  )
}
