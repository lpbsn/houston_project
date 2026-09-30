# SPORE — Navigation & Transitions

## 1. Objectif

Consolider la navigation de SPORE afin qu’elle soit :

- cohérente ;
- prévisible ;
- simple pour un utilisateur terrain ;
- adaptée à iOS, Android et desktop web ;
- scalable lorsque de nouvelles surfaces sont ajoutées ;
- maintenable pour un solo dev ;
- compatible avec les contextes de retour, deep links, changements de scope et mémoires de lecture existants.

Le chantier couvre également le langage de transitions entre écrans.

Les transitions doivent rester :

- rapides ;
- discrètes ;
- modernes ;
- utiles à la compréhension de la navigation ;
- adaptées à la relation réelle entre les surfaces.

L’objectif n’est pas de créer un framework de navigation ou d’animation propre à SPORE.

---

# 2. Principes fondamentaux

## 2.1 La navigation exprime une intention

Une navigation ne doit pas être traitée uniquement comme :

`route A → route B`.

Elle correspond à une relation fonctionnelle.

Relations à distinguer :

1. navigation primaire ;
2. ouverture hiérarchique ;
3. retour hiérarchique ;
4. changement d’état ou de représentation locale ;
5. flow de création ou modification ;
6. présentation temporaire ;
7. redirection système ;
8. ouverture externe / deep link ;
9. changement de scope.

Ces relations déterminent :

- le comportement du retour ;
- le contexte à restaurer ;
- la place éventuelle dans l’historique ;
- la transition appropriée.

---

# 3. Règle canonique du Retour

Le bouton Retour doit revenir vers le **contexte pertinent ayant conduit à la surface courante**, lorsqu’un tel contexte existe encore.

Exemples :

- Feed Signal → Signal → Retour = même Feed Signal.
- Historique → Signal → Retour = Historique.
- Analytics → Signal → Retour = Analytics.
- Exécution → Détail Exécution → Retour = Exécution.
- Bibliothèque → Modèle → Retour = Bibliothèque.

Le Retour ne doit pas être résolu à partir d’un simple chemin hardcodé dans le composant courant.

---

# 4. Priorité de résolution du Back

Lorsqu’une action Back est déclenchée, l’ordre comportemental attendu est :

1. fermer une présentation temporaire active si elle doit capter le Back ;
2. revenir à la provenance fonctionnelle valide de la surface courante lorsqu’elle existe ;
3. utiliser un historique interne/navigation précédent uniquement lorsqu’il représente réellement cette provenance ;
4. utiliser le fallback métier déterministe de la destination ;
5. au niveau racine, laisser le comportement système approprié s’appliquer.

Cette règle doit rester cohérente entre :

- bouton Retour visible ;
- Android Back ;
- geste système lorsqu’il est disponible ;
- navigation déclenchée depuis le desktop.

Ne pas maintenir plusieurs règles contradictoires selon le mécanisme utilisé.

---

# 5. Historique navigateur

L’historique navigateur n’est pas automatiquement équivalent à l’historique métier.

Un écran peut être atteint depuis :

- navigation interne ;
- deep link ;
- notification ;
- URL ouverte directement ;
- authentification ;
- changement d’établissement ;
- redirection système.

Ne pas remplacer la logique de retour par un `history.back()` global.

L’historique navigateur peut être utilisé lorsqu’il représente réellement le parcours actuel, mais il ne doit pas produire un retour vers :

- login obsolète ;
- mauvais établissement ;
- page technique de redirection ;
- provenance devenue invalide ;
- état intermédiaire sans intérêt utilisateur.

---

# 6. Navigation primaire

Les grandes destinations SPORE sont des destinations sœurs.

Exemples :

- Dashboard ;
- Observations ;
- Exécution ;
- Chat ;
- Général ;
- autres destinations principales accessibles depuis la navigation de la plateforme.

Changer de destination primaire n’est pas une navigation hiérarchique.

## Invariants

Lors d’un changement de destination primaire :

- la destination cible devient le contexte principal actif ;
- elle ne doit pas créer artificiellement une relation Parent/Enfant avec la destination précédente ;
- le bouton Retour d’un hub racine ne doit pas permettre de parcourir successivement toutes les destinations primaires visitées ;
- la sidebar desktop et la bottom navigation mobile restent stables ;
- l’état propre à chaque destination peut être restauré lorsque cette surface possède déjà une mémoire adaptée.

Exemple à éviter :

`Observations → Exécution → Chat → Back → Exécution → Back → Observations`

uniquement parce que l’utilisateur a changé de destination primaire.

La navigation primaire ne doit pas devenir une pile artificielle de tabs.

---

# 7. Navigation hiérarchique

Une navigation hiérarchique correspond à l’entrée dans une surface plus précise du contexte courant.

Exemples :

- Observations → Signal ;
- Exécution → Détail Exécution ;
- Historique → objet ;
- Bibliothèque → Modèle ;
- liste équipe → membre.

## Forward

L’utilisateur entre dans un niveau plus profond.

Le contexte de provenance utile au Retour doit être préservé.

## Back

Le retour inverse cette relation.

Lorsque la surface précédente possède déjà une mémoire de lecture, retrouver autant que possible :

- scope ;
- filtres ;
- catégorie ;
- mode de vue ;
- position de scroll ;
- pages déjà hydratées ;
- sections repliées ;
- autres états explicitement mémorisés par cette surface.

La navigation ne doit pas recréer ces mécanismes.

---

# 8. Provenance

Un même détail peut être ouvert depuis différentes surfaces.

Exemple Signal :

- Feed Observations ;
- Historique ;
- Analytics ;
- notification ;
- deep link.

Ces entrées peuvent produire des Retours différents.

## Invariant

La provenance doit être représentée uniquement lorsqu’elle est nécessaire pour distinguer ces parcours.

Cursor doit auditer les mécanismes actuels :

- URL/search params ;
- contexte de retour ;
- helpers de navigation ;
- mémoire de lecture ;
- résolution du Back ;
- autres mécanismes existants.

Les consolider si nécessaire.

Ne pas introduire un second router ou une pile parallèle si l’existant peut porter correctement le besoin.

---

# 9. Validité de la provenance

Une provenance n’est utilisable que si elle reste valide au moment du Retour.

Elle devient notamment invalide si :

- l’utilisateur n’a plus accès à la destination ;
- le scope établissement ne correspond plus ;
- la destination n’existe plus ;
- une redirection système a remplacé le contexte ;
- le contexte d’authentification a changé.

Dans ce cas, utiliser le fallback métier correspondant.

Ne jamais forcer un retour vers une provenance connue mais devenue invalide.

---

# 10. Fallbacks métier

Toute destination pouvant être ouverte directement doit posséder un fallback métier déterministe.

Exemples conceptuels :

- Signal établissement → Observations du même établissement ;
- Exécution établissement → Exécution du même établissement ;
- Signal Cross → Observations Cross ;
- Exécution Cross → Exécution Cross ;
- modèle Action Plan → Bibliothèque / hub Action Plans approprié ;
- conversation → Chat ;
- membre → surface équipe appropriée.

Les fallbacks doivent être définis au niveau de responsabilité navigation approprié.

Ils ne doivent pas être dispersés dans les composants de présentation.

---

# 11. Deep links et ouvertures externes

Les deep links constituent des points d’entrée légitimes.

Ils peuvent arriver sans historique interne préalable.

Le chantier doit préserver :

- ouverture du bon objet ;
- sélection ou switch du bon établissement lorsqu’autorisé ;
- authentification ;
- permissions ;
- Cross ;
- fallback Back cohérent.

Un deep link ne doit pas fabriquer artificiellement un faux parcours précédent simplement pour alimenter Back.

Exemple :

deep link → Signal

ne doit pas prétendre que l’utilisateur vient du feed Signal.

Le fallback Signal prend alors le relais si aucune provenance réelle n’existe.

---

# 12. Changement de scope

Changer :

- d’établissement ;
- établissement → Cross ;
- Cross → établissement ;

constitue un changement de contexte fonctionnel.

## Invariants

Après changement de scope :

- une provenance incompatible doit être invalidée ;
- un Retour ne doit jamais rouvrir un objet du mauvais établissement ;
- les mémoires déjà isolées par scope restent isolées ;
- la navigation ne doit pas dupliquer la logique de changement de session établissement.

Le chantier doit préserver les protections existantes autour de l’établissement actif.

---

# 13. États locaux et historique

Les interactions locales ne doivent pas automatiquement produire une nouvelle étape de Back.

Exemples :

- filtre ;
- chip ;
- période ;
- `Ma vue | Vue globale` ;
- `Liste | Calendrier` ;
- section repliée ;
- recherche locale.

L’URL peut continuer à représenter certains de ces états lorsque cela sert le partage, le refresh ou la restauration.

Mais :

**Back ne doit pas obliger l’utilisateur à annuler une par une toutes ses modifications de filtres avant de quitter la surface.**

Le chantier doit auditer les usages actuels de `push` / `replace` et conserver un historique utilisateur utile, pas un historique de chaque micro-interaction.

Le choix technique exact reste à déterminer à partir des contrats actuels.

---

# 14. Redirections système

Les redirections techniques ne sont pas des navigations métier ordinaires.

Exemples :

- login ;
- onboarding ;
- permission ;
- établissement inaccessible ;
- chat indisponible ;
- route réservée desktop ;
- sélection établissement.

Elles doivent généralement remplacer une entrée obsolète lorsque revenir dessus ne produirait aucune action utile.

Le chantier doit auditer l’utilisation actuelle de navigation avec remplacement.

Une redirection technique ne doit pas :

- créer une étape Back inutile ;
- déclencher une transition hiérarchique métier ;
- modifier artificiellement la provenance fonctionnelle.

---

# 15. Formulaires et modifications non sauvegardées

Ce chantier ne redessine pas les formulaires.

Mais l’architecture de navigation doit pouvoir gérer correctement un flow de création ou d’édition.

Une navigation hors d’un formulaire ne doit pas provoquer silencieusement une perte de données lorsque le formulaire possède déjà une notion d’état non sauvegardé.

Cursor doit vérifier les comportements actuels.

Ne pas inventer un système global de confirmation de sortie si les formulaires ne l’exigent pas aujourd’hui.

Lorsque ce besoin existe réellement, la décision de quitter doit précéder la navigation et non être gérée par l’animation.

---

# 16. Android Back

Le bouton système Android doit converger fonctionnellement avec le bouton Retour visible.

Ordre attendu :

1. fermer l’overlay temporaire approprié ;
2. revenir dans la hiérarchie courante ;
3. utiliser le fallback métier si nécessaire ;
4. au niveau racine, laisser le comportement système approprié prendre le relais.

Le chantier doit auditer l’interception Capacitor actuelle.

Objectifs :

- éviter deux logiques Back divergentes ;
- conserver les fallbacks métier ;
- vérifier la compatibilité avec Predictive Back ;
- ne pas intercepter plus de navigation système que nécessaire.

Le cadrage n’impose pas une implémentation spécifique de Predictive Back.

---

# 17. iOS

Le comportement fonctionnel doit rester identique à Android :

- même provenance ;
- mêmes fallbacks ;
- même hiérarchie.

Les interactions système peuvent différer.

Le chantier doit éviter de construire une navigation web qui empêcherait inutilement un comportement natif pertinent de la WebView/Capacitor.

Ne pas supposer qu’un geste iOS particulier existe ou doit être simulé sans vérification du runtime réel.

---

# 18. Langage des transitions

L’animation découle de la **relation entre les surfaces**, pas du nom exact des routes.

Ne pas construire une matrice du type :

`route A → route B = animation X`.

Le nombre de familles de transitions doit rester faible.

---

# 19. Mobile — navigation hiérarchique

## Forward

Pour :

`hub/liste → détail`

utiliser une transition directionnelle horizontale légère.

Intention :

**entrer dans un niveau plus profond.**

Attendu :

- déplacement court ;
- fade léger possible ;
- pas de slide plein écran lourd ;
- shell stable autant que possible ;
- navigation immédiatement déclenchée.

## Back

Utiliser le mouvement inverse.

L’utilisateur doit percevoir qu’il remonte dans la hiérarchie.

Le sens du mouvement dépend de l’intention Forward/Back, pas du chemin URL.

---

# 20. Mobile — navigation primaire

Pour :

- Observations → Exécution ;
- Exécution → Chat ;
- Chat → Général ;

ne pas utiliser de transition directionnelle.

Attendu :

- changement instantané ou cross-fade très court ;
- bottom navigation stable ;
- pas d’impression de hiérarchie.

La rapidité prime.

---

# 21. Changements locaux

Pour :

- Liste ↔ Calendrier ;
- Ma vue ↔ Vue globale ;
- filtres ;
- périodes ;
- catégories ;
- autres changements locaux ;

aucune transition de page.

Le contrôle reste stable.

Une transition locale courte peut être utilisée uniquement si elle améliore la continuité.

---

# 22. Présentations temporaires

Exemples :

- bottom sheet ;
- action sheet ;
- modal ;
- picker ;
- menu ;
- popover.

Elles ne créent pas une destination de navigation principale sauf lorsque l’architecture existante les représente explicitement comme telle.

## Mobile

Entrée/sortie verticale naturelle lorsque adaptée à la surface.

## Desktop

Fade et éventuellement scale très léger.

Fermer la présentation ramène au contexte sous-jacent sans créer artificiellement une nouvelle destination Back.

---

# 23. Flows de création et édition

Il n’existe pas de règle universelle :

`formulaire = modal`

ou :

`formulaire = sheet`.

Un formulaire peut être :

- une destination hiérarchique ;
- une étape ;
- une édition ;
- une interaction temporaire.

Le chantier Navigation doit seulement permettre aux futurs chantiers Formulaires/Bibliothèque de s’intégrer proprement.

Ne pas redessiner ces écrans ici.

---

# 24. Desktop

Le desktop doit rester plus stable visuellement que le mobile.

## Navigation primaire

- sidebar immobile ;
- pas de slide horizontal global ;
- contenu immédiat ou fade très court.

## Hub → détail

- sidebar et shell immobiles ;
- changement limité à la zone utile ;
- fade ou translation très faible seulement si pertinent.

## Split views

Lorsque seule une région change :

**animer uniquement cette région.**

Exemple Chat desktop :

la liste ne doit pas être remontée/réanimée lors d’un changement de conversation.

---

# 25. Durées

Conserver peu de timings.

La durée courte déjà présente autour de `180 ms` constitue une référence raisonnable.

Orientation :

- micro-interaction : très courte ;
- navigation écran : environ 160–220 ms ;
- overlay : légèrement supérieur uniquement si nécessaire.

Ne pas multiplier les constantes.

Cible :

**rapide d’abord, animée ensuite.**

---

# 26. Reduced Motion

Respecter systématiquement Reduced Motion.

Lorsque cette préférence est active :

- supprimer les translations significatives ;
- éviter les scales décoratifs ;
- navigation immédiate ou fade minimal lorsque pertinent ;
- aucun comportement fonctionnel dépendant de l’animation.

---

# 27. Performance des transitions

Une transition ne doit jamais :

- retarder la navigation ;
- attendre une requête réseau ;
- provoquer un remount injustifié ;
- casser le scroll ;
- invalider un cache ;
- déclencher un fetch supplémentaire uniquement pour l’animation ;
- animer une grande liste complète sans nécessité ;
- produire un layout shift évitable.

La navigation reste intégralement fonctionnelle sans animation.

---

# 28. Technologie

Le frontend utilise actuellement Framer Motion.

Ce chantier ne présume pas son remplacement.

La View Transition API peut être évaluée si elle simplifie réellement une responsabilité existante.

Ce n’est pas un objectif.

Ne pas :

- ajouter une nouvelle librairie sans nécessité ;
- maintenir deux moteurs concurrents pour la même responsabilité ;
- réécrire les transitions seulement pour adopter une technologie récente.

Priorités :

1. simplicité ;
2. Capacitor ;
3. performance ;
4. maintenabilité ;
5. cohérence.

---

# 29. Responsabilités à clarifier

Cursor doit analyser l’architecture existante avant de proposer sa consolidation.

Les concepts fonctionnels sont :

## Destination

Écran réellement affiché.

## Provenance

Contexte précédent pertinent lorsqu’il influence le Retour.

## Intention

Nature de la navigation :

- primary ;
- forward ;
- back ;
- replace/system ;
- local change ;
- temporary presentation.

## Transition

Conséquence visuelle éventuelle de cette intention.

Le cadrage ne prescrit pas leur représentation technique.

---

# 30. Hardcoded navigation

Auditer les destinations et fallbacks définis directement dans :

- pages ;
- composants ;
- topbars ;
- callbacks ;
- Android Back ;
- `App`;
- helpers de routes.

Objectif :

supprimer la **logique métier de navigation contradictoire ou dispersée**.

Ne pas chercher à supprimer tous les chemins littéraux.

Une destination explicitement connue et stable peut rester une URL explicite.

Ne pas créer une abstraction uniquement pour remplacer des strings.

---

# 31. Mémoires de lecture

Préserver les systèmes existants pour :

- filtres ;
- pages chargées ;
- fenêtre mémoire ;
- scroll ;
- sections repliées ;
- modes de vue ;
- états spécifiques aux surfaces.

La navigation doit permettre de retrouver la surface qui possède cette mémoire.

Elle ne doit pas créer une nouvelle mémoire globale de pages.

---

# 32. Focus et scroll

Après navigation :

## Forward vers détail

Le détail doit présenter son contenu depuis un état de lecture logique.

Ne pas hériter arbitrairement du scroll du parent.

## Back vers parent

Restaurer la position précédente lorsque cette surface possède déjà une mémoire de lecture.

## Desktop

Le focus clavier doit suivre la destination utile sans être déplacé arbitrairement par une animation.

## Overlay

À la fermeture, restaurer le focus vers l’élément déclencheur lorsqu’applicable.

Le chantier doit préserver les comportements accessibles existants et corriger les incohérences observées.

---

# 33. URLs

La refonte globale des URLs lisibles reste hors scope.

L’architecture navigation ne doit cependant pas augmenter son couplage aux IDs ou aux URLs actuellement affichées.

Une modification locale d’un helper de route est acceptable si nécessaire à la cohérence de navigation.

Ne pas lancer une migration générale des URLs.

---

# 34. Matrice de transitions de référence

| Relation | Mobile | Desktop |
|---|---|---|
| Navigation primaire | instantané ou cross-fade court | instantané ou fade très court |
| Hub/liste → détail | directionnel horizontal léger | fade / mouvement minimal |
| Détail → parent | inverse du forward | fade / mouvement minimal |
| Changement de vue local | transition locale ou aucune | transition locale ou aucune |
| Sheet / overlay | verticale / fade selon surface | fade / scale léger |
| Redirection système | aucune transition métier | aucune transition métier |
| Deep link initial | aucun faux forward | aucun faux forward |
| Changement de scope | aucune fausse relation hiérarchique | aucune fausse relation hiérarchique |

Cette matrice définit le langage.

Elle ne signifie pas que chaque case doit obligatoirement être animée.

---

# 35. Ce que le chantier doit éviter

- `history.back()` global ;
- back paths arbitraires dispersés ;
- Back qui traverse les tabs primaires ;
- Back qui traverse chaque changement de filtre ;
- animations basées directement sur les pathnames ;
- animation inventée écran par écran ;
- slides entre destinations primaires ;
- animation globale du shell desktop ;
- provenance conservée après changement de scope incompatible ;
- nouvelle librairie de navigation sans nécessité ;
- second router ;
- seconde mémoire de lecture ;
- transition longue ou décorative ;
- dépendance fonctionnelle à une animation ;
- faux historique généré pour un deep link.

---

# 36. Hors scope

Ne pas profiter du chantier pour refondre :

- UI détail Signal ;
- UI détail Exécution ;
- formulaires mobile ;
- Bibliothèque ;
- Chat ;
- calendrier ;
- Feed ;
- pagination ;
- realtime ;
- permissions ;
- URLs lisibles globales.

Ces surfaces peuvent servir à tester le comportement de navigation sans être redesignées.

---

# 37. Validation fonctionnelle attendue

Le plan d’implémentation devra couvrir les parcours réels du repo.

## Signal

- feed → détail → retour ;
- Historique → détail → retour ;
- Analytics → détail → retour lorsque ce parcours existe ;
- deep link/direct → détail → fallback ;
- changement de filtre → détail → retour vers le même état de feed.

## Exécution

- feed → détail → retour ;
- Historique → détail → retour ;
- planifiées → détail → retour ;
- accès direct → fallback ;
- Liste/Calendrier sans pollution de la pile Back.

## Action Plans

- hub/Bibliothèque → modèle ;
- modèle → création ou édition lorsque ces parcours existent ;
- retour sans perte de contexte injustifiée.

## Chat

- mobile liste → conversation → retour ;
- desktop split-view sans transition globale ;
- changement de conversation sans remount inutile du panneau liste.

## Scope

- établissement A → établissement B ;
- établissement → Cross ;
- Cross → établissement ;
- provenance précédente devenue invalide.

## Système

- Android Back ;
- overlay + Android Back ;
- accès direct ;
- redirection auth ;
- permission ;
- établissement incompatible.

## Navigation primaire

- changements successifs entre destinations principales ;
- Back ne doit pas remonter artificiellement ces changements.

---

# 38. Critères de succès

À l’issue du chantier :

1. Back revient toujours vers une destination pertinente et prévisible.
2. Les détails ouverts depuis plusieurs surfaces retournent au bon contexte.
3. Les deep links fonctionnent sans historique préalable.
4. Les fallbacks sont cohérents et non dispersés arbitrairement.
5. Les mémoires de feed restent fonctionnelles.
6. Les filtres et changements locaux ne polluent pas la pile Back.
7. La navigation primaire ne devient pas une pile artificielle de destinations.
8. Les changements de scope invalident les provenances incompatibles.
9. Android Back et les Retours visibles convergent fonctionnellement.
10. Les transitions mobiles distinguent navigation primaire et hiérarchique.
11. Le desktop reste stable et peu animé.
12. Les transitions locales ne deviennent pas des transitions de page.
13. Reduced Motion est respecté.
14. Focus et scroll restent cohérents.
15. Aucun système parallèle de navigation n’est introduit sans nécessité démontrée.
16. L’architecture reste compatible avec les futures URLs et surfaces SPORE.
17. Le résultat reste simple à maintenir et faire évoluer par un solo dev.