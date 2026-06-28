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

Validation (see [`docs/engineering/testing.md`](../../docs/engineering/testing.md)):
- focused tests: `make backend-test PYTEST_ARGS='path/to/test_file.py::test_name'`
- broader gate: `make backend-check` (lint, migrations, schema diff, pytest)

Final:
- Changed
- Validated
- Risks