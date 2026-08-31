# Dashboard Analytics — Cible UX (compréhension)

**Statut :** source de vérité wording / compréhension du Dashboard.  
**Calculs, KPI, API :** [`spore-analytics-cadrage.md`](./spore-analytics-cadrage.md).  
**Hiérarchie visuelle / grille :** [`spore-analytics-dashboard-bi-a-cadrage.md`](./spore-analytics-dashboard-bi-a-cadrage.md).

En cas de conflit de libellé, d’unité, de delta, de tooltip ou d’explication à l’écran, **ce document prime**.

Structure et grille actuelles. Pas de nouveau KPI. Volume ≠ performance.

---

## Principes globaux

Deux horloges, toujours visibles par le contexte de zone :

- **En ce moment** : photo du stock (observations encore ouvertes).
- **Sur la période** : ce qui a été créé, clôturé ou échu sur la fenêtre sélectionnée.

Règles d’affichage :

- Unité visible (`observations`, `plans`, jours en `j` dans les chips et durées).
- Volumes : delta en **nombre** (`+3` / `−2`).
- Taux : delta en **points** (`+7 points vs 7 j d’avant`) — ne pas écrire `pts`.
- Durées : signe visible (`+1,4 j vs 7 j d’avant`).
- Interdits à l’écran : `P90`, `mesuré`, `clôture` (sauf si le wording cible l’utilise), `charge`, `non datable`, `requalification`, `Signal`.
- Badge volume absent de la période précédente : **`Absent des 7 jours précédents`** (le `7` suit le preset). Jamais **« Nouveau »**.
- Pôles et lieux : tendance **neutre** (gris). Pas de rouge/vert de performance.
- Terme métier **annulation** (pas « abandon »).

---

## 1. En-tête + période + bandeau d’historique

**Comprendre**  
Établissement courant ou vue agrégée. Fenêtre = les N derniers jours jusqu’à maintenant. Les flèches comparent à la même durée immédiatement précédente.

**Risque actuel**  
`7 j` lu comme semaine civile. Comparaisons orphelines. « Historique fiable » opaque.

**Cible**
- Chips : `3 j` · `7 j` · `15 j` · `30 j` · `90 j` (inchangés).
- Sous-ligne unique, selon le preset actif, ex. 7 j :  
  **`7 derniers jours · jusqu’à maintenant · comparé aux 7 jours précédents`**
- Coverage (`{date}` = `history_reliable_from` formaté) :
  - aucune comparaison disponible :  
    **`Comparaison indisponible pour cette période. Données comparables depuis le {date}.`**
  - certaines comparaisons indisponibles :  
    **`Certaines comparaisons ne sont pas encore disponibles. Données comparables depuis le {date}.`**
- Export : désactivé, légende visible **Bientôt** (pas seulement au survol).

**Micro-explication / tooltip**  
Non pour la période (la sous-ligne suffit). Non pour le coverage.

**Priorité** P0 (chips + sous-ligne) · P2 (export « Bientôt »).

---

## 2. Bandeau de synthèse (4 KPI)

**Comprendre**  
Combien attendent **maintenant** ; combien depuis **plus de 15 jours** ; délai pour **résoudre** (déjà résolues sur la période) ; part des **plans concernés** en retard.

**Risque actuel**  
Une seule horloge apparente. `+15 jours` ambigu. Délai lu comme attente du stock. Retard lu comme % de tous les plans. Noms d’observations parfois absents.

**Cible**

1. Ouvertes  
   - `12`  
   - `observations encore ouvertes`  
   - ancre : `En ce moment`

2. Ancienneté  
   - `4 · 33 %`  
   - `depuis plus de 15 jours`  
   - `parmi les 12 ouvertes`

3. Résolution  
   - `6 j`  
   - `pour résoudre · médiane`  
   - `sur 18 observations · sur la période`  
   - delta : `+1,4 j vs 7 j d’avant`

4. Plans  
   - n ≥ 5 : `18 %` · `en retard` · **`3 sur 17 déjà dus ou terminés`** (dénominateur **toujours visible**)  
   - n < 5 : **`1 en retard sur 3 concernés`** (pas de %)  
   - même dénominateur métier : déjà dus ou déjà terminés

Empty : `0 observation encore ouverte` · `Aucune résolution sur la période` · `Aucun plan avec date d’échéance`. Vocabulaire unique : **ouverte**.

**Tooltip**  
Oui, courts, KPI 3 et 4 :  
- Résolution : `Parmi les observations déjà résolues sur la période, pas le temps d’attente actuel.`  
- Plans : `Uniquement les plans déjà dus ou déjà terminés. Ceux encore dans les délais ne sont pas comptés.`

**Priorité** P0.

---

## 3. Motifs récurrents

**Comprendre**  
Sujets vus **au moins 2 fois sur la période**. Volume = observations **créées** sur la période. Hausse = plus de répétition, pas un score.

**Risque actuel**  
Nombre nu, % relatif trompeur, badge « Nouveau » vs carte Nouveaux motifs.

**Cible**
- Titre : `Motifs récurrents`
- Sous-titre : `Sujets vus au moins 2 fois sur la période`
- Ligne : nom · `12 observations` · `+3` / `−2`
- Série à 0 sur la période précédente : `Absent des 7 jours précédents`
- Empty : `Aucun problème récurrent détecté` · `Aucun motif n’apparaît sur plusieurs observations pendant cette période.`
- Cross : sous-titre additionnel `Tous établissements` (le « où » reste pôles / lieux)

**Tooltip**  
Non.

**Priorité** P0 (unité, delta nombre, badge) · P2 (`Tous établissements`).

---

## 4. Nouveaux motifs

**Comprendre**  
Première apparition **ici** (établissement ou organisation). Le volume compte **depuis le premier signalement**, pas seulement la période. Un sujet peut aussi être dans les récurrents.

**Risque actuel**  
Volume lu comme « sur les 7 j ». Confusion avec récurrents.

**Cible**
- Titre : `Nouveaux motifs`
- Sous-titre : `Première apparition ici`
- Date : `Détecté il y a 6 j` (inchangé)
- Établissement : `4 observations depuis ce premier signalement`
- Cross : `4 observations · 2 établissements`
- Empty : `Aucun nouveau motif détecté` · `Aucun sujet inédit n’est apparu sur cette période.`

**Tooltip** (carte)  
`Le volume compte depuis la première fois que ce sujet a été vu, pas seulement sur la période affichée.`

**Priorité** P1.

---

## 5. Temps de traitement

**Comprendre**  
Trois délais **concurrents** (pas trois issues exclusives), **sur la période**, parmi les cas déjà arrivés à l’événement. Puis : part du travail disponible **résolue maintenant** ; parmi les dossiers **fermés**, part réellement **résolue** vs **annulée**. Réouvertures = filet, pas un taux.

**Risque actuel**  
Confondu avec le stock ouvert. Deux % jumeaux. Jargon. Annulation lue comme jugement qualité.

**Cible**
- Titre : **`Temps de traitement`**
- Sous-titre : `Sur la période, parmi les cas déjà clôturés ou mis en plan`

**Trois héros**

| Libellé | Sous-ligne |
|---|---|
| `Délai pour résoudre` | `médiane · sur 18 observations` |
| `Délai avant annulation` | idem |
| `Délai avant plan d’action` | idem |

Si n ≥ 2 : `en moyenne 8 j`  
Si n ≥ 10 : `9 sur 10 en 12 j ou moins` (jamais « P90 »)  
Exclusion : `3 dossiers sans date fiable, non inclus`

Hints visibles :  
- Résoudre / annulation : `La moitié des cas en X ou moins.`  
- Plan d’action : `Jusqu’au premier plan. La même observation peut ensuite être résolue ou annulée.`  
- Annulation : `Temps jusqu’à l’annulation. Ce n’est pas un jugement de qualité.`

**Secondaires**

| Libellé | Hint |
|---|---|
| `Part des sujets résolus` | `Des sujets à traiter sur la période, ceux qui sont résolus maintenant.` |
| `Résolutions parmi les dossiers fermés` | `Parmi les dossiers fermés sur la période. Le stock ouvert n’entre pas.` |
| `Observations rouvertes` | `Résolues puis rouvertes sur la période.` |

Empty : `Aucune résolution sur la période` · `Aucune annulation sur la période` · `Aucune observation mise en plan sur la période`. Si stock sans date : `X observations résolues, sans date fiable.`

**Tooltip**  
Oui sur les deux taux (phrases du hint). Pas de tooltip « P90 ».

**Priorité** P0 (sous-titre période, deux taux, héros) · P1 (9 sur 10, hints annulation / plan, exclusions).

---

## 6. Observations encore ouvertes

**Comprendre**  
Stock **en ce moment**, toutes les ouvertes, y compris plus anciennes que la période. Barres = ancienneté. Seuil 15 j **descriptif**, pas un SLA.

**Risque actuel**  
Changer la période semble sans effet (bug apparent). Tranches abrégées.

**Cible**
- Titre : `Observations encore ouvertes`
- Sous-titre : `En ce moment · toutes les ouvertes, pas seulement la période`
- Hero : `12 encore ouvertes`
- Tranches : `Moins de 3 jours` · `3 à 7 jours` · `8 à 15 jours` · `Plus de 15 jours`
- Focus : `4 observations ouvertes depuis plus de 15 jours` · `33 % des ouvertes`
- Empty : `Aucune observation encore ouverte` · `Toutes les observations sont actuellement clôturées.`

**Tooltip**  
Non. Pas de libellé « à risque / critique / SLA ».

**Priorité** P0 (sous-titre stock) · P1 (tranches en toutes lettres).

---

## 7. Respect des échéances

**Comprendre**  
Parmi les plans **déjà dus ou déjà terminés**, quelle part est en retard. En avance / à temps = surtout des plans **terminés** au bon moment. En bas : attente de validation une fois le plan fini ; délais d’annulation et de clôture des plans.

**Risque actuel**  
% de tous les plans. « En avance » lu comme planning en cours. Jargon délais.

**Cible**
- Titre : `Respect des échéances`
- Hero : même règle que le bandeau (n < 5 → fraction)
- **Dénominateur toujours visible** sous le hero :  
  `Parmi les plans déjà dus ou déjà terminés. Les plans encore dans les délais ne sont pas comptés.`
- Barre : `En avance` · `À temps` · `En retard` + `count · %`
- Délais :
  - `Attente de validation une fois le plan terminé`
  - `Délai d’annulation des plans`
  - `Délai de clôture des plans`
- Empty : `Aucun plan avec date d’échéance sur la période`

**Tooltip**  
Non (le dénominateur est à l’écran). Le bandeau garde son tooltip plans pour la lecture 5 secondes.

**Priorité** P0 (dénominateur) · P1 (libellés délais plans).

---

## 8. Lieux les plus cités

**Comprendre**  
Où l’on cite le plus **sur la période**. Pas un stock encore ouvert, pas un score de risque.

**Risque actuel**  
Lu comme zones critiques ou dossiers restants.

**Cible**
- Titre : **`Lieux les plus cités`**
- Sous-titre : `Observations créées sur la période, pas les dossiers encore ouverts`
- Unité : `12 observations`
- Delta : `+3` neutre · ou `Absent des 7 jours précédents`
- Empty : `Aucun lieu cité sur la période`
- Cross : nom d’établissement sous la ligne (inchangé)

**Tooltip**  
Non.

**Priorité** P1.

---

## 9. Activité du pôle

**Comprendre**  
Volume d’observations **créées sur la période**, pôle **responsable aujourd’hui**. Pas le pôle du déclarant. Recalasser un sujet déplace aussi le passé. Pas un classement d’efficacité.

**Risque actuel**  
Podium performance / gravité. Hint illisible.

**Cible**
- Titre : `Activité du pôle`
- Sous-titre : `Observations créées sur la période, selon le pôle responsable aujourd’hui`
- Unité : `12 observations`
- Delta : nombre, neutre · ou `Absent des 7 jours précédents`
- Hint (remplace le texte actuel) : `Si on reclasse un sujet, il change aussi de pôle sur les périodes passées.`
- Empty : `Aucune observation rattachée à un pôle sur la période`
- Cross : nom d’établissement sous la ligne (inchangé)

**Tooltip**  
Non (hint visible).

**Priorité** P1.

---

## 10. Qui a le plus contribué

**Comprendre**  
Points d’activité **sur la période**. Lecture de contribution, pas un nouveau KPI.

**Risque actuel**  
Podium RH. Collision `pts` (taux vs score).

**Cible**
- Titre : **`Qui a le plus contribué`**
- **Pas** de disclaimer RH permanent (ni sous-titre d’évaluation).
- Score : `24 points` (mot entier, pas `pts`)
- Lignes rôle / pôle / établissement : inchangées
- Empty : `Aucune contribution comptabilisée sur cette période`

**Tooltip**  
Non.

**Priorité** P1 (titre + `points`).

---

## 11. Placeholders

**Cible**  
`Résumé IA` et `Chiffre d’affaires vs observations` : badge **Bientôt disponible**. Ne pas les faire monter dans le premier écran.

**Priorité** P2.

---

## Récap priorités

**P0** — Sous-ligne période ; En ce moment vs sur la période (bandeau, ouvertes, motifs, délais) ; dénominateur échéances toujours visible ; unité + delta nombre + `Absent des N jours précédents` ; deux taux cibles ; deltas de durée signés.

**P1** — Nouveaux motifs (volume depuis détection) ; tranches d’âge ; P90 → « 9 sur 10 » ; hints annulation / plan ; délais des plans ; lieux / pôles (titre, sous-titre, unité, hint pôle) ; contributeurs (titre + `points`).

**P2** — Export « Bientôt » ; Cross motifs `Tous établissements` ; placeholders.
