export function ActionPlanFormFeedback({
  fieldErrors,
  submitError,
}: {
  fieldErrors: Record<string, string>
  submitError: string | null
}) {
  const messages = [...new Set(Object.values(fieldErrors))]
  if (messages.length === 0 && !submitError) return null
  return (
    <>
      {messages.length > 0 && (
        <ul role="alert" className="list-disc pl-5 text-sm text-destructive">
          {messages.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      )}
      {submitError && (
        <p role="alert" className="text-sm text-destructive">
          {submitError}
        </p>
      )}
    </>
  )
}
