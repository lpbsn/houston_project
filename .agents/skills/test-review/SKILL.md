---
name: test-review
description: Review and improve the tests for the actual change without modifying product code.
disable-model-invocation: true
---

# Test review

Review the testing strategy for the actual change, not the surrounding test suite.

Do not modify product code. You may add, remove, consolidate, or correct tests and test helpers when needed.

Read the applicable `AGENTS.md`, determine the intended behavior and actual change, then inspect existing coverage at the owning layers.

Use surrounding tests and implementation only as evidence needed to judge coverage. They are not additional cleanup scope.

Review test depth according to product risk, not diff size, file count, or coverage percentage.

A coverage gap exists only when a meaningful failure mode introduced or affected by the change is not already protected at an appropriate layer.

Prefer one owning test layer per risk by default. Add another layer only when it protects a distinct boundary or failure mode.

Test observable behavior, contracts, permissions, lifecycle, state, integration boundaries, and critical regressions rather than internal implementation shape.

Extend existing parameterized suites, matrices, corpora, helpers, or focused test files when they already own the invariant.

Do not create duplicate tests for the same rule merely because multiple layers expose it.

Remove or consolidate tests only when the current change makes them directly redundant, misleading, or invalid. Do not turn this workflow into historical test cleanup.

Prefer deterministic tests. Avoid real time, external providers, incidental ordering, styling details, or unstable implementation coupling when the same product risk can be protected more directly.

For Spore backend changes, test tenant isolation, lifecycle, feed semantics, persisted-data behavior, concurrency, async/realtime, and external contracts at the layer that actually owns the relevant failure mode.

For Spore frontend changes, keep shared product behavior coverage shared. Add separate Web or Native coverage only when runtime, navigation, persistence, layout behavior, or interaction genuinely diverges.

Running validation does not imply new tests are required. Runtime, device, migration, production-data, or provider behavior may require validation outside the automated suite.

If testing reveals an objective product-code defect, report it instead of fixing product code in this workflow.

Use targeted test execution first, then broaden only according to the realistic blast radius.

Output:

## Coverage findings

Report only meaningful coverage gaps, duplication, fragility, or invalid assumptions relevant to this change.

## Test changes

Summarize tests or test helpers added, corrected, consolidated, or removed. Omit when none were needed.

## Validation

Report only tests and checks actually run and their result.

## Product issues found

Include only objective product-code defects revealed by testing. Omit when none were found.

## Risks / not verified

Include only meaningful remaining uncertainty.