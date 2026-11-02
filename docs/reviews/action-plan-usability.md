# Plans d’action : raccourcis terrain et vue Kanban

Base de revue : `main`, commit `7dc06f04c924d5a5db33739ce686d85698358f63`.
Cette PR est indépendante de « Ma journée » (#358) et de la messagerie (#359).

## Pourquoi

Les équipes doivent pouvoir transformer une intention en travail assigné, puis modifier ce travail sans multiplier les écrans. La chronologie, les modèles, la discussion et les documents existaient déjà ; ils restent les sources de vérité. Cette PR ajoute des raccourcis à ces fonctions plutôt qu’un deuxième moteur de projet.

## Parcours livrés

- **Nouveau plan** : formulaire court dans une fenêtre, avec titre, pôle, tâches facultatives, assignés et échéance. Les validations existantes restent obligatoires, notamment l’assignation. Un salarié s’assigne à lui-même. La création détaillée et le catalogue restent accessibles dans le menu.
- **Tâches** : saisie d’un titre puis Entrée pour en ajouter une ; glisser-déposer ou boutons Monter/Descendre pour réordonner. Identité, description, pôle, assigné et date suivent la tâche. Les tâches déjà traitées restent figées et comptent dans la limite existante de dix tâches.
- **Modifier ici** : depuis la fiche d’exécution, modifier titre/description, tâches, assignés ou échéances, puis enregistrer. Réutilise l’hydratation, la validation et le hook de soumission de l’éditeur existant, avec `expected_updated_at` et traitement des conflits.
- **Dupliquer** : préremplit la création d’une nouvelle exécution avec le titre, la description et toutes les tâches, y compris celles déjà terminées, toutes remises à faire. Les pôles sont conservés et revérifiés par les règles de création. Dates, assignations, état d’avancement, commentaires, pièces jointes, sources et décisions de validation ne sont pas recopiés. Aucune écriture avant confirmation du formulaire.
- **Documents et médias** : nom explicite de l’accès au regroupement existant dans la discussion. Aucun nouveau stockage ni élargissement des formats autorisés ; les documents affichés restent les PDF actuellement pris en charge.
- **Tableau Kanban** : En cours / À valider / Terminés, avec Annulés sur demande. Un plan en cours dont l’échéance est passée reste dans En cours avec un badge « En retard » ; il n’a pas de colonne propre. Chaque colonne utilise le feed paginé existant. La colonne En cours demande `include_overdue=true` pour recevoir ces plans dans la même requête. La vue personnelle/globale et le périmètre établissement/siège restent ceux du feed.
- **Changement d’état** : le menu de la carte est toujours disponible hors siège. Le glisser-déposer vers une colonne reste réservé à l’ordinateur (pointeur fin qui peut survoler). Déposer sur une colonne ne lance que la commande de cette colonne, après relecture du détail et confirmation. Un plan qui exige une validation ne passe pas directement d’En cours à Terminé, y compris pour un valideur. La validation conserve la note obligatoire. Le siège reste en lecture seule.
- **Calendrier ordinateur** : glisser un plan modifiable sur une date ouvre une confirmation d’échéance. Un plan « À valider » ne se déplace pas ; la carte renvoie vers sa fiche. PATCH minimal `expected_updated_at` + `end_at`. Le début ne bouge pas. Conservation de l’heure locale et du fuseau du calendrier ; journée entière jusqu’à 23:59 locale. Les chronologies individuelles et les plans sans début renvoient vers la fiche, sans changement automatique. L’édition depuis la fiche reste utilisable au clavier et sur mobile.

## Intégration pour Léo

1. La promotion vers staging conserve la messagerie terrain et ne reprend de la discussion que le libellé « Documents et médias ». Le feed gagne le paramètre optionnel `include_overdue` (défaut false) pour la colonne En cours. Aucune migration.
2. Conserver les owners existants : `useActionPlanCreateSubmit`, `useActionPlanExecutionEditSubmit`, mutations de cycle de vie et invalidations TanStack Query. Les nouveaux composants sont des entrées supplémentaires vers ces owners.
3. Si #359 est intégré d’abord, conserver son évolution de `CommentSection` et reprendre uniquement le libellé Documents et médias de cette PR. Ne pas remplacer sa logique de conversation.
4. Vérifier en recette un compte salarié, un manager limité à ses pôles et un propriétaire. Faire un test sur deux sessions pour le conflit de mise à jour.
5. Les états et droits restent décidés par l’API. Aucun déplacement optimiste qui ferait croire à une réussite avant sa réponse.

## Vérifications

- Tests ciblés action-plans/execution et documents, plus nouveaux tests de copie, dates/fuseaux, positions de tâches figées, autorisations, confirmation, note de validation et pagination.
- TypeScript, ESLint, builds Web et Native/Capacitor.
- Tests backend ciblés : `validate/` refuse le passage direct En cours → Terminé quand une validation est obligatoire, même pour un valideur ; `category=in_progress` n’inclut les plans en retard que si `include_overdue=true`.

## Points de recette visuelle

À vérifier avec les données réelles : formulaire court sur téléphone, éditeur dans la fiche, glisser-déposer calendrier semaine/mois, lecture horizontale du tableau sur petit écran. Aucun enregistrement n’a été effectué dans la production pour cette revue.
