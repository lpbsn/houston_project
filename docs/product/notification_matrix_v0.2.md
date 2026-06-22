# Notification Matrix v0.2

> **Status: draft / reference only**  
> **Not an implementation contract** until the Notification model/API ticket is delivered.  
> **Authoritative implementation source (future):** `houston/notifications/` models + services + `apps/api/schema.yml`  
> **Business-fact reference:** [event_catalogue_v0.1.md](event_catalogue_v0.1.md)

Last reviewed: 2026-06-22

---

## 0. How to read this document

| Document | Role |
|---|---|
| [event_catalogue_v0.1.md](event_catalogue_v0.1.md) | Complete business-fact catalogue (~35 entries) |
| **This document** | Draft rules for turning catalogue events into user notifications |
| [notification_domain.md](domains/notification_domain.md) | Notification domain boundaries (not started in code) |

```txt
Event        = system fact (catalogue)
Notification = user attention message (matrix rules)
Realtime/Feed = visibility (not replaced by notifications)
```

**Principle (unchanged from archive matrix):**

```txt
Notify only when attention or action is required.
Realtime/feed handles visibility.
```

---

## 1. Notifications Lot 1 scope

### 1.1 Strict event subset (8 only)

```txt
action.created
action.reassigned
action.pending_validation
action.reopened
action.canceled
checklist.execution.created
checklist.execution.canceled
comment.mention.created
```

All other catalogue entries: `notification_lot: later` or `no` — **zero** Lot 1 notifications.

### 1.2 Signal — explicitly out of Lot 1

No Signal event produces a Lot 1 notification. Signal visibility is handled by:
- Signal Feed (authorized REST)
- Realtime `signal.created` / `signal.updated`

Signal notification rules are deferred to `notification_lot: later` in the catalogue.

### 1.3 Channels Lot 1

```txt
Lot 1 channels: in_app only
```

- **No push** in Lot 1
- **No email** in Lot 1 (except unrelated identity flows — invitations, etc.)
- Push / email = post-MVP / separate ticket

---

## 2. Global guardrails

### 2.1 Recipients as a set

```txt
Recipients must be resolved as a set.
If a membership appears in multiple recipient groups → one notification, highest priority wins.
```

Priority order: `urgent` > `action_required` > `info` > `system`

Dedup window (recommended for implementation): same recipient + `event_key` + `subject_id` within 5 minutes → skip or merge.

### 2.2 Actor exclusion

```txt
Actor exclusion applies only when actor is a membership.
System/Celery events → actor = system → no actor exclusion.
```

### 2.3 RBAC recheck

Before creating any notification:
1. Resolve candidate recipients from matrix rules
2. Re-check membership is active
3. Re-check recipient can view the notification subject (establishment scope + object visibility)
4. Skip silently if check fails — notification never grants access

### 2.4 Mentions

For `comment.mention.created`:

```txt
If mentioned membership cannot view parent subject (Signal or Action) → do not create notification.
```

- Same visibility as `can_view_signal_detail` / `action_visible_to_membership`
- Mention does not grant permission
- Exclude comment author (actor membership)

### 2.5 `action.created` semantic

- **event_key:** `action.created` (aligned with code and realtime — do not rename)
- **notification_semantic:** « action assigned to recipient »
- Do **not** introduce `action.assigned` unless a future EventEnvelope ticket adds it

### 2.6 Forbidden payload fields

Never include in notifications:
- Observation raw text
- Comment body (use generic short copy)
- Chat body
- Media URLs / signed URLs
- Secrets / tokens
- `operational_domains` / `detected_domains`

---

## 3. Recipient resolution (MembershipScope)

Use **`MembershipScope` on BusinessUnit** — not legacy `operational_domains`.

| Role | Visibility / validation helper |
|---|---|
| Owner / Director | Broad establishment access |
| Manager | `MembershipScope` must cover canonical responsible BU (Actions) or affected/responsible BU (Signals — post-Lot 1) |
| Staff | Scoped visibility; no validation by default |

For `action.pending_validation`:
- Owner/Director: may validate any action in establishment
- Manager: only when canonical responsible BU ∈ `MembershipScope` ([action_domain.md](domains/action_domain.md))

---

## 4. Lot 1 rules by event

### 4.1 `action.created`

| Field | Value |
|---|---|
| Priority | `action_required` |
| Channel | `in_app` |
| Recipients | All current assignees (set) |
| Actor exclusion | Exclude `created_by` membership if in assignee set |
| notification_semantic | action assigned to recipient |
| Title/body direction | Short non-sensitive copy pointing to action detail fetch |

### 4.2 `action.reassigned`

| Field | Value |
|---|---|
| Priority | `action_required` |
| Channel | `in_app` |
| Recipients | ∪(new assignees, removed assignees) — set dedup |
| Actor exclusion | Exclude actor membership if present in union |

### 4.3 `action.pending_validation`

| Field | Value |
|---|---|
| Priority | `action_required` |
| Channel | `in_app` |
| Recipients | Validators: Owner/Director + Managers with responsible BU in scope |
| Actor exclusion | Exclude `accepted_by` (actor who marked done) |

### 4.4 `action.reopened`

| Field | Value |
|---|---|
| Priority | `action_required` |
| Channel | `in_app` |
| Recipients | ∪(assignees, creator) — set dedup |
| Actor exclusion | Exclude actor membership |

### 4.5 `action.canceled`

| Field | Value |
|---|---|
| Priority | `info` |
| Channel | `in_app` |
| Recipients | ∪(assignees, creator) — set dedup; highest priority if overlap with other rules |
| Actor exclusion | Exclude actor membership |

### 4.6 `checklist.execution.created`

| Field | Value |
|---|---|
| Priority | `action_required` |
| Channel | `in_app` |
| Recipients | `assigned_to` membership |
| Actor exclusion | N/A when `actor = system` (materialization). When actor is membership (manual launch for others), exclude actor only if actor equals assignee |

### 4.7 `checklist.execution.canceled`

| Field | Value |
|---|---|
| Priority | `info` |
| Channel | `in_app` |
| Recipients | ∪(assignee, assigned_by) — set dedup |
| Actor exclusion | Exclude actor membership if in union |

### 4.8 `comment.mention.created`

| Field | Value |
|---|---|
| Priority | `info` |
| Channel | `in_app` |
| Recipients | Each mentioned membership **only if** they can view parent subject |
| Actor exclusion | Exclude comment author |
| Skip | No notification if mentioned user lacks subject visibility |

---

## 5. Lot 1 summary table

| event_key | Priority | Channel | Recipients (set) | Semantic / notes |
|---|---|---|---|---|
| `action.created` | action_required | in_app | assignees | « action assigned to recipient » |
| `action.reassigned` | action_required | in_app | ∪(new, removed) | −actor if membership |
| `action.pending_validation` | action_required | in_app | validators in-scope | −accepted_by |
| `action.reopened` | action_required | in_app | ∪(assignees, creator) | −actor |
| `action.canceled` | info | in_app | ∪(assignees, creator) | −actor |
| `checklist.execution.created` | action_required | in_app | assignee | system actor OK |
| `checklist.execution.canceled` | info | in_app | ∪(assignee, assigned_by) | −actor |
| `comment.mention.created` | info | in_app | mentioned (if access) | skip without visibility |

---

## 6. Deferred (`notification_lot: later`)

Not in Lot 1 implementation. Documented in catalogue for future lots.

| event_key | Direction (draft) | Channel (future) |
|---|---|---|
| `signal.created` | Managers with BU scope; Owner/Director targeted | in_app (push post-MVP) |
| `signal.aggregated` | Conditional — high urgency / pinned | in_app |
| `signal.urgency_changed` | Managers BU scope when → high | in_app + push (post-MVP) |
| `signal.resolved` / `signal.canceled` | Linked action stakeholders | in_app |
| `action.accepted` | Creator | in_app |
| `action.completed` / `action.validated` | Creator / assignee | in_app |
| `checklist.execution.completed` | assigned_by | in_app |
| `comment.signal.created` / `comment.action.created` | Assignee + creator (not mentions) | in_app |

---

## 7. Excluded / not planned

| Item | Reason |
|---|---|
| `signal.pinned` / `signal.unpinned` | Feed + realtime only |
| `action.due_at_changed` | Feed + realtime only |
| Checklist template/assignment CRUD | Library noise |
| `comment.action.resolved` / `unresolved` | No attention message |
| `action.overdue` | No detector in code |
| `action.assigned` | Use `action.created` instead |
| `operational_domains` recipients | Legacy — use MembershipScope |
| `SignalDomainAdded` | Removed taxonomy |
| Chat message notifications | Out of Chat V1 scope |
| Push / email Lot 1 | Separate ticket |

---

## 8. Future implementation tests (draft)

When Notification model/API ticket starts, minimum matrix tests:

```txt
Given action.created with 2 assignees including creator
When dispatcher runs
Then creator receives 0 notifications (actor exclusion)
And other assignee receives 1 in_app action_required notification

Given action.canceled where creator is also assignee
When dispatcher runs
Then exactly 1 notification (set dedup, highest priority)

Given comment.mention.created where mentioned user cannot view action
When dispatcher runs
Then mentioned user receives 0 notifications

Given checklist.execution.created from Celery materialization (actor=system)
When dispatcher runs
Then assignee receives 1 in_app notification

Given same recipient + event_key + subject_id within 5 minutes
When second event is evaluated
Then second notification is skipped or merged
```

---

## 9. Changes from archive matrix (v0.1 codex)

| Archive (codex) | v0.2 draft |
|---|---|
| Many events in MVP | Lot 1 strict: 8 events |
| Push in MVP | Push deferred — in_app only Lot 1 |
| `operational_domains` / `detected_domains` | `MembershipScope` on BusinessUnit |
| `SignalDomainAdded` | Removed |
| `ActionAssigned` event name | `action.created` + semantic « assigned » |
| Mention → notify then 403 | Skip notification without subject access |
| SignalCreated Staff rules | Signal notifications entirely deferred from Lot 1 |

---

## 10. Document status

| Item | Status |
|---|---|
| This matrix v0.2 | **Draft / reference** |
| [event_catalogue_v0.1.md](event_catalogue_v0.1.md) | **Authoritative** (documentary catalogue) |
| Notification implementation | **Not started** — `houston/notifications/` stub only |
| OpenAPI notification endpoints | **None** in `schema.yml` |

Do not treat this document as a binding API or service contract until the Notification model/API ticket explicitly promotes it.
