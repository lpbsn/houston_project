# Agent Configuration Refactor — Design Brief

**Status:** Temporary design brief  
**Purpose:** Input for the current Cursor agent-configuration refactor  
**Product:** Spore  
**Repository / technical name:** Houston  
**Authority:** This document is not an implementation source of truth. It captures validated human design constraints and the current target hypothesis for the refactor.  
**Lifecycle:** Remove or archive this document once the refactor is implemented, validated, and the resulting configuration becomes the source of truth.

---

## 1. Objective

Refactor the repository's Cursor agent configuration so that agents receive:

- less irrelevant context;
- stronger relevant guardrails;
- clearer workflow and authority boundaries;
- better Spore-specific architectural understanding;
- fewer duplicated instructions;
- fewer stale implementation details;
- better resistance to configuration drift;
- simpler day-to-day workflows for a solo developer.

The objective is **not** to maximize the number of Cursor features used.

Prefer the smallest durable configuration that correctly represents Spore, its architecture, and its development workflows.

When two approaches solve the same problem equally well, prefer:

1. fewer files;
2. less permanent context;
3. less duplication;
4. less maintenance;
5. fewer speculative abstractions.

---

## 2. Scope of the refactor

The audit and refactor must cover at least:

- `AGENTS.md`
- `apps/api/AGENTS.md`
- `apps/web/AGENTS.md`
- `.cursor/**`
- `.agents/**`
- `scripts/agent_config_check.py`
- relevant CI configuration for agent-config checks
- relevant ignore/indexing configuration
- architecture/docs/code/tests only when necessary to verify configuration claims

The refactor must inspect the real repository before proposing changes.

Do not preserve an instruction merely because it already exists.

---

# Part I — Validated Design Constraints

The following principles have already been discussed and validated. Treat them as design requirements unless the actual repository exposes a serious contradiction that must be raised explicitly.

---

## 3. Core context strategy

Agent configuration should teach agents **where to find truth**, rather than duplicate all repository knowledge.

Use this exploration principle:

> **Explore proportionally to the blast radius. Follow ownership and dependencies, not directory breadth. Ask the human only when the remaining uncertainty is a real product or architectural decision that cannot be resolved from the repository.**

Agents should not scan the entire repository by default.

When planning or modifying a change, they should:

- identify the relevant entry points;
- read the applicable `AGENTS.md`;
- inspect the owning implementation;
- inspect existing tests;
- follow dependencies and consumers when the blast radius requires it;
- inspect API/schema/cache/realtime/RBAC implications when relevant;
- consult docs only when they materially help understand architecture or intent.

When modifying a shared abstraction, agents must inspect its meaningful current consumers before proposing or implementing changes.

---

## 4. Source-of-truth hierarchy

Configuration must distinguish between stable policy and volatile repository facts.

Practical authority order:

1. owning implementation code;
2. owning tests;
3. generated contracts such as OpenAPI when applicable;
4. stable agent policies and architectural invariants;
5. living architecture/product documentation;
6. Git history.

Documentation and agent configuration must not replace inspection of the real implementation when behavior matters.

If descriptive configuration conflicts with current code or tests:

- verify the current implementation;
- identify the drift;
- do not blindly preserve stale instructions;
- distinguish between a stale description and a deliberate stable policy.

Prefer durable invariants in `AGENTS.md` and Rules over volatile descriptions of specific implementation details.

---

## 5. Spore product context

Spore is the product/UI name. Houston remains the technical repository/backend name where applicable.

Spore has a stable operational loop approximately:

**Observation → Signal → Action Plan → Execution → Validation → Feed update**

This core loop may be retained as durable product context.

Detailed lifecycle rules, exact statuses, permissions, pipeline ownership, and domain-specific implementation details must be discovered from the owning backend implementation and tests rather than copied extensively into agent configuration.

Do not create domain Skills such as:

- `observations-skill`
- `signals-skill`
- `action-plans-skill`

unless the actual repository demonstrates a substantial, stable, reusable specialized procedure that justifies one.

---

## 6. Solo-developer and project-phase context

The project currently has a solo developer and is pre-commercial / before broad real-world usage.

Do **not** encode "production has no real users/data" as a permanent global invariant.

That fact can become false quickly.

Instead preserve the durable principle:

> **Do not introduce compatibility layers, rollout mechanisms, backfills, dual paths or transitional architecture for hypothetical consumers or data. Preserve compatibility only when the repository or the task demonstrates an existing requirement.**

Temporary permissions such as destructive migrations or direct schema changes should come from the current task or project-phase context when applicable.

Do not pay complexity for hypothetical compatibility.

---

## 7. Scalability and realistic growth

Spore is expected to move from real-world testing to commercial usage and support an increasing number of users, establishments, observations, signals, analytics data, background jobs, and realtime activity.

The codebase must be **scale-aware now**, without introducing speculative hyperscale infrastructure.

Core principle:

> **Do not pay complexity for hypothetical hyperscale, but do not accept implementations whose cost grows poorly with realistic product adoption.**

Agents should be critical about relevant issues such as:

### Backend / database

- N+1 queries;
- unbounded collections;
- missing pagination where data can grow;
- repeated queries;
- inefficient Python-side aggregation when the database is the appropriate owner;
- filters/sorts on growing tables;
- useful indexes based on real access patterns;
- unnecessarily long transactions;
- lock/contention risks;
- oversized API payloads;
- synchronous work that genuinely belongs in async processing.

### Async / realtime

- unbounded fan-out;
- large serialized business snapshots;
- retries;
- idempotency;
- task volume;
- unnecessary repeated work;
- Redis misuse.

### Frontend

- duplicated queries;
- unnecessarily broad invalidation;
- avoidable refetches;
- loading very large datasets into the browser;
- unbounded lists;
- Analytics flows that pull full histories when aggregation/bounding is more appropriate.

Prefer simple designs with good scaling characteristics.

Do not prematurely introduce:

- distributed systems;
- read replicas;
- event streams;
- complex caching;
- sharding;
- data warehouses;
- extra infrastructure

unless demonstrated constraints justify them.

---

## 8. Abstractions and refactors

Prefer the smallest change that fits the existing architecture.

> **Introduce an abstraction only when the current change proves a stable shared responsibility.**

Before creating a new abstraction:

- inspect existing patterns;
- identify real current consumers;
- verify that the abstraction solves demonstrated duplication or responsibility sharing;
- avoid designing for hypothetical future callers.

Do not introduce:

- generic adapters;
- extra interfaces;
- feature flags;
- compatibility layers;
- generic providers;
- new service layers

only because they may be useful later.

A local implementation is preferable when it is simpler and sufficient.

Refactoring outside the current scope is allowed only when required for correctness, testability, or architectural consistency of the current change.

---

# Part II — Configuration Responsibility Model

---

## 9. `AGENTS.md`

`AGENTS.md` files contain:

- durable repository-specific architecture;
- stable ownership boundaries;
- important invariants;
- sources of truth;
- pointers toward specialized context.

They must **not** become:

- workflow prompts;
- long procedural checklists;
- copies of detailed docs;
- volatile maps of implementation files/functions;
- exhaustive testing guides.

Current expectation is to retain:

- `AGENTS.md`
- `apps/api/AGENTS.md`
- `apps/web/AGENTS.md`

Their exact content must be challenged and reduced where necessary.

---

## 10. Rules

Rules are scarce automatic guardrails.

A Rule deserves to exist only when:

1. forgetting the instruction could realistically produce an incorrect Spore implementation; and
2. the instruction must automatically appear in a particular context.

> **Rules are scarce automatic guardrails, not documentation. Prefer no Rule over a weak or redundant Rule.**

Default:

- no `alwaysApply` Rules unless strongly justified;
- prefer scoped / auto-attached Rules;
- keep Rules short and normative;
- do not write tutorials in Rules.

Do not create generic Rules such as:

- React best practices;
- Django best practices;
- clean code;
- generic security;
- generic performance.

Current Rule candidates:

- `api-contract.mdc`
- `responsive-surfaces.mdc`

Both remain hypotheses and must be challenged against the actual repository.

---

## 11. Skills

Skills are scarce, dynamically loaded expertise.

A Skill deserves to exist when a recurring task requires:

- substantial Spore-specific knowledge;
- a reusable diagnostic or procedural workflow;
- knowledge that should not pollute persistent context.

> **Skills provide expertise, not authority.**

A Skill must respect the active Command's permissions and scope.

Do not create a Skill merely because a domain is important.

Do not create Skills for generic framework knowledge.

Do not copy large documentation into `SKILL.md`.

Prefer a Skill structure such as:

- purpose;
- decision/diagnostic procedure;
- Spore-specific traps;
- where to inspect;
- canonical commands;
- links to authoritative references.

Scripts or hooks inside Skills should be introduced only when they automate a repetitive, deterministic, error-prone procedure that cannot be handled cleanly with normal agent tooling.

No hooks should be introduced merely because Cursor supports them.

Current Skill candidates:

### `native-runtime-debug`

Potentially justified for genuinely specialized Web/Capacitor/native problems involving:

- iOS viewport behavior;
- keyboard behavior;
- safe areas;
- native lifecycle;
- Web vs Native runtime differences;
- runtime-specific network/realtime behavior.

It must **not** become a generic mobile frontend Skill.

### `testing-spore`

Potentially justified if Spore has a real repository-specific testing decision procedure involving:

- risk ownership;
- backend layer selection;
- frontend layer selection;
- existing coverage inspection;
- weak-test removal;
- query/cache integration;
- cross-stack contract validation.

If the Skill would merely say "read `testing.md`", it should not exist.

Do not add more Skills unless the repository strongly demonstrates the need.

A Skill should be removable later if its knowledge becomes:

- trivial;
- duplicated;
- obsolete;
- better enforced by tooling.

---

## 12. Commands

Commands represent explicit human workflow and authority.

They should define:

- the user's intent;
- what the agent is authorized to do;
- where the workflow stops;
- task-specific output expectations.

Commands must not duplicate all Spore architecture, security, responsive, testing, API, or backend guidance.

Current target workflows:

- `create-plan`
- `implement-changes`
- `review-changes`
- `hygiene-pass`
- `test-review`
- `docs-review`

Specialized historical commands should disappear when their concerns are better represented by Rules or Skills.

---

# Part III — Command Semantics

---

## 13. `create-plan`

`create-plan` is strictly read-only.

It may:

- inspect code;
- inspect tests;
- inspect Git;
- inspect relevant docs;
- inspect architecture;
- follow ownership and dependencies;
- challenge the requested approach;
- ask genuinely blocking product/architecture questions.

It must never:

- edit a file;
- start implementation;
- perform a small fix while investigating;
- silently create code or migrations.

The output must be an implementation-ready plan, followed by a stop for human validation.

A good plan should cover:

- objective;
- relevant current behavior/architecture;
- concrete affected areas/files when known;
- proposed changes and ownership;
- impacts and risks;
- tests/validation;
- out of scope;
- genuinely blocking remaining questions.

Do not invent unverified:

- helpers;
- APIs;
- abstractions;
- hooks;
- services;
- files.

Core principle:

> **A plan must be implementation-ready without being implementation itself. It should reduce uncertainty, not simulate coding in prose.**

A plan is ready when it makes clear:

- what changes;
- where;
- why;
- how correctness will be validated.

---

## 14. `implement-changes`

If a validated plan exists in the conversation:

- treat its product and architectural decisions as constraints;
- follow it unless repository reality invalidates a technical assumption;
- adapt technical details when necessary;
- do not silently reopen validated decisions.

A validated plan is not mandatory for a clearly scoped trivial/local implementation request.

Implementation should:

- use the smallest change fitting the architecture;
- reuse existing patterns;
- avoid speculative abstractions;
- validate proportionally to the blast radius.

---

## 15. `review-changes`

Determine scope from:

1. explicit user intent;
2. Git state and branch context.

Do not assume the last commit is always the target.

Before correcting anything:

- inspect the whole relevant diff;
- understand added/removed/renamed files;
- understand migrations;
- inspect tests/docs/generated consequences where relevant;
- expand into surrounding code only as required to understand ownership and blast radius.

Review for:

- correctness;
- regressions;
- architecture;
- API/contracts;
- RBAC/security/integrity;
- database/query behavior;
- cache behavior;
- async/realtime;
- realistic scalability;
- frontend surface behavior;
- tests/docs when relevant.

Correct objective defects directly.

Do not silently introduce new product or architectural decisions.

After corrections:

- inspect the final diff again;
- rerun appropriate validations.

---

## 16. `hygiene-pass`

Only clean code directly made obsolete or noisy by the current change.

Allowed examples:

- imports made unused by the change;
- helper made obsolete by the change;
- transitional branch made unnecessary by the change;
- duplication introduced by the change;
- stale comments directly invalidated by the change.

Out of scope:

- unrelated historical debt;
- nearby refactors;
- cleanup "while here";
- stylistic rewrites.

---

## 17. `test-review`

Review test quality for the current change.

Start with:

1. risk;
2. ownership layer;
3. existing coverage.

Prefer:

- strengthening existing useful tests;
- deleting weak/redundant tests;
- adding missing coverage at the appropriate layer.

Do not optimize for:

- number of tests;
- coverage percentage;
- duplicated integration tests.

Tests should prove product/technical risk, not implementation trivia.

---

## 18. `docs-review`

Review living documentation directly affected by the current change.

Update docs when the change makes them:

- false;
- incomplete;
- misleading.

Do not document implementation noise.

Do not rewrite historical/archive material merely to reflect the present.

For living docs, prefer:

- replacing stale content;
- removing obsolete instructions;
- simplifying;
- deleting misleading history.

Git is the history.

---

# Part IV — Git and Scope Handling

---

## 19. Current change scope

Use user intent first.

If no explicit scope is provided, derive it carefully from Git.

Possible sources include:

- working tree;
- staged + unstaged changes;
- current branch vs relevant base;
- last commit only when context clearly indicates it is the intended change.

Respect unrelated user work.

> **Do not revert, absorb, reformat, clean, or modify unrelated existing changes.**

Generated files should be inspected for expected consequences, but their generator/input remains the source of truth.

All review-oriented Commands should operate on the same task scope while examining different dimensions of it.

---

# Part V — Frontend Product Architecture

---

## 20. One integrated frontend, multiple usage contexts

Spore is one integrated React application.

It has two important usage contexts.

### Terrain

Terrain workflows are primarily used on mobile.

They should:

- be mobile-first;
- prioritize touch ergonomics;
- work well on constrained screens;
- remain fully usable responsively on desktop.

### Analytics / management

Analytics and management experiences are primarily used on desktop.

They should:

- use desktop space appropriately;
- support information-dense interfaces when appropriate;
- not be artificially constrained into phone-style layouts;
- remain coherent and reasonably responsive on smaller screens.

Core principle:

> **Mobile-first does not mean mobile-only.**

Do not create separate mobile and desktop frontends.

Before changing UI, identify which product surface is being modified.

---

## 21. Frontend interaction quality

Frontend changes should consider the interaction modes appropriate to the affected surface.

Relevant concerns include:

- touch;
- mouse;
- keyboard;
- accessibility fundamentals;
- touch target size;
- no hover-only critical actions;
- correct interactive semantics;
- focus behavior;
- existing UI primitives;
- loading states;
- empty states;
- error states;
- forbidden/unauthorized states;
- disabled states;
- degraded/offline states only when relevant.

A frontend change is not complete merely because the nominal screen renders.

Visual behavior that cannot be automatically validated must be listed explicitly as not validated.

---

## 22. Responsive guardrail

The current hypothesis is that stable frontend context belongs in `apps/web/AGENTS.md`, with a short scoped Rule such as `responsive-surfaces.mdc` for automatic UI guardrails.

The Rule should focus on:

- identifying Terrain vs Analytics/management;
- respecting the primary usage context;
- preserving usability on the secondary viewport class;
- reusing existing shells/layout conventions;
- avoiding separate desktop/mobile implementations;
- considering touch/mouse/keyboard;
- validating materially affected viewports.

It must not become a generic CSS/Tailwind guide.

The exact need, name, and globs must be challenged against the current frontend structure.

---

## 23. Web / Native runtime

Spore uses one frontend codebase with Web and Native/Capacitor runtimes.

Do not reintroduce PWA assumptions if the repository no longer targets PWA architecture.

General frontend context should not be polluted with deep runtime debugging procedure.

This is the rationale for the `native-runtime-debug` Skill candidate.

Verify the actual runtime/build architecture before defining its final responsibility.

---

# Part VI — Backend Architecture and Integrity

---

## 24. Backend ownership

Keep stable backend ownership principles in `apps/api/AGENTS.md`.

Where confirmed by the repository, preserve principles such as:

- backend owns business rules;
- services own writes/workflows;
- selectors own reads;
- permissions own authorization/RBAC;
- HTTP views remain orchestration;
- serializers validate/represent rather than own workflows;
- frontend permission logic is UX only;
- transaction boundaries matter.

Do not retain large volatile maps of which exact function currently owns every workflow step.

---

## 25. Security and data integrity

Security and integrity are durable invariants and should primarily live in AGENTS rather than a generic dedicated security Rule.

Agents should understand:

- backend owns authorization;
- tenant/establishment isolation must be preserved;
- frontend visibility is not security;
- role/membership/establishment scope must be respected;
- sensitive payloads should be minimized;
- raw observations/private media/tokens/sensitive AI context must not be unnecessarily exposed;
- async and realtime paths must preserve access and integrity;
- destructive actions must consider references, auditability, analytics, and related workflows.

Core principle:

> **Enforce authorization, tenant isolation and data integrity at the backend ownership layer. Treat frontend restrictions as UX only. Minimize sensitive data exposure across API, realtime, async jobs, uploads and AI workflows.**

---

## 26. Database and schema evolution

Schema changes must consider:

- data integrity;
- realistic growth;
- access patterns;
- cardinality;
- constraints;
- uniqueness;
- nullability;
- cascades;
- indexes when justified;
- query consequences;
- migration impact.

Do not automatically build multi-step compatibility migrations or backfills for hypothetical production data.

When destructive changes are acceptable in the current project phase:

- identify them explicitly;
- understand what is lost or invalidated;
- prefer the simplest direct migration compatible with actual constraints.

Core principle:

> **Design schema changes for integrity and realistic growth. Preserve existing data only when current data or deployment constraints require it; otherwise prefer the simplest direct migration.**

---

# Part VII — Cross-Stack Contracts

---

## 27. API contracts

Treat actual API contract changes end-to-end.

When external request/response semantics change, consider:

**backend owner → backend validation/tests → OpenAPI/schema → generated frontend artifacts → affected client/query/hooks → UI/cache behavior**

Do not manually edit generated contract artifacts.

Do not trigger this whole workflow for internal backend changes when the external contract is unchanged.

The current hypothesis is that this belongs in a short scoped `api-contract.mdc` Rule.

Challenge whether a Rule is in fact the best representation.

---

# Part VIII — Async, Realtime and AI

---

## 28. Async jobs and lifecycle

Business state transitions belong to backend domain ownership.

Async jobs execute durable work from committed state.

Relevant invariants:

- side effects should respect transaction commit boundaries;
- Celery should generally work from durable IDs/current database state;
- stale serialized business snapshots should be avoided;
- retries should be bounded;
- tasks should be reasonably idempotent;
- tenant/access context must remain correct;
- jobs must not create duplicate business side effects.

---

## 29. Realtime

Realtime propagates changes but does not own business truth.

The API/database remain the source of server state.

Agents should consider:

- access scope;
- payload minimization;
- bounded fan-out;
- cache invalidation consequences;
- reconnect behavior;
- avoiding realtime as a parallel business state store.

Do not create a dedicated realtime Skill unless the repository demonstrates a substantial recurring specialized diagnostic workflow.

---

## 30. AI workflows

AI output is untrusted external input.

Agents working on AI flows should:

- minimize data sent to providers;
- prefer structured validated outputs when applicable;
- keep business invariants in backend code;
- distinguish provider failure from invalid output and business validation failure;
- support bounded retries;
- avoid duplicate side effects;
- maintain coherent permanent-failure product state when necessary;
- avoid unnecessary repeated model calls;
- avoid oversized prompt/context payloads;
- avoid logging sensitive raw payloads.

Do not create an AI Skill unless the repository demonstrates a substantial stable specialized procedure that would benefit from dynamic loading.

---

# Part IX — Observability

---

## 31. Failure visibility

Important workflows must fail visibly and diagnosably.

Prefer:

- meaningful errors;
- useful contextual identifiers;
- bounded retries;
- explicit failure states where product behavior requires them.

Avoid:

- silent exceptions;
- `except Exception: pass`;
- opaque fallback behavior;
- infinite/unbounded retries;
- sensitive payload logging.

Core principle:

> **Log identifiers and state transitions, not sensitive payloads.**

Do not add generic tracing, metrics, dashboards, or monitoring infrastructure to every change.

When a path is critical or expected to scale, agents should consider whether future failures/performance problems will be diagnosable.

---

# Part X — Dependencies and Technology Choices

---

## 32. Dependencies

Prefer existing project capabilities over new dependencies.

Before adding a package:

- inspect whether the existing stack already solves the problem;
- justify why the package materially reduces complexity or risk;
- consider maintenance;
- consider bundle/runtime impact;
- consider security;
- consider Web/Native compatibility for frontend dependencies;
- consider current Docker/runtime constraints for backend dependencies.

Any new dependency proposed in `create-plan` must be explicit and justified.

Do not replace an existing technology or architecture without demonstrated benefit.

Examples of existing architectural choices that must not be bypassed casually include routing, state management, API clients, realtime mechanisms, and backend service ownership.

---

# Part XI — Validation Strategy

---

## 33. Proportional validation

Validation should scale with blast radius.

Start with targeted checks for the changed behavior.

Then expand to likely consumers and affected systems when appropriate.

Core principle:

> **Validate the changed behavior first, then the likely blast radius.**

Broader validation is justified for changes involving shared abstractions, auth, routing, cache, API contracts, permissions, runtime, async/realtime, schema, or other cross-cutting behavior.

Do not run the full repository suite mechanically for every small change.

---

## 34. Explicit validation reporting

Agents must distinguish between:

- automated checks that passed;
- automated checks that failed;
- behavior not covered by automation;
- manual/physical validation still required.

Do not claim correctness from green tests alone.

Examples of potentially manual validation:

- responsive visual behavior;
- physical iOS keyboard behavior;
- safe areas;
- desktop Analytics density/layout;
- native lifecycle behavior.

Output should clearly state what was and was not validated.

---

# Part XII — Documentation Strategy

---

## 35. Documentation categories

Distinguish between:

### Living / authoritative docs

Expected to describe the current system accurately.

### Roadmaps / temporary design docs

May describe a migration, future direction, or intermediate state.

### Historical / archived docs

Should not be rewritten merely to reflect the current system.

---

## 36. Documentation maintenance

Update documentation when a change makes living docs:

- false;
- incomplete;
- misleading.

Do not document implementation noise.

Do not accumulate historical prose such as "previously X, now Y" in living docs when the old information has no operational value.

Delete stale content where appropriate.

Git is the history.

---

# Part XIII — Critical Agent Behavior

---

## 37. Challenge meaningful decisions

Cursor should act critically, not as a blind executor.

Challenge decisions with meaningful consequences for:

- product behavior;
- architecture;
- security;
- data integrity;
- scalability/performance;
- maintainability;
- frontend usability.

Do not create friction over equivalent implementation details or style preferences.

Challenges must be anchored in the actual repository.

Do not reopen validated human decisions without new evidence from the repository.

Core principle:

> **Be critical where consequences matter, pragmatic where alternatives are equivalent, and do not reopen validated decisions without new evidence from the repository.**

---

## 38. Contradictory configuration

Agent configuration is guidance that must remain consistent with repository reality.

If a Rule, Skill, AGENT or doc describes implementation behavior that contradicts current code/tests:

- inspect the real owner;
- identify whether the config is stale;
- flag the drift;
- follow the current implementation unless a stable human policy says otherwise.

Stable policies remain authoritative until explicitly changed.

Do not silently refactor agent configuration during an unrelated product task unless the task explicitly includes configuration maintenance.

---

# Part XIV — `.cursor` and `.agents`

---

## 39. Canonical source

Current intended principle:

> **`.cursor` is canonical. `.agents` is a strict synchronized mirror.**

Do not maintain both independently.

Assess whether Commands, Rules, and Skills should all be mirrored.

If mirroring remains appropriate, synchronization must be deterministic rather than dependent on agents remembering to copy files manually.

The exact synchronization implementation is challengeable.

---

## 40. Agent configuration checks

Review `scripts/agent_config_check.py` critically.

It should focus on meaningful structural invariants such as:

- expected Commands;
- absence of obsolete configuration artifacts;
- `.cursor` / `.agents` parity;
- valid Rule metadata;
- valid Skill structure;
- required `SKILL.md`;
- referenced Make targets that actually exist;
- no tracked plans that should remain ephemeral;
- invalid backend execution patterns;
- ignore/indexing coherence.

Avoid arbitrary style proxies such as:

- line-count limits;
- exact empty settings files;
- historical deprecated-name museums

unless a real technical constraint justifies them.

Core principle:

> **Validate structure and invariants, not style preferences disguised as CI checks.**

CI should explicitly and efficiently react to relevant `.cursor/**`, `.agents/**`, and agent-config-check changes.

---

# Part XV — Configuration Density

---

## 41. Density hierarchy

Do not use arbitrary line limits.

Use responsibility, relevance, and duplication as the quality criteria.

Approximate hierarchy:

### Rule

Very short and normative.

### Command

Short and procedural.

### AGENTS

Stable architectural and ownership context.

### Skill

Potentially deeper specialized procedure, dynamically loaded.

### Docs

Detailed reference.

Core principle:

> **Configuration files should contain decisions the agent needs, not everything the agent might someday find useful.**

Duplication is a stronger smell than raw line count.

---

# Part XVI — Current Target Hypothesis

The following tree is the current working hypothesis.

It is **not** a mandatory answer.

```text
AGENTS.md
apps/api/AGENTS.md
apps/web/AGENTS.md

.cursor/
├── commands/
│   ├── create-plan.md
│   ├── implement-changes.md
│   ├── review-changes.md
│   ├── hygiene-pass.md
│   ├── test-review.md
│   └── docs-review.md
│
├── rules/
│   ├── api-contract.mdc
│   └── responsive-surfaces.mdc
│
└── skills/
    ├── native-runtime-debug/
    │   └── SKILL.md
    │
    └── testing-spore/
        └── SKILL.md

.agents/
└── strict mirror of relevant `.cursor` configuration

scripts/
├── agent_config_check.py
└── possibly a dedicated deterministic sync mechanism
```

Current expected scale:

- 3 focused `AGENTS.md`;
- 6 workflow Commands;
- approximately 2 scoped Rules;
- approximately 2 specialized Skills;
- zero `alwaysApply` Rules by default.

These numbers are not requirements.

---

## 42. What may be challenged

The following are intentionally challengeable:

- exact number of Rules;
- exact number of Skills;
- Skill names;
- Rule names;
- Command names when there is a concrete improvement;
- exact placement of some instructions;
- whether `testing-spore` deserves to exist;
- whether `responsive-surfaces.mdc` deserves to exist;
- whether `api-contract.mdc` deserves to exist;
- exact `.cursor` → `.agents` sync implementation;
- exact structure of `agent_config_check.py`.

When recommending more configuration, justify every additional file with a concrete Spore-specific failure it prevents.

When a simpler architecture provides equivalent protection, prefer the simpler architecture.

---

## 43. What is considered closed

The following principles should not be reopened casually:

- `create-plan` is strictly read-only;
- planning and implementation are separate;
- Commands define workflow/authority;
- Skills provide expertise, not authority;
- Rules are scarce automatic guardrails;
- configuration must avoid duplication;
- code/tests beat stale descriptive docs/config;
- exploration is proportional to blast radius;
- unrelated user changes must be preserved;
- no speculative future-proofing;
- no speculative hyperscale infrastructure;
- realistic scalability must still be considered;
- Terrain is mobile-dominant but desktop-supported;
- Analytics/management is desktop-dominant but responsive;
- Spore remains one integrated frontend;
- API changes are treated as contracts when the external contract truly changes;
- backend remains the owner of authorization and business integrity;
- `.cursor` should be the single logical source of agent config rather than independent `.cursor`/`.agents` maintenance.

If the real repository exposes a serious reason to challenge one of these, raise it explicitly rather than silently ignoring it.

---

# Part XVII — Required Audit Deliverable

The first Cursor task using this brief must **not modify the repository**.

It must produce a plan for human validation.

Required output:

---

## 44. Current-state diagnostic

Identify important problems in the current agent configuration.

Focus on:

- duplication;
- stale instructions;
- contradictions with actual code;
- misplaced responsibilities;
- unnecessary permanent context;
- missing guardrails;
- brittle/historical config checks.

Ground important findings in actual repository files and implementation.

Avoid generic Cursor advice.

---

## 45. Keep / Refactor / Merge / Delete / Add matrix

Cover every current relevant:

- `AGENTS.md`;
- Rule;
- Command;
- Skill if any;
- relevant agent-config tooling.

For each artifact state:

- decision;
- rationale;
- destination of useful knowledge when removed or merged.

Do not preserve files merely because they exist.

---

## 46. Target architecture

Show the complete proposed configuration tree.

For every AGENT, Rule, Command and Skill state:

- exact responsibility;
- activation mechanism;
- what explicitly does **not** belong there.

Explain every meaningful divergence from the current target hypothesis.

---

## 47. Knowledge placement map

Show where major Spore concerns should live after the refactor.

At minimum cover:

- product core loop;
- backend ownership;
- frontend architecture;
- Terrain vs Analytics;
- responsive behavior;
- Web/Native runtime;
- API contracts;
- testing;
- security/integrity;
- scalability/performance;
- async/realtime;
- AI workflows;
- database/schema;
- observability;
- documentation;
- Git/change scope;
- human workflow authority.

The purpose is to expose duplication and gaps.

---

## 48. Ordered migration plan

Provide an implementation-ready refactor sequence.

For each step specify:

- affected files;
- intent;
- what moves;
- what remains;
- what is deleted;
- dependencies on prior steps;
- validation/checks.

Do not write the final contents of each config file yet.

---

## 49. Risks, disagreements and remaining decisions

Explicitly state:

- disagreements with the current target hypothesis;
- risks in the proposed architecture;
- facts the repository could not resolve;
- only genuinely blocking human decisions needed before implementation.

Do not manufacture questions merely to appear thorough.

---

# Part XVIII — Success Criteria

The refactor is successful if it produces:

- less irrelevant context;
- stronger contextual guardrails;
- clear ownership of each instruction;
- clear human/agent authority boundaries;
- fewer files when possible;
- less duplicated context;
- fewer stale implementation details;
- simpler configuration maintenance;
- deterministic `.cursor` / `.agents` consistency;
- better resistance to future drift;
- stronger understanding of Spore-specific architecture;
- no unnecessary ceremony in everyday development.

The common workflow should remain simple:

```text
/create-plan
→ human validation when needed
→ /implement-changes
```

Optional focused follow-ups:

```text
/review-changes
/hygiene-pass
/test-review
/docs-review
```

The developer should not need to remember a large catalog of specialized Commands or manually select Skills for routine work.

---

# Final Principle

> **Optimize the agent configuration for the smallest durable architecture that gives Cursor the right Spore-specific context, at the right time, with the right authority.**

During the initial audit:

**Audit → verify against the real repository → challenge the target where justified → propose the architecture → produce the migration plan → stop for human validation.**

Do not implement the refactor during the audit.
