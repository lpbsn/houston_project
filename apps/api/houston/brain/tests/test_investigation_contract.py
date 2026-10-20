"""Business readings the investigation contract can represent, and the ones it refuses.

No provider call, no publication, and no raw observation.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from houston.brain.investigation_contract import (
    assess_reading,
    causal_evidence_issue,
    correction_rules,
    investigation_prompt,
    investigation_response_schema,
    subject_figures_verified,
)
from houston.brain.numbers import decimal_text


def _ratio(base: str, current: str) -> str:
    return decimal_text((Decimal(current) - Decimal(base)) / Decimal(base))


def _op(item_id: str, value: str, unit: str = "") -> dict:
    return {"item_id": item_id, "value": value, "unit": unit}


def _limit(text: str, effect: str = "coverage", item_ids: list[str] | None = None) -> dict:
    return {"text": text, "effect": effect, "item_ids": item_ids or []}


def _subject(key: str, **extra) -> dict:
    body = {
        "key": key,
        "movement": "qualitative",
        "statement": f"Constat {key}.",
        "examined": True,
        "cause": "unknown",
        "evidence_ids": [],
        "contradiction_ids": [],
        "reported_facts": [],
        "explanations": [],
        "decisive_checks": [],
        "findings": [],
        "calculations": [],
        "breakdowns": [],
        "tradeoffs": [],
        "orientation": "NO_ACTION",
        "justification": "Aucune action nouvelle n'est justifiée.",
        "does_not_promise": "",
        "limits": [_limit("Limite tenue jusqu'à la conclusion.")],
    }
    body.update(extra)
    return body


def _reading(subjects: list[dict], contradictions: list[dict] | None = None) -> dict:
    return {
        "schema_version": "brain_investigation_v3",
        "subjects": subjects,
        "contradictions": contradictions or [],
        "deepening": None,
    }


_BEFORE = ("2026-02-01", "2026-02-08")
_AFTER = ("2026-02-08", "2026-02-15")
_N_MINUS_ONE = ("2025-02-01", "2025-02-08")


def _measure(
    measure_id: str,
    value: str,
    unit: str,
    *,
    definition: str,
    start: tuple[str, str] = _BEFORE,
    scope: str = "etablissement",
    tax: str = "unspecified",
    nature: str = "actual",
    ambiguities: tuple[str, ...] = (),
) -> dict:
    return {
        "measure_id": measure_id,
        "value": value,
        "unit": unit,
        "definition": definition,
        "scope": scope,
        "nature": nature,
        "tax_treatment": tax,
        "period_start": start[0],
        "period_end": start[1],
        "ambiguities": list(ambiguities),
    }


def _catalog(*rows: dict) -> dict[str, dict]:
    return {row["measure_id"]: row for row in rows}


def _assess(payload: dict, **kwargs):
    values = {
        "citable_ids": set(),
        "signal_ids": set(),
        "action_ids": set(),
        "proposed_keys": set(),
        "measures": {},
        "memory_ids": set(),
    }
    values.update(kwargs)
    return assess_reading(payload, **values)


def _variation(
    label: str,
    role: str,
    base: tuple[str, str],
    current: tuple[str, str],
    unit: str,
) -> dict:
    return {
        "operation": "variation",
        "role": role,
        "comparison": "temporal",
        "label": label,
        "operands": [_op(base[0], base[1], unit), _op(current[0], current[1], unit)],
        "published_value": _ratio(base[1], current[1]),
        "unit": "",
    }


def _revenue_breakdown() -> dict:
    return {
        "label": "CA restauration",
        "volume_before": _op("covers-before", "100", "couvert"),
        "volume_after": _op("covers-after", "88", "couvert"),
        "price_before": _op("basket-before", "10", "EUR"),
        "price_after": _op("basket-after", "10", "EUR"),
        "amount_before": _op("revenue-before", "1000", "EUR"),
        "amount_after": _op("revenue-after", "880", "EUR"),
        "volume_effect": "-120",
        "price_effect": "0",
        "amount_difference": "-120",
    }


def _revenue_ids() -> set[str]:
    return {
        "covers-before",
        "covers-after",
        "basket-before",
        "basket-after",
        "revenue-before",
        "revenue-after",
        "signal-wait",
    }


def _revenue_measures() -> dict[str, dict]:
    return _catalog(
        _measure("covers-before", "100", "couvert", definition="couverts"),
        _measure("covers-after", "88", "couvert", definition="couverts", start=_AFTER),
        _measure("basket-before", "10", "EUR", definition="panier"),
        _measure("basket-after", "10", "EUR", definition="panier", start=_AFTER),
        _measure("revenue-before", "1000", "EUR", definition="CA"),
        _measure("revenue-after", "880", "EUR", definition="CA", start=_AFTER),
    )


def test_the_schema_stops_before_plans_objectives_and_knowledge():
    schema = investigation_response_schema()["json_schema"]["schema"]
    subject = schema["$defs"]["subject"]["properties"]
    prompt = investigation_prompt()

    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == {
        "schema_version",
        "subjects",
        "contradictions",
        "deepening",
    }
    for name in (
        "tasks",
        "target",
        "objective",
        "assignees",
        "proposals",
        "mechanisms",
        "suggestions",
        "raw_text",
        "observation",
    ):
        assert name not in subject
        assert name not in schema["properties"]
    assert subject["movement"]["enum"] == [
        "degradation",
        "improvement",
        "stability",
        "qualitative",
    ]
    assert "breakdowns" in subject and "calculations" in subject
    for token in (
        "degradation",
        "improvement",
        "stability",
        "ACTION",
        "INVESTIGATION",
        "NO_ACTION",
        "does_not_promise",
        "not_comparable",
        "observation brute",
        "effet secondaire",
    ):
        assert token in prompt
    assert "objectif" in prompt


_OPENAI_FORBIDDEN_KEYWORDS = frozenset(
    {
        "allOf",
        "oneOf",
        "not",
        "dependentRequired",
        "dependentSchemas",
        "if",
        "then",
        "else",
        "patternProperties",
        "unevaluatedProperties",
        "propertyNames",
        "minProperties",
        "maxProperties",
        "uniqueItems",
        "contains",
        "unevaluatedItems",
    }
)


def test_the_strict_schema_stays_inside_the_openai_subset():
    wrapped = investigation_response_schema()
    spec = wrapped["json_schema"]
    schema = spec["schema"]

    assert wrapped["type"] == "json_schema"
    assert spec["name"] == "brain_investigation_v3"
    assert spec["strict"] is True
    assert schema["type"] == "object"
    assert "anyOf" not in schema

    properties = 0
    enums = 0
    characters = 0

    def walk(node: dict) -> None:
        nonlocal properties, enums, characters
        forbidden = _OPENAI_FORBIDDEN_KEYWORDS.intersection(node)
        assert not forbidden
        if "$ref" in node:
            assert set(node) == {"$ref"}
            return
        if "properties" in node:
            props = node["properties"]
            assert node.get("type") == "object"
            assert node.get("additionalProperties") is False
            assert list(node.get("required", [])) == list(props)
            properties += len(props)
            characters += sum(len(key) for key in props)
            for child in props.values():
                walk(child)
        if node.get("type") == "array":
            assert "items" in node
            walk(node["items"])
        for branch in node.get("anyOf", ()):
            walk(branch)
        if "enum" in node:
            enums += len(node["enum"])
            characters += sum(len(item) for item in node["enum"] if isinstance(item, str))
        if isinstance(node.get("const"), str):
            characters += len(node["const"])
        for name, child in node.get("$defs", {}).items():
            characters += len(name)
            walk(child)

    def depth(node: dict, level: int, defs: dict) -> int:
        if "$ref" in node:
            name = str(node["$ref"]).rsplit("/", 1)[-1]
            return depth(defs[name], level, defs)
        found = level if node.get("type") == "object" else 0
        if "properties" in node:
            nested = [depth(child, level + 1, defs) for child in node["properties"].values()]
            found = max(found, *nested) if nested else found
        if node.get("type") == "array":
            found = max(found, depth(node["items"], level, defs))
        for branch in node.get("anyOf", ()):
            found = max(found, depth(branch, level, defs))
        return found

    walk(schema)
    assert properties <= 5_000
    assert depth(schema, 1, schema["$defs"]) <= 10
    assert enums <= 1_000
    assert characters <= 120_000


def test_the_provider_schema_cannot_state_a_refused_cause_or_a_cited_gap():
    schema = investigation_response_schema()["json_schema"]["schema"]
    explanation = schema["$defs"]["explanation"]["properties"]["status"]
    cited, missing = schema["$defs"]["check"]["anyOf"]
    prompt = investigation_prompt()
    refused = _assess(
        _reading(
            [
                _subject(
                    "ca",
                    explanations=[
                        {
                            "text": "Le document suffirait.",
                            "status": "supported",
                            "support_ids": [],
                            "contradiction_ids": [],
                        }
                    ],
                    decisive_checks=[
                        {
                            "question": "Que manque-t-il ?",
                            "status": "missing",
                            "item_ids": ["measure:0"],
                            "finding": "La vérification n'est pas dans le dossier.",
                        }
                    ],
                )
            ]
        ),
        citable_ids={"measure:0"},
        proposed_keys={"ca"},
    )

    assert explanation["enum"] == ["plausible", "contradicted", "unresolved"]
    assert cited["properties"]["status"]["const"] == "checked"
    assert "item_ids" in cited["properties"]
    assert missing["properties"]["status"]["const"] == "missing"
    assert "item_ids" not in missing["properties"]
    assert "Leur statut est plausible, contradicted ou unresolved." in prompt
    assert "supported ne se pose pas" in prompt
    assert "supported, plausible" not in prompt
    assert refused.errors == ("explanation_not_cause", "missing_check_cited")
    assert correction_rules(refused.errors) == (
        "explanation_not_cause: supported ne se pose pas : "
        "aucun identifiant du dossier ne le porte.",
        "missing_check_cited: Une vérification missing ne cite rien et nomme le manque.",
    )
    assert correction_rules(("duration_base_missing", "missing_check_cited")) == (
        "missing_check_cited: Une vérification missing ne cite rien et nomme le manque.",
    )


def test_positive_negative_and_stable_subjects_all_remain():
    cited = {"down", "down_now", "flat", "flat_now", "rise-a", "rise-b"}
    measures = _catalog(
        _measure("down", "80", "couvert", definition="frequentation"),
        _measure("down_now", "70", "couvert", definition="frequentation", start=_AFTER),
        _measure("flat", "40", "EUR", definition="panier"),
        _measure("flat_now", "40", "EUR", definition="panier", start=_AFTER),
    )
    subjects = [
        _subject(
            "baisse",
            movement="degradation",
            statement="La fréquentation baisse sur une base comparable.",
            calculations=[
                _variation("fréquentation", "gap", ("down", "80"), ("down_now", "70"), "couvert")
            ],
            findings=[
                {
                    "kind": "arithmetic",
                    "text": "70 couverts contre 80 sur la même définition.",
                    "item_ids": ["down", "down_now"],
                }
            ],
            justification="L'écart est établi. Aucune cause opérationnelle ne l'est.",
        ),
        _subject(
            "hausse",
            movement="improvement",
            statement="Le chiffre affiché est plus haut, sur une base qui a changé.",
            findings=[
                {
                    "kind": "reporting",
                    "text": "Les deux colonnes ne partagent ni la durée ni l'unité.",
                    "item_ids": ["rise-a", "rise-b"],
                }
            ],
            limits=[
                _limit(
                    "Périmètre ou unité différents : la hausse n'est pas une performance.",
                    "blocks_comparison",
                    ["rise-a", "rise-b"],
                )
            ],
            justification="Aucune action ne se décide sur deux bases non comparables.",
        ),
        _subject(
            "stable",
            movement="stability",
            statement="Le panier reste à 40.",
            calculations=[_variation("panier", "gap", ("flat", "40"), ("flat_now", "40"), "EUR")],
            findings=[
                {
                    "kind": "arithmetic",
                    "text": "Le panier ne bouge pas.",
                    "item_ids": ["flat", "flat_now"],
                }
            ],
            justification="La stabilité est notable et aucune cause n'est établie.",
        ),
    ]
    proposed = {"baisse", "hausse", "stable"}
    assessment = _assess(
        _reading(subjects),
        citable_ids=cited,
        proposed_keys=proposed,
        measures=measures,
    )

    assert assessment.ok
    reading = assessment.parsed
    assert reading is not None
    assert [subject.movement for subject in reading.subjects] == [
        "degradation",
        "improvement",
        "stability",
    ]
    assert reading.subjects[0].cause == "unknown"
    assert reading.subjects[1].calculations == []
    assert reading.subjects[1].limits[0].effect == "blocks_comparison"
    assert reading.subjects[2].calculations[0].published_value == "0"
    assert reading.subjects[2].explanations == []

    hidden = _assess(
        _reading(subjects[:2]),
        citable_ids=cited,
        proposed_keys=proposed,
        measures=measures,
    )
    assert hidden.errors == ("subject_removed",)

    invented = _subject(
        "hausse",
        movement="improvement",
        calculations=[
            {
                **_variation("faux", "gap", ("rise-a", "5"), ("rise-b", "9"), "EUR"),
                "comparison": "not_comparable",
            }
        ],
    )
    refused = _assess(
        _reading([invented]),
        citable_ids={"rise-a", "rise-b"},
        proposed_keys={"hausse"},
    )
    assert "comparison_refused" in refused.errors


def test_a_cover_drop_explains_the_revenue_gap_without_blaming_the_wait():
    subject = _subject(
        "ca",
        movement="degradation",
        statement="Le CA baisse de 120, soit la baisse des couverts à panier stable.",
        cause="unknown",
        reported_facts=[{"item_id": "signal-wait", "declared_as": "reported"}],
        explanations=[
            {
                "text": (
                    "L'attente au déjeuner est une piste rapportée, "
                    "pas la cause de la fréquentation."
                ),
                "status": "plausible",
                "support_ids": ["signal-wait"],
                "contradiction_ids": [],
            }
        ],
        decisive_checks=[
            {
                "question": "Jours d'ouverture, réservations et annulations.",
                "status": "missing",
                "item_ids": [],
                "finding": "Ces facteurs ne figurent pas dans le dossier.",
            }
        ],
        findings=[
            {
                "kind": "arithmetic",
                "text": "L'effet volume est -120 et l'effet prix est nul.",
                "item_ids": ["revenue-before", "revenue-after", "covers-before", "covers-after"],
            }
        ],
        calculations=[
            _variation(
                "CA",
                "gap",
                ("revenue-before", "1000"),
                ("revenue-after", "880"),
                "EUR",
            ),
            _variation(
                "couverts",
                "component",
                ("covers-before", "100"),
                ("covers-after", "88"),
                "couvert",
            ),
            _variation(
                "panier",
                "component",
                ("basket-before", "10"),
                ("basket-after", "10"),
                "EUR",
            ),
            {
                "operation": "product",
                "role": "identity",
                "comparison": "identity",
                "label": "CA = couverts × panier",
                "operands": [
                    _op("covers-after", "88", "couvert"),
                    _op("basket-after", "10", "EUR"),
                ],
                "published_value": "880",
                "unit": "EUR",
            },
        ],
        breakdowns=[_revenue_breakdown()],
        tradeoffs=[
            {
                "kind": "constraint",
                "text": "La correction de l'attente reste réversible.",
                "item_ids": ["signal-wait"],
            }
        ],
        orientation="ACTION",
        justification=(
            "Traiter l'attente constatée. La baisse des couverts rend compte du CA, "
            "sans prouver que l'attente a fait partir les clients."
        ),
        does_not_promise="Cette action ne rétablit pas la fréquentation.",
        limits=[
            _limit(
                "Le lien entre l'attente et la fréquentation n'est pas démontré.",
                "blocks_cause",
            )
        ],
    )
    assessment = _assess(
        _reading([subject]),
        citable_ids=_revenue_ids(),
        signal_ids={"signal-wait"},
        proposed_keys={"ca"},
        measures=_revenue_measures(),
    )

    assert assessment.ok
    reading = assessment.parsed
    assert reading is not None
    kept = reading.subjects[0]
    assert [row.published_value for row in kept.calculations[:3]] == ["-0.12", "-0.12", "0"]
    assert kept.breakdowns[0].volume_effect == "-120"
    assert kept.breakdowns[0].price_effect == "0"
    assert kept.breakdowns[0].amount_difference == "-120"
    assert kept.cause == "unknown"
    assert kept.reported_facts[0].declared_as == "reported"
    assert kept.explanations[0].status == "plausible"
    assert kept.orientation == "ACTION"
    assert "fréquentation" in kept.does_not_promise
    assert kept.tradeoffs[0].kind == "constraint"

    wrong = _subject(
        "ca",
        movement="degradation",
        breakdowns=[{**_revenue_breakdown(), "volume_effect": "0"}],
        orientation="NO_ACTION",
    )
    refused = _assess(
        _reading([wrong]),
        citable_ids=_revenue_ids(),
        signal_ids={"signal-wait"},
        proposed_keys={"ca"},
        measures=_revenue_measures(),
    )
    assert "not_recomputed" in refused.errors

    promised = {**subject, "does_not_promise": ""}
    bare_action = _assess(
        _reading([promised]),
        citable_ids=_revenue_ids(),
        signal_ids={"signal-wait"},
        proposed_keys={"ca"},
        measures=_revenue_measures(),
    )
    assert "action_promises_unknown_cause" in bare_action.errors

    blamed = {
        **subject,
        "cause": "established",
        "evidence_ids": ["signal-wait"],
        "orientation": "NO_ACTION",
        "does_not_promise": "",
    }
    signal_cause = _assess(
        _reading([blamed]),
        citable_ids=_revenue_ids(),
        signal_ids={"signal-wait"},
        proposed_keys={"ca"},
        measures=_revenue_measures(),
    )
    assert "signal_cause_refused" in signal_cause.errors


def test_competing_leads_stay_open_and_block_an_exclusive_cause():
    mark = {
        "subject_key": "frequentation",
        "item_id": "housing",
        "note": "L'hébergement baisse sur les mêmes dates.",
    }
    subject = _subject(
        "frequentation",
        movement="degradation",
        statement="Deux pistes de la période restent ouvertes.",
        contradiction_ids=["housing"],
        explanations=[
            {
                "text": "Incidents de salle sur une partie de la semaine seulement.",
                "status": "plausible",
                "support_ids": ["service"],
                "contradiction_ids": [],
            },
            {
                "text": "Baisse des clients hébergés, piste concurrente non démontrée.",
                "status": "plausible",
                "support_ids": ["housing"],
                "contradiction_ids": [],
            },
        ],
        decisive_checks=[
            {
                "question": "La baisse d'hébergement couvre-t-elle les mêmes jours ?",
                "status": "checked",
                "item_ids": ["housing"],
                "finding": "Les dates se recouvrent. Cela ne prouve pas la causalité.",
            },
            {
                "question": "Autre facteur de fréquentation encore non lu.",
                "status": "missing",
                "item_ids": [],
                "finding": "Le dossier ne contient pas les réservations.",
            },
        ],
        findings=[
            {
                "kind": "field",
                "text": "Le service et l'hébergement sont tous deux dans la période.",
                "item_ids": ["service", "housing"],
            }
        ],
        orientation="INVESTIGATION",
        justification="Aucune des deux pistes ne peut être retenue seule.",
    )
    assessment = _assess(
        _reading([subject], [mark]),
        citable_ids={"service", "housing"},
        proposed_keys={"frequentation"},
    )

    assert assessment.ok
    reading = assessment.parsed
    assert reading is not None
    assert [row.status for row in reading.subjects[0].explanations] == ["plausible", "plausible"]
    assert reading.contradictions[0].item_id == "housing"
    assert reading.subjects[0].cause == "unknown"

    exclusive = {
        **subject,
        "cause": "established",
        "evidence_ids": ["service"],
        "orientation": "NO_ACTION",
    }
    refused = _assess(
        _reading([exclusive], [mark]),
        citable_ids={"service", "housing"},
        proposed_keys={"frequentation"},
    )
    assert "competing_explanation_open" in refused.errors

    supported = _subject(
        "frequentation",
        explanations=[
            {
                "text": "Le Signal suffirait.",
                "status": "supported",
                "support_ids": ["service"],
                "contradiction_ids": [],
            }
        ],
    )
    signal_only = _assess(
        _reading([supported]),
        citable_ids={"service"},
        signal_ids={"service"},
        proposed_keys={"frequentation"},
    )
    assert "explanation_not_cause" in signal_only.errors


def test_a_cheaper_menu_stays_an_investigation_until_the_economics_are_known():
    cited = {"basket", "basket_now", "covers", "covers_now"}
    measures = _catalog(
        _measure("basket", "25", "EUR", definition="panier"),
        _measure("basket_now", "23", "EUR", definition="panier", start=_AFTER),
        _measure("covers", "80", "couvert", definition="couverts"),
        _measure("covers_now", "80", "couvert", definition="couverts", start=_AFTER),
    )
    subjects = [
        _subject(
            "panier",
            movement="degradation",
            statement=(
                "Le panier baisse de 8 % et la fréquentation ne dit pas si l'offre est rentable."
            ),
            calculations=[
                _variation("panier", "gap", ("basket", "25"), ("basket_now", "23"), "EUR")
            ],
            explanations=[
                {
                    "text": "Les clients peuvent remplacer une offre plus chère.",
                    "status": "unresolved",
                    "support_ids": [],
                    "contradiction_ids": [],
                }
            ],
            decisive_checks=[
                {
                    "question": "Marge contributive de la formule.",
                    "status": "missing",
                    "item_ids": [],
                    "finding": "La marge n'est pas dans le dossier.",
                },
                {
                    "question": "Substitution et nouveaux clients.",
                    "status": "missing",
                    "item_ids": [],
                    "finding": "Ni la substitution ni les nouveaux clients ne sont mesurés.",
                },
            ],
            tradeoffs=[
                {
                    "kind": "cost",
                    "text": "Le panier baisse sans gain de fréquentation mesuré.",
                    "item_ids": ["basket", "basket_now"],
                },
                {
                    "kind": "side_effect",
                    "text": "Une substitution peut compenser une fréquentation stable.",
                    "item_ids": [],
                },
            ],
            orientation="INVESTIGATION",
            justification=(
                "Ni le maintien ni l'arrêt ne se décident avant la marge et la substitution."
            ),
            limits=[_limit("La popularité ne prouve pas la rentabilité.", "narrows_action")],
        ),
        _subject(
            "frequentation",
            movement="stability",
            statement="Les couverts restent à 80.",
            calculations=[
                _variation("couverts", "gap", ("covers", "80"), ("covers_now", "80"), "couvert")
            ],
            justification="La stabilité n'écarte pas un effet de compensation.",
        ),
    ]
    assessment = _assess(
        _reading(subjects),
        citable_ids=cited,
        proposed_keys={"panier", "frequentation"},
        measures=measures,
    )

    assert assessment.ok
    reading = assessment.parsed
    assert reading is not None
    offer = reading.subjects[0]
    assert offer.orientation == "INVESTIGATION"
    assert offer.calculations[0].published_value == "-0.08"
    assert [row.kind for row in offer.tradeoffs] == ["cost", "side_effect"]
    assert offer.explanations[0].status == "unresolved"
    assert reading.subjects[1].movement == "stability"
    assert reading.subjects[1].calculations[0].published_value == "0"

    closed = {
        **subjects[0],
        "decisive_checks": [
            {
                "question": "La marge a été lue.",
                "status": "checked",
                "item_ids": ["basket"],
                "finding": "Seul le panier est connu.",
            }
        ],
    }
    refused = _assess(
        _reading([closed]),
        citable_ids=cited,
        proposed_keys={"panier"},
        measures=measures,
    )
    assert "investigation_without_check" in refused.errors


def test_a_delay_without_a_baseline_asks_for_a_measure():
    subject = _subject(
        "attente",
        movement="qualitative",
        statement="Des attentes au déjeuner sont rapportées. Aucun délai de référence n'existe.",
        cause="reported",
        reported_facts=[{"item_id": "signal-delay", "declared_as": "reported"}],
        decisive_checks=[
            {
                "question": "Délai médian entre commande et service sur des déjeuners comparables.",
                "status": "missing",
                "item_ids": [],
                "finding": "Aucune mesure fiable du délai n'est disponible.",
            }
        ],
        findings=[
            {
                "kind": "field",
                "text": "Le Signal rapporte l'attente. Il ne donne pas de durée.",
                "item_ids": ["signal-delay"],
            }
        ],
        tradeoffs=[
            {
                "kind": "side_effect",
                "text": "Surveiller la charge, la qualité et les autres créneaux.",
                "item_ids": [],
            }
        ],
        orientation="INVESTIGATION",
        justification="Établir une référence avant toute cible chiffrée.",
        limits=[_limit("Une cible de délai serait inventée.", "narrows_action")],
    )
    assessment = _assess(
        _reading([subject]),
        citable_ids={"signal-delay"},
        signal_ids={"signal-delay"},
        proposed_keys={"attente"},
    )

    assert assessment.ok
    reading = assessment.parsed
    assert reading is not None
    kept = reading.subjects[0]
    assert kept.calculations == []
    assert kept.breakdowns == []
    assert kept.orientation == "INVESTIGATION"
    assert kept.decisive_checks[0].status == "missing"
    assert kept.cause == "reported"
    assert "cible" in kept.justification


def test_several_components_recompute_and_a_missing_one_stays_a_limit():
    measures = _catalog(
        _measure("room", "600", "EUR", definition="salle"),
        _measure("terrace", "400", "EUR", definition="terrasse"),
    )
    rate_measures = _catalog(
        _measure("room", "12", "%", definition="salle"),
        _measure("terrace", "8", "%", definition="terrasse"),
    )
    subject = _subject(
        "ca",
        movement="degradation",
        calculations=[
            {
                "operation": "sum",
                "role": "identity",
                "comparison": "identity",
                "label": "CA salle + terrasse",
                "operands": [_op("room", "600", "EUR"), _op("terrace", "400", "EUR")],
                "published_value": "1000",
                "unit": "EUR",
            }
        ],
        findings=[
            {
                "kind": "arithmetic",
                "text": "Les deux zones recomposent 1000.",
                "item_ids": ["room", "terrace"],
            }
        ],
        limits=[_limit("La marge contributive est absente.", "blocks_cause")],
        justification="La composition est connue. La marge ne l'est pas.",
    )
    assessment = _assess(
        _reading([subject]),
        citable_ids={"room", "terrace"},
        proposed_keys={"ca"},
        measures=measures,
    )

    assert assessment.ok
    reading = assessment.parsed
    assert reading is not None
    assert reading.subjects[0].calculations[0].published_value == "1000"
    assert reading.subjects[0].limits[0].effect == "blocks_cause"
    assert all(operand.value != "0" for operand in reading.subjects[0].calculations[0].operands)

    short = {
        **subject,
        "calculations": [
            {**subject["calculations"][0], "published_value": "900"},
        ],
    }
    refused = _assess(
        _reading([short]),
        citable_ids={"room", "terrace"},
        proposed_keys={"ca"},
        measures=measures,
    )
    assert "not_recomputed" in refused.errors

    rates = {
        **subject,
        "calculations": [
            {
                "operation": "sum",
                "role": "component",
                "comparison": "identity",
                "label": "taux",
                "operands": [_op("room", "12", "%"), _op("terrace", "8", "%")],
                "published_value": "20",
                "unit": "%",
            }
        ],
    }
    summed_rates = _assess(
        _reading([rates]),
        citable_ids={"room", "terrace"},
        proposed_keys={"ca"},
        measures=rate_measures,
    )
    assert "rate_not_summable" in summed_rates.errors


def test_findings_limits_and_contradictions_stay_attached_to_the_subject():
    mark = {
        "subject_key": "service",
        "item_id": "late",
        "note": "Les incidents sont en début de période, la baisse à la fin.",
    }
    subject = _subject(
        "service",
        movement="degradation",
        contradiction_ids=["late"],
        explanations=[
            {
                "text": "Les incidents du début n'expliquent pas la baisse de fin de période.",
                "status": "contradicted",
                "support_ids": ["early"],
                "contradiction_ids": ["late"],
            }
        ],
        findings=[
            {
                "kind": "field",
                "text": "La chronologie sépare les incidents et la baisse.",
                "item_ids": ["early", "late"],
            }
        ],
        limits=[
            _limit(
                "Le statut actuel du Signal n'est pas celui de la période.",
                "blocks_cause",
                ["late"],
            )
        ],
        justification="La coïncidence ne suffit pas.",
    )
    assessment = _assess(
        _reading([subject], [mark]),
        citable_ids={"early", "late"},
        proposed_keys={"service"},
    )

    assert assessment.ok
    reading = assessment.parsed
    assert reading is not None
    kept = reading.subjects[0]
    assert kept.findings[0].item_ids == ["early", "late"]
    assert kept.limits[0].effect == "blocks_cause"
    assert kept.explanations[0].contradiction_ids == ["late"]
    assert reading.contradictions[0].subject_key == "service"

    loose = _subject(
        "service",
        findings=[{"kind": "field", "text": "Sans source.", "item_ids": []}],
    )
    assert (
        "finding_without_source"
        in _assess(
            _reading([loose]),
            proposed_keys={"service"},
        ).errors
    )

    detached = {
        **subject,
        "contradiction_ids": [],
    }
    assert (
        "contradiction_detached"
        in _assess(
            _reading([detached], [mark]),
            citable_ids={"early", "late"},
            proposed_keys={"service"},
        ).errors
    )

    foreign = _subject(
        "service",
        findings=[{"kind": "field", "text": "Mémoire.", "item_ids": ["memory-1"]}],
    )
    memory = _assess(
        _reading([foreign]),
        citable_ids=set(),
        memory_ids={"memory-1"},
        proposed_keys={"service"},
    )
    assert memory.errors == ("memory_not_evidence",)

    smuggled = _reading([_subject("service")])
    smuggled["raw_text"] = "OBSERVATION-BRUTE"
    assert _assess(smuggled).errors == ("forbidden_material",)


def test_a_stable_subject_cannot_carry_a_nonzero_gap():
    measures = _catalog(
        _measure("before", "25", "EUR", definition="panier"),
        _measure("after", "23", "EUR", definition="panier", start=_AFTER),
    )
    subject = _subject(
        "panier",
        movement="stability",
        calculations=[_variation("panier", "gap", ("before", "25"), ("after", "23"), "EUR")],
    )
    assessment = _assess(
        _reading([subject]),
        citable_ids={"before", "after"},
        proposed_keys={"panier"},
        measures=measures,
    )
    assert "movement_conflict" in assessment.errors


def test_stability_refuses_a_nonzero_difference_without_reading_its_sign_as_meaning():
    measures = _catalog(
        _measure("before", "25", "EUR", definition="panier"),
        _measure("after", "23", "EUR", definition="panier", start=_AFTER),
    )
    difference = {
        "operation": "difference",
        "role": "gap",
        "comparison": "temporal",
        "label": "panier",
        "operands": [_op("before", "25", "EUR"), _op("after", "23", "EUR")],
        "published_value": "2",
        "unit": "EUR",
    }
    stable = _assess(
        _reading([_subject("panier", movement="stability", calculations=[difference])]),
        citable_ids={"before", "after"},
        proposed_keys={"panier"},
        measures=measures,
    )
    assert "movement_conflict" in stable.errors

    improved = _assess(
        _reading(
            [
                _subject(
                    "panier",
                    movement="improvement",
                    calculations=[
                        _variation("panier", "gap", ("before", "25"), ("after", "23"), "EUR")
                    ],
                )
            ]
        ),
        citable_ids={"before", "after"},
        proposed_keys={"panier"},
        measures=measures,
    )
    assert improved.ok

    qualitative = _assess(
        _reading(
            [
                _subject(
                    "panier",
                    movement="qualitative",
                    calculations=[
                        _variation("panier", "gap", ("before", "25"), ("after", "23"), "EUR")
                    ],
                )
            ]
        ),
        citable_ids={"before", "after"},
        proposed_keys={"panier"},
        measures=measures,
    )
    assert "movement_conflict" in qualitative.errors


def test_an_operand_must_match_the_cited_measure():
    measures = _catalog(
        _measure("before", "1000", "EUR", definition="CA"),
        _measure("after", "880", "EUR", definition="CA", start=_AFTER),
    )
    subject = _subject(
        "ca",
        movement="degradation",
        calculations=[_variation("CA", "gap", ("before", "1000"), ("after", "7777"), "EUR")],
    )
    assessment = _assess(
        _reading([subject]),
        citable_ids={"before", "after"},
        proposed_keys={"ca"},
        measures=measures,
    )
    assert "operand_value_mismatch" in assessment.errors

    elsewhere = _catalog(
        _measure("before", "12", "EUR", definition="CA"),
        _measure("after", "10", "EUR", definition="CA"),
        _measure("decoy", "120", "EUR", definition="autre"),
    )
    borrowed = _subject(
        "ca",
        movement="degradation",
        calculations=[
            {
                "operation": "product",
                "role": "identity",
                "comparison": "identity",
                "label": "produit",
                "operands": [_op("before", "12", "EUR"), _op("after", "10", "EUR")],
                "published_value": "120",
                "unit": "EUR",
            }
        ],
    )
    accepted = _assess(
        _reading([borrowed]),
        citable_ids={"before", "after", "decoy"},
        proposed_keys={"ca"},
        measures=elsewhere,
    )
    assert accepted.ok
    swapped = _subject(
        "ca",
        movement="degradation",
        calculations=[
            {
                **borrowed["calculations"][0],
                "operands": [_op("before", "120", "EUR"), _op("after", "10", "EUR")],
                "published_value": "1200",
            }
        ],
    )
    stolen = _assess(
        _reading([swapped]),
        citable_ids={"before", "after", "decoy"},
        proposed_keys={"ca"},
        measures=elsewhere,
    )
    assert "operand_value_mismatch" in stolen.errors


def test_a_comparison_uses_the_frozen_measure_conditions():
    ht = _measure("before", "100", "EUR", definition="CA", tax="ht")
    ttc = _measure("after", "110", "EUR", definition="CA", tax="ttc", start=_AFTER)
    mixed_tax = _assess(
        _reading(
            [
                _subject(
                    "ca",
                    movement="degradation",
                    calculations=[
                        _variation("CA", "gap", ("before", "100"), ("after", "110"), "EUR")
                    ],
                )
            ]
        ),
        citable_ids={"before", "after"},
        proposed_keys={"ca"},
        measures=_catalog(ht, ttc),
    )
    assert "tax_mismatch" in mixed_tax.errors

    other_scope = _assess(
        _reading(
            [
                _subject(
                    "ca",
                    movement="degradation",
                    calculations=[
                        _variation("CA", "gap", ("before", "100"), ("after", "110"), "EUR")
                    ],
                )
            ]
        ),
        citable_ids={"before", "after"},
        proposed_keys={"ca"},
        measures=_catalog(
            _measure("before", "100", "EUR", definition="CA", scope="salle"),
            _measure("after", "110", "EUR", definition="CA", scope="terrasse", start=_AFTER),
        ),
    )
    assert "scope_mismatch" in other_scope.errors


def test_an_action_or_a_measure_is_not_an_established_cause():
    action = _assess(
        _reading([_subject("service", cause="established", evidence_ids=["plan-1"])]),
        citable_ids={"plan-1"},
        action_ids={"plan-1"},
        proposed_keys={"service"},
    )
    assert "action_not_cause" in action.errors

    measured = _assess(
        _reading([_subject("ca", cause="established", evidence_ids=["measure:0"])]),
        citable_ids={"measure:0"},
        proposed_keys={"ca"},
        measures=_catalog(_measure("measure:0", "80", "couvert", definition="frequentation")),
    )
    assert "measurement_not_cause" in measured.errors


_ROLES = ("gap", "component", "identity")


def _calculation(
    operation: str,
    role: str,
    operands: list[dict],
    published: str,
    unit: str,
) -> dict:
    comparison = "temporal" if operation in {"variation", "difference"} else "identity"
    return {
        "operation": operation,
        "role": role,
        "comparison": comparison,
        "label": operation,
        "operands": operands,
        "published_value": published,
        "unit": unit,
    }


def _published(operation: str, values: tuple[str, ...]) -> str:
    numbers = tuple(Decimal(value) for value in values)
    if operation == "variation":
        return decimal_text((numbers[1] - numbers[0]) / numbers[0])
    if operation == "difference":
        return decimal_text(numbers[0] - numbers[1])
    if operation == "product":
        return decimal_text(numbers[0] * numbers[1])
    if operation == "ratio":
        return decimal_text(numbers[0] / numbers[1])
    return decimal_text(sum(numbers, Decimal(0)))


@pytest.mark.parametrize("role", _ROLES)
def test_relabeling_an_operation_does_not_bypass_measure_compatibility(role):
    left = _measure("left", "100", "EUR", definition="CA", tax="ht")
    right = _measure("right", "80", "EUR", definition="CA", tax="ttc", start=_AFTER)
    ambiguous = _measure(
        "ambiguous",
        "50",
        "EUR",
        definition="CA",
        tax="unspecified",
        ambiguities=("ht_ttc",),
    )
    budget = _measure("budget", "90", "EUR", definition="CA", tax="ht", nature="budget")
    earlier = _measure("earlier", "70", "EUR", definition="CA", tax="ht", start=_N_MINUS_ONE)
    same_ttc = _measure("same-ttc", "120", "EUR", definition="CA", tax="ttc")
    room = _measure("room", "600", "EUR", definition="salle", scope="salle", tax="ht")
    terrace = _measure("terrace", "400", "EUR", definition="terrasse", scope="terrasse", tax="ht")
    covers = _measure("covers", "88", "couvert", definition="couverts", tax="unspecified")
    price = _measure("price", "10", "EUR", definition="panier", tax="ht")
    catalog = _catalog(
        left, right, ambiguous, budget, earlier, same_ttc, room, terrace, covers, price
    )
    refused = (
        ("variation", (left, right), "tax_mismatch"),
        ("difference", (left, right), "tax_mismatch"),
        ("sum", (left, same_ttc), "tax_mismatch"),
        ("product", (left, same_ttc), "tax_mismatch"),
        ("ratio", (left, same_ttc), "tax_mismatch"),
        ("variation", (left, ambiguous), "ambiguous"),
        ("sum", (room, ambiguous), "ambiguous"),
        ("product", (covers, ambiguous), "ambiguous"),
        ("sum", (left, budget), "nature_mixed"),
        ("product", (left, budget), "nature_mixed"),
        ("ratio", (left, budget), "nature_mixed"),
        ("sum", (left, earlier), "period_mismatch"),
        ("product", (left, earlier), "period_mismatch"),
        ("ratio", (left, earlier), "period_mismatch"),
    )
    for operation, terms, code in refused:
        operands = [_op(term["measure_id"], term["value"], term["unit"]) for term in terms]
        published = _published(operation, tuple(term["value"] for term in terms))
        unit = "" if operation in {"variation", "ratio", "product"} else terms[0]["unit"]
        assessment = _assess(
            _reading(
                [
                    _subject(
                        "ca",
                        movement="degradation",
                        calculations=[
                            _calculation(operation, role, operands, published, unit),
                        ],
                    )
                ]
            ),
            citable_ids={term["measure_id"] for term in terms},
            proposed_keys={"ca"},
            measures=catalog,
        )
        assert code in assessment.errors, (operation, role)
        assert assessment.ok is False

    accepted = (
        (
            "variation",
            (earlier, left),
            "degradation",
            {"earlier", "left"},
        ),
        (
            "difference",
            (earlier, left),
            "degradation",
            {"earlier", "left"},
        ),
        ("sum", (room, terrace), "degradation", {"room", "terrace"}),
        ("product", (covers, price), "degradation", {"covers", "price"}),
        ("ratio", (price, covers), "degradation", {"price", "covers"}),
    )
    for operation, terms, movement, cited in accepted:
        operands = [_op(term["measure_id"], term["value"], term["unit"]) for term in terms]
        published = _published(operation, tuple(term["value"] for term in terms))
        unit = "" if operation in {"variation", "ratio", "product"} else terms[0]["unit"]
        assessment = _assess(
            _reading(
                [
                    _subject(
                        "ca",
                        movement=movement,
                        calculations=[_calculation(operation, role, operands, published, unit)],
                    )
                ]
            ),
            citable_ids=cited,
            proposed_keys={"ca"},
            measures=catalog,
        )
        assert assessment.ok, (operation, role, assessment.errors)


@pytest.mark.parametrize("role", _ROLES)
def test_a_movement_does_not_follow_the_role_written_on_the_figure(role):
    before = _measure("before", "25", "EUR", definition="panier")
    after = _measure("after", "23", "EUR", definition="panier", start=_AFTER)
    base = _measure("base", "40", "EUR", definition="panier")
    flat = _measure("flat", "40", "EUR", definition="panier", start=_AFTER)
    room = _measure("room", "600", "EUR", definition="salle", scope="salle")
    terrace = _measure("terrace", "400", "EUR", definition="terrasse", scope="terrasse")
    measures = _catalog(before, after, base, flat, room, terrace)
    change = _variation("panier", role, ("before", "25"), ("after", "23"), "EUR")
    gap = _calculation(
        "difference",
        role,
        [_op("before", "25", "EUR"), _op("after", "23", "EUR")],
        "2",
        "EUR",
    )
    stable = _variation("panier", role, ("base", "40"), ("flat", "40"), "EUR")
    level = _calculation(
        "sum",
        role,
        [_op("room", "600", "EUR"), _op("terrace", "400", "EUR")],
        "1000",
        "EUR",
    )

    def verdict(movement: str, calculations: list[dict]):
        return _assess(
            _reading([_subject("panier", movement=movement, calculations=calculations)]),
            citable_ids={"before", "after", "base", "flat", "room", "terrace"},
            proposed_keys={"panier"},
            measures=measures,
        )

    assert "movement_conflict" in verdict("stability", [change]).errors
    assert "movement_conflict" in verdict("stability", [gap]).errors
    assert "movement_conflict" in verdict("qualitative", [change]).errors
    assert "movement_conflict" in verdict("qualitative", [gap]).errors
    assert "movement_conflict" in verdict("qualitative", [level]).errors
    assert verdict("stability", [stable]).ok
    assert verdict("improvement", [change]).ok
    assert verdict("stability", [level]).ok


def test_a_declared_source_is_not_causal_proof_and_only_recomputed_figures_qualify():
    sources = {
        "signal_ids": {"signal-1"},
        "action_ids": {"plan-1"},
        "measure_ids": {"measure:0"},
        "reporting_ids": {"reporting-1"},
    }
    claims = (
        (["reporting-1"], "reporting_not_cause"),
        (["signal-1"], "signal_cause_refused"),
        (["plan-1"], "action_not_cause"),
        (["measure:0"], "measurement_not_cause"),
        (["measure:0", "reporting-1"], "reporting_not_cause"),
        (["invented-lead"], "source_not_cause"),
        ([], "cause_without_evidence"),
    )
    for evidence, code in claims:
        assert causal_evidence_issue(evidence, **sources) == code
        assessment = _assess(
            _reading([_subject("ca", cause="established", evidence_ids=evidence)]),
            citable_ids=set(evidence),
            signal_ids=sources["signal_ids"],
            action_ids=sources["action_ids"],
            reporting_ids=sources["reporting_ids"],
            proposed_keys={"ca"},
            measures=_catalog(_measure("measure:0", "80", "couvert", definition="frequentation")),
        )
        assert code in assessment.errors

    supported = _subject(
        "ca",
        explanations=[
            {
                "text": "Le document suffirait.",
                "status": "supported",
                "support_ids": ["invented-lead"],
                "contradiction_ids": [],
            }
        ],
    )
    assert (
        "explanation_not_cause"
        in _assess(
            _reading([supported]),
            citable_ids={"invented-lead"},
            proposed_keys={"ca"},
        ).errors
    )

    mixed = _subject(
        "ca",
        movement="degradation",
        calculations=[
            _calculation(
                "sum",
                "identity",
                [_op("ht", "100", "EUR"), _op("ttc", "120", "EUR")],
                "220",
                "EUR",
            )
        ],
    )
    measures = _catalog(
        _measure("ht", "100", "EUR", definition="CA", tax="ht"),
        _measure("ttc", "120", "EUR", definition="CA", tax="ttc"),
        _measure("before", "100", "couvert", definition="frequentation"),
        _measure("after", "80", "couvert", definition="frequentation", start=_AFTER),
    )
    assert (
        subject_figures_verified(
            mixed,
            measures=measures,
            signal_ids=set(),
            action_ids=set(),
        )
        is False
    )
    verified = _subject(
        "ca",
        movement="degradation",
        calculations=[
            _variation(
                "frequentation",
                "component",
                ("before", "100"),
                ("after", "80"),
                "couvert",
            )
        ],
    )
    assert subject_figures_verified(
        verified,
        measures=measures,
        signal_ids=set(),
        action_ids=set(),
    )
