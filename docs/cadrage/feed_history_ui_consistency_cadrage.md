# SPORE — Feed UI consistency & History

## 1. Objectif

Consolider l’expérience des feeds SPORE et remettre `/history` au même niveau de qualité et de cohérence que les interfaces Observations et Exécution déjà travaillées.

Le chantier couvre :

- cohérence UI entre Signal, Exécution et Historique ;
- densité et lisibilité mobile / desktop ;
- filtres et contrôles de vue ;
- refresh ;
- sections épinglées ;
- cartes terminales ;
- placement d’Historique dans la navigation ;
- évolution ciblée des fenêtres de visibilité des éléments terminaux.

L’objectif n’est pas de reconstruire l’architecture des feeds.

---

# 2. Principes et invariants

- Mobile et desktop restent un même produit avec les mêmes contrats fonctionnels.
- Les adaptations de présentation peuvent différer lorsque les usages le justifient.
- Les chips actuelles du feed Signal constituent la référence visuelle des filtres.
- Les patterns déjà validés dans SPORE doivent être réutilisés lorsqu’ils correspondent réellement au besoin.
- Une factorisation n’est attendue que lorsqu’une duplication ou responsabilité commune réelle le justifie.
- Ne pas créer d’abstraction générique uniquement pour homogénéiser artificiellement plusieurs surfaces.
- Préserver les comportements déjà stabilisés : pagination cursor, infinite scroll, mémoire de lecture, cache, realtime, optimistic updates, Cross et retour depuis détail.
- Les modifications fonctionnelles explicites de ce document priment sur les anciens délais ou présentations.
- Ne pas profiter de ce chantier pour effectuer une refonte adjacente non demandée.

---

# 3. Fenêtres de visibilité terminale

Les éléments terminaux restent temporairement visibles dans leur feed avant de devenir accessibles uniquement via Historique.

Cette évolution remplace les fenêtres terminales actuellement appliquées.

Elle concerne les feeds établissement **et Cross** lorsque ces objets y sont exposés.

Elle ne change pas :

- la signification des statuts ;
- les transitions métier ;
- les permissions ;
- l’éligibilité aux actions ;
- les règles de pin ;
- le fonctionnement de l’Historique.

Seule la durée de présence dans le feed opérationnel change.

## 3.1 Signal annulé

Un Signal annulé reste visible dans le feed pendant les **48 heures suivant son événement métier d’annulation**.

À partir de :

`canceled_at + 48 h`

il ne doit plus apparaître dans le feed opérationnel.

Il reste accessible dans Historique.

## 3.2 Signal résolu

Un Signal résolu reste visible dans le feed pendant les **10 jours suivant son événement métier de résolution**.

À partir de :

`resolved_at + 10 jours`

il ne doit plus apparaître dans le feed opérationnel.

Il reste accessible dans Historique.

## 3.3 Exécution annulée

Une Exécution annulée reste visible dans le feed pendant les **48 heures suivant son événement métier d’annulation**.

À partir de :

`canceled_at + 48 h`

elle ne doit plus apparaître dans le feed opérationnel.

Elle reste accessible dans Historique.

## 3.4 Exécution validée

Une Exécution ayant atteint son état terminal à la suite de la **validation métier existante** reste visible dans le feed pendant les **10 jours suivant cette validation**.

À partir de :

`validated_at + 10 jours`

elle ne doit plus apparaître dans le feed opérationnel.

Elle reste accessible dans Historique.

Cursor doit vérifier le modèle de domaine actuel afin d’utiliser l’événement/timestamp canonique correspondant réellement à cette validation.

Ne pas redéfinir ici la différence entre `pending_validation`, `done`, validation ou autres transitions existantes.

## 3.5 Règles communes

- Utiliser les timestamps métier canoniques existants.
- Ne pas dériver ces fenêtres depuis un `updated_at` générique.
- Conserver les règles existantes de classement/positionnement des éléments terminaux dans les feeds ; ce chantier modifie leur **durée de visibilité**, pas leur logique de tri sans nécessité démontrée.
- Un objet devenu terminal ne devient pas pinnable du fait de sa présence temporaire dans le feed.
- Les comportements existants de retrait de pin lors d’une transition terminale restent applicables.
- À la frontière exacte du délai, l’élément n’appartient plus au feed opérationnel.
- L’Historique ne doit pas attendre la fin de cette fenêtre pour connaître l’élément : pendant la période de coexistence, le contrat actuel d’Historique reste inchangé.

---

# 4. `/history`

`/history` doit devenir une continuité naturelle des feeds Signal et Exécution.

Il ne doit plus donner l’impression d’utiliser une ancienne génération d’UI.

## 4.1 Cartes

Les éléments Signal et Exécution affichés dans Historique doivent reprendre **exactement le rendu des variantes terminales déjà validées pour leurs feeds respectifs**, sur mobile comme sur desktop.

Cela signifie notamment :

- même hiérarchie d’information ;
- même densité ;
- mêmes badges/statuts ;
- mêmes conventions typographiques ;
- même traitement responsive ;
- même langage visuel.

L’objectif porte sur le **résultat UI exact**, pas sur l’obligation de forcer Signal et Exécution dans un composant React universel.

Cursor doit d’abord rechercher les renderers/composants existants et les réutiliser directement lorsque leur contrat le permet.

Si une réutilisation directe imposait une mauvaise abstraction ou couplait Historique à un contrat opérationnel inadapté, préserver exactement la présentation validée tout en gardant une séparation de responsabilités propre.

Ne pas inventer une troisième famille de cartes spécifique à Historique.

Les actions qui n’ont pas de sens dans Historique ne doivent pas apparaître uniquement parce qu’elles existent dans la carte opérationnelle.

---

# 5. Filtres Historique

Les chips actuelles du feed Signal sont la référence visuelle.

Les contrôles qui sont réellement des **filtres** doivent reprendre ce langage.

Cela concerne notamment :

- période ;
- statut ;
- futurs filtres de même nature.

L’interface doit rester compacte et éviter l’accumulation inutile de plusieurs lignes de contrôles.

La disposition précise peut être adaptée au viewport.

---

# 6. Hiérarchie des selectors

Tous les contrôles ne doivent pas être représentés sous forme de chips.

Leur traitement visuel doit refléter leur fonction.

## 6.1 `Observations | Exécutions`

Ce contrôle change la **famille d’objets consultée** dans Historique.

Il doit rester :

- compact ;
- discret ;
- clairement distinct des chips de filtres.

Il ne doit pas être traité comme une série de filtres activables.

## 6.2 `Ma vue | Vue globale`

Ce contrôle change le **scope de lecture**.

Il conserve un selector / segmented control compact.

Il doit être visuellement secondaire par rapport au contenu et aux filtres.

Ce n’est pas un switch booléen.

## 6.3 `Liste | Calendrier`

Ce contrôle change uniquement la **représentation d’un même ensemble de données**.

Il doit utiliser un langage visuel distinct de `Ma vue | Vue globale`.

Attendu :

- plus discret que le selector de scope ;
- représentation principalement iconographique ;
- état actif perceptible mais léger ;
- cohérence mobile / desktop ;
- compréhension et accessibilité conservées.

Ne pas reproduire un second segmented control ayant exactement le même poids visuel que `Ma vue | Vue globale`.

Le design précis doit être déterminé à partir du langage UI et des primitives réellement disponibles dans le frontend.

---

# 7. Refresh

## 7.1 Mobile

Conserver le **pull-to-refresh existant**.

Ne pas ajouter de bouton de refresh permanent en parallèle.

Les comportements de chargement, erreur et conservation des données actuellement prévus doivent rester fonctionnels.

## 7.2 Desktop

Remplacer les gros boutons texte de refresh des feeds concernés par une action :

- icon-only ;
- compacte ;
- secondaire ;
- intégrée naturellement à la toolbar de la vue ;
- avec état visuel clair pendant une actualisation ;
- inaccessible à une seconde activation pendant l’opération si le comportement actuel le nécessite ;
- avec un nom accessible pour les technologies d’assistance.

**Aucun tooltip, y compris via un attribut générant un tooltip navigateur.**

Le même langage de refresh doit être appliqué à Signal, Exécution et Historique lorsqu’ils exposent cette action.

Ne pas modifier les mécanismes de refresh ou d’invalidation existants sauf nécessité fonctionnelle directement liée à ce chantier.

---

# 8. Historique dans la navigation

Historique appartient fonctionnellement à **Opérations**.

Cette règle vaut pour les présentations mobile et desktop de la navigation.

Cela ne signifie pas qu’Historique doit devenir un nouvel item permanent de la bottom navigation mobile si cette navigation n’expose pas directement toutes les destinations d’Opérations.

L’objectif est son **classement fonctionnel**, en respectant l’architecture de navigation actuellement utilisée par chaque plateforme.

Ne pas profiter de ce changement pour lancer la refonte globale Navigation / Transitions.

Les routes existantes restent hors scope sauf adaptation minimale nécessaire au nouveau classement.

---

# 9. Feed Signal

## 9.1 Desktop

La zone de filtres doit gagner en densité.

Attendu :

- conserver les chips actuelles comme référence ;
- privilégier une seule ligne lorsque l’espace disponible permet de le faire sans dégrader lisibilité ou interaction ;
- éviter les espaces ou contrôles surdimensionnés ;
- regrouper les filtres secondaires lorsque cela améliore réellement la hiérarchie.

Ne pas forcer artificiellement tous les contrôles sur une ligne à des largeurs où cela détériore l’usage.

## 9.2 Mobile

La zone de filtres occupe actuellement trop de hauteur.

Attendu :

- conserver les chips Signal comme référence ;
- réduire l’empreinte verticale ;
- préserver un accès rapide aux filtres courants ;
- éviter plusieurs lignes permanentes lorsque ce n’est pas nécessaire ;
- préserver les touch targets et la lisibilité.

La solution précise doit tenir compte des interactions et composants déjà présents dans le feed.

---

# 10. Sections Épinglées

Les sections Épinglées de Signal et Exécution doivent devenir pliables/dépliables lorsqu’elles existent.

Attendu :

- mobile et desktop ;
- suppression de la pastille jaune actuelle ;
- section ouverte lorsqu’aucune préférence précédente n’existe ;
- mémorisation du choix de lecture ensuite ;
- comportement cohérent avec les mécanismes existants de mémoire de feed lorsque ceux-ci peuvent couvrir proprement ce besoin.

La préférence doit être isolée selon le contexte nécessaire pour ne pas faire fuiter arbitrairement l’état d’un feed vers une autre surface ou un autre scope.

Cursor doit déterminer, à partir de l’architecture existante, le niveau de mémorisation approprié sans introduire un nouveau système de persistance si l’existant suffit.

Le fait de replier une section ne change pas les données chargées, les règles de pin ou le contrat backend.

---

# 11. Feed Exécution

## 11.1 Filtres

Les véritables filtres du feed Exécution doivent reprendre le langage visuel des chips du feed Signal.

Mobile et desktop.

Les contrôles de scope ou de représentation restent distincts conformément à la section 6.

## 11.2 CTA desktop

Le CTA :

`Créer`

devient :

**`+ Nouveau plan`**

Il reste compact et clairement identifiable comme l’action de création.

Ne pas modifier le parcours de création dans ce chantier.

## 11.3 Cartes `À valider` sur mobile

Sur les cartes Exécution affichées dans l’état **À valider**, supprimer :

`Fin prévue …`

uniquement de la carte mobile.

Ne pas supprimer cette donnée du domaine, des détails ou des autres vues qui l’utilisent utilement.

## 11.4 Métadonnée `Avec …`

Supprimer des cartes Exécution la ligne de type :

`Avec Restaurant · Maintenance +2`

Cette modification concerne la présentation des cartes de feed.

Elle ne modifie pas les assignations, pôles ou données sous-jacentes et ne supprime pas ces informations des écrans où elles sont nécessaires.

---

# 12. Cohérence et factorisation

Avant toute extraction, Cursor doit examiner les composants et primitives existants liés à :

- chips ;
- selectors ;
- toolbar ;
- refresh ;
- sections de feed ;
- pins ;
- cartes Signal ;
- cartes Exécution ;
- responsive mobile / desktop.

La stratégie attendue est :

**réutilisation existante → factorisation si répétition réelle → nouvelle primitive seulement si nécessaire.**

Éviter notamment :

- composant universel `Feed` ;
- carte générique artificielle Signal/Exécution ;
- toolbar paramétrable couvrant toutes les variantes du produit ;
- abstraction introduite uniquement pour réduire quelques lignes de JSX ;
- duplication d’un pattern existant déjà satisfaisant.

Une factorisation est justifiée lorsqu’elle rend une responsabilité réellement commune plus cohérente, maintenable ou sûre.

---

# 13. Performance

Ce chantier ne doit pas dégrader les garanties acquises sur les feeds.

Préserver :

- pagination cursor ;
- infinite scroll ;
- fenêtre mémoire ;
- conservation du contexte au retour ;
- TanStack Query et ses caches ;
- optimistic updates ;
- realtime ;
- Cross ;
- déduplication existante ;
- comportements de refresh existants.

Les éléments terminaux conservés 48 h / 10 jours doivent respecter les contrats de pagination et de tri existants.

Ne pas introduire de chargements supplémentaires ou de duplication d’état uniquement pour répondre au nouveau design.

Les optimisations supplémentaires ne doivent être réalisées que si l’analyse du code montre un problème réel ou une simplification évidente.

---

# 14. Accessibilité et interaction

Préserver ou améliorer :

- navigation clavier desktop ;
- focus visible ;
- état sélectionné des selectors ;
- noms accessibles des actions icon-only ;
- touch targets mobiles suffisantes ;
- contraste ;
- reduced motion lorsqu’il est déjà pris en compte ;
- comportement attendu des contrôles interactifs.

L’absence volontaire de tooltip sur l’action Refresh ne dispense pas de fournir un nom accessible.

---

# 15. Responsive

Les invariants fonctionnels restent identiques entre mobile et desktop.

Les différences de présentation explicitement prévues dans ce document sont volontaires.

Ne pas :

- appliquer automatiquement le layout desktop au mobile ;
- dupliquer toute une surface uniquement pour quelques différences responsive ;
- fusionner artificiellement des variantes dont les usages sont réellement différents.

L’architecture responsive actuelle doit être respectée et simplifiée uniquement lorsqu’une simplification réelle est démontrée.

---

# 16. Hors scope

Ne pas rouvrir dans ce chantier :

- architecture générale des feeds ;
- stratégie de pagination cursor ;
- fenêtre mémoire ;
- infinite scroll ;
- architecture realtime ;
- architecture Cross ;
- grand chantier Navigation / Transitions ;
- refonte des URLs ;
- détail Signal mobile ;
- détail Exécution mobile ;
- formulaires Action Plan mobile ;
- Bibliothèque mobile ;
- Chat mobile ;
- refonte du calendrier Exécution desktop.

`Liste | Calendrier` est concerné uniquement par son **contrôle de changement de vue**, pas par une refonte de la vue Calendrier elle-même.

---

# 17. Critères de résultat

À l’issue du chantier :

1. Signal, Exécution et Historique utilisent un langage cohérent de filtres.
2. Les contrôles de filtre, scope et représentation sont clairement différenciés.
3. `/history` utilise le même rendu terminal validé que les feeds correspondants.
4. Historique est classé dans Opérations sur les surfaces de navigation concernées.
5. Mobile utilise uniquement pull-to-refresh.
6. Desktop utilise une action refresh compacte et icon-only, sans tooltip.
7. Les sections Épinglées sont repliables et leur préférence de lecture est conservée proprement.
8. Le feed Signal gagne en densité sans sacrifier sa lisibilité.
9. Le feed Exécution adopte les ajustements de présentation décrits.
10. Les Signals annulés restent 48 h et les Signals résolus 10 jours dans le feed.
11. Les Exécutions annulées restent 48 h et les Exécutions validées 10 jours dans le feed.
12. Ces changements fonctionnent également dans les feeds Cross concernés.
13. Les contrats stabilisés de pagination, mémoire, cache, realtime et permissions restent intacts.
14. Aucune abstraction ou refonte adjacente n’est introduite sans besoin démontré.