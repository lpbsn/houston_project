import { useState } from 'react'
import { SendHorizonal } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const MAX_MESSAGE_LENGTH = 2000

type ChatComposerProps = {
  disabled?: boolean
  onSend: (body: string) => void
}

export function ChatComposer({ disabled = false, onSend }: ChatComposerProps) {
  const [draft, setDraft] = useState('')

  function handleSubmit() {
    const trimmed = draft.trim()
    if (!trimmed || disabled) {
      return
    }
    onSend(trimmed)
    setDraft('')
  }

  return (
    <footer
      className={cn(
        'sticky bottom-0 z-10 shrink-0 border-t border-[#E8E6DF] bg-[#F5F4F0]',
        'px-3 pt-2 pb-[max(0.75rem,env(safe-area-inset-bottom))]',
      )}
    >
      <div className="flex items-end gap-2">
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value.slice(0, MAX_MESSAGE_LENGTH))}
          placeholder="Écrire un message…"
          rows={1}
          disabled={disabled}
          className={cn(
            'min-h-11 max-h-32 flex-1 resize-none rounded-2xl border border-[#E8E6DF] bg-white px-3 py-2.5 text-sm',
            'text-[#1a1a1a] placeholder:text-[#a3a19a] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30',
          )}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              handleSubmit()
            }
          }}
        />
        <Button
          type="button"
          size="icon"
          className="h-11 w-11 shrink-0 rounded-full bg-[#1B4FD8] text-white hover:bg-[#1B4FD8]/95"
          disabled={disabled || !draft.trim()}
          onClick={handleSubmit}
          aria-label="Envoyer"
        >
          <SendHorizonal className="h-5 w-5" />
        </Button>
      </div>
      <p className="mt-1 px-1 text-[10px] text-[#a3a19a]">
        {draft.length}/{MAX_MESSAGE_LENGTH}
      </p>
    </footer>
  )
}
