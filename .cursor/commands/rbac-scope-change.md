# RBAC / scope change

Implement or review a permission, membership, role, or BusinessUnit scope change.

Before editing:
- inspect permission class/helper
- inspect membership status handling
- inspect establishment isolation
- inspect existing allowed/forbidden tests

Required tests:
- Owner/Director allowed when expected
- Manager/Staff scoped behavior
- forbidden role
- inactive membership
- wrong establishment
- out-of-scope BusinessUnit

Constraints:
- frontend permission hints are UX only
- backend must enforce security
- do not leak objects across establishments
- do not rely on client-provided role/scope

Final:
- Permission logic changed
- Tests added/updated
- Validated
- Risks