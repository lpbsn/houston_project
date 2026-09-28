---
name: docs-review
description: Review the documentation impact of the actual change and update only documentation whose intended meaning is materially affected.
disable-model-invocation: true
---

# Docs review

Review the documentation impact of the actual change, not the documentation tree in general.

Do not modify product code.

Read the applicable `AGENTS.md`, determine the validated behavior and actual change, then identify only documentation whose intended purpose may be affected.

Use owning implementation, tests, and published contracts to verify current behavior. Documentation is supporting context, not authority over contradictory implementation.

Before editing documentation, determine whether any implementation/documentation mismatch comes from an intentional validated change or from a product-code defect. Report suspected product defects instead of documenting them as intended behavior.

A documentation obligation exists only when the validated change makes an existing documented claim false or incomplete, or introduces durable behavior that the repository already expects to document at that level.

Missing documentation is a defect only when there is a clear documentation owner or established repository expectation for that behavior.

Do not document internal implementation details merely because files, helpers, modules, or plumbing changed.

Preserve generalized rules and current truth, not the history of the issue, PR, lot, workaround, or incident that revealed them.

Prefer one clear documentation owner per concept. Do not duplicate the same rule across multiple documents without a distinct audience or responsibility.

When existing documentation is obsolete, misleading, or contradicted by the validated change, replace or remove it rather than layering another explanation on top.

Respect the document's role:

- architecture/domain docs describe durable behavior and ownership;
- operational docs describe commands and procedures developers or operators must actually follow;
- product-state docs describe an intentional point-in-time state.

Do not update product-state snapshots for refactors, internal plumbing, transient work-in-progress, or implementation detail. Update them only when the user-visible or operational state they claim to summarize has materially changed.

Do not use documentation to justify or normalize a confusing implementation when the change should instead be corrected at its owner.

Do not broaden the task into unrelated documentation cleanup.

If no documentation obligation exists, make no documentation change.

After editing, reread the affected sections in context and check links, terminology, ownership, and contradictions with nearby authoritative documentation.

Run documentation validation only when the repository provides a relevant check and the change justifies it.

Output:

## Findings

Report only meaningful documentation gaps, inaccuracies, contradictions, confirmed absence of documentation impact, or product-code issues discovered while reconciling documentation.

## Changed

Summarize meaningful documentation updates, removals, or consolidations. Omit when none were needed.

## Validation

Report checks actually performed and their outcome.

## Risks / not verified

Include only meaningful remaining uncertainty.