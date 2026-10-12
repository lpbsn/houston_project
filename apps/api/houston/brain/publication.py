"""Derived objects written in the same transaction as a completed analysis.

Follow-ups do not call this module. They publish no decision object.
"""

from __future__ import annotations

from houston.brain.knowledge import publish_mechanism_candidates
from houston.brain.objectives import publish_objective_evaluations
from houston.brain.suggestions import publish_suggested_drafts


def persist_completed_analysis(analysis, result: dict | None) -> None:
    publish_objective_evaluations(analysis)
    proposals = {}
    if isinstance(result, dict) and isinstance(result.get("proposals"), dict):
        proposals = result["proposals"]
    publish_suggested_drafts(analysis, proposals.get("suggestions"))
    publish_mechanism_candidates(analysis, proposals.get("mechanisms"))
