from __future__ import annotations

import pytest

from houston.establishments.catalog_import import preflight_catalog_import_from_rows
from houston.establishments.catalog_source_normalization import (
    load_normalized_activity_subject_rows,
    load_normalized_business_unit_rows,
)

pytestmark = pytest.mark.django_db

# Validated Mr.Bricolage Nancy seed: dedicated retail poles, transversal support poles.
MRBRICOLAGE_NANCY_UNIT_TYPES = {
    "decoration": "dedicated",
    "jardin": "dedicated",
    "technique": "dedicated",
    "caisse_accueil": "transversal",
    "logistique": "transversal",
    "sav": "transversal",
    "administration_direction": "transversal",
    "entretien_securite": "transversal",
}

MRBRICOLAGE_NANCY_SUBJECT_BUSINESS_UNITS = {
    "decoration__clientele": "decoration",
    "decoration__offre": "decoration",
    "decoration__stocks": "decoration",
    "decoration__prix": "decoration",
    "decoration__presentation": "decoration",
    "decoration__saisonnalite": "decoration",
    "decoration__fournisseurs": "decoration",
    "decoration__organisation": "decoration",
    "decoration__proprete": "decoration",
    "decoration__pertes": "decoration",
    "jardin__clientele": "jardin",
    "jardin__offre": "jardin",
    "jardin__stocks": "jardin",
    "jardin__prix": "jardin",
    "jardin__presentation": "jardin",
    "jardin__saisonnalite": "jardin",
    "jardin__fournisseurs": "jardin",
    "jardin__organisation": "jardin",
    "jardin__proprete": "jardin",
    "jardin__pertes": "jardin",
    "jardin__vegetaux": "jardin",
    "technique__clientele": "technique",
    "technique__offre": "technique",
    "technique__stocks": "technique",
    "technique__prix": "technique",
    "technique__presentation": "technique",
    "technique__saisonnalite": "technique",
    "technique__fournisseurs": "technique",
    "technique__organisation": "technique",
    "technique__proprete": "technique",
    "technique__pertes": "technique",
    "caisse_accueil__accueil": "caisse_accueil",
    "caisse_accueil__encaissement": "caisse_accueil",
    "caisse_accueil__fidelite": "caisse_accueil",
    "caisse_accueil__reclamations": "caisse_accueil",
    "caisse_accueil__pickup": "caisse_accueil",
    "caisse_accueil__commandes_web": "caisse_accueil",
    "caisse_accueil__prix": "caisse_accueil",
    "caisse_accueil__presentation": "caisse_accueil",
    "caisse_accueil__stocks": "caisse_accueil",
    "caisse_accueil__saisonnalite": "caisse_accueil",
    "caisse_accueil__organisation": "caisse_accueil",
    "logistique__reception": "logistique",
    "logistique__stockage": "logistique",
    "logistique__inventaires": "logistique",
    "logistique__livraisons": "logistique",
    "logistique__dechets": "logistique",
    "logistique__equipements": "logistique",
    "logistique__organisation": "logistique",
    "sav__prise_en_charge": "sav",
    "sav__reparations": "sav",
    "sav__garanties": "sav",
    "sav__retours": "sav",
    "sav__fournisseurs": "sav",
    "sav__delais": "sav",
    "administration_direction__rh": "administration_direction",
    "administration_direction__plannings": "administration_direction",
    "administration_direction__facturation": "administration_direction",
    "administration_direction__comptabilite": "administration_direction",
    "administration_direction__donnees": "administration_direction",
    "administration_direction__communication": "administration_direction",
    "administration_direction__commercial": "administration_direction",
    "administration_direction__evenements": "administration_direction",
    "entretien_securite__nettoyage": "entretien_securite",
    "entretien_securite__maintenance": "entretien_securite",
    "entretien_securite__securite": "entretien_securite",
}


def test_mrbricolage_nancy_catalog_keys_attachment_and_preflight():
    business_unit_rows = load_normalized_business_unit_rows()
    activity_subject_rows = load_normalized_activity_subject_rows()
    business_units = {row.key: row for row in business_unit_rows}
    subjects = {row.key: row for row in activity_subject_rows}

    assert len(business_units) == len(business_unit_rows) == 27
    assert len(subjects) == len(activity_subject_rows) == 227
    assert len(MRBRICOLAGE_NANCY_UNIT_TYPES) == 8
    assert len(MRBRICOLAGE_NANCY_SUBJECT_BUSINESS_UNITS) == 66

    missing_units = sorted(set(MRBRICOLAGE_NANCY_UNIT_TYPES) - set(business_units))
    assert not missing_units, missing_units
    for key, unit_type in MRBRICOLAGE_NANCY_UNIT_TYPES.items():
        assert business_units[key].unit_type == unit_type

    missing_subjects = sorted(
        set(MRBRICOLAGE_NANCY_SUBJECT_BUSINESS_UNITS) - set(subjects)
    )
    assert not missing_subjects, missing_subjects
    for key, business_unit_key in MRBRICOLAGE_NANCY_SUBJECT_BUSINESS_UNITS.items():
        assert subjects[key].catalog_business_unit_key == business_unit_key
        assert business_unit_key in MRBRICOLAGE_NANCY_UNIT_TYPES

    preflight_catalog_import_from_rows(
        business_unit_rows=business_unit_rows,
        activity_subject_rows=activity_subject_rows,
    )
