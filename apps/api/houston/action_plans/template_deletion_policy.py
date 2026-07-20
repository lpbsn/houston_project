"""Status-only classification for template hard-deletion execution fate.

Internal primitives only — no public API. Classification ignores start_at,
visible_from, cancel_origin, and comments.
"""

from __future__ import annotations

from typing import Literal

from houston.action_plans.constants import EXECUTION_STATUS_SCHEDULED

TemplateDeletionExecutionFate = Literal["hard_delete", "keep_detach"]

TEMPLATE_DELETION_FATE_HARD_DELETE: TemplateDeletionExecutionFate = "hard_delete"
TEMPLATE_DELETION_FATE_KEEP_DETACH: TemplateDeletionExecutionFate = "keep_detach"


def classify_execution_for_template_deletion(
    *,
    status: str,
) -> TemplateDeletionExecutionFate:
    """Classify an execution by its persistent status alone."""
    if status == EXECUTION_STATUS_SCHEDULED:
        return TEMPLATE_DELETION_FATE_HARD_DELETE
    return TEMPLATE_DELETION_FATE_KEEP_DETACH
