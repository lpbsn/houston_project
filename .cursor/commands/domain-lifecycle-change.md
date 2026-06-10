# Domain lifecycle change

Implement a lifecycle change for Signal, Action, Checklist, Observation, or Chat.

Before editing:
- inspect current statuses/enums
- inspect services handling transitions
- inspect permission checks
- inspect tests for valid and forbidden transitions

Required tests:
- valid transition
- forbidden transition
- side effects
- permission boundary
- idempotency if relevant

Constraints:
- do not update status directly from views/components
- lifecycle writes belong in services
- preserve feed/query/realtime side effects
- preserve read-only behavior after terminal states

Final:
- Transition changed
- Side effects changed
- Tests updated
- Validated
- Risks