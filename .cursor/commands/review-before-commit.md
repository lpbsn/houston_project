# Review before commit

Review the current diff before commit.

Read-only mode:
- do not edit files unless explicitly asked
- inspect git diff and impacted tests
- identify regression risks

Review checklist:
- API contract drift
- RBAC/scope bypass
- tenant isolation leak
- lifecycle inconsistency
- missing migration/schema/type update
- missing loading/error/mobile state
- weak or missing tests
- unnecessary refactor or duplication

Output:
- Blockers
- Should fix
- Acceptable debt
- Suggested validation commands