# Trois parcours Pattern

## Clim des chambres

### signal:clim-214 — La clim de la chambre 214 souffle tiède

- Archétype : Clim d'une chambre
- Date : 2025-11-12 09:10:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:clim-214
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Hébergement et chambres
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : plan:diagnostic-clim — Diagnostic climatisation d'une chambre
- Exécution : exec:signal:signal:clim-214
- Observations :
  - En chambre 214 la clim tourne et l'air reste tiède. Le client l'a dit à la réception hier soir.
- Tâches principales :
  - Prendre en charge l'incident climatisation
  - Diagnostiquer l'unité et le thermostat
  - Corriger ou escalader au prestataire CVC
  - Tester le refroidissement en chambre
  - Informer l'Hôtel du statut chambre
  - Clôturer l'intervention

### signal:clim-426 — La clim de la chambre 426 s'est coupée

- Archétype : Clim d'une chambre
- Date : 2026-07-08 10:05:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:clim-426
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Hébergement et chambres
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : plan:diagnostic-clim — Diagnostic climatisation d'une chambre
- Exécution : exec:signal:signal:clim-426
- Observations :
  - La clim de la chambre 426 s'est arrêtée dans la nuit. Le client a appelé la réception à 6 h.
- Tâches principales :
  - Prendre en charge l'incident climatisation
  - Diagnostiquer l'unité et le thermostat
  - Corriger ou escalader au prestataire CVC
  - Tester le refroidissement en chambre
  - Informer l'Hôtel du statut chambre
  - Clôturer l'intervention

### signal:golden-clim-318 — La clim de la chambre 318 ne refroidit plus

- Archétype : Clim d'une chambre
- Date : 2026-09-21 08:12:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:golden-clim-318
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Hébergement et chambres
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : plan:diagnostic-clim — Diagnostic climatisation d'une chambre
- Exécution : exec:signal:signal:golden-clim-318
- Observations :
  - La clim de la 318 souffle mais ne refroidit plus, le client revient vers 18 h.
  - Passage étage : air tiède en chambre 318, le client l'a redit à la réception.
- Tâches principales :
  - Prendre en charge l'incident climatisation
  - Diagnostiquer l'unité et le thermostat
  - Corriger ou escalader au prestataire CVC
  - Tester le refroidissement en chambre
  - Informer l'Hôtel du statut chambre
  - Clôturer l'intervention

## Ruptures du buffet

### signal:buffet-viennoiseries — Les viennoiseries manquent au buffet dès 8 h

- Archétype : Buffet petit-déjeuner
- Date : 2026-04-15 08:10:00+02:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:buffet-viennoiseries
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : pattern:ruptures-buffet — Ruptures récurrentes au buffet du petit-déjeuner
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:buffet-viennoiseries
- Observations :
  - Au buffet, les viennoiseries sont vides dès 8 h, deuxième matin de la semaine.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:jus-orange — Il manque les jus d'orange au buffet à l'ouverture

- Archétype : Buffet petit-déjeuner
- Date : 2026-09-22 07:12:00+02:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : petit_dejeuner
- Signal : signal:jus-orange
- Statut : open
- Famille : Coordination cross-pôles
- Activité : Petit-déjeuner
- Pattern : pattern:ruptures-buffet — Ruptures récurrentes au buffet du petit-déjeuner
- Plan : aucun
- Exécution : aucun
- Observations :
  - Il manque les jus d'orange sur le buffet à l'ouverture, deuxième fois cette semaine.
  - En cuisine, plus de bidons de jus pour le buffet de 7 h.
- Tâches principales : aucune

## Audiovisuel des Ateliers

### signal:clickshare-atelier-1-historique — Le ClickShare de l'Atelier 1 ne projetait plus en mai

- Archétype : Audiovisuel Atelier ou Studio
- Date : 2026-05-12 09:30:00+02:00
- Lieu : atelier_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:clickshare-atelier-1-historique
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : plan:verification-clickshare — Vérification d'un équipement ClickShare
- Exécution : exec:signal:signal:clickshare-atelier-1-historique
- Observations :
  - En Atelier 1, le ClickShare ne projetait plus pour un brief de deux heures.
- Tâches principales :
  - Vérifier les branchements
  - Redémarrer l'équipement
  - Tester l'affichage et le son
  - Confirmer le statut de la salle
  - Consigner le résultat

### signal:clickshare-atelier-2 — Le ClickShare de l'Atelier 2 ne détecte aucun écran

- Archétype : Audiovisuel Atelier ou Studio
- Date : 2026-09-18 09:20:00+02:00
- Lieu : atelier_2
- Auteur : maintenance
- Responsable : evenements_privatisations
- Signal : signal:clickshare-atelier-2
- Statut : in_progress
- Famille : Coordination cross-pôles
- Activité : Ateliers et Studios
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : plan:verification-clickshare — Vérification d'un équipement ClickShare
- Exécution : exec:signal:signal:clickshare-atelier-2
- Observations :
  - Le ClickShare de l'Atelier 2 ne détecte aucun écran depuis ce matin.
  - Maintenance : HDMI et réseau testés, toujours pas d'image en Atelier 2.
  - L'accueil du séminaire a le même écran noir à l'ouverture de salle.
- Tâches principales :
  - Vérifier les branchements
  - Redémarrer l'équipement
  - Tester l'affichage et le son
  - Confirmer le statut de la salle
  - Consigner le résultat
