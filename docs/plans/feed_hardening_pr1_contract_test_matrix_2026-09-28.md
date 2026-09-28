# Feed hardening PR1 — matrice des tests contractuels

Cette matrice fixe le propriétaire final des invariants revus en PR1. Elle n'est pas un
inventaire exhaustif des tests Feed : les règles de transition, de permissions et de
concurrence restent couvertes par leurs suites métier propriétaires.

| Invariant | Couche propriétaire | Test conservé |
|---|---|---|
| Signals opérationnels : sortie immédiate d'un résolu et retrait des pins | API contractuelle Signals | `test_signal_feed_contract.py::test_si01_resolve_leaves_feed_and_pins` |
| Signals : ordre global et continuation sans doublon | API contractuelle Signals | `test_signal_feed_contract.py::test_si06_global_page_then_direct_status` |
| Signals : filtre métier conservé dans la continuation et enveloppe slim | API filtres Signals | `test_signal_feed_filters.py::test_pagination_with_bu_filter_returns_next_cursor` |
| Signals : format et validation locale du curseur | Codec Signals | `test_feed_cursor.py` |
| Signals : hints d'un élément en cours cohérents entre feed et détail | API Signals | `test_signal_feed_api.py::test_in_progress_permission_hints_are_consistent_in_feed_and_detail` |
| Signal résolu : détail lisible mais actions opérationnelles interdites, même sur une ancienne pin sale | API détail/lifecycle Signals | `test_signal_cancel_resolve_api.py::test_detail_resolved_denies_operational_hints` |
| Pins Signals Cross : pagination bornée et rejet d'un contexte modifié | API Cross Signals | `test_cross_feeds.py::test_cross_signal_pins_paginate_and_reject_changed_filter_context` |
| Exécution établissement : parcours curseur et continuation sans metadata de première page | API Exécution | `test_execution_feed_api.py::test_feed_pagination_cursor_is_stable` |
| Exécution Cross : liste, metadata et pins séparées | API Cross Exécution | `test_cross_feeds.py::test_cross_execution_feed_pins_use_per_establishment_membership_and_paginate` |
| Fenêtre hydratée : éviction bornée, déduplication, réponse stale et stall | Bibliothèque de fenêtre partagée | `feed-reading-window.test.ts` |
| Signals : une continuation stale ne remplace pas la génération courante et un stall conserve la fenêtre | Hook TanStack Query Signals | `hooks.feed.test.ts` |
| Historique : un jour civil réparti sur deux pages reste un groupe unique | Composition de page History | `history-page.test.tsx::keeps one day group when that day spans two pages` |

Nettoyage associé :

- la compatibilité de helper avec l'ancienne enveloppe `sections` et
  `signal_feed_section` sont supprimés faute de consommateur ;
- le tri d'un résolu via l'ancien queryset de feed est supprimé ;
- les doublons API Signals de sortie terminale et de round-trip curseur sont supprimés ;
- l'accès au détail terminal reste prouvé par History et les permissions, hors des tests
  de projection du feed ;
- le prédicat de non-progression reste testé une seule fois dans la fenêtre partagée ; le
  test du hook Signals couvre uniquement son orchestration et la conservation du cache.
