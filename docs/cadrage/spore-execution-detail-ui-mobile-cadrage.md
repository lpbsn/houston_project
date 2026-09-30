# SPORE — Refonte / consolidation du détail Exécution mobile

## 1. Objectif

Refondre le détail Exécution mobile afin qu’il soit :

- immédiatement compréhensible sur le terrain ;
- orienté action plutôt que lecture documentaire ;
- cohérent avec le feed Exécution mobile déjà validé ;
- cohérent entre mobile web et Capacitor iOS/Android ;
- compatible avec le détail desktop existant sans en reprendre la mise en page ;
- maintenable et scalable à mesure que les états métier et les usages évoluent.

Le chantier concerne uniquement le **détail Exécution mobile**.

Il ne doit pas rouvrir :

- les contrats Feed/Pagination ;
- l’architecture Navigation/Transitions ;
- le calendrier ;
- les contrats backend existants, sauf besoin produit explicitement validé.

---

# 2. Principes directeurs

Le détail mobile doit répondre en priorité à quatre questions :

1. **Quelle est cette Exécution ?**
2. **Dans quel état est-elle ?**
3. **Y a-t-il quelque chose d’urgent ou à faire maintenant ?**
4. **Que dois-je faire ensuite ?**

Les informations administratives ou historiques ne doivent pas concurrencer ces éléments.

La hiérarchie mobile doit donc suivre :

**comprendre → agir → contextualiser**

et non reproduire la structure des données backend.

L’état métier participe à la hiérarchie visuelle, mais **les `permission_hints` restent l’unique source de vérité pour déterminer quelles actions sont réellement autorisées**.

---

# 3. Structure cible mobile

La composition cible suit cet ordre général :

1. titre + statut ;
2. temporalité / urgence ;
3. assignés ;
4. progression des tâches si des tâches existent ;
5. description si elle existe ;
6. tâches si elles existent ;
7. contexte secondaire compact ;
8. review selon l’état de l’Exécution.

Les commentaires restent accessibles dans leur espace dédié via le selector `Détails | Commentaires`.

Cette structure peut légèrement adapter son importance visuelle selon le statut, mais ne doit pas devenir une implémentation différente par état.

---

# 4. Niveau 1 — Comprendre immédiatement

Le haut du détail doit concentrer les informations opérationnelles essentielles.

## Contenu

Afficher prioritairement :

- titre ;
- statut ;
- temporalité pertinente ;
- état de retard éventuel ;
- assignés ;
- progression des tâches lorsqu’elle existe.

Le créateur et la date de création ne doivent plus être des informations dominantes.

## Statuts

Les statuts métier existants restent utilisés :

- `scheduled`
- `in_progress`
- `pending_validation`
- `done`
- `canceled`

Le retard reste une condition calculée à partir de l’échéance et ne devient pas un nouveau statut métier.

La représentation visuelle doit néanmoins permettre de comprendre immédiatement qu’une Exécution est en retard.

Ne pas reconstruire côté UI une machine à états métier différente du backend.

---

# 5. Temporalité

La présentation mobile actuelle sous forme de cartes distinctes `Début` et `Deadline` est trop volumineuse.

La cible est une lecture compacte de la temporalité.

Exemples possibles :

- `Aujourd’hui · avant 18:00`
- `2 h 15 restantes`
- `Demain · journée entière`
- `En retard de 1 h 20`
- `Du 2 au 4 octobre`

L’urgence relative doit avoir plus d’importance visuelle que la représentation brute des timestamps.

Les dates complètes peuvent rester accessibles plus bas dans le contexte secondaire lorsqu’elles apportent une information utile.

Pour une Exécution terminale, la temporalité doit perdre en importance visuelle.

## Progression temporelle

Le produit possède déjà une notion de progression temporelle basée sur `start_at` / `end_at`, notamment dans le feed Exécution.

Cette notion reste distincte de la progression des tâches.

Si une barre visuelle est conservée pour représenter le temps écoulé, elle doit rester explicitement une **progression temporelle**.

Ne pas utiliser la même représentation visuelle pour la progression des tâches afin d’éviter toute confusion.

---

# 6. Assignation

L’utilisateur doit pouvoir comprendre rapidement qui est concerné par l’Exécution.

Le contrat actuel ne définit pas de notion de `responsable principal`.

Le détail dispose notamment de :

- `assignees_by_pole` ;
- `pilot_business_unit` ;
- données d’assignation par tâche.

La UI ne doit pas inventer une responsabilité principale inexistante.

Le haut de page doit afficher un **résumé compact des assignés** :

- avatars ;
- noms ;
- éventuel overflow `+N`.

Le pôle pilote reste une information distincte de l’assignation.

La logique existante de déduplication des assignés doit être réutilisée lorsqu’elle convient.

---

# 7. Progression des tâches

La progression des tâches n’apparaît que lorsqu’une Exécution possède réellement des tâches.

La sémantique actuelle du produit doit être conservée.

Une tâche est considérée comme **traitée** lorsqu’elle n’est plus `pending`.

Cela inclut notamment :

- `done` ;
- `skipped` ;
- `observation_created`.

La UI doit donc utiliser une formulation du type :

`6 / 8 traitées`

et non :

`6 / 8 réalisées`

qui serait incorrecte par rapport au contrat métier actuel.

Ne pas créer un nouveau calcul de progression frontend divergent de la logique existante.

## Représentation

Privilégier un compteur compact.

Exemple :

`Tâches · 6/8 traitées`

Une barre de progression dédiée aux tâches n’est pas requise en V1.

La barre existante doit rester réservée à la progression temporelle si elle est affichée.

## Sans tâche

Lorsque `taskTotal === 0` :

- ne pas afficher de compteur ;
- ne pas afficher `0/0` ;
- ne pas afficher de section Tâches ;
- ne pas afficher `Aucune tâche dans cette exécution`.

L’absence de tâche est un cas normal du produit.

---

# 8. Description

La description constitue le premier contenu métier détaillé après le résumé opérationnel.

Elle doit apparaître avant :

- le créateur ;
- les métadonnées administratives ;
- les détails de classification secondaires ;
- la review historique.

Lorsque la description est vide sur mobile :

- ne pas rendre une carte dédiée ;
- ne pas afficher `Aucune description.` ;
- ne pas créer d’espace vide destiné à cette information.

La section disparaît simplement.

Le comportement desktop actuel peut rester inchangé.

---

# 9. Tâches

Les tâches sont facultatives et ne doivent pas structurer artificiellement toutes les Exécutions.

## Avec tâches

Afficher une section de type :

`Tâches · X/Y traitées`

Les comportements existants sont conservés :

- terminer ;
- remettre en cours ;
- passer ;
- créer une observation.

Les `permission_hints` de chaque tâche restent l’unique source de vérité pour les actions disponibles.

Les protections existantes contre les doubles mutations ou mutations concurrentes doivent être conservées.

## Sans tâche

La section n’est pas rendue.

Aucun état vide important n’est nécessaire.

## Multi-pôle

Les filtres par pôle restent utiles lorsqu’au moins plusieurs pôles sont effectivement représentés dans les tâches.

Le résumé actuel des pôles avant la liste des tâches est supprimé sur mobile.

Les chips de filtre suffisent à représenter la segmentation lorsque nécessaire.

Le libellé générique devient `Tâches`, et non systématiquement `Tâches par pôle`.

---

# 10. Pôles

Éviter de répéter la même information de pôle dans plusieurs surfaces successives.

Le pôle pilote peut apparaître dans le contexte secondaire.

Lorsqu’une tâche appartient à un pôle spécifique, cette information peut rester dans la tâche si elle apporte un contexte utile.

Les filtres multi-pôles restent affichés lorsque plusieurs pôles possèdent effectivement des tâches.

La UI ne doit pas reproduire simultanément :

- badge pôle dans le header ;
- résumé pôle ;
- filtres pôle ;
- pôle dans chaque tâche ;

sauf lorsque chaque occurrence apporte une information réellement distincte.

---

# 11. Actions lifecycle

Les `permission_hints` backend restent l’unique source de vérité.

La UI ne doit pas déduire automatiquement une permission depuis le statut.

Par exemple :

`status === in_progress`

ne signifie pas à lui seul que `Marquer terminé` doit être affiché.

Il faut toujours respecter :

- `can_mark_done`
- `can_validate`
- `can_reopen`
- `can_cancel`
- `can_update`

Le statut sert à hiérarchiser l’affichage, pas à décider des autorisations.

## Action dominante

Lorsqu’une action lifecycle opérationnelle principale existe, une seule doit dominer l’interface mobile.

Cas typiques :

### `in_progress`

Si `can_mark_done === true` :

`Marquer terminé`

### `pending_validation`

Si `can_validate === true` :

`Valider`

### `done`

Si `can_reopen === true` :

`Rouvrir` peut être proposé, avec une importance visuelle inférieure à celle des actions opérationnelles d’une Exécution active.

### `scheduled`

Ne pas inventer une action lifecycle si aucun permission hint correspondant n’est exposé.

## Actions secondaires

Les actions rares, administratives ou destructives ne doivent pas concurrencer l’action principale.

Notamment :

`Annuler`

doit être déplacée dans un menu secondaire `…` ou une surface équivalente.

Si `Annuler` est la seule action disponible, ne pas en faire automatiquement un gros CTA sticky.

Elle reste une action secondaire.

---

# 12. Footer mobile

Le footer sticky reste pertinent lorsqu’une action lifecycle dominante existe.

Il doit être :

- simple ;
- stable ;
- compatible safe-area iOS/Android ;
- non intrusif ;
- limité à l’action réellement prioritaire.

Il ne doit pas devenir un conteneur générique regroupant toutes les actions disponibles.

Les erreurs lifecycle peuvent continuer à être affichées dans cette zone lorsqu’elles concernent directement l’action exécutée.

Le footer doit disparaître lorsque l’onglet `Commentaires` est actif, comme aujourd’hui.

---

# 13. Deep-link validation

Le comportement actuel de deep-link vers la validation doit être conservé.

Un lien contenant :

`?focus=validation`

doit continuer à :

- ouvrir / maintenir l’espace `Détails` ;
- conduire visuellement vers l’action de validation lorsqu’elle est autorisée ;
- ne rien déclencher lorsque `can_validate === false`.

La refonte du layout peut modifier la position physique de l’action, mais ne doit pas casser cette intention de navigation.

Ce comportement reste compatible avec le chantier Navigation/Transitions futur.

---

# 14. Détails / Commentaires

Le principe de séparation :

`Détails | Commentaires`

est conservé.

Le selector actuel doit cependant devenir plus discret et moderne.

Objectifs :

- ne pas concurrencer le contenu ;
- conserver une cible tactile correcte ;
- rester immédiatement compréhensible ;
- rester cohérent avec le détail Signal mobile ;
- conserver l’accessibilité `tablist / tab / tabpanel`.

La logique actuelle de lazy mount des commentaires doit être conservée.

Le composer de commentaire reste adapté au mobile et compatible avec le comportement sticky existant.

Les deep-links vers :

`?tab=comments&commentId=...`

doivent continuer à fonctionner.

La sélection manuelle des tabs ne doit pas nécessairement écrire ces paramètres dans l’URL si le comportement actuel reste pertinent.

---

# 15. Signal lié

Lorsqu’une Exécution provient d’un Signal, le lien doit rester accessible.

Il ne doit cependant pas concurrencer l’état courant de l’Exécution.

La position actuelle très haute dans l’écran peut être revue.

Le Signal lié fait partie du contexte secondaire de l’Exécution, pas de son action principale.

La refonte visuelle ne doit modifier aucun des contrats de navigation existants.

Elle doit notamment préserver :

- le scope établissement ;
- le scope Cross ;
- le contexte Analytics transporté dans l’URL ;
- les paramètres nécessaires au retour vers les surfaces Analytics existantes.

Ne pas reconstruire manuellement ces URLs si les helpers actuels existent déjà.

---

# 16. Review / validation

La validation existante conserve son workflow :

- ouverture depuis l’action `Valider` ;
- choix de la note ;
- commentaire éventuel ;
- confirmation.

La bottom sheet actuelle constitue une base fonctionnelle valide.

Après validation, la review existante ne doit plus apparaître immédiatement sous le titre sur mobile.

Elle doit être replacée dans une zone de résultat / contexte secondaire.

Une Exécution `done` peut accorder davantage de visibilité à cette review qu’une Exécution active, puisqu’elle décrit alors le résultat final.

La review ne doit pas être artificiellement affichée pour les états où elle n’existe pas.

---

# 17. Contexte secondaire

Le mobile ne doit pas reproduire le gros panneau `Contexte` desktop.

Après les contenus opérationnels, afficher seulement les informations effectivement présentes et utiles.

Cette zone peut notamment contenir :

- pôle pilote ;
- éventuels pôles contributeurs pertinents ;
- créateur ;
- date de création ;
- dates détaillées ;
- Signal lié ;
- review ;
- autres informations historiques réellement utiles.

Cette zone doit rester compacte et ne pas devenir un nouvel empilement systématique de cartes.

Ne pas afficher un champ uniquement pour montrer qu’il est vide.

---

# 18. Adaptation selon l’état

La structure reste commune, mais l’importance visuelle s’adapte selon le statut.

## `scheduled`

Priorités :

- quoi ;
- quand ;
- qui.

Pas de faux sentiment d’urgence.

Les informations de démarrage peuvent être plus importantes que les tâches.

## `in_progress`

Priorités :

- état ;
- échéance / retard ;
- assignés ;
- progression des tâches ;
- tâches ;
- action de fin.

C’est l’état le plus orienté exécution terrain.

## `pending_validation`

Priorités :

- compréhension du travail traité ;
- progression finale ;
- informations nécessaires au contrôle ;
- action `Valider`.

Le deep-link `focus=validation` doit rester fonctionnel.

## `done`

Lecture principalement historique.

Priorités :

- résultat ;
- review lorsqu’elle existe ;
- contexte ;
- possibilité de réouverture si autorisée.

## `canceled`

Interface calme et essentiellement read-only.

Aucune mise en avant inutile de progression ou d’action opérationnelle.

---

# 19. Cross

Le détail Cross reste strictement read-only conformément aux contrats actuels.

Cela concerne notamment :

- actions lifecycle ;
- modification ;
- changement d’état des tâches ;
- actions secondaires sur les tâches ;
- création d’observation depuis une tâche ;
- écriture de commentaires.

La refonte mobile ne doit pas réintroduire une action mutante dans Cross par erreur.

Le Signal lié doit conserver sa navigation dans le scope Cross.

---

# 20. Mobile web / Capacitor

Mobile web et Capacitor iOS/Android partagent la même UI mobile.

La distinction mobile / desktop ne doit pas dépendre uniquement de la largeur du viewport.

Un runtime natif Capacitor avec une grande largeur d’écran doit continuer à utiliser les patterns tactiles mobile lorsque c’est le comportement actuel attendu.

Ne pas transformer automatiquement une tablette ou un grand viewport natif en composition desktop simplement parce qu’il dépasse un breakpoint CSS.

Les safe areas natifs doivent être conservés.

---

# 21. Desktop

Le détail desktop actuel reste la référence fonctionnelle.

Sa structure validée est conservée :

- contenu principal ;
- tâches ;
- commentaires ;
- colonne Contexte / Planification ;
- actions desktop.

Le chantier mobile ne doit pas dégrader ce rendu.

Les composants partagés peuvent évoluer seulement lorsque leur responsabilité est réellement commune.

Une divergence de composition mobile/desktop est acceptable et souhaitable lorsque les usages sont différents.

Les comportements desktop existants liés aux deep-links commentaires et validation doivent rester fonctionnels.

---

# 22. Architecture frontend

Conserver le principe actuel :

- page métier commune ;
- données et mutations communes ;
- `permission_hints` communs ;
- composants métier réutilisables ;
- composition spécifique mobile/desktop lorsque nécessaire.

Ne pas créer :

- un nouveau design system ;
- un framework de sections génériques ;
- des abstractions de layout hypothétiques ;
- une nouvelle couche métier frontend ;
- une nouvelle machine à états locale.

Factoriser uniquement lorsqu’une duplication réelle apparaît pendant l’implémentation.

Les helpers existants de :

- permissions ;
- formatage ;
- calcul de temporalité ;
- assignation ;
- navigation ;

doivent être réutilisés lorsqu’ils correspondent au besoin.

---

# 23. Performance

Conserver les bons comportements actuels :

- commentaires montés uniquement après première ouverture ;
- TanStack Query existant ;
- mutations ciblées ;
- aucune nouvelle requête pour des informations déjà présentes dans le détail ;
- pas de recalcul ou transformation lourde dans le rendu sans nécessité ;
- protections existantes contre les doubles mutations sur les tâches.

La refonte visuelle ne doit pas créer de nouveaux contrats API.

Elle ne doit pas introduire de fetch uniquement pour alimenter une présentation mobile différente.

---

# 24. Accessibilité

Préserver ou améliorer :

- zones tactiles adaptées au mobile ;
- labels accessibles des actions ;
- `aria` des statuts ;
- distinction explicite entre progression temporelle et progression des tâches ;
- `aria` des tabs et panels ;
- navigation clavier sur mobile web lorsque pertinente ;
- `prefers-reduced-motion` sur les interactions animées ;
- contraste suffisant ;
- distinction d’état ne reposant pas uniquement sur la couleur.

Les actions secondaires placées dans un menu ou une bottom sheet doivent rester accessibles et correctement nommées.

---

# 25. Tests et invariants à préserver

La refonte ne doit pas casser les comportements déjà couverts.

Invariants importants :

- lazy mount des commentaires ;
- deep-link commentaire ;
- deep-link validation ;
- footer lifecycle seulement dans `Détails` ;
- filtres pôle uniquement en multi-pôle ;
- permissions lifecycle ;
- permissions tâches ;
- Cross read-only ;
- Signal lié dans le scope établissement ;
- Signal lié dans le scope Cross ;
- préservation du contexte Analytics ;
- mobile tactile conservé sur runtime natif avec grand viewport ;
- desktop inchangé fonctionnellement ;
- prévention des doubles mutations tâche ;
- workflows d’observation depuis une tâche ;
- workflow validation + rating.

Les tests existants doivent être adaptés aux changements de hiérarchie visuelle lorsque nécessaire, sans affaiblir les contrats fonctionnels qu’ils protègent.

---

# 26. Hors scope

Ce chantier ne couvre pas :

- Feed Exécution / Pagination ;
- refonte backend des Exécutions ;
- nouveaux statuts métier ;
- nouvelle sémantique de progression ;
- architecture realtime ;
- Navigation / Transitions ;
- refonte du calendrier ;
- bibliothèque / modèles ;
- formulaires de création ou d’édition généraux ;
- refonte desktop ;
- nouveau design system.

---

# 27. Critère produit final

Un utilisateur ouvrant une Exécution sur mobile doit comprendre en quelques secondes :

**ce qu’il doit faire, où en est l’Exécution, qui est concerné et s’il existe une urgence.**

Les informations historiques et administratives restent accessibles mais ne doivent jamais masquer ces quatre éléments.

La UI ne doit inventer aucune responsabilité, permission, progression ou état qui n’existe pas dans les contrats métier actuels.