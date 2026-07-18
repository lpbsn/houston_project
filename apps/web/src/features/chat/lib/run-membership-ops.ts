export type MembershipOpTarget = {
  membershipId: string
  displayName: string
}

export type MembershipOpFailure = MembershipOpTarget & {
  reason: string
}

export type MembershipOpsResult = {
  successCount: number
  failures: MembershipOpFailure[]
}

function resolveOpErrorReason(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim()
  }
  return 'Une erreur est survenue.'
}

export async function runSequentialMembershipOps(options: {
  targets: MembershipOpTarget[]
  run: (membershipId: string) => Promise<void>
}): Promise<MembershipOpsResult> {
  let successCount = 0
  const failures: MembershipOpFailure[] = []

  for (const target of options.targets) {
    try {
      await options.run(target.membershipId)
      successCount += 1
    } catch (error) {
      failures.push({
        ...target,
        reason: resolveOpErrorReason(error),
      })
    }
  }

  return { successCount, failures }
}

export function formatMembershipOpsSummary(
  result: MembershipOpsResult,
  verbs: { successSingular: string; successPlural: string },
): string {
  const successLabel =
    result.successCount === 1
      ? `1 ${verbs.successSingular}`
      : `${result.successCount} ${verbs.successPlural}`

  if (result.failures.length === 0) {
    return successLabel
  }

  const failureDetails = result.failures
    .map((failure) => `${failure.displayName} : ${failure.reason}`)
    .join(' ; ')

  if (result.successCount === 0) {
    return `${result.failures.length} échec${result.failures.length > 1 ? 's' : ''} : ${failureDetails}`
  }

  return `${successLabel}. ${result.failures.length} échec${
    result.failures.length > 1 ? 's' : ''
  } : ${failureDetails}`
}
