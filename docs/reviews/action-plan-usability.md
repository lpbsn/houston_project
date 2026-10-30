# Plans d’action : raccourcis terrain et vue Kanban

Base de revue : `main`, commit `7dc06f04c924d5a5db33739ce686d85698358f63`.
Cette PR est indépendante de « Ma journée » (#358) et de la messagerie (#359).

## Pourquoi

Les équipes doivent pouvoir transformer une intention en travail assigné, puis modifier ce travail sans multiplier les écrans. La chronologie, les modèles, la discussion et les documents existaient déjà ; ils restent les sources de vérité. Cette PR ajoute des raccourcis à ces fonctions plutôt qu’un deuxième moteur de projet.

## Parcours livrés

- **Nouveau plan** : formulaire court dans une fenêtre, avec titre, pôle, tâches facultatives, assignés et échéance. Les validations existantes restent obligatoires, notamment l’assignation. Un salarié s’assigne à lui-même. La création détaillée et le catalogue restent accessibles dans le menu.
- **Tâches** : saisie d’un titre puis Entrée pour en ajouter une ; glisser-déposer ou boutons Monter/Descendre pour réordonner. Identité, description, pôle, assigné et date suivent la tâche. Les tâches déjà traitées restent figées et comptent dans la limite existante de dix tâches.
- **Modifier ici** : depuis la fiche d’exécution, modifier titre/description, tâches, assignés ou échéances, puis enregistrer. Réutilise l’hydratation, la validation et le hook de soumission de l’éditeur existant, avec `expected_updated_at` et traitement des conflits.
- **Dupliquer** : préremplit la création d’une nouvelle exécution avec le titre, la description et les tâches, y compris les tâches anciennement terminées. Les pôles sont conservés et revérifiés par les règles de création. Dates, assignations, état d’avancement, commentaires, pièces jointes, sources et décisions de validation ne sont pas recopiés. Aucune écriture avant confirmation du formulaire.
- **Documents et médias** : nom explicite de l’accès au regroupement existant dans la discussion. Aucun nouveau stockage ni élargissement des formats autorisés ; les documents affichés restent les PDF actuellement pris en charge.
- **Tableau Kanban** : En retard / En cours / À valider / Terminés, avec Annulés sur demande. Chaque colonne utilise le feed paginé existant, la vue personnelle/globale et le périmètre établissement/siège. Le retard est calculé, pas un état que l’utilisateur peut imposer.
- **Changement d’état** : menu accessible ou glisser-déposer sur une colonne, relecture du détail, confirmation, puis commande métier existante. Les transitions interdites sont expliquées ; un plan exigeant validation ne peut pas passer directement d’En cours à Terminé. La validation conserve la note obligatoire. Les écritures depuis le tableau siège restent désactivées, comme dans le parcours cross existant.
- **Calendrier ordinateur** : glisser un plan modifiable sur une date ouvre une confirmation d’échéance. PATCH minimal `expected_updated_at` + `end_at`. Le début ne bouge pas. Conservation de l’heure locale et du fuseau du calendrier ; journée entière jusqu’à 23:59 locale. Les chronologies individuelles et les plans sans début renvoient vers la fiche, sans changement automatique. L’édition depuis la fiche reste utilisable au clavier et sur mobile.

## Intégration pour Léo

1. Relire/fusionner cette branche sur le code actuel. Aucun fichier API, migration, contrat généré ou dépendance ajouté.
2. Conserver les owners existants : `useActionPlanCreateSubmit`, `useActionPlanExecutionEditSubmit`, mutations de cycle de vie et invalidations TanStack Query. Les nouveaux composants sont des entrées supplémentaires vers ces owners.
3. Si #359 est intégré d’abord, conserver son évolution de `CommentSection` et reprendre uniquement le libellé Documents et médias de cette PR. Ne pas remplacer sa logique de conversation.
4. Vérifier en recette un compte salarié, un manager limité à ses pôles et un propriétaire. Faire un test sur deux sessions pour le conflit de mise à jour.
5. Les états et droits restent décidés par l’API. Aucun déplacement optimiste qui ferait croire à une réussite avant sa réponse.

## Vérifications

- Tests ciblés action-plans/execution et documents, plus nouveaux tests de copie, dates/fuseaux, positions de tâches figées, autorisations, confirmation, note de validation et pagination.
- TypeScript, ESLint, builds Web et Native/Capacitor.
- Aucun test backend lancé localement : pas de modification serveur et environnement Docker de test indisponible. La CI du dépôt reste le contrôle d’intégration.

## Points de recette visuelle

À vérifier avec les données réelles : formulaire court sur téléphone, éditeur dans la fiche, glisser-déposer calendrier semaine/mois, lecture horizontale du tableau sur petit écran. Aucun enregistrement n’a été effectué dans la production pour cette revue.
