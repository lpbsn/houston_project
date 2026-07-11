import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export type ActionPlanTaskDetailLayoutProps = {
  leading?: ReactNode
  title: ReactNode
  meta?: ReactNode
  actions?: ReactNode
  deadline?: ReactNode
  status?: ReactNode
  description?: ReactNode
  className?: string
}

export function ActionPlanTaskDetailLayout({
  leading,
  title,
  meta,
  actions,
  deadline,
  status,
  description,
  className,
}: ActionPlanTaskDetailLayoutProps) {
  const hasBottomBlock = Boolean(meta || deadline || status)
  const contentColStart = leading ? 'col-start-2' : 'col-start-1'
  const bottomBlockRowClass = description ? 'row-start-3' : 'row-start-2'

  return (
    <div className={cn('px-4 py-3', className)}>
      <div
        className={cn(
          'grid items-center gap-x-1',
          leading && actions && 'grid-cols-[2.5rem_minmax(0,1fr)_auto]',
          leading && !actions && 'grid-cols-[2.5rem_minmax(0,1fr)]',
          !leading && actions && 'grid-cols-[minmax(0,1fr)_auto]',
          !leading && !actions && 'grid-cols-[minmax(0,1fr)]',
        )}
      >
        {leading ? <div className="row-start-1 shrink-0 self-center">{leading}</div> : null}

        <div className={cn('row-start-1 min-w-0', contentColStart)}>{title}</div>

        {actions ? (
          <div className="row-start-1 flex shrink-0 items-center justify-center self-center">
            {actions}
          </div>
        ) : null}

        {description ? (
          <div
            className={cn(
              'row-start-2 mt-0 min-w-0 break-words whitespace-pre-wrap text-sm text-[#7D7B75]',
              contentColStart,
            )}
          >
            {description}
          </div>
        ) : null}

        {hasBottomBlock ? (
          <div
            className={cn(
              bottomBlockRowClass,
              'mt-3 border-t border-[#E8E6DF] pt-2 text-xs text-[#7D7B75]',
              contentColStart,
            )}
          >
            {meta ? <div>{meta}</div> : null}
            {deadline || status ? (
              <div
                className={cn(
                  'flex items-end gap-2',
                  meta ? 'mt-0.5' : undefined,
                  deadline ? 'justify-between' : 'justify-end',
                )}
              >
                {deadline ? <div className="min-w-0">{deadline}</div> : null}
                {status ? <div className="shrink-0">{status}</div> : null}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  )
}
