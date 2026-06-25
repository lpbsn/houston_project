# Event Catalogue v0.1

Status: authoritative (documentary contract)  
Last reviewed: 2026-06-22  
Implementation status: documentary only — no `EventEnvelope`, no event persistence, no notification dispatcher

Related:
- [realtime_domain.md](domains/realtime_domain.md) — transport invalidation truth
- [notification_matrix_v0.2.md](notification_matrix_v0.2.md) — draft/reference for Notifications Lot 1 (not an implementation contract)
- [notification_domain.md](domains/notification_domain.md)
- [rbac_permissions_domain.md](domains/rbac_permissions_domain.md)

---

## 0. Scope distinction

| Périmètre | Rôle | Taille |
|---|---|---|
| **Event Catalogue v0.1** (this document) | Catalogue documentaire de **faits métier** (lifecycle transitions) | 35 entries |
| **Notifications Lot 1** | Subset strict déclenchant une notification in-app persistée | 8 events |

```txt
Event Catalogue v0.1  =  complete business-fact reference (doc)
Notifications Lot 1   =  strict subset: action / checklist execution / mention
Signal (Lot 1)        =  Feed + realtime only — no Signal notifications
```

**Out of scope for this catalogue ticket:** code, migrations, OpenAPI schema, `EventEnvelope` implementation, notification dispatcher, `events` table, push, email.

**Current code truth:** domain services emit **realtime invalidation hints** via `schedule_establishment_invalidation` after commit. The catalogue documents **semantic business facts** that those transitions represent — not persisted event records.

---

## 1. Field contract

Every catalogue entry uses the following fields.

| Field | Rule |
|---|---|
| `event_key` | Stable snake_case identifier (`domain.entity.verb`) |
| `domain` | `signal` \| `action` \| `checklist` \| `comment` |
| `service` | Source file + function in `apps/api/houston/` |
| `actor` | `membership_id` (user command) or `system` (async pipeline, Celery, materialization) |
| `subject_type` | Primary entity type |
| `subject_id` | UUID of primary entity |
| `establishment_id` | Always required |
| `emission_moment` | After which DB mutation; realtime uses `transaction.on_commit` |
| `payload_safe` | Allowed IDs + enums only — see §1.1 |
| `realtime_transport` | `subject_type` + `reason` emitted today, or `none` |
| `consumers` | `realtime` \| `notification` \| `audit` \| `async` (future candidates) |
| `notification_candidate` | `yes` \| `no` \| `conditional` |
| `notification_lot` | `lot1` \| `later` \| `no` |
| `notification_reason` | Product justification, or `N/A — feed/realtime sufficient` |
| `notification_semantic` | Optional product label when different from `event_key` |
| `tests_futurs` | Contract for future implementation tickets |

### 1.1 Safe payload allowlist (all consumers)

**Allowed:** UUIDs, status enums, role hints, `execution_source`, mention membership IDs (not bodies), transition `from_status` / `to_status` where documented.

**Forbidden:** raw Observation text, comment body, chat body, media URLs, signed URLs, secrets, tokens, title/instruction text, AI prompts/outputs, `operational_domains`, `detected_domains`.

RBAC for notification recipients uses **`MembershipScope` on BusinessUnit** only — never legacy `operational_domains`.

---

## 2. Notification guardrails

These rules apply to Notifications Lot 1 and all future notification lots documented here.

### 2.1 Recipients resolved as a set

```txt
Recipients must be resolved as a set.
If a membership appears in multiple recipient groups → one notification, highest priority wins.
```

Priority order: `urgent` > `action_required` > `info` > `system`.

Example: `action.canceled` resolves `assignees ∪ creator` → deduplicate before create.

Dedup window (5 minutes, same recipient + event_key + subject) is compatible with this rule — to be enforced in the Notification implementation ticket.

### 2.2 Actor `system` vs membership

```txt
Actor exclusion applies only when actor is a membership.
System/Celery events → actor = system → no actor exclusion.
```

Example: `checklist.execution.created` from `materialize_execution_from_assignment` uses `actor = system`; assignee is still notified.

Example: `action.created` uses `actor = creator.membership_id`; exclude creator from assignee notifications when overlapping.

### 2.3 `action.created` — no `action.assigned`

Keep `event_key = action.created` (aligned with code and realtime `action.created`).

Document notification semantic as **« action assigned to recipient »** via `notification_semantic`.

Do **not** introduce `action.assigned` unless a separate EventEnvelope ticket explicitly adds it.

### 2.4 Mentions — skip without subject access

```txt
If the mentioned membership cannot view the parent subject (Signal or Action) → do not create a notification.
```

- Use the same visibility rules as `can_view_signal_detail` / `action_visible_to_membership`
- Mention never grants permission
- No « notify then open → 403 » pattern

### 2.5 `notification_matrix_v0.2.md` status

[notification_matrix_v0.2.md](notification_matrix_v0.2.md) is **draft/reference only**. It is not an implementation contract until the Notification model/API ticket ships. Future implementation authority: `houston/notifications/` models + services + `apps/api/schema.yml`.

---

## 3. Notifications Lot 1 annex

**Channels Lot 1:** `in_app` only — no push, no email (post-MVP / separate ticket).

**No Signal events in Lot 1.** Signal visibility is handled by Signal Feed + realtime `signal.*`.

### 3.1 Lot 1 event keys (strict — 8 only)

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

### 3.2 Lot 1 summary table

| event_key | Priority | Channel | Recipients (set dedup) | notification_semantic |
|---|---|---|---|---|
| `action.created` | action_required | in_app | assignees; −actor if membership | action assigned to recipient |
| `action.reassigned` | action_required | in_app | ∪(new assignees, removed assignees); −actor if membership | — |
| `action.pending_validation` | action_required | in_app | validators in-scope (Manager BU scope; Owner/Director) | — |
| `action.reopened` | action_required | in_app | ∪(assignees, creator) | — |
| `action.canceled` | info | in_app | ∪(assignees, creator); highest priority if overlap | — |
| `checklist.execution.created` | action_required | in_app | assignee; actor=system OK | — |
| `checklist.execution.canceled` | info | in_app | ∪(assignee, assigned_by) | — |
| `comment.mention.created` | info | in_app | mentioned membership **only if** subject access | mention on authorized context |

---

## 4. Transport mapping annex (realtime ↔ catalogue)

Operational WebSocket invalidation is documented in [realtime_domain.md](domains/realtime_domain.md).

**Invalidate payload allowlist:** `type`, `subject_type`, `reason`, `establishment_id`, `entity_id`, `occurred_at`

### 4.1 Live operational reasons

| `subject_type` | `reason` | Service source | Catalogue event_key(s) covered |
|---|---|---|---|
| `signal` | `signal.created` | `signals/services.py::create_signal_from_candidate` | `signal.created` |
| `signal` | `signal.updated` | `signals/services.py` (aggregate, pin, unpin, urgency, cancel, resolve) | `signal.aggregated`, `signal.urgency_changed`, `signal.pinned`, `signal.unpinned`, `signal.resolved`, `signal.canceled` |
| `action` | `action.created` | `actions/services.py::create_action` | `action.created` |
| `action` | `action.updated` | `actions/services.py` (accept, mark_done, validate, reopen, cancel, reassign, due_at) | `action.accepted`, `action.pending_validation`, `action.completed`, `action.validated`, `action.reopened`, `action.canceled`, `action.reassigned`, `action.due_at_changed` |
| `checklist` | `checklist.updated` | `checklists/services.py` (template/assignment writers) | all `checklist.template.*`, `checklist.assignment.*` |
| `execution` | `execution.created` | `checklists/services.py`, `materialization.py` | `checklist.execution.created` |
| `execution` | `execution.updated` | `checklists/services.py` | `checklist.execution.started`, `checklist.execution.completed`, `checklist.execution.canceled`, `checklist.task.observation_created` |
| `comment` | `comment.signal.created` | `comments/services.py::create_signal_comment` | `comment.signal.created` (+ facet `comment.mention.created`) |
| `comment` | `comment.signal.inherited` | `comments/services.py` (per linked action) | transport only — refreshes action comment lists |
| `comment` | `comment.action.created` | `comments/services.py::create_action_comment` | `comment.action.created` (+ facet `comment.mention.created`) |
| `comment` | `comment.action.resolved` | `comments/services.py::resolve_action_comment` | `comment.action.resolved` |
| `comment` | `comment.action.unresolved` | `comments/services.py::unresolve_action_comment` | `comment.action.unresolved` |

### 4.2 Signal side-effects from Action lifecycle (cross-domain)

| Business transition | DB mutation | Transport emitted |
|---|---|---|
| Linked `create_action`: Signal `open→in_progress`, optional unpin | yes | `action.created` (+ `signal.updated` only if unpin) |
| `reopen_action`: Signal `resolved→in_progress` | yes | `action.updated` + `signal.updated` |
| All linked actions canceled → Signal reopens to `open` | yes | `action.updated` + `signal.updated` |
| `mark_done` / `validate` → auto `resolve_signal` | yes | `action.updated` + `signal.updated` |

Frontend: `invalidateActionMutationSurfaces` also invalidates Signal queries ([apps/web/src/lib/query-invalidation.ts](apps/web/src/lib/query-invalidation.ts)).

### 4.3 Access events (technical annex — not catalogue business entries)

| `reason` | Source |
|---|---|
| `session.revoked` | `accounts/services.py` |
| `establishment.switched` | `accounts/services.py` |
| `membership.deactivated` | `establishments/services.py` |
| `membership.updated` | `establishments/services.py` |

---

## 5. Stale docs cross-reference

The following domain docs are stale relative to current code. **Transport truth:** [realtime_domain.md](domains/realtime_domain.md). Domain doc correction is a follow-up ticket — not required for this catalogue.

| Document | Stale claim | Code truth |
|---|---|---|
| [comments_domain.md](domains/comments_domain.md) §9 Non-goals | « no realtime invalidation » | Comment realtime **implemented** — 5 `comment.*` reasons in `comments/services.py` |
| [checklist_domain.md](domains/checklist_domain.md) §6 Hors MVP | « Realtime checklist deferred » | `checklist.updated` + `execution.*` **live** in `checklists/services.py` |

---

## 6. Domain catalogues

### 6.1 Signal (8 entries)

#### `signal.created`

| Field | Value |
|---|---|
| domain | signal |
| service | `signals/services.py::create_signal_from_candidate` |
| actor | `system` (observation async pipeline) |
| subject_type / subject_id | `signal` / `signal.id` |
| establishment_id | `signal.establishment_id` |
| emission_moment | After `Signal.objects.create`, source observation link, before `on_commit` → `signal.created` |
| payload_safe | `{ signal_id, establishment_id, observation_id, affected_business_unit_id, responsible_business_unit_id, activity_subject_id, status, urgency }` |
| realtime_transport | `signal` / `signal.created` |
| consumers | realtime=yes, notification=later, audit=later, async=later |
| notification_candidate | conditional |
| notification_lot | **later** |
| notification_reason | New operational situation — Lot 1 covered by Feed; Signal notification deferred |
| tests_futurs | Pipeline emits realtime after commit; payload excludes observation text; no Lot 1 notification |

#### `signal.aggregated`

| Field | Value |
|---|---|
| domain | signal |
| service | `signals/services.py::aggregate_candidate_into_signal` |
| actor | `system` |
| subject_type / subject_id | `signal` / `signal.id` |
| establishment_id | `signal.establishment_id` |
| emission_moment | After aggregation link + `signal.save`, before `on_commit` → `signal.updated` |
| payload_safe | `{ signal_id, establishment_id, observation_id, link_type: "aggregated_from" }` |
| realtime_transport | `signal` / `signal.updated` (bundled) |
| consumers | realtime=yes, notification=later, audit=later |
| notification_candidate | conditional |
| notification_lot | **later** |
| notification_reason | Recurring same situation — noisy if notified systematically |
| tests_futurs | Realtime bundle; conditional notification only if high urgency / pinned (post-Lot 1) |

#### `signal.urgency_changed`

| Field | Value |
|---|---|
| domain | signal |
| service | `signals/services.py::set_signal_urgency` |
| actor | membership (command caller) |
| subject_type / subject_id | `signal` / `signal.id` |
| establishment_id | `signal.establishment_id` |
| emission_moment | After urgency `save`, before `on_commit` → `signal.updated` |
| payload_safe | `{ signal_id, establishment_id, from_urgency, to_urgency }` |
| realtime_transport | `signal` / `signal.updated` (bundled) |
| consumers | realtime=yes, notification=later |
| notification_candidate | conditional |
| notification_lot | **later** |
| notification_reason | High urgency visible in feed/realtime; manager notification post-Lot 1 |
| tests_futurs | Manager in MembershipScope for affected/responsible BU (post-Lot 1 rules) |

#### `signal.pinned`

| Field | Value |
|---|---|
| domain | signal |
| service | `signals/services.py::pin_signal` |
| actor | membership |
| subject_type / subject_id | `signal` / `signal.id` |
| establishment_id | `signal.establishment_id` |
| emission_moment | After pin fields `save`, before `on_commit` → `signal.updated` |
| payload_safe | `{ signal_id, establishment_id, pinned_by_membership_id }` |
| realtime_transport | `signal` / `signal.updated` (bundled) |
| consumers | realtime=yes, notification=no |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | Feed + realtime sufficient |
| tests_futurs | Realtime only |

#### `signal.unpinned`

| Field | Value |
|---|---|
| domain | signal |
| service | `signals/services.py::unpin_signal` (also side-effect from linked `create_action`) |
| actor | membership or side-effect from action create |
| subject_type / subject_id | `signal` / `signal.id` |
| establishment_id | `signal.establishment_id` |
| emission_moment | After pin cleared `save`, before `on_commit` → `signal.updated` |
| payload_safe | `{ signal_id, establishment_id }` |
| realtime_transport | `signal` / `signal.updated` (bundled) |
| consumers | realtime=yes, notification=no |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | Feed + realtime sufficient |
| tests_futurs | Linked action create may emit both `action.created` and `signal.updated` when unpinning |

#### `signal.resolved`

| Field | Value |
|---|---|
| domain | signal |
| service | `signals/services.py::resolve_signal` or `actions/services.py::sync_signal_after_action_change` (auto) |
| actor | membership (manual) or `system` (auto after all linked actions terminal) |
| subject_type / subject_id | `signal` / `signal.id` |
| establishment_id | `signal.establishment_id` |
| emission_moment | After terminal transition `save` (unpin, optional urgency reset), before `on_commit` → `signal.updated` |
| payload_safe | `{ signal_id, establishment_id, from_status, to_status: "resolved" }` |
| realtime_transport | `signal` / `signal.updated` (bundled) |
| consumers | realtime=yes, notification=later |
| notification_candidate | conditional |
| notification_lot | **later** |
| notification_reason | Situation closed — notify linked action stakeholders post-Lot 1 |
| tests_futurs | Auto-resolve after action completion emits `signal.updated` |

#### `signal.canceled`

| Field | Value |
|---|---|
| domain | signal |
| service | `signals/services.py::cancel_signal` |
| actor | membership |
| subject_type / subject_id | `signal` / `signal.id` |
| establishment_id | `signal.establishment_id` |
| emission_moment | After `_transition_active_signal_to_terminal`, before `on_commit` → `signal.updated` |
| payload_safe | `{ signal_id, establishment_id, from_status, to_status: "canceled" }` |
| realtime_transport | `signal` / `signal.updated` (bundled) |
| consumers | realtime=yes, notification=later |
| notification_candidate | conditional |
| notification_lot | **later** |
| notification_reason | Same as resolved — post-Lot 1 |
| tests_futurs | Realtime bundle; Staff denied cancel command |

#### `signal.status_changed` (implicit)

| Field | Value |
|---|---|
| domain | signal |
| service | `actions/services.py::create_action` (Signal `open→in_progress`) |
| actor | membership (action creator) |
| subject_type / subject_id | `signal` / `signal.id` |
| establishment_id | `signal.establishment_id` |
| emission_moment | During linked action create; **no** dedicated `signal.*` transport |
| payload_safe | `{ signal_id, establishment_id, from_status: "open", to_status: "in_progress" }` |
| realtime_transport | **none** (covered by `action.created`) |
| consumers | realtime=via action, notification=no |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | Visibility via action create + frontend co-invalidation |
| tests_futurs | Only `action.created` emitted; Signal queries still refresh on frontend |

---

### 6.2 Action (9 entries)

#### `action.created`

| Field | Value |
|---|---|
| domain | action |
| service | `actions/services.py::create_action` |
| actor | membership (`created_by`) |
| subject_type / subject_id | `action` / `action.id` |
| establishment_id | `action.establishment_id` |
| emission_moment | After assignees + linked signal side-effects, before `on_commit` → `action.created` |
| payload_safe | `{ action_id, establishment_id, signal_id?, responsible_business_unit_id, assignee_membership_ids[], status, requires_validation }` |
| realtime_transport | `action` / `action.created` |
| consumers | realtime=yes, notification=lot1, audit=later |
| notification_candidate | yes |
| notification_lot | **lot1** |
| notification_reason | Assignee must take ownership |
| notification_semantic | **action assigned to recipient** |
| tests_futurs | Assignee receives 1 in_app notif; creator self-assign excluded; no `action.assigned` key; payload excludes title/instruction |

#### `action.accepted`

| Field | Value |
|---|---|
| domain | action |
| service | `actions/services.py::accept_action` |
| actor | membership (`accepted_by`) |
| subject_type / subject_id | `action` / `action.id` |
| establishment_id | `action.establishment_id` |
| emission_moment | After status `in_progress` save, before `on_commit` → `action.updated` |
| payload_safe | `{ action_id, establishment_id, accepted_by_membership_id, status }` |
| realtime_transport | `action` / `action.updated` (bundled) |
| consumers | realtime=yes, notification=later |
| notification_candidate | yes |
| notification_lot | **later** |
| notification_reason | Creator info — not critical for Lot 1 |
| tests_futurs | Creator notified post-Lot 1; actor excluded |

#### `action.pending_validation`

| Field | Value |
|---|---|
| domain | action |
| service | `actions/services.py::mark_action_done` (when `requires_validation=true`) |
| actor | membership (`accepted_by`) |
| subject_type / subject_id | `action` / `action.id` |
| establishment_id | `action.establishment_id` |
| emission_moment | After status `pending_validation` save, before `on_commit` → `action.updated` |
| payload_safe | `{ action_id, establishment_id, signal_id?, responsible_business_unit_id, status }` |
| realtime_transport | `action` / `action.updated` (bundled) |
| consumers | realtime=yes, notification=lot1 |
| notification_candidate | yes |
| notification_lot | **lot1** |
| notification_reason | Validator must act |
| tests_futurs | In-scope Manager validator receives notif; actor excluded; Staff validator denied |

#### `action.completed`

| Field | Value |
|---|---|
| domain | action |
| service | `actions/services.py::mark_action_done` (when `requires_validation=false`) |
| actor | membership (`accepted_by`) |
| subject_type / subject_id | `action` / `action.id` |
| establishment_id | `action.establishment_id` |
| emission_moment | After status `done` save + optional signal sync, before `on_commit` → `action.updated` |
| payload_safe | `{ action_id, establishment_id, signal_id?, status: "done" }` |
| realtime_transport | `action` / `action.updated` (bundled) |
| consumers | realtime=yes, notification=later |
| notification_candidate | yes |
| notification_lot | **later** |
| notification_reason | Creator info post-Lot 1 |
| tests_futurs | May also emit `signal.updated` if auto-resolve |

#### `action.validated`

| Field | Value |
|---|---|
| domain | action |
| service | `actions/services.py::validate_action` |
| actor | membership (validator) |
| subject_type / subject_id | `action` / `action.id` |
| establishment_id | `action.establishment_id` |
| emission_moment | After status `done` + `validated_at` save, before `on_commit` → `action.updated` |
| payload_safe | `{ action_id, establishment_id, status: "done", validated_at }` |
| realtime_transport | `action` / `action.updated` (bundled) |
| consumers | realtime=yes, notification=later |
| notification_candidate | yes |
| notification_lot | **later** |
| notification_reason | Assignee info post-Lot 1 |
| tests_futurs | Signal auto-resolve may add `signal.updated` |

#### `action.reopened`

| Field | Value |
|---|---|
| domain | action |
| service | `actions/services.py::reopen_action` |
| actor | membership |
| subject_type / subject_id | `action` / `action.id` |
| establishment_id | `action.establishment_id` |
| emission_moment | After status `reopened` save + optional signal reopen, before `on_commit` → `action.updated` |
| payload_safe | `{ action_id, establishment_id, signal_id?, status: "reopened" }` |
| realtime_transport | `action` / `action.updated` (bundled) |
| consumers | realtime=yes, notification=lot1 |
| notification_candidate | yes |
| notification_lot | **lot1** |
| notification_reason | Work must resume — assignees need attention |
| tests_futurs | ∪(assignees, creator) set dedup; linked signal reopen emits `signal.updated` |

#### `action.canceled`

| Field | Value |
|---|---|
| domain | action |
| service | `actions/services.py::cancel_action` |
| actor | membership |
| subject_type / subject_id | `action` / `action.id` |
| establishment_id | `action.establishment_id` |
| emission_moment | After status `canceled` save + signal sync, before `on_commit` → `action.updated` |
| payload_safe | `{ action_id, establishment_id, signal_id?, status: "canceled" }` |
| realtime_transport | `action` / `action.updated` (bundled) |
| consumers | realtime=yes, notification=lot1 |
| notification_candidate | yes |
| notification_lot | **lot1** |
| notification_reason | Cancellation affects assignees and creator |
| tests_futurs | ∪(assignees, creator) set dedup, highest priority if overlap; actor excluded if membership |

#### `action.reassigned`

| Field | Value |
|---|---|
| domain | action |
| service | `actions/services.py::reassign_action` |
| actor | membership |
| subject_type / subject_id | `action` / `action.id` |
| establishment_id | `action.establishment_id` |
| emission_moment | After assignee list replaced, before `on_commit` → `action.updated` |
| payload_safe | `{ action_id, establishment_id, assignee_membership_ids[], previous_assignee_membership_ids[] }` |
| realtime_transport | `action` / `action.updated` (bundled) |
| consumers | realtime=yes, notification=lot1 |
| notification_candidate | yes |
| notification_lot | **lot1** |
| notification_reason | New and removed assignees must know |
| tests_futurs | ∪(new, removed) set dedup; −actor if membership |

#### `action.due_at_changed`

| Field | Value |
|---|---|
| domain | action |
| service | `actions/services.py::update_action_due_at` |
| actor | membership |
| subject_type / subject_id | `action` / `action.id` |
| establishment_id | `action.establishment_id` |
| emission_moment | After `due_at` save, before `on_commit` → `action.updated` |
| payload_safe | `{ action_id, establishment_id, due_at }` |
| realtime_transport | `action` / `action.updated` (bundled) |
| consumers | realtime=yes, notification=no |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | Feed + realtime sufficient |
| tests_futurs | Realtime only |

---

### 6.3 Checklist (13 entries)

#### `checklist.template.created`

| Field | Value |
|---|---|
| domain | checklist |
| service | `checklists/services.py::create_checklist_template`, `create_registered_checklist_template` |
| actor | membership |
| subject_type / subject_id | `checklist_template` / `template.id` |
| establishment_id | `template.establishment_id` |
| emission_moment | After template (+ optional tasks) create, before `on_commit` → `checklist.updated` |
| payload_safe | `{ checklist_template_id, establishment_id, business_unit_id, status }` |
| realtime_transport | `checklist` / `checklist.updated` (bundled) |
| consumers | realtime=yes, notification=no |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | Library management — no attention message |
| tests_futurs | Realtime bundle only |

#### `checklist.template.updated`

| Field | Value |
|---|---|
| domain | checklist |
| service | `checklists/services.py::update_checklist_template` |
| actor | membership |
| subject_type / subject_id | `checklist_template` / `template.id` |
| establishment_id | `template.establishment_id` |
| emission_moment | After template patch save, before `on_commit` → `checklist.updated` |
| payload_safe | `{ checklist_template_id, establishment_id, status }` |
| realtime_transport | `checklist` / `checklist.updated` (bundled) |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | Library — feed/realtime sufficient |

#### `checklist.template.activated`

| Field | Value |
|---|---|
| domain | checklist |
| service | `checklists/services.py::activate_checklist_template` |
| actor | membership |
| subject_type / subject_id | `checklist_template` / `template.id` |
| establishment_id | `template.establishment_id` |
| emission_moment | After status `active` save, before `on_commit` → `checklist.updated` |
| payload_safe | `{ checklist_template_id, establishment_id, status: "active" }` |
| realtime_transport | `checklist` / `checklist.updated` (bundled) |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | N/A — feed/realtime sufficient |

#### `checklist.template.deactivated`

| Field | Value |
|---|---|
| domain | checklist |
| service | `checklists/services.py::deactivate_checklist_template` |
| actor | membership |
| subject_type / subject_id | `checklist_template` / `template.id` |
| establishment_id | `template.establishment_id` |
| emission_moment | After status `inactive` save, before `on_commit` → `checklist.updated` |
| payload_safe | `{ checklist_template_id, establishment_id, status: "inactive" }` |
| realtime_transport | `checklist` / `checklist.updated` (bundled) |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | N/A — feed/realtime sufficient |

#### `checklist.template.deleted`

| Field | Value |
|---|---|
| domain | checklist |
| service | `checklists/services.py::delete_checklist_template` |
| actor | membership |
| subject_type / subject_id | `checklist_template` / `template.id` |
| establishment_id | `template.establishment_id` |
| emission_moment | Before/after delete flow, `on_commit` → `checklist.updated` |
| payload_safe | `{ checklist_template_id, establishment_id }` |
| realtime_transport | `checklist` / `checklist.updated` (bundled) |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | N/A — feed/realtime sufficient |

#### `checklist.assignment.created`

| Field | Value |
|---|---|
| domain | checklist |
| service | `checklists/services.py::create_checklist_assignment`, `schedule_checklist_from_template` (recurrent branch) |
| actor | membership |
| subject_type / subject_id | `checklist_assignment` / `assignment.id` |
| establishment_id | `assignment.establishment_id` |
| emission_moment | After assignment create (+ eager first materialization may follow), `on_commit` → `checklist.updated` |
| payload_safe | `{ checklist_assignment_id, checklist_template_id, establishment_id, assigned_to_membership_id }` |
| realtime_transport | `checklist` / `checklist.updated` (bundled); may also emit `execution.created` |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | Notification on execution, not assignment |

#### `checklist.assignment.updated`

| Field | Value |
|---|---|
| domain | checklist |
| service | `checklists/services.py::update_checklist_assignment` |
| actor | membership |
| subject_type / subject_id | `checklist_assignment` / `assignment.id` |
| establishment_id | `assignment.establishment_id` |
| emission_moment | After assignment patch + execution sync, `on_commit` → `checklist.updated` + possible `execution.updated` |
| payload_safe | `{ checklist_assignment_id, establishment_id, status }` |
| realtime_transport | `checklist` / `checklist.updated` (bundled) |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | Feed/realtime sufficient |

#### `checklist.assignment.deactivated`

| Field | Value |
|---|---|
| domain | checklist |
| service | `checklists/services.py::deactivate_checklist_assignment` |
| actor | membership |
| subject_type / subject_id | `checklist_assignment` / `assignment.id` |
| establishment_id | `assignment.establishment_id` |
| emission_moment | After deactivate + canceled assigned executions, `on_commit` |
| payload_safe | `{ checklist_assignment_id, establishment_id, status: "inactive" }` |
| realtime_transport | `checklist` / `checklist.updated` + `execution.updated` (bundled) |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | Feed/realtime sufficient |

#### `checklist.execution.created`

| Field | Value |
|---|---|
| domain | checklist |
| service | `checklists/services.py::create_execution_from_template`, `materialization.py::materialize_execution_from_assignment` |
| actor | membership (sync launch) or **`system`** (Celery/materialization) |
| subject_type / subject_id | `checklist_execution` / `execution.id` |
| establishment_id | `execution.establishment_id` |
| emission_moment | After execution + task snapshots create, before `on_commit` → `execution.created` (skipped on idempotent materialization retry) |
| payload_safe | `{ execution_id, establishment_id, checklist_template_id, checklist_assignment_id?, execution_source, assigned_to_membership_id, assigned_by_membership_id, business_unit_id, status }` |
| realtime_transport | `execution` / `execution.created` |
| consumers | realtime=yes, notification=lot1 |
| notification_candidate | yes |
| notification_lot | **lot1** |
| notification_reason | Assignee must execute |
| tests_futurs | Assignee notified; `actor=system` does not suppress assignee notification; materialization idempotent path skips duplicate realtime |

#### `checklist.execution.started`

| Field | Value |
|---|---|
| domain | checklist |
| service | `checklists/services.py::_maybe_start_execution` (first task event) |
| actor | membership |
| subject_type / subject_id | `checklist_execution` / `execution.id` |
| establishment_id | `execution.establishment_id` |
| emission_moment | On first `mark_task_done` / `skip` / observation handoff when status `assigned→in_progress` |
| payload_safe | `{ execution_id, establishment_id, from_status: "assigned", to_status: "in_progress" }` |
| realtime_transport | `execution` / `execution.updated` (bundled) |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | Execution feed sufficient |

#### `checklist.execution.completed`

| Field | Value |
|---|---|
| domain | checklist |
| service | `checklists/services.py::_maybe_complete_execution` |
| actor | membership or `system` |
| subject_type / subject_id | `checklist_execution` / `execution.id` |
| establishment_id | `execution.establishment_id` |
| emission_moment | When all tasks treated → status `done`, before `on_commit` → `execution.updated` |
| payload_safe | `{ execution_id, establishment_id, status: "done" }` |
| realtime_transport | `execution` / `execution.updated` (bundled) |
| notification_candidate | yes |
| notification_lot | **later** |
| notification_reason | Inform `assigned_by` post-Lot 1 |
| tests_futurs | Post-Lot 1: assigned_by in_app only |

#### `checklist.execution.canceled`

| Field | Value |
|---|---|
| domain | checklist |
| service | `checklists/services.py::cancel_checklist_execution`, assignment sync paths |
| actor | membership |
| subject_type / subject_id | `checklist_execution` / `execution.id` |
| establishment_id | `execution.establishment_id` |
| emission_moment | After status `canceled` save, before `on_commit` → `execution.updated` |
| payload_safe | `{ execution_id, establishment_id, status: "canceled" }` |
| realtime_transport | `execution` / `execution.updated` (bundled) |
| consumers | realtime=yes, notification=lot1 |
| notification_candidate | yes |
| notification_lot | **lot1** |
| notification_reason | Assignee and assigner must know |
| tests_futurs | ∪(assignee, assigned_by) set dedup |

#### `checklist.task.observation_created`

| Field | Value |
|---|---|
| domain | checklist |
| service | `checklists/services.py::record_task_observation_created` |
| actor | membership |
| subject_type / subject_id | `checklist_task_execution` / `task_execution.id` |
| establishment_id | `execution.establishment_id` |
| emission_moment | After task status `observation_created`, before `on_commit` → `execution.updated` |
| payload_safe | `{ task_execution_id, execution_id, establishment_id, task_status: "observation_created" }` |
| realtime_transport | `execution` / `execution.updated` (bundled) |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | Wait for observation pipeline → `signal.created` / Signal feed |
| tests_futurs | No direct notification; pipeline may emit `signal.created` |

---

### 6.4 Comment (5 entries)

#### `comment.signal.created`

| Field | Value |
|---|---|
| domain | comment |
| service | `comments/services.py::create_signal_comment` |
| actor | membership (`author_membership`) |
| subject_type / subject_id | `signal` / `signal.id` |
| establishment_id | `signal.establishment_id` |
| emission_moment | After comment + mentions create, before `on_commit` → `comment.signal.created` + `comment.signal.inherited` per linked action |
| payload_safe | `{ comment_id, subject_type: "signal", subject_id, author_membership_id, mentioned_membership_ids[] }` — **no body** |
| realtime_transport | `comment` / `comment.signal.created` (+ inherited per linked action) |
| notification_candidate | conditional |
| notification_lot | **no** (Lot 1 uses `comment.mention.created` facet only) |
| notification_reason | Lot 1: mentions only via facet |
| tests_futurs | Realtime refreshes signal comment list; no full-body payload |

#### `comment.action.created`

| Field | Value |
|---|---|
| domain | comment |
| service | `comments/services.py::create_action_comment` |
| actor | membership |
| subject_type / subject_id | `action` / `action.id` |
| establishment_id | `action.establishment_id` |
| emission_moment | After comment create (root or reply), before `on_commit` → `comment.action.created` |
| payload_safe | `{ comment_id, subject_type: "action", subject_id, author_membership_id, parent_comment_id?, mentioned_membership_ids[] }` |
| realtime_transport | `comment` / `comment.action.created` |
| notification_candidate | conditional |
| notification_lot | **no** |
| notification_reason | Lot 1: mentions only; no assignee/creator notification |
| tests_futurs | Realtime only for non-mention creates |

#### `comment.action.resolved`

| Field | Value |
|---|---|
| domain | comment |
| service | `comments/services.py::resolve_action_comment` |
| actor | membership (`resolved_by_membership`) |
| subject_type / subject_id | `action` / `action.id` |
| establishment_id | `action.establishment_id` |
| emission_moment | After `resolved_at` save, before `on_commit` → `comment.action.resolved` |
| payload_safe | `{ comment_id, action_id, establishment_id, resolved_by_membership_id }` |
| realtime_transport | `comment` / `comment.action.resolved` |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | No attention message in MVP |
| tests_futurs | Realtime only |

#### `comment.action.unresolved`

| Field | Value |
|---|---|
| domain | comment |
| service | `comments/services.py::unresolve_action_comment` |
| actor | membership |
| subject_type / subject_id | `action` / `action.id` |
| establishment_id | `action.establishment_id` |
| emission_moment | After clear resolved fields, before `on_commit` → `comment.action.unresolved` |
| payload_safe | `{ comment_id, action_id, establishment_id }` |
| realtime_transport | `comment` / `comment.action.unresolved` |
| notification_candidate | no |
| notification_lot | **no** |
| notification_reason | No attention message in MVP |

#### `comment.mention.created` (facet)

| Field | Value |
|---|---|
| domain | comment |
| service | Facet of `create_signal_comment` / `create_action_comment` when `mentioned_membership_ids` non-empty |
| actor | membership (comment author) |
| subject_type / subject_id | `signal` or `action` / parent subject id |
| establishment_id | establishment of parent subject |
| emission_moment | Same transaction as parent comment create — **no** dedicated realtime transport |
| payload_safe | `{ comment_id, subject_type, subject_id, author_membership_id, mentioned_membership_id }` — **no body** |
| realtime_transport | **none** (parent comment realtime covers list refresh) |
| consumers | notification=lot1 |
| notification_candidate | yes |
| notification_lot | **lot1** |
| notification_reason | Mentioned user should know — only if they can view parent subject |
| tests_futurs | Skip notification when mentioned membership lacks subject visibility; exclude actor author; one notif per mentioned membership; no permission grant |

**Note:** `comment.signal.inherited` is realtime transport only (invalidates linked action comment lists). It is not a separate catalogue business entry.

---

## 7. Excluded from catalogue v0.1

| Family | Reason |
|---|---|
| `signal.archived`, `signal.domain_*` | Not implemented; legacy taxonomy removed |
| `action.overdue`, `action.no_acceptance_detected` | No scheduler/detector in code |
| Chat WebSocket events | Separate protocol — [chat_domain.md](domains/chat_domain.md) |
| Notification meta-events (`notification.created`, etc.) | Domain not started |
| Observation pipeline intermediate steps | Future annex — [ai_observation_pipeline_contract.md](domains/ai_observation_pipeline_contract.md) |
| Identity/Membership business events | Separate ticket; access WS only today |
| Personal/Flash checklist | Product removed |
| `operational_domains`, `detected_domains` | Forbidden — use `MembershipScope` on BusinessUnit |
| `action.assigned` | Do not invent — use `action.created` + `notification_semantic` |

---

## 8. Future tests checklist

### 8.1 Lot 1 notification contract tests (implementation ticket)

| event_key | Test focus |
|---|---|
| `action.created` | Assignee receives in_app; creator self-assign → no duplicate; semantic « assigned »; no `action.assigned` key |
| `action.reassigned` | ∪(new, removed) dedup; −actor membership |
| `action.pending_validation` | Validator in-scope only; actor excluded |
| `action.reopened` | ∪(assignees, creator) dedup |
| `action.canceled` | ∪(assignees, creator) dedup; priority max on overlap |
| `checklist.execution.created` | Assignee notified; `actor=system` still notifies assignee |
| `checklist.execution.canceled` | ∪(assignee, assigned_by) dedup |
| `comment.mention.created` | Skip without subject access; exclude author; no body in payload |

### 8.2 Cross-cutting

- Recipients union → single notification per membership, highest priority
- No sensitive fields in any notification or event payload
- `notification_lot: later` events produce zero notifications in Lot 1 implementation
- No Signal event produces Lot 1 notification
- Channels Lot 1: `in_app` only

### 8.3 Realtime transport tests (existing — maintain on catalogue changes)

See `apps/api/houston/realtime/tests/test_*invalidation*.py` and `apps/web/src/features/realtime/lib/apply-operational-invalidation.test.ts`.

---

## 9. Document status

| Item | Status |
|---|---|
| Event Catalogue v0.1 | **authoritative** (documentary) |
| Notifications Lot 1 | Documented subset — **not implemented** |
| EventEnvelope / persistence | **Out of scope** — separate ticket |
| [notification_matrix_v0.2.md](notification_matrix_v0.2.md) | **Draft/reference only** |
