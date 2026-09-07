import { useCallback, useEffect, useRef, useState, type PropsWithChildren } from 'react'

import { subscribeAppForeground } from '@/lib/app-lifecycle'

import { AndroidAppUpdateDialog } from './android-app-update-dialog'
import { fetchAndroidMinSupportedVersionCode } from './api'
import { logAndroidAppUpdate } from './log'
import {
  completeAndroidFlexibleUpdateIfDownloaded,
  isAndroidInAppUpdateRuntime,
  readAndroidPlayUpdate,
  startAndroidPlayUpdate,
} from './play-bridge'
import { decideAndroidAppUpdatePrompt, isPlayUpdateInstallable, shouldCheckPlayOnForeground } from './rules'
import {
  markAndroidAppUpdateChecked,
  readAndroidAppUpdateState,
  snoozeAndroidAppUpdate,
} from './storage'

type PromptMode = 'flexible' | 'force'

export function AndroidAppUpdateHost({ children }: PropsWithChildren) {
  const [prompt, setPrompt] = useState<PromptMode | null>(null)
  const [availableVersionCode, setAvailableVersionCode] = useState('')
  const [updateBusy, setUpdateBusy] = useState(false)
  const updateInFlightRef = useRef(false)
  const promptRef = useRef<PromptMode | null>(null)
  promptRef.current = prompt

  const runCheck = useCallback(async (reason: 'launch' | 'foreground') => {
    if (!isAndroidInAppUpdateRuntime()) {
      return
    }

    const nowMs = Date.now()
    const stored = readAndroidAppUpdateState()
    if (reason === 'foreground' && !shouldCheckPlayOnForeground(stored.lastCheckAtMs, nowMs)) {
      return
    }

    const play = await readAndroidPlayUpdate()
    markAndroidAppUpdateChecked(nowMs)
    if (!play) {
      setPrompt((current) => (current === 'force' ? current : null))
      return
    }

    const minSupportedVersionCode = await fetchAndroidMinSupportedVersionCode()
    const decision = decideAndroidAppUpdatePrompt({
      play,
      minSupportedVersionCode,
      nowMs,
      snooze: stored.snooze,
    })
    const floorUnknown = minSupportedVersionCode == null
    const keepForceWhileUnknown =
      promptRef.current === 'force' && floorUnknown && isPlayUpdateInstallable(play)

    if (decision.action === 'complete_downloaded') {
      await completeAndroidFlexibleUpdateIfDownloaded()
      setPrompt(null)
      return
    }

    if (decision.action === 'resume_in_progress') {
      return
    }

    if (decision.action === 'log_force_unavailable') {
      logAndroidAppUpdate('force_required_but_play_unavailable', {
        currentVersionCode: play.currentVersionCode,
        availableVersionCode: play.availableVersionCode,
        minSupportedVersionCode,
      })
      setPrompt(null)
      return
    }

    if (decision.action === 'show_force' || decision.action === 'show_flexible') {
      if (decision.action === 'show_flexible' && keepForceWhileUnknown) {
        return
      }
      const nextMode = decision.action === 'show_force' ? 'force' : 'flexible'
      logAndroidAppUpdate('update_detected', {
        currentVersionCode: play.currentVersionCode,
        availableVersionCode: play.availableVersionCode,
        mode: nextMode,
      })
      logAndroidAppUpdate('popup_shown', {
        availableVersionCode: play.availableVersionCode,
        mode: nextMode,
      })
      setAvailableVersionCode(play.availableVersionCode)
      setPrompt(nextMode)
      return
    }

    if (keepForceWhileUnknown) {
      return
    }
    setPrompt(null)
  }, [])

  useEffect(() => {
    const launchTimer = window.setTimeout(() => {
      void runCheck('launch')
    }, 0)
    const stopForeground = subscribeAppForeground(() => {
      void runCheck('foreground')
    })
    return () => {
      window.clearTimeout(launchTimer)
      stopForeground()
    }
  }, [runCheck])

  async function handleUpdate() {
    if (!prompt || updateInFlightRef.current) {
      return
    }
    updateInFlightRef.current = true
    setUpdateBusy(true)
    logAndroidAppUpdate('update_clicked', {
      availableVersionCode,
      mode: prompt,
    })
    try {
      const outcome = await startAndroidPlayUpdate(prompt === 'force' ? 'immediate' : 'flexible')
      if (outcome === 'ok') {
        if (prompt === 'flexible') {
          setPrompt(null)
        }
        return
      }

      const play = await readAndroidPlayUpdate()
      if (prompt === 'force') {
        if (!play || isPlayUpdateInstallable(play)) {
          return
        }
        setPrompt(null)
        return
      }
      setPrompt(null)
    } finally {
      updateInFlightRef.current = false
      setUpdateBusy(false)
    }
  }

  function handleLater() {
    if (updateInFlightRef.current) {
      return
    }
    logAndroidAppUpdate('later_clicked', { availableVersionCode })
    snoozeAndroidAppUpdate(availableVersionCode, Date.now())
    setPrompt(null)
  }

  return (
    <>
      <div className="flex h-full min-h-0 flex-col" inert={prompt === 'force' ? true : undefined}>
        {children}
      </div>
      {prompt ? (
        <AndroidAppUpdateDialog
          mode={prompt}
          updateBusy={updateBusy}
          onUpdate={() => {
            void handleUpdate()
          }}
          onLater={prompt === 'flexible' ? handleLater : undefined}
        />
      ) : null}
    </>
  )
}
