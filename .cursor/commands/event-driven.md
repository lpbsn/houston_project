# Event-driven change

Implement or review event-driven behavior.

**Runtime side effects today:** post-commit hubs in `apps/api/houston/realtime/broadcast.py` and `apps/api/houston/notifications/scheduling.py`. The `houston.events` app and `EventEnvelope` in `houston/core/events.py` are non-runtime scaffolding (tests only) — do not treat them as the live event bus.

Before editing:
- identify the business state transition
- inspect existing event type/registry/publisher pattern
- inspect consumers: notification, realtime, audit, analytics, async jobs
- inspect existing event tests

Constraints:
- business tables remain source of truth
- persist valid state before publishing event
- publish after commit when transaction safety matters
- event payload must be minimal and non-sensitive
- consumers must be async/retry-safe and idempotent
- do not notify or broadcast directly if an event consumer should handle it
- do not introduce event sourcing unless explicitly requested

Required tests:
- event emitted for significant transition
- no event emitted for failed/forbidden transition
- payload shape
- consumer behavior if changed

Final:
- Event source changed
- Event payload changed
- Consumers changed
- Validated
- Risks