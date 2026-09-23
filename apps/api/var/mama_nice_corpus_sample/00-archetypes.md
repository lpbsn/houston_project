# Archétypes métier Mama Nice

Les volumes globaux ne changent pas. Cet échantillon valide le modèle avant expansion.

Un incident isolé conserve sa famille métier naturelle. `continuous_improvement` exige que le titre et les observations décrivent explicitement une récurrence, une cause commune, une faiblesse de processus ou une amélioration concrète recherchée. Appartenir à un Pattern ne suffit pas. Aucun suffixe générique ne justifie cette famille.

## Clim d'une chambre (`clim_chambre`)

- Familles : continuous_improvement, operational_incident
- Pôles observateurs : hotel, maintenance
- Pôles responsables : maintenance
- Activités : hebergement_chambres
- Patterns : pattern:clim-chambres
- Plans : plan:diagnostic-clim
- Statuts : canceled, in_progress, interesting, open, resolved

## Chambre non prête à l'arrivée (`chambre_non_prete`)

- Familles : continuous_improvement, guest_experience, process_inefficiency
- Pôles observateurs : hotel
- Pôles responsables : hotel
- Activités : hebergement_chambres, reception
- Patterns : pattern:chambres-non-pretes
- Plans : plan:rattrapage-chambre
- Statuts : canceled, in_progress, open, resolved

## Rupture ou écart de linge (`linge`)

- Familles : continuous_improvement, process_inefficiency
- Pôles observateurs : hotel
- Pôles responsables : hotel
- Activités : hebergement_chambres
- Patterns : pattern:linge
- Plans : plan:rupture-linge
- Statuts : canceled, open, pending_validation, resolved

## Accueil et attente au lobby (`accueil_lobby`)

- Familles : guest_experience, opportunity, service_quality
- Pôles observateurs : hotel
- Pôles responsables : hotel
- Activités : hebergement_chambres, reception
- Patterns : pattern:attente-checkin
- Plans : aucun
- Statuts : canceled, interesting, open, resolved

## Buffet petit-déjeuner (`buffet_pdj`)

- Familles : continuous_improvement, cross_pole_coordination, opportunity, process_inefficiency, service_quality
- Pôles observateurs : petit_dejeuner, restaurant
- Pôles responsables : petit_dejeuner
- Activités : petit_dejeuner
- Patterns : pattern:equipements-cafe, pattern:proprete-buffet, pattern:ruptures-buffet
- Plans : plan:reassort-buffet-pdj, plan:remise-conformite-buffet
- Statuts : canceled, interesting, open, resolved

## Service restaurant ou file (`service_restaurant`)

- Familles : continuous_improvement, guest_experience, opportunity, service_quality
- Pôles observateurs : hotel, restaurant
- Pôles responsables : restaurant
- Activités : restaurant_cuisine_salle
- Patterns : pattern:attente-restaurant, pattern:erreurs-service
- Plans : plan:incident-service-resto
- Statuts : canceled, interesting, open, resolved

## Écart de caisse (`caisse`)

- Familles : process_inefficiency
- Pôles observateurs : hotel, restaurant
- Pôles responsables : hotel, restaurant
- Activités : reception, restaurant_cuisine_salle
- Patterns : pattern:cloture-caisse, pattern:facturation-caisse
- Plans : plan:anomalie-caisse, plan:anomalie-cloture-caisse
- Statuts : canceled, open, pending_validation, resolved

## Fuite sanitaire en chambre (`fuite_sanitaire`)

- Familles : continuous_improvement, operational_incident
- Pôles observateurs : hotel, maintenance
- Pôles responsables : maintenance
- Activités : hebergement_chambres
- Patterns : pattern:fuites
- Plans : plan:fuite-sanitaire
- Statuts : canceled, in_progress, open, resolved

## Borne électrique du parking (`borne_parking`)

- Familles : continuous_improvement, operational_incident
- Pôles observateurs : hotel, maintenance
- Pôles responsables : maintenance
- Activités : maintenance
- Patterns : pattern:bornes
- Plans : plan:borne-electrique
- Statuts : canceled, open, resolved

## Éclairage des circulations (`eclairage`)

- Familles : continuous_improvement, operational_incident, prevention
- Pôles observateurs : hotel, maintenance
- Pôles responsables : maintenance
- Activités : maintenance
- Patterns : pattern:eclairage
- Plans : plan:defaut-eclairage
- Statuts : canceled, pending_validation, resolved

## Avis clients sur un irritant déjà vu (`avis_client`)

- Familles : continuous_improvement, guest_experience, opportunity
- Pôles observateurs : communication
- Pôles responsables : communication
- Activités : communication_avis
- Patterns : pattern:avis-negatifs
- Plans : plan:avis-client-negatif
- Statuts : canceled, interesting, open, resolved

## Staffing et extras (`staffing`)

- Familles : opportunity, prevention, process_inefficiency
- Pôles observateurs : evenements_privatisations, hotel, rh
- Pôles responsables : rh
- Activités : reception, staffing_rh, super_sunday
- Patterns : pattern:sous-effectif
- Plans : plan:runtime-rh-routines
- Statuts : canceled, interesting, open, pending_validation, resolved

## Audiovisuel Atelier ou Studio (`audiovisuel_salle`)

- Familles : continuous_improvement, cross_pole_coordination, operational_incident
- Pôles observateurs : evenements_privatisations, maintenance
- Pôles responsables : evenements_privatisations, maintenance
- Activités : ateliers_studios, dj_sets, seminaires
- Patterns : pattern:audiovisuel-ateliers
- Plans : plan:verification-clickshare
- Statuts : canceled, in_progress, interesting, open, resolved

## Événement public figé (`evenement_public`)

- Familles : cross_pole_coordination, prevention
- Pôles observateurs : communication, evenements_privatisations, maintenance, rh
- Pôles responsables : evenements_privatisations
- Activités : dj_sets, la_bringue, mama_club_sonore, super_sunday
- Patterns : pattern:audiovisuel-ateliers, pattern:signaletique-event
- Plans : plan:preparation-evenement-dj
- Statuts : canceled, in_progress, open, resolved

## Séminaire ou privatisation (`seminaire_privatisation`)

- Familles : cross_pole_coordination, guest_experience, opportunity
- Pôles observateurs : evenements_privatisations, hotel, restaurant
- Pôles responsables : evenements_privatisations
- Activités : ateliers_studios, privatisations, seminaires
- Patterns : aucun
- Plans : plan:preparation-privatisation, plan:preparation-seminaire
- Statuts : canceled, interesting, open, resolved

## Saison rooftop et piscine (`saison_rooftop`)

- Familles : guest_experience, opportunity, prevention
- Pôles observateurs : evenements_privatisations, hotel, maintenance, restaurant
- Pôles responsables : evenements_privatisations, hotel, restaurant
- Activités : rooftop_piscine
- Patterns : pattern:equipements-rooftop, pattern:piscine
- Plans : plan:ouverture-saison-rooftop-piscine
- Statuts : canceled, interesting, resolved

## Wifi ou réseau chambre (`wifi_reseau`)

- Familles : operational_incident
- Pôles observateurs : hotel, maintenance
- Pôles responsables : maintenance
- Activités : hebergement_chambres, maintenance
- Patterns : aucun
- Plans : aucun
- Statuts : canceled, interesting, resolved

## Bruit en chambre ou circulation (`bruit_chambre`)

- Familles : guest_experience, opportunity
- Pôles observateurs : hotel
- Pôles responsables : hotel
- Activités : hebergement_chambres
- Patterns : aucun
- Plans : aucun
- Statuts : canceled, interesting, open
