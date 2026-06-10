# Backend fix

Fix the backend issue with the smallest safe patch.

Before editing:
- inspect the existing model/service/selector/permission/test pattern
- identify the focused pytest file to run
- check whether API contract changes are required

Constraints:
- keep views thin
- keep writes in services
- keep reusable reads in selectors
- preserve RBAC, membership status, and establishment isolation
- do not change API shape unless required

Tests:
- add/update focused pytest only if behavior changes or regression exists
- run the smallest relevant backend validation

Final:
- Changed
- Validated
- Risks