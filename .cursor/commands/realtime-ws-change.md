# Realtime / WebSocket change

Implement or fix realtime, WebSocket, chat, or query invalidation behavior.

Before editing:
- inspect consumer/provider/hook/query-key pattern
- inspect auth and membership validation
- inspect broadcast payload shape
- inspect reconnect/duplicate handling

Constraints:
- DB remains source of truth
- realtime should invalidate or patch query cache safely
- validate membership before joining/broadcasting
- broadcast minimal payloads
- do not trust client-provided membership or role

Tests:
- backend access/payload tests when consumer changes
- frontend query-cache/reconnect/unread tests when UI changes

Final:
- Backend realtime changed
- Frontend realtime changed
- Validated
- Risks