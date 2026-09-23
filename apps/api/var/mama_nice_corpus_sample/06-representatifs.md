# Couverture réelle par famille et activité

Chaque famille et chaque activité apparaît ici avec un scénario réellement authored,
un retard ou un projet proactif. Les absences de Signal, Pattern ou plan restent explicites.

## Familles

### signal:fuite-512 — Le siphon de la chambre 512 fuit encore

- Archétype : Fuite sanitaire en chambre
- Date : 2026-09-19 09:40:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:fuite-512
- Statut : in_progress
- Famille : Incident opérationnel
- Activité : Hébergement et chambres
- Pattern : pattern:fuites — Petites fuites sanitaires récurrentes
- Plan : plan:fuite-sanitaire — Traitement d'une fuite sanitaire légère
- Exécution : exec:signal:signal:fuite-512
- Observations :
  - Le siphon de la chambre 512 fuit encore. Une flaque revient sous le lavabo.
- Tâches principales :
  - Sécuriser la zone et couper l'eau si besoin
  - Localiser et réparer la fuite
  - Assécher et contrôler l'évacuation
  - Confirmer la remise en service

### signal:unassigned-lobby — Un client attend au lobby sans chambre identifiée

- Archétype : Accueil et attente au lobby
- Date : 2026-09-22 07:40:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:unassigned-lobby
- Statut : open
- Famille : Expérience client
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Routage : non qualifié
- Observations :
  - Un client tourne dans le lobby. Sa réservation n'est pas encore identifiée.
- Tâches principales : aucune

### signal:file-diner — La file du dîner dépasse le lobby depuis vingt minutes

- Archétype : Service restaurant ou file
- Date : 2026-09-21 20:40:00+02:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:file-diner
- Statut : open
- Famille : Qualité de service
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:attente-restaurant — Attente excessive au restaurant
- Plan : aucun
- Exécution : aucun
- Observations :
  - La file du dîner dépasse le lobby depuis vingt minutes. Les clients s'impatientent au restaurant.
- Tâches principales : aucune

### signal:controle-eclairage-3e — Le contrôle éclairage du 3e a trouvé deux ampoules mortes

- Archétype : Éclairage des circulations
- Date : 2026-09-14 15:00:00+02:00
- Lieu : circulations_chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:controle-eclairage-3e
- Statut : resolved
- Famille : Prévention
- Activité : Maintenance
- Pattern : pattern:eclairage — Défauts d'éclairage dans les chambres et circulations
- Plan : plan:defaut-eclairage — Traitement d'un défaut d'éclairage
- Exécution : exec:signal:signal:controle-eclairage-3e
- Observations :
  - Ronde du 14 septembre : deux ampoules mortes au palier du 3e, changées le jour même.
- Tâches principales :
  - Identifier le circuit et le luminaire
  - Remplacer ou réparer
  - Tester l'éclairage de la zone
  - Consigner le résultat

### signal:chambre-406 — La chambre 406 n'est pas prête, le client est au lobby

- Archétype : Chambre non prête à l'arrivée
- Date : 2026-09-21 16:20:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:chambre-406
- Statut : open
- Famille : Inefficacité de processus
- Activité : Hébergement et chambres
- Pattern : pattern:chambres-non-pretes — Chambres non prêtes à l'heure d'arrivée
- Plan : aucun
- Exécution : aucun
- Observations :
  - La chambre 406 n'est pas prête. Le client attend au lobby avec ses bagages.
- Tâches principales : aucune

### signal:prepa-lienders — Le ClickShare de l'Atelier 1 reste à tester pour TIM LIENDERSS

- Archétype : Audiovisuel Atelier ou Studio
- Date : 2026-09-19 10:00:00+02:00
- Lieu : atelier_1
- Auteur : maintenance
- Responsable : evenements_privatisations
- Signal : signal:prepa-lienders
- Statut : in_progress
- Famille : Coordination cross-pôles
- Activité : DJ sets
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : plan:verification-clickshare — Vérification d'un équipement ClickShare
- Exécution : exec:signal:signal:prepa-lienders
- Observations :
  - Le ClickShare de l'Atelier 1 reste à tester pour le DJ set TIM LIENDERSS du 26.
  - Maintenance doit valider HDMI et sono avant l'accueil du 24.
- Tâches principales :
  - Vérifier les branchements
  - Redémarrer l'équipement
  - Tester l'affichage et le son
  - Confirmer le statut de la salle
  - Consigner le résultat

### signal:ci-clim-filtres — Les clim du 3e reviennent tièdes à chaque arrivée, le filtre n'est jamais changé

- Archétype : Clim d'une chambre
- Date : 2026-09-20 09:15:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:ci-clim-filtres
- Statut : open
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : aucun
- Exécution : aucun
- Observations :
  - Trois chambres du 3e ont eu la même clim tiède depuis juillet. La cause commune est le filtre laissé en place entre deux séjours. Il faut améliorer le processus : changer le filtre au départ, pas seulement diagnostiquer pièce par pièce.
- Tâches principales : aucune

### signal:interesting-bruit-3e — Les départs du 3e mentionnent le bruit du couloir, sans chambre en cause

- Archétype : Bruit en chambre ou circulation
- Date : 2026-09-16 11:20:00+02:00
- Lieu : circulations_chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:interesting-bruit-3e
- Statut : interesting
- Famille : Opportunité
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Interesting : opportunity
- Observations :
  - Trois départs du 3e cette semaine parlent du bruit dans le couloir, sans numéro de chambre.
- Tâches principales : aucune

## Activités

### signal:ci-clim-filtres — Les clim du 3e reviennent tièdes à chaque arrivée, le filtre n'est jamais changé

- Archétype : Clim d'une chambre
- Date : 2026-09-20 09:15:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:ci-clim-filtres
- Statut : open
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : aucun
- Exécution : aucun
- Observations :
  - Trois chambres du 3e ont eu la même clim tiède depuis juillet. La cause commune est le filtre laissé en place entre deux séjours. Il faut améliorer le processus : changer le filtre au départ, pas seulement diagnostiquer pièce par pièce.
- Tâches principales : aucune

### signal:unassigned-lobby — Un client attend au lobby sans chambre identifiée

- Archétype : Accueil et attente au lobby
- Date : 2026-09-22 07:40:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:unassigned-lobby
- Statut : open
- Famille : Expérience client
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Routage : non qualifié
- Observations :
  - Un client tourne dans le lobby. Sa réservation n'est pas encore identifiée.
- Tâches principales : aucune

### signal:interesting-sans-gluten — Des clients cherchent une option sans gluten plus visible sur le buffet

- Archétype : Buffet petit-déjeuner
- Date : 2026-09-14 08:25:00+02:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:interesting-sans-gluten
- Statut : interesting
- Famille : Opportunité
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Interesting : opportunity
- Observations :
  - Au buffet, des clients cherchent une option sans gluten plus visible, sans rupture ce matin.
- Tâches principales : aucune

### signal:file-diner — La file du dîner dépasse le lobby depuis vingt minutes

- Archétype : Service restaurant ou file
- Date : 2026-09-21 20:40:00+02:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:file-diner
- Statut : open
- Famille : Qualité de service
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:attente-restaurant — Attente excessive au restaurant
- Plan : aucun
- Exécution : aucun
- Observations :
  - La file du dîner dépasse le lobby depuis vingt minutes. Les clients s'impatientent au restaurant.
- Tâches principales : aucune

### signal:interesting-table-rooftop — Les groupes du rooftop aimeraient garder la table après le dessert

- Archétype : Saison rooftop et piscine
- Date : 2026-09-13 22:10:00+02:00
- Lieu : rooftop
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:interesting-table-rooftop
- Statut : interesting
- Famille : Opportunité
- Activité : Rooftop et piscine
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Interesting : opportunity
- Observations :
  - En fin de saison, les groupes du rooftop demandent à garder la table après le dessert.
- Tâches principales : aucune

### signal:borne-2 — La borne 2 ne démarre plus la charge

- Archétype : Borne électrique du parking
- Date : 2026-09-20 11:10:00+02:00
- Lieu : bornes_electriques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:borne-2
- Statut : open
- Famille : Incident opérationnel
- Activité : Maintenance
- Pattern : pattern:bornes — Indisponibilité des bornes électriques
- Plan : aucun
- Exécution : aucun
- Observations :
  - La borne 2 du parking ne démarre plus la charge. Un badge clignote rouge.
- Tâches principales : aucune

### signal:avis-attente-pdj — Trois avis de la semaine parlent de l'attente au petit-déjeuner

- Archétype : Avis clients sur un irritant déjà vu
- Date : 2026-09-19 14:30:00+02:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:avis-attente-pdj
- Statut : open
- Famille : Expérience client
- Activité : Communication et avis
- Pattern : pattern:avis-negatifs — Thèmes négatifs récurrents dans les avis clients
- Plan : aucun
- Exécution : aucun
- Observations :
  - Trois avis de la semaine parlent de l'attente au petit-déjeuner. Une réponse publique est encore à écrire.
- Tâches principales : aucune

### signal:interesting-studios — Des sociétés demandent le Studio 1 pour des demi-journées

- Archétype : Séminaire ou privatisation
- Date : 2026-09-10 11:50:00+02:00
- Lieu : studio_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:interesting-studios
- Statut : interesting
- Famille : Opportunité
- Activité : Ateliers et Studios
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Interesting : opportunity
- Observations :
  - Deux sociétés ont demandé le Studio 1 à la demi-journée, pas seulement les Ateliers.
- Tâches principales : aucune

### signal:prepa-lienders — Le ClickShare de l'Atelier 1 reste à tester pour TIM LIENDERSS

- Archétype : Audiovisuel Atelier ou Studio
- Date : 2026-09-19 10:00:00+02:00
- Lieu : atelier_1
- Auteur : maintenance
- Responsable : evenements_privatisations
- Signal : signal:prepa-lienders
- Statut : in_progress
- Famille : Coordination cross-pôles
- Activité : DJ sets
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : plan:verification-clickshare — Vérification d'un équipement ClickShare
- Exécution : exec:signal:signal:prepa-lienders
- Observations :
  - Le ClickShare de l'Atelier 1 reste à tester pour le DJ set TIM LIENDERSS du 26.
  - Maintenance doit valider HDMI et sono avant l'accueil du 24.
- Tâches principales :
  - Vérifier les branchements
  - Redémarrer l'équipement
  - Tester l'affichage et le son
  - Confirmer le statut de la salle
  - Consigner le résultat

### Super Sunday — concert

- Date de création du plan : 2026-09-22 16:00:00+02:00
- Plan utilisé : schedule:super-sunday — Préparation opérationnelle Super Sunday
- seed_key de l'exécution : schedule:super-sunday:2026-09-27
- Statut de l'exécution : scheduled
- start_at : 2026-09-27 16:00:00+02:00
- end_at : 2026-09-27 19:00:00+02:00
- schedule_id : schedule:super-sunday
- Mois comptabilisé : 2026-09
- Signal : aucun
- Pôle : evenements_privatisations
- Activité : Super Sunday
- Nature : schedule
- Contexte : Occurrence du schedule #7 le 27 septembre 16 h–19 h. Pas de second one-shot et pas le libellé « Préparation d'un événement DJ ».
- Tâches principales : aucune

### signal:bringue-fichiers — La signalétique de l'Atelier 2 pour La Bringue n'était pas calée

- Archétype : Événement public figé
- Date : 2026-09-04 11:20:00+02:00
- Lieu : atelier_2
- Auteur : communication
- Responsable : evenements_privatisations
- Signal : signal:bringue-fichiers
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : La Bringue à Mémé
- Pattern : pattern:signaletique-event — Défauts de signalétique événementielle
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les fichiers de signalétique de l'Atelier 2 pour La Bringue du 15 octobre n'étaient pas calés.
- Tâches principales : aucune

### signal:club-sonore-sono — La sono de l'Atelier 1 pour Mama Club Sonore a été testée à vide

- Archétype : Événement public figé
- Date : 2026-08-20 16:00:00+02:00
- Lieu : atelier_1
- Auteur : maintenance
- Responsable : evenements_privatisations
- Signal : signal:club-sonore-sono
- Statut : resolved
- Famille : Prévention
- Activité : Mama Club Sonore
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Test à vide le 20 août : la sono de l'Atelier 1 pour Mama Club Sonore du 22 octobre passe.
- Tâches principales : aucune

### signal:horizon-azur-brief — Le brief de l'Atelier 1 pour le séminaire Horizon Azur n'est pas figé

- Archétype : Séminaire ou privatisation
- Date : 2026-09-16 09:40:00+02:00
- Lieu : atelier_1
- Auteur : hotel
- Responsable : evenements_privatisations
- Signal : signal:horizon-azur-brief
- Statut : open
- Famille : Coordination cross-pôles
- Activité : Séminaires
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Horizon Azur, jauge 80 : le brief Atelier 1 n'est pas figé avant le 20 octobre.
- Tâches principales : aucune

### signal:privatisation-atelier-2-devis — Une privatisation de l'Atelier 2 demande un devis demi-journée

- Archétype : Séminaire ou privatisation
- Date : 2026-09-12 14:15:00+02:00
- Lieu : atelier_2
- Auteur : restaurant
- Responsable : evenements_privatisations
- Signal : signal:privatisation-atelier-2-devis
- Statut : open
- Famille : Coordination cross-pôles
- Activité : Privatisations
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une société demande un devis pour privatiser l'Atelier 2 une demi-journée, sans brief restauration.
- Tâches principales : aucune

### signal:extras-dimanche — Le planning du dimanche 27 Super Sunday est encore à deux extras près

- Archétype : Staffing et extras
- Date : 2026-09-17 10:15:00+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:extras-dimanche
- Statut : open
- Famille : Inefficacité de processus
- Activité : Staffing et RH
- Pattern : pattern:sous-effectif — Sous-effectif ou besoin de formation récurrent
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le planning affiché au breakroom laisse Super Sunday le 27 à deux extras près.
- Tâches principales : aucune
