# Six exécutions en retard

### Valider la revue linge de la semaine

- Retard : 7 jours
- Famille : Inefficacité de processus
- Pôle : hotel
- Activité : Hébergement et chambres
- Signal : aucun
- Pattern : aucun
- Plan : plan:rupture-linge — Traitement d'une rupture de linge
- Contexte : Le comptage du 8 septembre trouve 40 draps d'écart avec la blanchisserie.
- Tâches principales :
  - Constater le stock manquant
  - Réaffecter le linge disponible
  - Relancer le prestataire linge
  - Confirmer le réassort

### Valider la clôture de caisse du samedi 12

- Retard : 6 jours
- Famille : Inefficacité de processus
- Pôle : restaurant
- Activité : Restaurant, cuisine et salle
- Signal : aucun
- Pattern : aucun
- Plan : plan:anomalie-caisse — Analyse d'une anomalie de clôture de caisse
- Contexte : Écart de 18 € expliqué par un pourboire mal ventilé.
- Tâches principales :
  - Isoler l'écart de caisse
  - Retracer les tickets
  - Documenter la cause
  - Valider la clôture corrigée

### Valider l'intégration de la réceptionniste

- Retard : 5 jours
- Famille : Prévention
- Pôle : rh
- Activité : Staffing et RH
- Signal : aucun
- Pattern : aucun
- Plan : oneshot:integration-receptionniste — Intégration de la réceptionniste
- Contexte : Arrivée le 7 septembre, modules cochés, badge et planning faits.
- Tâches principales :
  - Remettre badge et accès réception
  - Cocher les modules d'intégration
  - Planifier les shifts d'accompagnement
  - Confirmer l'autonomie sur le poste

### Valider le contrôle éclairage des circulations

- Retard : 4 jours
- Famille : Prévention
- Pôle : maintenance
- Activité : Maintenance
- Signal : aucun
- Pattern : aucun
- Plan : plan:defaut-eclairage — Traitement d'un défaut d'éclairage
- Contexte : Passage du 14 septembre, ampoules du 3e changées, compte-rendu rédigé.
- Tâches principales :
  - Identifier le circuit et le luminaire
  - Remplacer ou réparer
  - Tester l'éclairage de la zone
  - Consigner le résultat

### Valider le contrôle des stocks buffet

- Retard : 3 jours
- Famille : Prévention
- Pôle : petit_dejeuner
- Activité : Petit-déjeuner
- Signal : aucun
- Pattern : aucun
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Contexte : Jeudi 17, rupture de jus constatée et réassortie le jour même.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### Valider le BAT de la signalétique de La Bringue

- Retard : 2 jours
- Famille : Coordination cross-pôles
- Pôle : evenements_privatisations
- Activité : La Bringue à Mémé
- Signal : aucun
- Pattern : aucun
- Plan : oneshot:bat-signaletique-bringue — BAT de la signalétique de La Bringue
- Contexte : Le BAT n'est pas encore transmis à l'impression. La pose n'est pas commencée au 20 septembre.
- Tâches principales :
  - Consolider les contenus et parcours
  - Faire valider les supports par Communication
  - Transmettre le BAT à l'impression
  - Planifier la pose
