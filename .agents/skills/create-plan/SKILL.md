---
name: create-plan
description: Analyze a requested change against the repository and produce a bounded, implementation-ready plan without modifying files.
disable-model-invocation: true
---

# Create plan

Work strictly read-only. Do not edit files, implement code, create migrations, or apply fixes while investigating.

Read the applicable `AGENTS.md`, then inspect only the implementation, tests, contracts, consumers, and specialized documentation needed to understand the requested outcome and realistic blast radius.

Establish the observable outcome and success criteria before choosing an implementation approach.

Find the current owning boundaries. Follow responsibilities and dependencies rather than directory breadth, and inspect meaningful consumers when a shared abstraction or contract may change.

Use repository evidence to choose the technical approach. Treat validated product and architectural decisions as constraints unless new evidence makes them inconsistent or impossible.

If a requested technical approach conflicts with the repository, preserves a broken concept, or creates avoidable structural debt, propose the better repo-compatible approach and explain the deviation briefly.

Plan the root-cause correction at the narrowest appropriate owner. Prefer the smallest coherent solution, not the smallest diff or another local workaround.

Identify real compatibility constraints from active consumers, persisted production data, deployment boundaries, or published contracts. Do not invent compatibility work for hypothetical legacy behavior.

Do not assume unverified existing APIs, helpers, services, hooks, or abstractions. New modules or abstractions may be proposed only when the requested change and repository evidence justify a clear owner.

Do not split work into phases, PRs, or lots by default. Decompose only when it materially reduces risk, clarifies ownership, or creates independently coherent validation boundaries.

State non-goals only when they materially protect the scope from adjacent work.

The plan is complete when an implementation agent can execute it without repeating the product, ownership, or architectural analysis.

Output:

## Outcome

State the intended behavior and relevant success criteria.

## Repository findings

Include only findings that materially determine the implementation approach.

## Implementation plan

Describe the ordered changes through their verified owners and important cross-layer consequences.

## Risks / trade-offs

Include only meaningful implementation, compatibility, performance, data, security, or maintenance risks.

## Validation

Describe how the resulting behavior should be validated, proportionate to the blast radius.

## Open questions

Include only genuine unresolved product or architectural decisions that block a correct plan.

Stop after the plan and wait for human validation.