# Frontend fix

Fix the frontend issue with the smallest safe patch.

Before editing:
- inspect existing component/hook/API-client/query-key pattern
- identify affected route and user flow
- check whether generated API types are involved

Constraints:
- keep server state in TanStack Query
- use existing API wrappers and generated types
- preserve mobile-first layout
- preserve loading, empty, error, unauthorized states
- do not duplicate backend permissions except for UX hints

Tests:
- add/update focused UI/query/routing test if behavior changes
- run typecheck, lint, and affected tests

Final:
- Changed
- Validated
- Risks