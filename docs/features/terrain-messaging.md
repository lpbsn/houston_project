# Messagerie terrain — proposition pour revue

La messagerie regroupe les échanges d’équipe, les discussions des plans et les mentions. Les commentaires restent attachés à leur plan : aucun fil parallèle ni copie de commentaires.

## Parcours

- Équipe : conversations existantes, accusé de réception 👍, réglages Tous / Mentions / Silencieux.
- Plans d’action : dernière discussion par plan accessible, indicateur non lu, filtre non résolues. Clic vers le commentaire dans le plan.
- Mentions : messages de chat et commentaires de plans mentionnant le membre connecté.
- Rechercher : recherche française dans le contenu, filtres auteur/date/pièce jointe, pagination de 30. Le serveur accepte aussi execution_id pour une recherche ciblée sur un plan.
- Un message peut devenir une observation après relecture et confirmation explicite. Le texte inclut initialement l’auteur et la date. Les pièces jointes ne sont pas transférées ; les droits du chat ne sont pas transmis à l’observation.
- Une discussion de plan peut être épinglée comme décision ou transformée en tâche après confirmation du titre, du responsable et de l’échéance. Les permissions et règles de modification du plan restent celles du service existant. Un même commentaire ne crée qu’une tâche.
- La dictée ajoute une transcription relue au brouillon, sans envoi automatique. Elle réutilise le consentement et le fournisseur IA existants. Elle ne crée pas de message audio conservé.

## Intégration

Base : main 7dc06f04c924d5a5db33739ce686d85698358f63. Branche indépendante de la PR Ma journée.

1. Revoir/merger sur une branche de test après passage de CI et sauvegarde habituelle.
2. Appliquer les migrations Django habituelles. Aucune nouvelle dépendance ou variable secrète. Les index de recherche PostgreSQL sont créés CONCURRENTLY dans des migrations non atomiques.
3. Déployer API/worker et frontend depuis le même commit. Contrats OpenAPI, types et événements de rafraîchissement sont inclus.
4. Recompiler/synchroniser Capacitor selon la procédure native existante pour distribuer l’interface mobile.

Aucun changement de rétention : les messages purgés selon la politique existante ne sont plus recherchables. Une observation confirmée conserve sa provenance minimale même après purge du message. Les discussions des plans suivent la visibilité du feed opérationnel existant, pas un nouvel accès aux archives.

## Validation attendue avant fusion

- CI serveur PostgreSQL : migrations, droits inter-établissements, historique masqué, départ d’une conversation, idempotence, tâches, préférences et contrats.
- Web : recherche puis ouverture d’un ancien message ; mention vers le commentaire exact ; lecture simultanée par deux membres ; refus d’accès et échec réseau sans faux succès.
- Native iOS/Android réel : permission microphone, dictée puis correction, fermeture pendant transcription, clavier et dialogue. Le support MediaRecorder dépend de la WebView ; en cas d’indisponibilité, l’utilisateur conserve la saisie texte.
- Le mode silencieux ne doit pas supprimer les notifications métier d’affectation/échéance : seuls les messages/commentaires sont filtrés.
- Vérifier les décisions épinglées et 👍 avec deux sessions, ainsi que la modification de tâche dans le formulaire existant.

## Propriété du code

Les services métier existants restent propriétaires de la création des observations et de la mise à jour des plans. Les lectures de messagerie sont bornées et utilisent les droits serveur. Le partage d’un message privé n’est jamais automatique. Les suggestions IA n’ont aucun rôle dans ces décisions d’accès.
