# Golden pipeline v3 ↔ v4 mapping (Lot 1 baseline — revue statique)

Source v3: `apps/api/houston/signals/tests/test_observation_pipeline_v3_golden.py` (9 tests)
Source v4: `apps/api/houston/testing/pipeline_golden_v4_corpus.json` (11 cas G01–G11, paramétrisés dans `test_pipeline_v4_golden.py`)

## Tableau de correspondance

| v3 test | Scénario v3 (résumé) | Cas v4 équivalent | Couverture v4 | Notes |
|---------|----------------------|-------------------|---------------|-------|
| `test_g1_clim_hs_chambre_104_transversal_maintenance` | Clim HS ch.104 → hotel/maintenance/climatisation transversal | **Aucun cas direct** | — | Routage transversal CVC ; v4 G03–G06 couvrent d'autres routages (ménage/plomberie/ascenseur) |
| `test_g2_lumiere_hs_restaurant_maintenance_transversal` | Lumière HS restaurant → maintenance transversal | **Aucun cas direct** | — | Même famille « transversal » que G1, scénario électricité distinct |
| `test_g3_lumiere_hs_restaurant_local_maintenance_subject` | Lumière HS → maintenance locale au restaurant | **Aucun cas direct** | — | Responsable non transversal sur même pôle ; pas de `issue_focus` |
| `test_g4_sale_chambre_104_hotel_proprete` | Sale ch.104 → hotel/propreté chambre | **Aucun cas direct** | — | Propreté chambre ; v4 G03/G05 traitent ménage couloir/verre, pas chambre |
| `test_g5_stock_au_bar` | Stock bar → bar/bar/stock | **Partiel** G01, G02 | Oui (issue_focus) | v3 = signal unique ; v4 G01 = 2 signals (pain + mojito), G02 = pain avec mojito actif |
| `test_g6_subject_hors_responsible_rejected` | Subject attaché au mauvais BU → rejet | **Aucun cas direct** | — | Règle validation apply ; v4 corpus n'a aucun `rejected_count > 0` |
| `test_g7_non_transversal_responsible_rejected` | Responsible non transversal inter-pôles → rejet | **Aucun cas direct** | — | Idem ; couvert ailleurs par `test_pipeline_validation.py` (hors PR) |
| `test_g8_business_unit_description_in_pipeline_input` | `build_pipeline_input` inclut description BU | **Aucun cas direct** | — | Test input-side, pas apply ; **unique v3** |
| `test_no_signal_created_when_candidates_empty` | Candidats vides → NO_SIGNAL_CREATED | **Aucun cas direct** | — | Edge case apply ; absent du corpus v4 |

## Synthèse factuelle

- **9 tests v3** ; **11 cas v4** (numérotation différente : G01≠G1).
- **0 correspondance 1:1** par identifiant ou scénario identique.
- **1 chevauchement thématique partiel** : stock bar (v3 G5 ↔ v4 G01/G02) avec assertions différentes (v4 exige `issue_focus`).
- **2 règles de rejet v3 (G6, G7)** : non présentes dans le corpus v4 ; à croiser avec `test_pipeline_validation.py` (marqué `slow`, exclu PR).
- **2 tests v3 sans équivalent v4** : G8 (pipeline input), `no_signal_created_when_candidates_empty`.

## Fichiers v4-only (non couverts par v3)

| Cas v4 | Description courte |
|--------|-------------------|
| G01 | 2 ruptures stock distinctes (pain + sirop mojito) → 2 signals |
| G02 | Signal mojito actif + pain → nouveau signal |
| G03 | Eau couloir → ménage (pas plomberie) |
| G04 | Fuite couloir → plomberie (pas ménage) |
| G05 | Verre ascenseurs → ménage (pas panne ascenseur) |
| G06 | Ascenseur panne → équipements d'exploitation |
| G07 | Agrégation légitime sirop mojito |
| G08 | Non-agrégation pain vs mojito actif |
| G09 | Reformulation mojito syrup → nouveau signal |
| G10 | Pain blanc vs pain actif → nouveau signal |
| G11 | Climatisation ch.104 vs propreté chambre (disambiguation issue_focus) |
