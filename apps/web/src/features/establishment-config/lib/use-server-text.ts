import { useState } from 'react'

export function useServerText(serverText: string, identity: string) {
  const [text, setText] = useState(serverText)
  const [baseline, setBaseline] = useState(serverText)
  const [boundIdentity, setBoundIdentity] = useState(identity)

  let visibleText = text
  if (identity !== boundIdentity) {
    visibleText = serverText
    setBoundIdentity(identity)
    setText(serverText)
    setBaseline(serverText)
  } else if (serverText !== baseline) {
    const untouched = text.trim() === baseline.trim()
    setBaseline(serverText)
    if (untouched) {
      visibleText = serverText
      setText(serverText)
    }
  }

  return {
    text: visibleText,
    setText,
    changed: visibleText.trim() !== serverText.trim(),
  }
}
