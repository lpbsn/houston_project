---
name: review-changes
description: Review the delivered change against its validated intent, correct confirmed defects within scope, and validate the final state before commit.
disable-model-invocation: true
---

# Review changes

Review the delivered change, not the surrounding repository.

Read the applicable `AGENTS.md`, then determine the intended behavior from the explicit user request and any validated plan or decisions.

Determine the actual review target from that intent first. Otherwise use the relevant Git evidence. For branch review, inspect the change that would actually merge from the appropriate merge base rather than assuming the last commit is the target.

Inspect the complete relevant change before correcting anything, including added, removed, renamed, generated, migrated, tested, and documented consequences.

Use surrounding implementation, consumers, contracts, and tests as evidence needed to judge the change. They are not additional cleanup scope.

Review depth should follow semantic risk rather than diff size.

Treat something as a defect only when repository evidence shows that the change introduces or exposes a meaningful correctness, security, integrity, contract, performance, scalability, or maintainability problem that should be fixed within the validated intent.

Do not report stylistic preference, hypothetical improvement, unrelated legacy debt, or an alternative architecture as a defect.

Verify suspected defects against the owning code, relevant call sites, contracts, or tests before correcting them.

Correct confirmed defects directly when the required fix follows from already validated product behavior and architecture.

Do not silently change product behavior, reopen architectural decisions, introduce a new architecture, broaden feature scope, or clean unrelated code.

If a confirmed defect requires a new product or architectural decision, leave it unresolved and report it.

For Spore cross-layer changes, verify every affected owner and surface necessary to preserve the intended behavior. Pay particular attention when relevant to tenant isolation, feed semantics, API contracts, persisted data and migrations, concurrency, TanStack Query/cache ownership, navigation, realtime, Native/Web behavior, and AI/provider boundaries.

Do not accept a local workaround when the change demonstrably extends the same broken concept it was intended to correct. Fix the narrowest owning abstraction that remains inside scope.

After confirmed defects are understood, apply coherent corrections, then inspect the complete resulting diff again.

Rerun validation proportionate to the final semantic blast radius. Report only checks actually performed.

Do not claim device, runtime, production-data, migration, concurrency, or external-provider behavior was validated unless it was exercised.

Stop when the final change is safe within the validated scope or when a remaining issue genuinely requires human decision.

Output:

## Findings

Report only unresolved defects or decisions. If none remain, say so briefly.

## Corrected during review

Summarize meaningful corrections made by the review. Omit when none were required.

## Validation

Report the validation actually performed and its result.

## Risks / not verified

Include only meaningful remaining uncertainty.

## Verdict

Use exactly one:

- `OK to commit`
- `Not safe`