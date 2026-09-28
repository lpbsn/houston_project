---
name: hygiene-pass
description: Remove leftovers and inconsistencies introduced by the actual change without altering validated behavior or architecture.
disable-model-invocation: true
---

# Hygiene pass

Clean the delivered change, not the surrounding repository.

Read the applicable `AGENTS.md`, determine the actual changed scope, and inspect only the implementation, tests, migrations, generated consequences, and documentation materially affected by it.

Remove objectively unnecessary leftovers introduced by the change: dead code, unused imports or exports, stale branches or comments, debugging scaffolding, temporary helpers or guards, obsolete compatibility paths, orphaned tests, and documentation made obsolete by the final implementation.

Remove duplication only when the change itself introduced another implementation of a responsibility that already has a clear owner.

Do not change validated behavior, architecture, ownership, contracts, or product semantics.

Do not redesign abstractions, introduce new factoring, broaden scope, or clean adjacent legacy code. If hygiene exposes a structural defect, report it instead of turning this workflow into a refactor.

Hygiene is not stylistic normalization. Do not rename, reformat, reorder, move, or reorganize unaffected code merely for consistency.

Do not remove apparently redundant behavior unless repository evidence shows that no active consumer, persisted data, migration path, deployment constraint, or runtime behavior still requires it.

Do not merge Web desktop and Native/mobile implementations merely to reduce duplication. Preserve intentional surface-specific presentation and interaction.

Do not collapse specialized service, selector, feature, or surface owners into generic modules for superficial simplicity.

Do not remove tests or documentation merely because they look old. Remove or consolidate them only when the current change makes them objectively obsolete, invalid, or redundant.

Inspect generated artifacts when relevant, but never hand-edit them. Correct their owning source and regenerate them through the established workflow when required.

Prefer deleting accidental complexity over adding abstractions during cleanup.

Inspect the complete resulting diff after cleanup and confirm that it contains no temporary scaffolding, contradictory paths, or accidental scope expansion introduced by the change.

Validate only hygiene edits that could affect behavior or repository checks. If no files change, do not run validation solely to satisfy the workflow.

Output:

## Findings

Report only meaningful leftovers, inconsistencies, or structural issues found in the changed scope.

## Cleaned

Summarize cleanup performed. Omit when no changes were needed.

## Validation

Report only checks actually performed and their outcome.

## Risks / not verified

Include only meaningful remaining uncertainty or issues that require another workflow.