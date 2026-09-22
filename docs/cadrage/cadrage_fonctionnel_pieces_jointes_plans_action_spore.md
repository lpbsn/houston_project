**SPORE**

# Pièces jointes aux commentaires des plans d’action

Cadrage fonctionnel — V1

| Produit | Spore |
| --- | --- |
| Statut | Cadrage fonctionnel validé |
| Date | 21 septembre 2026 |

> Finalité. Permettre aux utilisateurs autorisés d’ajouter des photos ou documents lorsqu’ils commentent un plan d’action, tout en conservant ces pièces jointes comme éléments consultables du plan lui-même.

## 1. Contexte et problème à résoudre

Les commentaires d’un plan d’action permettent aujourd’hui de documenter son suivi, mais ils ne permettent pas d’y joindre des preuves ou documents utiles : photo terrain, capture, justificatif, compte rendu ou PDF.

Le besoin n’est pas uniquement d’ajouter un fichier dans un commentaire. Une pièce jointe doit également rester retrouvable depuis le plan d’action, afin de ne pas dépendre de la relecture de tout le fil de commentaires.

### Résultat attendu

- Un utilisateur autorisé peut joindre des fichiers lorsqu’il publie un commentaire sur un plan d’action.
- La pièce jointe est visible dans le commentaire qui l’a introduite.
- La même pièce jointe est également retrouvable depuis une vue globale du plan.
- Les droits d’accès aux fichiers suivent les droits d’accès au plan.
- La disponibilité des fichiers suit le cycle de vie du plan.
## 2. Cas d’usage

### 2.1 Ajouter une pièce jointe

Depuis le fil de commentaires d’un plan d’action en cours, l’utilisateur peut sélectionner une ou plusieurs pièces jointes avant de publier son commentaire.

- L’ajout est possible sur un commentaire principal ou sur une réponse.
- Le commentaire texte reste obligatoire en V1.
- L’utilisateur voit les fichiers sélectionnés avant publication et peut retirer un fichier de sa sélection.
- En cas d’échec d’un fichier, l’utilisateur est informé et peut réessayer sans perdre le contexte de son commentaire.
### 2.2 Consulter une pièce jointe

- Depuis le commentaire : la pièce jointe apparaît avec le message qui l’a introduite.
- Depuis le plan : une zone « Pièces jointes du plan » permet de retrouver l’ensemble des fichiers encore disponibles.
- Une image peut être prévisualisée ; un document PDF peut être ouvert avec le comportement adapté au web ou au mobile.
### 2.3 Retrouver l’origine d’un fichier

Lorsqu’un fichier est affiché dans la vue globale du plan, l’utilisateur doit pouvoir comprendre de quel commentaire il provient, afin de conserver le contexte métier de la pièce jointe.

## 3. Règles fonctionnelles

### 3.1 Statut du plan

| Statut du plan | Ajouter un fichier | Consulter les fichiers existants |
| --- | --- | --- |
| Planifié | Non | Selon l’accès au plan |
| En cours | Oui | Oui |
| En attente de validation | Oui | Oui |
| Terminé | Non | Oui pendant la période de conservation |
| Annulé | Non | Non |

> Choix V1. Les pièces jointes ne peuvent être ajoutées que lorsque le plan est réellement actif : « En cours » ou « En attente de validation ».

### 3.2 Formats et limites

- Formats image : JPEG, PNG, WebP, HEIC / HEIF.
- Documents : PDF.
- Taille maximale : 10 MB par fichier.
- Maximum : 4 fichiers par commentaire.
- Ces limites doivent être communiquées dans l’interface avant ou au moment de la sélection.
### 3.3 Appartenance fonctionnelle

Une pièce jointe est considérée comme un élément du plan d’action. Le commentaire dans lequel elle a été ajoutée constitue son origine et son contexte, mais n’est pas son seul point d’accès.

Cette règle garantit qu’un document important reste retrouvable depuis le plan même si le fil devient long. En V1, aucune suppression manuelle d’une pièce jointe déjà publiée n’est proposée.

### 3.4 Hébergement des médias

Les photos et documents de cette fonctionnalité sont hébergés dans un bucket S3 dédié à ces médias, distinct notamment du bucket utilisé par les pièces jointes du Chat. Cette séparation fait partie du cadrage V1.

Le stockage doit être optimisé pour limiter l’accumulation de fichiers inutiles et maîtriser durablement le volume de données conservé. Les fichiers abandonnés lors d’un ajout non finalisé doivent être supprimés automatiquement, au même titre que les fichiers arrivés en fin de période de conservation. Seuls les médias encore utiles au produit doivent rester stockés.

## 4. Accès et confidentialité

Les pièces jointes n’introduisent pas de nouveau niveau de permission. Un utilisateur peut consulter un fichier uniquement s’il est autorisé à consulter le plan concerné.

- Un utilisateur qui perd l’accès au plan perd également l’accès aux pièces jointes.
- Un utilisateur qui obtient légitimement l’accès au plan bénéficie du même accès aux pièces jointes.
- Un fichier ne doit pas être accessible via un lien ou une référence permettant de contourner les droits du plan.
- Les pièces jointes ne sont pas destinées à être partagées publiquement ou en dehors de Spore.
## 5. Cycle de vie des pièces jointes

### 5.1 Plan terminé

Lorsqu’un plan passe effectivement au statut « Terminé », ses pièces jointes restent disponibles pendant 30 jours.

- Pendant ces 30 jours, les utilisateurs ayant accès au plan peuvent encore consulter les fichiers.
- Aucun nouveau fichier ne peut être ajouté.
- À l’issue des 30 jours, les fichiers ne sont plus consultables et sont supprimés définitivement du stockage Spore.
### 5.2 Plan annulé

Lorsqu’un plan passe au statut « Annulé », ses pièces jointes deviennent immédiatement indisponibles et doivent être supprimées définitivement.

> Comportement utilisateur. Dès que l’annulation est effective, aucun utilisateur ne doit pouvoir rouvrir une pièce jointe du plan.

### 5.3 Copie déjà ouverte ou téléchargée

Spore contrôle la disponibilité de la copie hébergée dans l’application. Une copie qu’un utilisateur a déjà téléchargée, exportée ou ouverte dans une application tierce ne peut pas être reprise à distance. Cette limite doit être comprise comme une contrainte fonctionnelle du produit.

## 6. Expérience utilisateur attendue

### Dans le composer de commentaire

- Action claire pour ajouter des fichiers.
- Affichage des fichiers sélectionnés avant envoi.
- Possibilité de retirer un fichier avant publication.
- Indication des formats, de la taille maximale et du nombre maximal.
- Retour explicite en cas de fichier non supporté, trop volumineux ou d’échec d’envoi.
### Dans le fil de commentaires

- Les pièces jointes sont affichées sous le commentaire correspondant.
- Le nom du fichier est lisible.
- Les images bénéficient d’une prévisualisation adaptée.
- Les PDF disposent d’une action claire d’ouverture.
### Dans le plan

La V1 conserve la consultation globale dans l’espace Commentaires du plan, via une zone dédiée « Pièces jointes du plan ». Il n’est pas nécessaire de créer un nouvel onglet Documents.

- La liste regroupe uniquement les fichiers encore disponibles.
- Chaque fichier permet d’identifier son commentaire d’origine.
- L’affichage doit fonctionner de façon cohérente sur la version web/desktop et sur l’application mobile.
- Le comportement doit rester cohérent avec le niveau d’optimisation déjà attendu sur les surfaces Chat et Signal.
- L’application doit éviter les requêtes et téléchargements redondants.
- Le chargement des médias doit rester progressif.
- Le fichier original n’est chargé qu’au moment où l’utilisateur souhaite le consulter.
- Les images doivent disposer d’une représentation optimisée pour les miniatures et aperçus.
L’affichage des pièces jointes doit limiter le volume de données transférées et les accès inutiles au stockage. Les listes de commentaires et la vue globale du plan ne doivent pas charger systématiquement les fichiers originaux.

### Optimisation des médias et des accès

## 7. Cas limites attendus

| Situation | Comportement attendu |
| --- | --- |
| Le plan change de statut pendant l’ajout | La publication ne doit pas créer de pièce jointe si le nouveau statut ne l’autorise plus. |
| Un fichier dépasse 10 MB | Il est refusé et l’utilisateur reçoit un message explicite. |
| Plus de 4 fichiers sont sélectionnés | La sélection ou la publication est bloquée avec une explication. |
| Le type de fichier n’est pas supporté | Le fichier est refusé. |
| Une partie des fichiers échoue | L’utilisateur identifie clairement les fichiers concernés et peut réessayer. |
| Le plan est annulé pendant qu’un fichier est ouvert | Toute nouvelle tentative d’accès est refusée dès l’annulation. |
| Le plan atteint 30 jours après sa clôture | Les fichiers ne sont plus accessibles. |

## 8. Critères d’acceptation V1

- Un utilisateur autorisé peut publier un commentaire avec 1 à 4 fichiers supportés sur un plan « En cours ».
- Le même comportement fonctionne sur une réponse à un commentaire.
- Un commentaire reste obligatoire même lorsqu’un fichier est joint.
- Un fichier apparaît à la fois dans son commentaire d’origine et dans la vue globale du plan.
- Un utilisateur sans accès au plan ne peut pas consulter ses fichiers.
- Aucun nouvel attachment ne peut être ajouté sur un plan planifié, terminé ou annulé.
- Les pièces jointes d’un plan terminé restent consultables pendant 30 jours puis deviennent indisponibles.
- Les pièces jointes d’un plan annulé deviennent immédiatement indisponibles.
- Les limites de format, taille et quantité sont explicites pour l’utilisateur.
- L’ouverture des images et PDF est utilisable sur web/desktop et mobile.
- Les fichiers abandonnés lors d’un ajout non finalisé sont supprimés automatiquement afin d’éviter l’accumulation de stockage inutile.
- Les listes et aperçus de pièces jointes utilisent une représentation optimisée des images ; le fichier original n’est chargé qu’à la consultation.
## 9. Périmètre V1

### Inclus

- Ajout de photos et PDF dans les commentaires de plans actifs.
- Support des commentaires principaux et des réponses.
- Consultation depuis le commentaire et depuis le plan.
- Gestion cohérente web/desktop et mobile.
- Règles d’accès alignées sur celles du plan.
- Conservation 30 jours après terminaison.
- Suppression immédiate à l’annulation.
- Hébergement des médias dans un bucket S3 dédié à cette fonctionnalité, distinct du Chat.
- Nettoyage automatique des fichiers abandonnés et des fichiers arrivés en fin de rétention afin de limiter le stockage inutile.
- Optimisation des aperçus média afin d’éviter le chargement systématique des fichiers originaux.
### Hors périmètre

- Ajout de fichiers directement au plan sans commentaire.
- Pièces jointes sur un plan simplement planifié.
- Suppression manuelle d’un fichier déjà publié.
- Restauration d’un fichier supprimé ou expiré.
- Versioning de documents.
- Dossiers, tags ou classement documentaire avancé.
- Partage public ou lien externe permanent.
- Scan antivirus avancé ou traitement documentaire métier.
- Monitoring de coût/volume de stockage.
## 10. Synthèse des décisions

| Sujet | Décision |
| --- | --- |
| Moment d’ajout | En cours / En attente de validation |
| Origine | Commentaire principal ou réponse |
| Texte obligatoire | Oui |
| Fichiers | JPEG, PNG, WebP, HEIC/HEIF, PDF |
| Limites | 10 MB par fichier ; 4 par commentaire |
| Visibilité | Dans le commentaire + vue globale du plan |
| Droits | Identiques aux droits d’accès au plan |
| Plan terminé | Consultation pendant 30 jours puis suppression |
| Plan annulé | Indisponibilité immédiate et suppression |
| Suppression manuelle | Non en V1 |
| Optimisation du stockage | Nettoyage automatique des fichiers abandonnés et en fin de rétention |
| Optimisation médias | Miniatures/aperçus optimisés ; original chargé uniquement à la demande |
