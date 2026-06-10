# Test audit

Audit and refactor the test suite for the requested scope.

Mode:
- destructive cleanup is allowed when justified
- prefer fewer stronger tests over many weak tests

Audit:
- slow tests
- fragile tests
- redundant tests
- over-mocked tests
- obsolete behavior tests
- fixture bloat
- missing critical lifecycle/RBAC/API tests

Protected areas:
- Signal lifecycle
- Action lifecycle
- Checklist
- Chat WebSocket
- Bootstrap/Auth/RBAC
- Observation pipeline

Rules:
- delete duplicate/obsolete/implementation-detail tests
- replace weak tests with stronger focused coverage
- add only missing critical tests
- keep test names clear and business-oriented

Final:
- Deleted
- Refactored
- Added
- Validated
- Remaining test debt