"""One investigator, the v7.1 prompt, and sealed searches.

The provider chooses the searches and the restitution. This module commits
the trace after each provider turn and rebuilds the dialogue from that trace
and the sealed dossier. It does not admit an analysis and it does not run V1 or V3.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django.db import transaction

from houston.brain.capture import capture_investigation_dossier
from houston.brain.configuration import CALL_FRAMING_TOKENS, frozen_counter, json_token_count
from houston.brain.engine_guard import SCHEMA_VERSION, qualify_restitution
from houston.brain.engine_tools import (
    TOOL_SCHEMAS,
    SealedView,
    execute_tool,
    render_tool_result,
)
from houston.brain.errors import BrainWorkError
from houston.brain.models import BrainAnalysis, BrainDossier, BrainDossierItem
from houston.brain.publication import persist_completed_analysis

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "metier_v7_1.md"
MAX_TOOL_CALLS = 8
MAX_DISTINCT_COPIES = 40
PROVIDER_TIMEOUT_SECONDS = 90
RESTITUTION_SENTENCE = (
    "Le budget de recherches est épuisé. Restitue à partir de ce qui a été examiné."
)
FORMAT_TEXT = (
    "Canal de format. Libellés de champs.\n"
    "subjects : key, significant, examined, contribution, epistemic_status, statement, "
    "evidence_ids, compare_ids, decisive_contradiction_unexamined, figures.\n"
    "epistemic_status : constat, explication_etayee, hypothese, hypothese_fragilisee, "
    "absence_explication.\n"
    "figures : source measure et item_id, ou source compare et compare_id. "
    "N'énonce pas un chiffre qui n'est pas cette référence.\n"
    "anchors : anchor_id, disposition attached ou not_significant, subject_key si attached.\n"
    "limits : limites nommées.\n"
    "proposals.suggestions : key, title, description.\n"
    "proposals.objectives : key, indicator, target, period.\n"
    "proposals.mechanisms : key, formulation, conditions, limits, uncertainty."
)


@dataclass(frozen=True)
class EngineToolCall:
    name: str
    arguments: dict


@dataclass(frozen=True)
class EngineTurn:
    tool_calls: tuple[EngineToolCall, ...] = ()
    restitution: dict | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


def metier_prompt() -> str:
    """Packaged v7.1 text. The image does not read docs/ at runtime."""
    return _PROMPT_PATH.read_text(encoding="utf-8")


def run_engine(analysis_id, provider) -> dict:
    """Seal the dossier if needed, then investigate until a restitution or the tool budget."""
    dossier = _ensure_dossier(analysis_id)
    view = _load_view(dossier)
    analysis = _load_analysis(analysis_id)
    if (
        isinstance(analysis.result, dict)
        and analysis.result.get("schema_version") == SCHEMA_VERSION
    ):
        return analysis.result
    trace = list(analysis.trace or [])
    _fill_pending(analysis, view, trace)
    if _restitution(trace) is not None:
        return _finish(analysis, view, trace)
    while True:
        if _tool_count(trace) >= MAX_TOOL_CALLS and not _instruction_sent(trace):
            trace.append({"kind": "instruction", "text": RESTITUTION_SENTENCE})
            _save_trace(analysis, trace)
        messages = build_messages(view, trace)
        _require_budget(analysis, messages, tools=_tools_for(trace))
        turn = provider.complete(
            analysis_id=str(analysis.id),
            messages=messages,
            tools=_tools_for(trace),
            timeout_seconds=PROVIDER_TIMEOUT_SECONDS,
        )
        if getattr(turn, "restitution", None) is not None:
            trace.append({"kind": "restitution", "output": turn.restitution})
            _save_trace(analysis, trace)
            return _finish(analysis, view, trace)
        if _tool_count(trace) >= MAX_TOOL_CALLS:
            trace.append({"kind": "restitution", "output": {}})
            _save_trace(analysis, trace)
            return _finish(analysis, view, trace)
        calls = tuple(getattr(turn, "tool_calls", ()) or ())
        room = MAX_TOOL_CALLS - _tool_count(trace)
        accepted = calls[:room]
        if not accepted:
            raise BrainWorkError(
                code="response_invalid",
                message="La réponse ne contient ni recherche ni restitution.",
            )
        for call in accepted:
            trace.append(
                {
                    "kind": "tool",
                    "tool": call.name,
                    "arguments": call.arguments if isinstance(call.arguments, dict) else {},
                    "item_ids": None,
                    "envelope": None,
                }
            )
        _save_trace(analysis, trace)
        _fill_pending(analysis, view, trace)


def build_messages(view: SealedView, trace: list) -> list[dict]:
    """Prompt, format, initial context, then each committed trace entry."""
    context, _examined = _context(view)
    messages = [
        {"role": "system", "content": metier_prompt()},
        {"role": "format", "content": FORMAT_TEXT},
        {"role": "user", "content": context},
    ]
    for entry in trace:
        kind = entry.get("kind")
        if kind == "instruction":
            messages.append({"role": "user", "content": entry.get("text") or RESTITUTION_SENTENCE})
            continue
        if kind != "tool" or entry.get("envelope") is None:
            continue
        messages.append(
            {
                "role": "assistant",
                "tool_calls": [
                    {"name": entry.get("tool"), "arguments": entry.get("arguments") or {}}
                ],
            }
        )
        messages.append(
            {
                "role": "tool",
                "name": entry.get("tool"),
                "content": render_tool_result(view, entry),
            }
        )
    return messages


def mechanisms_within_budget(
    mechanisms: list[dict],
    *,
    render,
    ceiling: int,
    provider: str,
    model: str,
    tools,
) -> tuple[list[dict], int]:
    """Keep a prefix of active mechanisms. The omitted count is explicit."""
    kept: list[dict] = []
    for mechanism in mechanisms:
        trial = kept + [mechanism]
        if _message_tokens(render(trial), tools, provider, model) > ceiling:
            return kept, len(mechanisms) - len(kept)
        kept = trial
    return kept, 0


def _finish(analysis: BrainAnalysis, view: SealedView, trace: list) -> dict:
    examined = _examined_ids(view, trace)
    result = qualify_restitution(_restitution(trace) or {}, view, trace, examined)
    with transaction.atomic():
        analysis.result = result
        analysis.trace = trace
        analysis.save(update_fields=["result", "trace", "updated_at"])
        persist_completed_analysis(analysis, result)
    return result


def _fill_pending(analysis: BrainAnalysis, view: SealedView, trace: list) -> None:
    context_ids = _context_ids(view)
    examined = _examined_ids(view, trace)
    for entry in trace:
        if entry.get("kind") != "tool" or entry.get("envelope") is not None:
            continue
        fresh_used = len(examined - context_ids)
        body = execute_tool(
            view,
            str(entry.get("tool") or ""),
            entry.get("arguments") or {},
            examined=examined,
            remaining_copies=max(0, MAX_DISTINCT_COPIES - fresh_used),
            consultations_remaining=max(0, MAX_TOOL_CALLS - _tool_count_before(trace, entry) - 1),
        )
        entry["item_ids"] = body["item_ids"]
        entry["envelope"] = body["envelope"]
        _assign_compare_id(trace, entry)
        for item_id in body["item_ids"]:
            if item_id not in _context_ids(view):
                examined.add(item_id)
        _save_trace(analysis, trace)


def _context(view: SealedView) -> tuple[dict, set[str]]:
    analysis = view.dossier.analysis
    provider, model = frozen_counter(analysis.configuration)
    ceiling = _input_ceiling(analysis)
    candidates = [
        _mechanism_view(item)
        for item in view.of("knowledge")
    ]
    def render(selected):
        return _messages_for(view, selected, omitted=0)

    if _message_tokens(render([]), TOOL_SCHEMAS, provider, model) > ceiling:
        raise BrainWorkError(
            code="input_budget_exceeded",
            message="Le contexte dépasse le plafond d'entrée avant toute recherche.",
        )
    kept, omitted = mechanisms_within_budget(
        candidates,
        render=lambda selected: _messages_for(
            view,
            selected,
            omitted=len(candidates) - len(selected),
        ),
        ceiling=ceiling,
        provider=provider,
        model=model,
        tools=TOOL_SCHEMAS,
    )
    # The omitted count used while fitting the last successful prefix is recomputed.
    context = _user_context(view, kept, omitted)
    return context, _context_ids(view, kept)


def _messages_for(view, mechanisms, *, omitted: int) -> list[dict]:
    return [
        {"role": "system", "content": metier_prompt()},
        {"role": "format", "content": FORMAT_TEXT},
        {"role": "user", "content": _user_context(view, mechanisms, omitted)},
    ]


def _user_context(view: SealedView, mechanisms: list[dict], omitted: int) -> dict:
    dossier = view.dossier
    organization = _single_payload(view, "organization")
    activity = _single_payload(view, "establishment_context")
    return {
        "establishment": {
            "id": organization.get("establishment_id"),
            "name": organization.get("name"),
        },
        "period": {
            "start": dossier.period_start.isoformat(),
            "end": dossier.period_end.isoformat(),
        },
        "timezone": dossier.timezone,
        "reference_at": dossier.capture_started_at.isoformat(),
        "reporting": [_anchor_view(item) for item in view.of("document")],
        "organization": {
            "business_units": organization.get("business_units") or [],
            "activities": organization.get("activities") or [],
        },
        "activity_description": activity,
        "mechanisms": mechanisms,
        "mechanisms_omitted": omitted,
        "consultations_remaining": MAX_TOOL_CALLS,
    }


def _examined_ids(view: SealedView, trace: list) -> set[str]:
    context, _ids = _context_ids_and_omitted(view)
    examined = set(context)
    for entry in trace:
        if entry.get("kind") != "tool" or entry.get("envelope") is None:
            continue
        for item_id in entry.get("item_ids") or []:
            examined.add(str(item_id))
    return examined


def _context_ids(view: SealedView, mechanisms: list[dict] | None = None) -> set[str]:
    if mechanisms is None:
        mechanisms = _fitted_mechanisms(view)
    kept = {str(item.get("item_id")) for item in mechanisms}
    ids = set()
    for item in view.items:
        if item.category in {"document", "organization", "establishment_context"}:
            ids.add(str(item.id))
        elif item.category == "knowledge" and str(item.id) in kept:
            ids.add(str(item.id))
    return ids


def _context_ids_and_omitted(view: SealedView) -> tuple[set[str], int]:
    provider, model = frozen_counter(view.dossier.analysis.configuration)
    ceiling = _input_ceiling(view.dossier.analysis)
    candidates = [_mechanism_view(item) for item in view.of("knowledge")]
    kept, omitted = mechanisms_within_budget(
        candidates,
        render=lambda selected: _messages_for(
            view, selected, omitted=len(candidates) - len(selected)
        ),
        ceiling=ceiling,
        provider=provider,
        model=model,
        tools=TOOL_SCHEMAS,
    )
    return _context_ids(view, kept), omitted


def _fitted_mechanisms(view: SealedView) -> list[dict]:
    provider, model = frozen_counter(view.dossier.analysis.configuration)
    ceiling = _input_ceiling(view.dossier.analysis)
    candidates = [_mechanism_view(item) for item in view.of("knowledge")]
    kept, _omitted = mechanisms_within_budget(
        candidates,
        render=lambda selected: _messages_for(
            view, selected, omitted=len(candidates) - len(selected)
        ),
        ceiling=ceiling,
        provider=provider,
        model=model,
        tools=TOOL_SCHEMAS,
    )
    return kept


def _anchor_view(item: BrainDossierItem) -> dict:
    payload = item.payload if isinstance(item.payload, dict) else {}
    kind = "measure" if item.role == "mesure" else "qualitative"
    return {
        "anchor_id": str(item.id),
        "item_id": str(item.id),
        "kind": kind,
        "label": payload.get("label"),
        "value": payload.get("value"),
        "unit": payload.get("unit"),
        "definition": payload.get("definition"),
        "scope": payload.get("scope"),
        "period_start": payload.get("period_start"),
        "period_end": payload.get("period_end"),
        "text": payload.get("text"),
    }


def _mechanism_view(item: BrainDossierItem) -> dict:
    payload = item.payload if isinstance(item.payload, dict) else {}
    return {
        "item_id": str(item.id),
        "identifier": payload.get("identifier"),
        "formulation": payload.get("formulation"),
        "conditions": payload.get("conditions"),
        "limits": payload.get("limits"),
        "uncertainty": payload.get("uncertainty"),
    }


def _single_payload(view: SealedView, category: str) -> dict:
    items = view.of(category)
    if not items:
        return {"availability": "unavailable", "reason": "not_captured"}
    payload = items[0].payload
    return payload if isinstance(payload, dict) else {}


def _assign_compare_id(trace: list, entry: dict) -> None:
    if entry.get("tool") != "compare":
        return
    compare = (entry.get("envelope") or {}).get("compare")
    if not isinstance(compare, dict) or compare.get("compare_id"):
        return
    prior = 0
    for other in trace:
        if other is entry or other.get("tool") != "compare":
            continue
        other_compare = (other.get("envelope") or {}).get("compare")
        if isinstance(other_compare, dict) and other_compare.get("compare_id"):
            prior += 1
    compare["compare_id"] = f"compare:{prior + 1}"


def _ensure_dossier(analysis_id) -> BrainDossier:
    existing = (
        BrainDossier.objects.filter(analysis_id=analysis_id)
        .select_related("analysis")
        .first()
    )
    if existing is None:
        return capture_investigation_dossier(analysis_id)
    if existing.closed_at and existing.items.filter(category="coverage").exists():
        return existing
    raise BrainWorkError(
        code="dossier_already_closed",
        message="Le dossier fermé n'est pas une capture d'investigation.",
    )


def _load_view(dossier: BrainDossier) -> SealedView:
    dossier = BrainDossier.objects.select_related("analysis", "establishment").get(pk=dossier.id)
    items = list(
        BrainDossierItem.objects.filter(dossier_id=dossier.id).order_by("created_at", "id")
    )
    return SealedView(dossier, items)


def _load_analysis(analysis_id) -> BrainAnalysis:
    analysis = BrainAnalysis.objects.filter(pk=analysis_id).first()
    if analysis is None:
        raise BrainWorkError(code="analysis_not_found", message="L'analyse est introuvable.")
    return analysis


def _save_trace(analysis: BrainAnalysis, trace: list) -> None:
    analysis.trace = trace
    analysis.save(update_fields=["trace", "updated_at"])


def _require_budget(analysis: BrainAnalysis, messages: list, tools) -> None:
    provider, model = frozen_counter(analysis.configuration)
    if _message_tokens(messages, tools, provider, model) > _input_ceiling(analysis):
        raise BrainWorkError(
            code="input_budget_exceeded",
            message="Le dialogue dépasse le plafond d'entrée.",
        )


def _message_tokens(messages, tools, provider: str, model: str) -> int:
    return (
        json_token_count({"messages": messages, "tools": tools}, provider=provider, model=model)
        + CALL_FRAMING_TOKENS
    )


def _input_ceiling(analysis: BrainAnalysis) -> int:
    config = analysis.configuration if isinstance(analysis.configuration, dict) else {}
    ceilings = config.get("ceilings") if isinstance(config.get("ceilings"), dict) else {}
    try:
        ceiling = int(ceilings["per_call_input_tokens"])
    except (KeyError, TypeError, ValueError) as exc:
        raise BrainWorkError(
            code="configuration_unusable",
            message="La configuration figée de l'analyse est inutilisable.",
        ) from exc
    if ceiling <= 0:
        raise BrainWorkError(
            code="configuration_unusable",
            message="La configuration figée de l'analyse est inutilisable.",
        )
    return ceiling


def _tools_for(trace: list):
    if _tool_count(trace) >= MAX_TOOL_CALLS or _instruction_sent(trace):
        return []
    return list(TOOL_SCHEMAS)


def _tool_count(trace: list) -> int:
    return sum(1 for entry in trace if entry.get("kind") == "tool")


def _tool_count_before(trace: list, entry: dict) -> int:
    count = 0
    for other in trace:
        if other is entry:
            break
        if other.get("kind") == "tool":
            count += 1
    return count


def _instruction_sent(trace: list) -> bool:
    return any(entry.get("kind") == "instruction" for entry in trace)


def _restitution(trace: list):
    for entry in reversed(trace):
        if entry.get("kind") == "restitution":
            output = entry.get("output")
            return output if isinstance(output, dict) else {}
    return None
