---
name: implement-changes
description: Implement an approved or clearly scoped change using the repository's current ownership and validate the resulting behavior.
disable-model-invocation: true
---

# Implement changes

Implement the requested change.

Read the applicable `AGENTS.md`, then inspect the owning implementation, relevant dependencies, consumers, and existing tests needed to understand the realistic blast radius before editing.

If a validated plan exists, treat its product, architectural, and behavioral decisions as constraints.

Do not follow a technical detail mechanically when repository evidence shows that it conflicts with current ownership or would preserve a structurally poor solution. Adapt the implementation to the repository and report the deviation.

A validated plan is not required for a clearly scoped local change.

Implement the smallest coherent solution at the appropriate owner. If the directly affected abstraction is the root cause, correct it rather than adding another local workaround.

Reuse existing code when it owns the same responsibility. Do not introduce unrelated refactors, speculative abstractions, compatibility layers, dual paths, rollout machinery, or infrastructure without a demonstrated requirement.

Do not preserve hypothetical legacy behavior. Respect real persisted data, active consumers, published contracts, and deployment constraints when they exist.

When shared product behavior changes, inspect every affected surface and runtime owner. Do not patch only the Web, desktop, or Native surface where the problem was first observed.

Do not duplicate feature logic across Web desktop and Native/mobile when the responsibility can remain shared. Split only presentation or interaction that genuinely differs by surface.

When behavior is contract-like, preserve or deliberately update its semantics end to end, including ordering, visibility, pagination, navigation, cache behavior, and lifecycle where relevant.

Resolve non-blocking technical ambiguity from repository evidence and continue. Ask the human only when a genuine product or architectural decision cannot be derived safely.

Do not overwrite, absorb, or clean unrelated user changes.

Validate the changed behavior first, then expand validation according to the realistic blast radius.

Inspect the complete final diff before finishing, including generated artifacts, migrations, renamed or removed files, and affected tests. Remove accidental scope creep, duplicated responsibility, dead compatibility code, and implementation leftovers introduced by the change.

Do not report validation as complete when relevant device, runtime, migration, production-data, or external-provider behavior was not exercised.

The work is complete when the requested behavior is implemented, proportionately validated, and remaining uncertainty is explicitly reported.

Output:

## Changed

Summarize the implemented behavior and any meaningful deviation from the validated plan.

## Validated

Report only validation actually performed and its outcome.

## Risks / not verified

Include only meaningful remaining uncertainty or behavior not exercised.