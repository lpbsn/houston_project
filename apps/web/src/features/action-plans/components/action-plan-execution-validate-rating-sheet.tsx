import { Star, StarOff } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { TerrainBottomSheet } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

const footerButtonClassName =
  'flex-1 rounded-full border border-[#E8E6DF] bg-white font-semibold text-[#1a1a1a]'

export const ACTION_PLAN_EXECUTION_REVIEW_COMMENT_MAX_LENGTH = 2000

type ActionPlanExecutionValidateRatingSheetProps = {
  open: boolean
  stars: number | null
  comment: string
  isPending: boolean
  onStarsChange: (stars: number) => void
  onCommentChange: (value: string) => void
  onConfirm: () => void
  onClose: () => void
}

const RATING_VALUES = [0, 1, 2, 3, 4, 5] as const

function ratingAriaLabel(value: number): string {
  return `${value} étoile${value > 1 ? 's' : ''}`
}

export function ActionPlanExecutionValidateRatingSheet({
  open,
  stars,
  comment,
  isPending,
  onStarsChange,
  onCommentChange,
  onConfirm,
  onClose,
}: ActionPlanExecutionValidateRatingSheetProps) {
  return (
    <TerrainBottomSheet
      title="Évaluer la réalisation du plan d'action"
      open={open}
      onClose={onClose}
      dismissible={false}
      footer={
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            className={footerButtonClassName}
            disabled={isPending}
            onClick={onClose}
          >
            Annuler
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className={cn(
              footerButtonClassName,
              'border-transparent bg-[#1a1a1a] text-white disabled:bg-[#c9c6bd] disabled:text-white',
            )}
            disabled={isPending || stars == null}
            onClick={onConfirm}
          >
            Confirmer
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="space-y-2">
          <p className="text-sm font-medium text-[#1a1a1a]">Choisir une note</p>
          <div
            className="mx-auto flex w-full max-w-[600px] items-center justify-between"
            role="radiogroup"
            aria-label="Note du plan"
          >
            {RATING_VALUES.map((value) => {
              const checked = stars === value
              const filled = value > 0 && stars !== null && stars >= value
              return (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={checked}
                  aria-label={ratingAriaLabel(value)}
                  className={cn(
                    'inline-flex size-12 items-center justify-center rounded-full bg-transparent',
                    'transition-colors outline-none focus-visible:ring-2 focus-visible:ring-[#EF9F27]/40',
                    'disabled:pointer-events-none disabled:opacity-50',
                  )}
                  disabled={isPending}
                  onClick={() => onStarsChange(value)}
                >
                  {value === 0 ? (
                    <StarOff
                      className="size-12 fill-none text-[#C9C6BD]"
                      strokeWidth={1.5}
                      aria-hidden
                    />
                  ) : (
                    <Star
                      className={cn(
                        'size-12',
                        filled ? 'fill-current text-[#EF9F27]' : 'fill-none text-[#C9C6BD]',
                      )}
                      strokeWidth={1.5}
                      aria-hidden
                    />
                  )}
                </button>
              )
            })}
          </div>
        </div>

        <label className="block space-y-2">
          <span className="text-sm font-medium text-[#1a1a1a]">Commentaire</span>
          <Textarea
            value={comment}
            disabled={isPending}
            maxLength={ACTION_PLAN_EXECUTION_REVIEW_COMMENT_MAX_LENGTH}
            onChange={(event) => onCommentChange(event.target.value)}
            placeholder="Ajouter un commentaire"
          />
        </label>
      </div>
    </TerrainBottomSheet>
  )
}
