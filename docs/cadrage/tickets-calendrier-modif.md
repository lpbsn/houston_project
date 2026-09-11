# P0 — Calendrier — Réduire l’emprise visuelle de la zone « Journée »

## Contexte

Dans les vues Jour et Semaine, les événements couvrant toute la journée sont affichés dans une zone dédiée au-dessus de la grille horaire.

Cette zone peut prendre une place importante, particulièrement sur mobile, et réduire fortement l’espace disponible pour consulter le planning horaire.

Le problème devient plus visible lorsque plusieurs événements journée sont présents simultanément. Son occupation persistante pendant la consultation de la timeline doit également être challengée.

## Objectif

Réduire fortement l’emprise visuelle de la zone « Journée » dans les vues Jour et Semaine, particulièrement sur mobile, afin qu’elle ne pénalise pas la consultation de la grille horaire.

## Comportement attendu

- La présence d’événements journée ne doit pas monopoliser une part importante de l’espace visible.
- Le comportement doit rester adapté au nombre d’événements présents.
- Tous les événements journée doivent rester accessibles et identifiables.
- L’utilisateur doit continuer à pouvoir ouvrir le détail d’un événement.
- L’expérience doit rester efficace aussi bien sur mobile que sur desktop.
- Lorsqu’aucun contenu journée n’est pertinent, cette zone ne doit pas dégrader inutilement l’espace disponible.
- Le comportement de la zone pendant le scroll doit être cohérent avec l’objectif de préserver l’espace utile de la timeline.

## Critère principal de réussite

Sur téléphone, la zone « Journée » ne doit plus empêcher l’utilisateur d’accéder rapidement à une portion significative de la grille horaire.

------

## P1 — Calendrier — Améliorer l’expérience responsive des vues Jour et Semaine
Contexte
Les vues Jour et Semaine sont utilisées aussi bien sur desktop que sur mobile.
Sur téléphone, la vue Semaine actuelle cherche à représenter trop de jours dans une largeur limitée. Cela réduit fortement la largeur disponible pour chaque colonne et provoque des cartes trop étroites : titres tronqués, métadonnées tassées et chevauchements visuels qui rendent les événements difficiles à lire et à distinguer.
Le problème est particulièrement visible lorsque plusieurs événements occupent des créneaux proches ou se chevauchent dans une même journée.
La vue Jour et la vue Semaine n’ont pas nécessairement les mêmes contraintes UX et peuvent donc adopter des comportements responsive différents.
Objectif
Rendre les vues Jour et Semaine réellement confortables à utiliser sur mobile, sans sacrifier la lisibilité des événements pour faire tenir artificiellement toute une semaine dans le viewport.
Pour la vue Semaine mobile, privilégier une fenêtre multi-jours horizontale permettant de consulter plusieurs jours à la fois tout en conservant une largeur de colonne suffisante.
Comportement attendu
Les événements doivent rester lisibles sur téléphone, y compris lorsque plusieurs événements sont présents ou se chevauchent.
Les colonnes de jours ne doivent pas être comprimées au point de rendre le contenu difficile à identifier.
En vue Semaine sur mobile, l’utilisateur doit voir plusieurs jours simultanément sans obligation d’afficher les 7 jours de la semaine dans le même viewport.
Une cible d’environ 3 jours visibles à la fois est attendue en portrait, sous réserve du rendu réel sur différentes largeurs d’écran.
L’utilisateur doit pouvoir parcourir horizontalement les autres jours de la semaine de manière simple et naturelle.
La semaine complète reste la période métier consultée : le déplacement horizontal ne doit pas changer silencieusement de semaine.
La navigation horizontale doit permettre de comprendre facilement quels jours sont actuellement visibles et quels jours restent accessibles.
La grille horaire doit conserver suffisamment d’espace pour être comprise rapidement.
Les informations essentielles permettant d’identifier les événements doivent rester disponibles.
Les contrôles du calendrier ne doivent pas occuper une part disproportionnée de l’écran.
La vue Jour doit rester pleinement lisible sur mobile et peut conserver un comportement différent de la vue Semaine.
L’expérience desktop ne doit pas être dégradée : lorsque l’espace disponible le permet, la vue Semaine doit continuer à offrir une lecture globale efficace de la semaine.
Points UX à challenger pendant l’implémentation
Le comportement exact de la fenêtre multi-jours doit être évalué sur le rendu réel, notamment :
largeur minimale confortable d’une colonne jour ;
nombre de jours visibles selon la largeur d’écran ;
comportement du défilement horizontal ;
intérêt éventuel d’un alignement ou d’un snap lors du scroll ;
maintien de la lisibilité du repère horaire pendant le déplacement horizontal ;
comportement sur mobile paysage et tablette.
Ces points doivent être tranchés à partir de l’usage et du rendu, sans imposer à l’avance une mécanique précise.
Critère principal de réussite
En portrait sur téléphone, la vue Semaine doit permettre de lire clairement les événements de plusieurs jours sans zoom, sans compression excessive des cartes et sans superpositions visuelles dues au manque de largeur.
L’utilisateur doit pouvoir parcourir naturellement l’ensemble de la semaine depuis cette fenêtre multi-jours horizontale.

------

# P2 — Calendrier — Améliorer la fluidité de navigation entre les périodes

## Contexte

Le passage d’un jour, d’une semaine ou d’un mois à l’autre entraîne le chargement des données correspondant à une nouvelle période.

Une latence ou une rupture visuelle répétée peut rendre la consultation du calendrier désagréable, notamment lorsque l’utilisateur navigue successivement entre plusieurs périodes.

## Objectif

Identifier les causes réelles des attentes perceptibles lors de la navigation temporelle du calendrier, puis améliorer la fluidité entre les périodes sans introduire de complexité inutile.

Le périmètre de ce ticket est limité au fonctionnement du calendrier existant. Il ne vise pas une refonte générale du chargement des feeds, du cache applicatif ou de l’architecture de données.

## Comportement attendu

- Le passage à la période précédente ou suivante doit rester fluide.
- La consultation successive de plusieurs périodes ne doit pas provoquer de ruptures visuelles inutiles.
- Les données déjà disponibles et encore pertinentes doivent pouvoir être exploitées efficacement.
- La navigation entre Jour, Semaine et Mois doit conserver une expérience cohérente.
- Une amélioration de la fluidité ne doit pas introduire de données obsolètes ou incohérentes.
- Les optimisations proposées doivent répondre à des causes réellement identifiées dans l’implémentation actuelle.

## Critère principal de réussite

La navigation répétée entre périodes doit donner une sensation de continuité plutôt que de rechargement complet.

------

# P3 — Calendrier — Vérifier la robustesse des règles temporelles

## Contexte

Les événements du calendrier peuvent :

- commencer ou terminer à la frontière entre deux journées ;
- couvrir plusieurs jours ;
- être affichés selon un fuseau horaire métier ;
- traverser un changement d’heure ;
- être consultés dans différentes vues du calendrier.

Ces situations peuvent produire des incohérences d’affichage difficiles à détecter dans les cas standards.

## Objectif

Vérifier que les règles temporelles actuellement utilisées par le calendrier sont cohérentes et robustes dans les principaux cas limites.

## Comportement attendu

- Un événement doit apparaître uniquement dans les périodes auxquelles il appartient réellement.
- Les événements couvrant plusieurs jours doivent apparaître sur toutes les journées concernées.
- Les frontières entre jours, semaines et mois doivent être traitées de manière cohérente.
- Un événement ne doit ni disparaître ni être dupliqué à cause d’une frontière temporelle.
- Le fuseau horaire métier ne doit pas provoquer de décalage inattendu.
- Les changements d’heure saisonniers ne doivent pas modifier incorrectement la date ou la durée apparente d’un événement.
- Les vues Jour, Semaine et Mois doivent appliquer les mêmes règles fonctionnelles.
- Le comportement doit rester cohérent entre un calendrier établissement et un calendrier multi-établissements.

## Critère principal de réussite

Un même événement doit être positionné de façon cohérente quelle que soit la vue utilisée et même dans les cas limites temporels.

------

# P4 — Calendrier — Clarifier la sémantique des événements « journée complète »

## Contexte

Une exécution peut représenter soit une activité positionnée à une heure précise, soit une activité couvrant une journée complète.

Les événements journée complète ont une sémantique différente des événements horaires, notamment lorsqu’ils couvrent plusieurs dates, sont récurrents ou sont manipulés dans différents fuseaux horaires.

La représentation actuelle doit être challengée avant que les fonctionnalités de planification deviennent plus complexes.

## Objectif

Vérifier que le fonctionnement actuel des événements journée complète garantit une sémantique métier cohérente sur l’ensemble de leur cycle de vie.

L’investigation doit couvrir le fonctionnement actuel depuis la création ou la planification de l’événement jusqu’à sa persistance, son exposition au frontend et son affichage dans les vues Jour, Semaine et Mois. Les occurrences issues d’une récurrence doivent également être prises en compte lorsqu’elles reposent sur ce même fonctionnement.

Ce ticket ne présuppose pas qu’une évolution du modèle de données ou de l’API soit nécessaire.

## Comportement attendu

- Un événement journée complète doit apparaître sur les dates métier attendues.
- Il ne doit pas changer de journée de manière inattendue en fonction du fuseau horaire utilisé pour consulter l’application.
- Les événements journée couvrant plusieurs dates doivent rester cohérents sur l’ensemble de cette période.
- Les vues Jour, Semaine et Mois doivent représenter les mêmes dates pour un même événement.
- Le comportement doit être cohérent entre les événements créés directement et ceux issus d’une planification ou d’une récurrence.
- Les éventuelles ambiguïtés ou limites du fonctionnement actuel doivent être identifiées de bout en bout avant de décider d’une évolution technique.

## Critère principal de réussite

La notion de « journée complète » doit avoir une signification métier stable et prévisible depuis sa création jusqu’à son affichage dans le calendrier.