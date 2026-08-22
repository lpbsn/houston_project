# Spore Analytics — Cadrage BI&A / Data Visualization du Dashboard

## 1. Objet du document

Ce document définit la cible **BI&A, UX et Data Visualization** du Dashboard Spore Analytics.

Il complète le cadrage fonctionnel et data existant :

- le **cadrage fonctionnel/data** reste la source de vérité pour la définition des métriques, les règles de calcul, les scopes Cross / Établissement, les permissions et la couverture historique ;
- les **maquettes cibles** sont la référence principale pour la composition, la densité, les proportions et le langage visuel ;
- le présent document définit **ce qu’un dirigeant doit comprendre, dans quel ordre, et comment les données doivent être restituées**.

L’objectif n’est pas de produire un rapport de KPI, mais un **dashboard de pilotage** lisible en quelques secondes.

Une implémentation techniquement correcte mais visuellement pauvre, générique, difficile à scanner ou sensiblement éloignée des maquettes n’est pas considérée comme terminée.

---

# 2. Audience et rôle du Dashboard

## 2.1 Audience

Le Dashboard Spore Analytics s’adresse en priorité à :

- **Owner** : pilotage global de l’organisation ;
- **Manager/Director** : pilotage des établissements auxquels il a accès.

Le staff opérationnel n’est pas la cible principale du Dashboard Analytics.

La logique BI reste la même en :

- scope **Cross** ;
- scope **Établissement**.

Seule la population analysée change.

## 2.2 Fonction du Dashboard

Le Dashboard est un outil de :

- pilotage ;
- priorisation ;
- détection ;
- compréhension rapide de la situation terrain.

Il doit répondre d’abord à :

> **Qu’est-ce qui mérite mon attention maintenant ?**

Puis permettre d’approfondir :

> **Pourquoi ? Où ? Et est-ce que la situation évolue dans le bon sens ?**

Toutes les cartes n’ont donc pas le même poids.

---

# 3. Questions de pilotage prioritaires

## 3.1 Axe 1 — Qu’est-ce qui se passe sur le terrain ?

Questions prioritaires :

1. Quels problèmes reviennent ?
2. Quels nouveaux problèmes apparaissent ?
3. Où se concentrent-ils ?
4. Quels pôles concentrent le plus d’activité ?

Les **Motifs récurrents** et **Nouveaux motifs** sont des informations de pilotage de premier niveau. Ils ne doivent pas être traités comme de simples listes secondaires.

## 3.2 Axe 2 — Est-ce qu’on les traite correctement ?

Questions prioritaires :

1. Combien d’observations restent ouvertes ?
2. Depuis combien de temps ?
3. À quelle vitesse sont-elles traitées ?
4. Quelle part de la charge est réellement résolue ?
5. Les plans d’action tiennent-ils leurs échéances ?
6. Combien de temps faut-il pour valider un plan terminé ?

## 3.3 Informations de contexte

Utiles mais moins prioritaires :

- classement des contributeurs ;
- résumé IA futur ;
- CA vs Observations futur.

Le classement des contributeurs informe sur la dynamique de contribution. Il ne doit jamais être interprété comme une mesure RH de performance individuelle.

---

# 4. Test des 5 secondes

Sans lire les petits textes et sans connaître les définitions techniques des KPI, un directeur doit pouvoir identifier en environ 5 secondes :

- ce qui revient ;
- ce qui vient d’apparaître ;
- combien d’observations restent ouvertes ;
- combien sont ouvertes depuis plus de 15 jours ;
- le temps médian avant résolution ;
- la part ou le volume des plans en retard.

La lecture doit fonctionner dans cet ordre :

**nombre fort → forme visuelle → signal / tendance → libellé → détail statistique**

et non :

**titre → paragraphe → sous-texte → statistique → interprétation manuelle**.

---

# 5. Architecture générale du Dashboard

## 5.1 Ordre cible desktop

```text
HEADER + PÉRIODE
Coverage si nécessaire

SYNTHÈSE OPÉRATIONNELLE x4

MOTIFS RÉCURRENTS        | NOUVEAUX MOTIFS

TEMPS DE TRAITEMENT      | OBSERVATIONS ENCORE OUVERTES

RESPECT DES ÉCHÉANCES    | ZONES LES PLUS SIGNALÉES

ACTIVITÉ DU PÔLE         | CLASSEMENT CONTRIBUTEURS

RÉSUMÉ IA — futur        | CA VS OBSERVATIONS — futur
```

La grille n’a pas à être un 2×2 rigide. Les proportions et hauteurs doivent répondre :

- à l’importance métier ;
- au volume d’information ;
- à la densité réelle du contenu.

Une carte vide ne doit pas conserver artificiellement la hauteur d’une carte riche.

---

# 6. Premier viewport desktop

Sur 1440 / 1920 px, le premier écran sans scroll doit contenir :

1. le header ;
2. le contexte de coverage si nécessaire ;
3. la synthèse opérationnelle compacte ;
4. Motifs récurrents ;
5. Nouveaux motifs ;
6. au minimum le début de la zone traitement / backlog.

Les motifs doivent être immédiatement visibles.

Les placeholders IA / CA ne doivent jamais consommer cet espace tant qu’ils ne sont pas fonctionnels.

---

# 7. Canvas et utilisation de l’espace

Le Dashboard est un **canvas de pilotage**, pas une colonne de lecture.

Principes :

- largeur utile après sidebar réellement exploitée ;
- `w-full` ;
- centrage possible avec un max-width ultrawide ;
- pas de `max-w-6xl` ou largeur équivalente créant plusieurs centaines de pixels de marge perdue ;
- gutters desktop de l’ordre de 24–40 px ;
- max-width de sécurité ultrawide autour de 1536 px (`96rem`) acceptable ;
- gaps entre cartes autour de 16–20 px ;
- padding interne généralement 20–24 px.

La respiration visuelle doit venir du rythme interne, pas de grandes marges vides autour du dashboard.

---

# 8. Synthèse opérationnelle haute

## 8.1 Objectif

Répondre immédiatement à :

> **Quelle est la situation en un coup d’œil ?**

La synthèse doit être un **bandeau unique compact**, pas quatre grosses cartes.

## 8.2 Indicateurs

Quatre indicateurs existants :

1. Observations encore ouvertes
2. Observations ouvertes depuis plus de 15 jours
3. Temps avant résolution
4. Plans en retard

Exemple :

```text
12                     4 · 33 %              6 j                18 %
encore ouvertes        depuis +15 jours      avant résolution   en retard
                                               médiane            3 sur 17 plans
```

Hauteur cible : environ 90–110 px desktop.

## 8.3 Contexte des ratios

Un ratio ne doit jamais être affiché sans son volume lorsque le petit dénominateur peut tromper l’interprétation.

Exemples :

- `18 %` — `3 sur 17 plans`
- `33 %` — `4 sur 12 observations ouvertes`
- `6 j` — `médiane · 18 observations`

## 8.4 États particuliers

- aucune observation ouverte → `0 observation en attente`
- aucune résolution → `Aucune résolution sur la période`
- aucun plan mesurable → `Aucun plan avec échéance mesurable`
- coverage non comparable → pas de delta

---

# 9. Motifs récurrents

## 9.1 Question métier

> **Quels problèmes reviennent le plus sur la période ?**

L’utilisateur doit comprendre immédiatement :

- le motif ;
- sa fréquence ;
- son évolution ;
- son établissement en Cross si nécessaire.

## 9.2 Visualisation

Ranked list + mini-barres de volume.

Exemple :

```text
1  Porte chambre froide                    12 observations   ↑ +4
   Maintenance · Akatsuki        ███████████████

2  Rupture produit                         8 observations    ↓ -2
   Réception · Anbu             ██████████
```

Hiérarchie :

**nom → fréquence → tendance → contexte**.

La barre représente uniquement le volume.

## 9.3 Couleur

- volume : neutre / marque ;
- hausse d’un motif récurrent : négatif ;
- baisse : positif ;
- non comparable : pas de delta.

Aucun score de risque.

## 9.4 Top et CTA

Top 5.

Si davantage :

> `Voir tous les motifs`

Puis :

> `Réduire`

## 9.5 Empty state

**Aucun problème récurrent détecté**

`Aucun motif n'apparaît sur plusieurs observations pendant cette période.`

La carte doit se compacter.

---

# 10. Nouveaux motifs

## 10.1 Question métier

> **Quels nouveaux problèmes viennent d’apparaître ?**

Cette carte doit transmettre une logique d’émergence, différente de la fréquence.

## 10.2 Ligne cible

Exemple Cross :

**Grille de grill brûlée — remplacement nécessaire**

`Détecté il y a 6 j`

À droite ou en secondaire :

- `3 observations`
- `2 établissements`

En établissement :

- `3 observations depuis sa détection`

## 10.3 Principes

- nom du motif = point d’accroche principal ;
- date relative visible ;
- volumes correctement pluralisés ;
- pas de confiance ;
- pas de score ;
- pas de couleur négative par défaut ;
- pas de série temporelle inventée.

## 10.4 Empty state

**Aucun nouveau motif détecté**

`Aucun sujet inédit n’est apparu sur cette période.`

Carte compacte.

---

# 11. Temps de traitement

## 11.1 Question métier

> **Combien de temps faut-il pour traiter une observation ?**

Trois chemins :

- résolution ;
- annulation ;
- mise en plan.

## 11.2 Heroes

Trois durées principales :

- Temps avant résolution
- Temps avant annulation
- Temps avant mise en plan

Exemple :

```text
32 j                     4 j                     2 j
avant résolution         avant annulation        avant mise en plan
Médiane                  Médiane                 Médiane
```

La durée est le hero.

## 11.3 Statistiques secondaires

En secondaire / tooltip :

- Médiane
- `La moitié des cas en X ou moins`
- moyenne
- P90 si `n >= 10`
- taille d’échantillon

Exemple :

`Moyenne 38 j · P90 61 j · 18 observations mesurées`

## 11.4 `n = 0`

Pas de `— · moyenne — · n 0`.

Afficher une phrase métier :

- `Aucune observation résolue sur la période`
- `Aucune observation annulée sur la période`
- `Aucune observation mise en plan sur la période`

## 11.5 Résultats secondaires

Sous les délais :

### Part de la charge résolue

Exemple :

**68 %**

`des observations à traiter sont résolues en fin de période`

### Part résolue parmi les clôtures

Exemple :

**91 %**

`des clôtures sont des résolutions plutôt que des annulations`

### Observations rouvertes

Exemple :

**3**

`observations résolues ont été rouvertes`

Ces indicateurs restent secondaires par rapport aux durées.

---

# 12. Observations encore ouvertes

## 12.1 Question métier

> **Combien d’observations attendent encore d’être traitées, et depuis combien de temps ?**

Ne pas utiliser dans l’interface :

- Aging
- Ancienneté
- Stock

## 12.2 Hero

Exemple :

**12 observations encore ouvertes**

Puis :

**4 ouvertes depuis plus de 15 jours**

## 12.3 Distribution

Préférer des **barres horizontales par tranche**.

```text
Moins de 3 jours         █████████████        5
3 à 7 jours              ███████              3
8 à 15 jours             ███                  1
Plus de 15 jours         ████████             3
```

Le count est prioritaire.

Le pourcentage peut être secondaire.

## 12.4 Focus >15 jours

Exemple :

**3 observations sont ouvertes depuis plus de 15 jours**

`25 % des observations ouvertes`

Trend si comparable.

Une hausse = négative.

Ne jamais transformer ce seuil en SLA implicite ou score de risque.

## 12.5 Empty state

**Aucune observation en attente**

`Toutes les observations sont actuellement clôturées.`

---

# 13. Respect des échéances

## 13.1 Question métier

> **Les plans d’action sont-ils réalisés dans les temps ?**

## 13.2 Hero principal

Le retard est la lecture principale.

Exemple :

**22 % des plans sont en retard**

`8 plans concernés`

Avec faible volume :

**1 plan en retard sur 1 mesuré**

Le ratio ne doit jamais masquer le dénominateur.

## 13.3 Visualisation principale

Stacked bar :

- En avance
- À temps
- En retard

```text
████████████████████████████████████

28 %              50 %              22 %
En avance          À temps           En retard
```

Couleurs :

- En avance → positif discret
- À temps → neutre / sombre
- En retard → rouge d’attention

## 13.4 Tendance

Priorité à la tendance du retard.

Exemple :

`En retard : 22 % ↓ 6 pts`

Comparaisons en points de pourcentage.

## 13.5 Aucun plan mesurable

Ne pas afficher :

`0 % / 0 % / 0 %`

Afficher :

**Aucun plan avec échéance mesurable sur la période**

Les plans sans échéance et annulés restent exclus selon le cadrage data.

---

# 14. Temps avant validation

Question :

> **Une fois le travail terminé, combien de temps faut-il avant validation ?**

Affichage :

**1 j 6 h**

`Médiane`

Puis :

`Moyenne 1 j 14 h · 12 plans mesurés`

Pas de P90 si le cadrage ne le prévoit pas.

---

# 15. Délais des plans

Deux métriques secondaires :

- temps avant résolution du plan ;
- temps avant annulation du plan.

Afficher en bas de `Respect des échéances`, en densité faible.

Exemple :

```text
Traitement des plans

Résolution
4 j médian

Annulation
2 j médian
```

Pas de nouvelle grosse carte.

---

# 16. Zones les plus signalées

## 16.1 Question métier

> **Dans quelles zones les observations se concentrent-elles ?**

## 16.2 Visualisation

Bar chart horizontal ranké.

```text
Cuisine                   ███████████████████   24
Réserve                   █████████████         17
Accueil                   █████████              12
Vestiaires                ██████                  7
Sans zone                 ███                     3
```

Le count reste la donnée principale.

## 16.3 Cross

Le couple reste :

`(établissement, zone)`

Deux zones du même nom dans deux établissements restent deux lignes distinctes.

Le nom d’établissement est secondaire.

## 16.4 Couleur

Une seule teinte de volume :

- vert marque ;
- charcoal ;
- ou autre neutre cohérent.

Jamais de gradient vert → orange → rouge.

## 16.5 Tendance

Hausse / baisse de volume = **neutre**.

Pas d’interprétation automatique.

## 16.6 Top

Top 7 + `Autres`.

CTA :

`Voir toutes les zones`

---

# 17. Activité du pôle

## 17.1 Question métier

> **Quels pôles concentrent le plus d’observations ?**

## 17.2 Visualisation

Ranked list, volontairement différente des Zones.

```text
1   Cuisine                           27 observations
    ↑ +4

2   Maintenance                      18 observations
    ↓ -2

3   Service                          11 observations
    —
```

## 17.3 Cross

Le couple reste :

`(établissement, pôle)`

Pas de pseudo-pôle global Cross.

## 17.4 Tendance

Volume de pôle = neutre.

Pas de vert/rouge automatique.

`Sans pôle` reste une catégorie valide.

---

# 18. Classement des contributeurs

## 18.1 Question métier

> **Qui contribue le plus aux remontées et au traitement terrain ?**

Ce classement mesure la contribution comptabilisée dans Spore, pas la performance RH.

Ne jamais utiliser :

- Top performers
- Meilleurs employés
- Performance équipe

## 18.2 Visualisation

Top 5.

```text
1   LP   Léa Martin                    42 pts
         Manager · Cuisine

2   JM   Julien Morel                  35 pts
         Staff · Maintenance
```

Hiérarchie :

**rang → identité → rôle/pôle → points**

Les points ne doivent pas écraser visuellement le nom.

## 18.3 Cross

Plusieurs rôles / pôles possibles.

Ne pas inventer un rôle Cross.

Utiliser :

- listes compactes ;
- `+2 pôles` si nécessaire ;
- tooltip si besoin.

## 18.4 Empty state

**Aucune contribution comptabilisée sur cette période**

---

# 19. Résumé IA

Tant qu’il n’est pas fonctionnel :

- en bas du dashboard ;
- poids visuel faible ;
- pas de grand bandeau pleine largeur dominant ;
- pas de narratif fictif.

Affichage :

**Résumé IA**

`Une synthèse des évolutions et points d’attention sera disponible ici.`

Badge :

`BIENTÔT DISPONIBLE`

Quand l’IA sera réelle, son emplacement pourra être réévalué.

---

# 20. CA vs Observations

Même principe.

Tant que la feature n’est pas réelle :

**CA vs Observations**

`Croisement avec les données d’activité à venir.`

`BIENTÔT DISPONIBLE`

Pas de grande carte vide prioritaire.

---

# 21. Langage visuel global

## 21.1 Principe

La forme et la couleur transmettent de l’information avant de décorer.

Quatre niveaux :

### Niveau 1 — Hero
Valeur principale.

### Niveau 2 — Comparaison / distribution
Barres, rankings, parts, trends.

### Niveau 3 — Explication
Labels, unités, tailles d’échantillon, établissement.

### Niveau 4 — Définition
Médiane, P90, formule, dénominateur précis, tooltip.

---

# 22. Typographie

## Heroes

Environ 30–40 px desktop selon la carte.

Graisse forte, pas ultra-black.

## Titres de cartes

Environ 16–18 px, semi-bold.

## Labels

13–14 px.

## Métadonnées

12–13 px.

Le contraste doit rester suffisant.

---

# 23. Densité

Principe :

> **Dense sans être tassé.**

À éviter :

- grandes zones vides ;
- cartes hautes sans contenu ;
- padding excessif ;
- multiples sous-cards.

Préférer :

- séparateurs ;
- zones internes légères ;
- colonnes ;
- variations de fond discrètes.

---

# 24. Cartes et chrome UI

Éviter le pattern répété :

`rectangle blanc + border + radius + sous-cards`

Les cartes principales peuvent avoir :

- fond blanc ;
- bordure très légère ;
- shadow quasi imperceptible ;
- radius cohérent.

La hiérarchie interne ne doit pas dépendre de boîtes imbriquées.

Test :

> **Si retirer les bordures rend le dashboard incompréhensible, la hiérarchie visuelle est insuffisante.**

---

# 25. Palette

## Vert Spore

Usage :

- sélection ;
- accents ;
- rangs ;
- volumes neutres ;
- tendance positive lorsque justifiée.

Pas partout.

## Charcoal / noir

- titres ;
- heroes ;
- barres neutres ;
- `À temps`.

## Rouge

Uniquement pour une sémantique réellement défavorable :

- retard ;
- hausse des observations >15 j ;
- hausse des réouvertures ;
- hausse des délais ;
- hausse des motifs récurrents.

Jamais pour un volume de zone / pôle.

## Gris

- tracks ;
- séparateurs ;
- contexte ;
- coverage ;
- metadata.

---

# 26. Sémantique des tendances

La couleur dépend du **sens métier**, jamais du simple signe.

| Métrique | Hausse | Baisse |
|---|---|---|
| Temps de traitement | Négatif | Positif |
| Observations >15 j | Négatif | Positif |
| Réouvertures | Négatif | Positif |
| Plans en retard | Négatif | Positif |
| Part de la charge résolue | Positif | Négatif |
| Part résolue parmi les clôtures | Positif | Négatif |
| Motifs récurrents | Négatif | Positif |
| Zones | Neutre | Neutre |
| Pôles | Neutre | Neutre |
| Nouveau motif | Neutre | Neutre |

---

# 27. Trends

Préférer :

`32 j ↓ 4 j`

à :

`32 j [↓ -11.4 %]`

dans un gros badge.

Les tendances doivent être proches de la valeur, discrètes et sémantiques.

---

# 28. Barres de volume

Le maximum visible définit la longueur maximale.

Pas besoin :

- d’axes lourds ;
- de grille ;
- de légende complexe.

Objectif : comparaison immédiate.

---

# 29. Barres empilées

Les labels doivent rester lisibles.

Si un segment est trop petit :

- ne pas mettre le pourcentage dedans ;
- placer le label sous ou hors de la barre.

---

# 30. Icônes

Usage limité :

- information ;
- horloge ;
- observation ;
- plan ;
- empty state discret.

Pas d’icône décorative dans chaque KPI.

---

# 31. États de données

Quatre états doivent rester distincts.

## 31.1 Zéro réel

Exemple :

`0 observation rouverte`

C’est une vraie donnée.

## 31.2 Aucun cas mesurable

Exemple :

`Aucune observation résolue sur la période`

Pas de `0 j`.

## 31.3 Faible échantillon

La donnée reste affichée avec son contexte.

Exemple :

**32 j**

`Médiane · 1 observation mesurée`

## 31.4 Historique non comparable

La valeur actuelle reste affichée.

Le delta disparaît.

Le bandeau global explique la coverage.

---

# 32. Faible échantillon

Règle de présentation :

## `n = 1`

Hero + volume.

Ne pas afficher moyenne + médiane identiques juste pour remplir.

## `2 <= n < 10`

Hero + moyenne + volume.

P90 masqué de la lecture principale.

## `n >= 10`

Médiane + moyenne + P90 + volume disponibles.

Ce sont des règles de présentation, pas de calcul.

---

# 33. P90

Sous `n < 10`, le P90 disparaît de la lecture principale.

Tooltip possible :

`Le P90 est affiché à partir de 10 observations mesurées.`

Ne pas répéter :

`P90 — données insuffisantes`

sur chaque KPI.

---

# 34. Ratios et dénominateurs

Règle :

> **Un pourcentage sans volume est interdit lorsque le petit dénominateur peut fortement modifier son interprétation.**

Exemples :

- `1 plan en retard sur 1 mesuré`
- `8 sur 40 plans`
- `4 sur 12 observations ouvertes`

---

# 35. Faux zéros interdits

Ne jamais transformer une absence de mesure en zéro.

Exemples interdits :

- `0 j` sans résolution ;
- `0 % en retard` sans plan mesurable ;
- `P90 = 0` sans P90 calculable.

---

# 36. Empty states

Une carte vide doit :

- expliquer ce qu’elle aurait montré ;
- rester compacte ;
- ne pas utiliser une grosse illustration générique ;
- ne pas conserver artificiellement une grande hauteur.

---

# 37. Densité adaptative

Règle globale :

> **La densité visuelle s’adapte à la quantité d’information disponible. La structure générale reste stable, mais l’espace d’une donnée inexistante n’est pas réservé artificiellement.**

---

# 38. Coverage

Le backend reste la source de vérité.

Le frontend ne recalcule pas la coverage depuis les timestamps.

Le bandeau global agrège uniquement les états backend affichés.

Affichage cible :

`ⓘ Pas encore assez d’historique pour comparer certaines évolutions. Historique fiable depuis le 21 août.`

Principes :

- discret ;
- non alarmiste ;
- fond gris / légèrement teinté ;
- aucune répétition dans les cartes ;
- aucun gros orange / jaune type erreur système.

---

# 39. Responsive — principes

Le dashboard mobile n’est pas le dashboard desktop compressé.

Il partage :

- langage visuel ;
- couleurs ;
- typographie ;
- hiérarchie ;
- données.

Mais pas nécessairement la même composition.

---

# 40. Navigation mobile

La navigation mobile existante de Spore doit toujours rester disponible.

Le Dashboard Analytics ne doit jamais masquer le composant qui remplace la sidebar desktop.

`hideTopbar` ou toute logique similaire ne doit pas rendre l’utilisateur captif de la page.

Ne pas créer une navigation Analytics spécifique si le shell dispose déjà du bon pattern.

---

# 41. Aucun scroll horizontal global

Critère ferme :

> **À 320 px, le Dashboard ne doit pas rendre `document.documentElement.scrollWidth` supérieur à la largeur du viewport.**

Pas de scroll horizontal global.

Les composants doivent :

- shrink ;
- wrap ;
- passer en vertical ;
- retirer les `min-width` desktop ;
- utiliser `min-w-0` sur les flex children si nécessaire.

---

# 42. Viewports à valider

Au minimum :

- 320 px
- 375 px
- 390 px
- 430 px
- 768 px
- 1440 px
- 1920 px

---

# 43. Grille responsive

## Desktop

2 colonnes principales.

## Tablette

2 colonnes si lisible, sinon 1.

## Mobile

1 seule colonne.

Aucune carte ne garde un `min-width` desktop.

---

# 44. Ordre mobile

Ordre recommandé :

1. Synthèse opérationnelle
2. Motifs récurrents
3. Nouveaux motifs
4. Observations encore ouvertes
5. Temps de traitement
6. Respect des échéances
7. Zones
8. Pôles
9. Contributeurs
10. IA / CA

Le backlog passe avant les statistiques de flux en mobile car il est plus directement actionnable carte par carte.

---

# 45. Synthèse mobile

La synthèse x4 devient une grille 2×2 compacte.

```text
Observations ouvertes    >15 jours
12                       4

Résolution médiane       Plans en retard
6 j                      18 %
```

Pas quatre grandes cards.

---

# 46. Motifs mobile

## Motifs récurrents

```text
Porte chambre froide
12 observations ↑ +4
████████████████
```

## Nouveaux motifs

```text
Grille de grill brûlée
Détecté il y a 6 j

3 observations
2 établissements
```

Le texte peut wrap.

---

# 47. Temps de traitement mobile

Les trois heroes passent en empilement vertical.

```text
Temps avant résolution
32 j
Médiane · 18 observations

Temps avant annulation
4 j
Médiane · 3 observations
```

Pas de 3 colonnes compressées.

---

# 48. Observations encore ouvertes mobile

Les barres horizontales restent adaptées.

Les labels peuvent être raccourcis seulement si nécessaire.

Les counts restent prioritaires.

---

# 49. Respect des échéances mobile

Stacked bar conservée.

Les labels passent sous la barre si nécessaire.

Jamais de texte forcé dans un segment trop petit.

---

# 50. Zones / Pôles mobile

Nom en première ligne.

Établissement en Cross en seconde ligne.

Barre ou count ensuite.

Le contenu peut wrap.

---

# 51. Contributeurs mobile

Pas de tableau.

Exemple :

```text
1   LP   Léa Martin
         Manager · Cuisine
         42 pts
```

Le score peut être aligné à droite seulement si la largeur le permet.

---

# 52. Safe-area / Capacitor

Le shell partagé doit rester intact.

Principes :

- respect des safe areas existantes ;
- aucune topbar supprimée si elle gère aussi navigation / safe-area ;
- pas de `100vh` brut si le repo utilise une abstraction adaptée ;
- aucun CTA collé aux bords.

Cette passe ne refond pas Capacitor mais ne doit pas casser le runtime natif.

---

# 53. Critères d’acceptation BI/UX

## 53.1 Test des 5 secondes

Sur le premier viewport desktop, un directeur doit pouvoir identifier :

- les principaux motifs récurrents ;
- les nouveaux motifs ;
- combien d’observations restent ouvertes ;
- combien sont ouvertes depuis plus de 15 jours ;
- le temps médian avant résolution ;
- la part ou le volume des plans en retard.

## 53.2 Hiérarchie

Le regard doit suivre naturellement :

**Synthèse → Motifs → Traitement / backlog → Échéances → Zones / pôles → Contributeurs → Futures features**

## 53.3 Fidélité aux maquettes

Comparer le rendu aux maquettes sur :

- proportions ;
- densité ;
- importance des chiffres ;
- rythme des listes ;
- contraste ;
- barres ;
- quantité d’espace vide ;
- faible quantité de chrome UI.

Le résultat final doit clairement appartenir à la même famille visuelle.

## 53.4 Utilisation de l’espace

À 1440 / 1920 :

- pas de colonne étroite ;
- pas de grosses marges latérales inutiles ;
- pas de cartes artificiellement hautes ;
- premier viewport riche mais lisible.

## 53.5 Faible volume

Tester explicitement :

- `n=0`
- `n=1`
- une seule zone
- un seul plan
- aucun motif récurrent
- historique non comparable

Le dashboard doit rester crédible.

## 53.6 Cross vs établissement

Captures nécessaires dans les deux scopes.

Cross :

- établissement visible mais secondaire ;
- pas de faux regroupement.

Établissement :

- pas de contexte Cross inutile.

## 53.7 Responsive

Validation manuelle au minimum :

- 1920
- 1440
- 768
- 430
- 375
- 320

Mobile :

- navigation disponible ;
- aucune largeur globale > viewport ;
- aucune donnée importante inaccessible ;
- aucune mini-version compressée du desktop.

---

# 54. Méthode de validation visuelle avec Cursor

La tâche UI n’est pas terminée après :

- typecheck ;
- tests unitaires ;
- rendu fonctionnel.

Workflow attendu :

1. implémentation ;
2. capture desktop Cross à 1920 ;
3. capture desktop Établissement à 1440 ;
4. capture mobile à 375 ;
5. comparaison visuelle avec les maquettes ;
6. auto-review BI/UX par rapport au présent cadrage ;
7. correction des écarts ;
8. tests finaux.

Cursor doit explicitement vérifier :

- densité ;
- marges ;
- poids visuel ;
- place des placeholders ;
- comportement des empty states ;
- absence de scroll horizontal ;
- navigation mobile.

---

# 55. Critère de réussite final

> **Une implémentation techniquement conforme mais visuellement pauvre, générique, difficile à scanner ou sensiblement éloignée des maquettes n’est pas considérée comme terminée.**

Le Dashboard Spore Analytics doit fonctionner comme un **cockpit de pilotage**, pas comme une juxtaposition de KPI.

L’utilisateur doit pouvoir comprendre rapidement :

- ce qui revient ;
- ce qui apparaît ;
- ce qui reste ouvert ;
- ce qui vieillit ;
- si le traitement s’améliore ou se dégrade ;
- si les plans tiennent leurs engagements ;
- où se concentre l’activité.

---

# 56. Principes à ne pas réouvrir

Les règles suivantes restent hors de cette passe et ne doivent pas être réinventées côté UI :

- définitions des métriques ;
- règles de coverage backend ;
- RBAC ;
- règles Cross / Établissement ;
- calculs historiques ;
- timezone ;
- règles de motifs ;
- score gamification ;
- calcul des échéances ;
- absence de fake data ;
- absence de score de risque ;
- absence de taux de confiance ;
- absence de drag-and-drop ;
- absence de filtres non implémentés ;
- placeholders IA / CA tant que non fonctionnels.

Le cadrage fonctionnel/data reste la source de vérité pour ces sujets.

---

# 57. Références de conception

Ordre de priorité en cas de tension :

1. **Cadrage fonctionnel/data** — vérité des données et du comportement.
2. **Présent cadrage BI&A** — hiérarchie, compréhension, visualisation et responsive.
3. **Maquettes cibles** — composition, proportions, densité et langage visuel.
4. **Implémentation actuelle** — point de départ technique uniquement.

L’implémentation existante ne doit jamais être préservée uniquement parce qu’elle existe si elle empêche d’atteindre la cible BI/UX.
