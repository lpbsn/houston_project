# Scénarios par activité Mama Nice

## Hébergement et chambres

### signal:golden-clim-318 — La clim de la chambre 318 ne refroidit plus

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
  - Je confirme à l'étage : air tiède en chambre 318, le client l'a redit à la réception.
- Tâches principales :
  - Prendre en charge l'incident climatisation
  - Diagnostiquer l'unité et le thermostat
  - Corriger ou escalader au prestataire CVC
  - Tester le refroidissement en chambre
  - Informer l'Hôtel du statut chambre
  - Clôturer l'intervention

### signal:clim-214 — La clim de la chambre 214 souffle tiède

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
  - En chambre 214 la clim tourne et l'air reste tiède, le client l'a signalé hier soir.
- Tâches principales :
  - Prendre en charge l'incident climatisation
  - Diagnostiquer l'unité et le thermostat
  - Corriger ou escalader au prestataire CVC
  - Tester le refroidissement en chambre
  - Informer l'Hôtel du statut chambre
  - Clôturer l'intervention

### signal:clim-426 — La clim de la chambre 426 s'est coupée

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
  - La clim de la chambre 426 s'est arrêtée dans la nuit, le client a appelé la réception à 6 h.
- Tâches principales :
  - Prendre en charge l'incident climatisation
  - Diagnostiquer l'unité et le thermostat
  - Corriger ou escalader au prestataire CVC
  - Tester le refroidissement en chambre
  - Informer l'Hôtel du statut chambre
  - Clôturer l'intervention

### signal:ci-clim-filtres — Les clim du 3e reviennent tièdes à chaque arrivée, le filtre n'est jamais changé

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

### signal:chambre-406 — La chambre 406 n'est pas prête, le client est au lobby

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
  - La chambre 406 n'est pas prête, le client attend au lobby avec ses bagages.
- Tâches principales : aucune

### signal:fuite-512 — Le siphon de la chambre 512 fuit encore

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
  - Le siphon de la chambre 512 fuit encore, une flaque revient sous le lavabo.
- Tâches principales :
  - Sécuriser la zone et couper l'eau si besoin
  - Localiser et réparer la fuite
  - Assécher et contrôler l'évacuation
  - Confirmer la remise en service

### signal:interesting-bruit-3e — Les départs du 3e mentionnent le bruit du couloir en chambre

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
- Observations :
  - Les départs du 3e mentionnent le bruit du couloir en chambre, sans numéro en cause.
- Tâches principales : aucune

### signal:033 — Le lit de la chambre 102 est encore défait à 15 h

- Date : 2025-09-23 19:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:033
- Statut : resolved
- Famille : Qualité de service
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le lit de la chambre 102 est encore défait à 15 h, en chambre 102, l'arrivée est dans le lobby avec ses bagages. Au chambres, la chambre allonge le service plus que la jauge prévue.
- Tâches principales : aucune

### signal:034 — La télécommande de la chambre 128 ne répond plus

- Date : 2025-09-24 06:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:034
- Statut : resolved
- Famille : Qualité de service
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La télécommande de la chambre 128 ne répond plus, en chambre 128, l'écran ne réagit plus aux touches.
- Tâches principales : aucune

### signal:035 — Les serviettes manquent dans la chambre 109

- Date : 2025-09-24 17:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:035
- Statut : resolved
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:linge — Linge manquant ou livré en retard
- Plan : plan:rupture-linge — Traitement d'une rupture de linge
- Exécution : exec:signal:signal:035
- Observations :
  - Les serviettes manquent dans la chambre 109, en chambre 109, la salle de bain n'a aucun drap de bain. Récurrence depuis septembre au chambres : le linge à cause de les sacs d'enlèvement partent sans bordereau.
- Tâches principales :
  - Constater le stock manquant
  - Réaffecter le linge disponible
  - Relancer le prestataire linge
  - Confirmer le réassort

### signal:039 — Il manque une femme de chambre sur le planning du matin

- Date : 2025-09-26 13:00:00+02:00
- Lieu : breakroom
- Auteur : hotel
- Responsable : hotel
- Signal : signal:039
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Il manque une femme de chambre sur le planning du matin, au breakroom, le planning affiche un trou sur les départs.
- Tâches principales : aucune

### signal:043 — La chambre 144 n'est pas prête pour l'arrivée de 15 h

- Date : 2025-09-28 09:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:043
- Statut : resolved
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:chambres-non-pretes — Chambres non prêtes à l'heure d'arrivée
- Plan : plan:rattrapage-chambre — Rattrapage d'une chambre non prête
- Exécution : exec:signal:signal:043
- Observations :
  - La chambre 144 n'est pas prête pour l'arrivée de 15 h, en chambre 144, le ménage n'a pas encore commencé. À chaque arrivée depuis septembre, la chambre au chambres retombe sur la passation 14 h ne liste plus les départs tardifs.
- Tâches principales :
  - Prioriser le ménage de la chambre
  - Vérifier linge et équipements
  - Informer la réception
  - Confirmer la chambre prête

### signal:044 — La serrure de la chambre 136 clignote rouge

- Date : 2025-09-28 20:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:044
- Statut : resolved
- Famille : Qualité de service
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La serrure de la chambre 136 clignote rouge, en chambre 136, la clé ne déverrouille plus du premier coup. Prestation la serrure au chambres : le standard du brief n'est pas tenu.
- Tâches principales : aucune

### signal:045 — Les draps de la chambre 140 ne sont pas arrivés

- Date : 2025-09-29 07:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:045
- Statut : resolved
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:linge — Linge manquant ou livré en retard
- Plan : plan:rupture-linge — Traitement d'une rupture de linge
- Exécution : exec:signal:signal:045
- Observations :
  - Les draps de la chambre 140 ne sont pas arrivés, en chambre 140, le lit est nu à une heure de l'arrivée. Récurrence depuis septembre au chambres : le linge à cause de le geste de clôture n'est pas tenu dans le brief.
- Tâches principales :
  - Constater le stock manquant
  - Réaffecter le linge disponible
  - Relancer le prestataire linge
  - Confirmer le réassort

### signal:049 — La formation ménage prévue au breakroom est annulée

- Date : 2025-10-01 03:00:00+02:00
- Lieu : breakroom
- Auteur : hotel
- Responsable : hotel
- Signal : signal:049
- Statut : resolved
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:chambres-non-pretes — Chambres non prêtes à l'heure d'arrivée
- Plan : plan:rattrapage-chambre — Rattrapage d'une chambre non prête
- Exécution : exec:signal:signal:049
- Observations :
  - La formation ménage prévue au breakroom est annulée, au breakroom, les inscrits attendent un formateur qui ne vient pas. On cherche à améliorer le processus : le check ménage n'est pas croisé avec l'heure d'arrivée. Vu au breakroom depuis octobre sur la formation.
- Tâches principales :
  - Prioriser le ménage de la chambre
  - Vérifier linge et équipements
  - Informer la réception
  - Confirmer la chambre prête

### signal:050 — Le numéro de la chambre 270 est décollé sur la porte

- Date : 2025-10-01 14:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:050
- Statut : resolved
- Famille : Qualité de service
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le numéro de la chambre 270 est décollé sur la porte, en chambre 270, on devine le numéro seulement de près. Prestation la plaque au chambres : le standard du brief n'est pas tenu.
- Tâches principales : aucune

### signal:053 — La salle de bain de la chambre 203 est encore humide

- Date : 2025-10-02 23:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:053
- Statut : resolved
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:chambres-non-pretes — Chambres non prêtes à l'heure d'arrivée
- Plan : plan:rattrapage-chambre — Rattrapage d'une chambre non prête
- Exécution : exec:signal:signal:053
- Observations :
  - La salle de bain de la chambre 203 est encore humide, en chambre 203, le sol de douche n'est pas sec à l'arrivée. À chaque arrivée depuis octobre, la chambre au chambres retombe sur le geste de clôture n'est pas tenu dans le brief.
- Tâches principales :
  - Prioriser le ménage de la chambre
  - Vérifier linge et équipements
  - Informer la réception
  - Confirmer la chambre prête

### signal:054 — L'ampoule du chevet est grillée en chambre 245

- Date : 2025-10-03 10:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:054
- Statut : resolved
- Famille : Qualité de service
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'ampoule du chevet est grillée en chambre 245, en chambre 245, le côté lit reste dans le noir. Au chambres, l'ampoule allonge le service plus que la jauge prévue.
- Tâches principales : aucune

### signal:055 — Le peignoir de la chambre 206 est troué

- Date : 2025-10-03 21:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:055
- Statut : resolved
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:linge — Linge manquant ou livré en retard
- Plan : plan:rupture-linge — Traitement d'une rupture de linge
- Exécution : exec:signal:signal:055
- Observations :
  - Le peignoir de la chambre 206 est troué, en chambre 206, le client a reposé le peignoir sur le lit. Récurrence depuis octobre au chambres : le linge à cause de le même écart revient faute de consigne d'étage.
- Tâches principales :
  - Constater le stock manquant
  - Réaffecter le linge disponible
  - Relancer le prestataire linge
  - Confirmer le réassort

### signal:059 — Deux arrivées de contrat ne sont pas au planning du breakroom

- Date : 2025-10-05 17:00:00+02:00
- Lieu : breakroom
- Auteur : hotel
- Responsable : hotel
- Signal : signal:059
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Deux arrivées de contrat ne sont pas au planning du breakroom, au breakroom, les nouveaux sont là sans créneau d'accueil.
- Tâches principales : aucune

### signal:063 — Des cheveux restent dans la douche de la chambre 330

- Date : 2025-10-07 13:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:063
- Statut : resolved
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:chambres-non-pretes — Chambres non prêtes à l'heure d'arrivée
- Plan : plan:rattrapage-chambre — Rattrapage d'une chambre non prête
- Exécution : exec:signal:signal:063
- Observations :
  - Des cheveux restent dans la douche de la chambre 330, en chambre 330, la douche n'a pas été reprise. À chaque arrivée depuis octobre, la chambre au chambres retombe sur le même écart revient faute de consigne d'étage.
- Tâches principales :
  - Prioriser le ménage de la chambre
  - Vérifier linge et équipements
  - Informer la réception
  - Confirmer la chambre prête

### signal:064 — La chasse d'eau de la chambre 260 coule sans s'arrêter

- Date : 2025-10-08 00:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:064
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La chasse d'eau de la chambre 260 coule sans s'arrêter, en chambre 260, on entend l'eau toute la nuit. Contrôle fait au chambres avant le service, la chasse d'eau était déjà signalé.
- Tâches principales : aucune

### signal:065 — La housse de couette de la chambre 250 est tachée

- Date : 2025-10-08 11:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:065
- Statut : resolved
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:linge — Linge manquant ou livré en retard
- Plan : plan:rupture-linge — Traitement d'une rupture de linge
- Exécution : exec:signal:signal:065
- Observations :
  - La housse de couette de la chambre 250 est tachée, en chambre 250, la tache est visible dès l'entrée. Récurrence depuis octobre au chambres : le linge à cause de l'écart blanchisserie n'est pas confronté le jour même.
- Tâches principales :
  - Constater le stock manquant
  - Réaffecter le linge disponible
  - Relancer le prestataire linge
  - Confirmer le réassort

### signal:069 — Un extra prévu au breakroom ne s'est pas présenté

- Date : 2025-10-10 07:00:00+02:00
- Lieu : breakroom
- Auteur : hotel
- Responsable : hotel
- Signal : signal:069
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un extra prévu au breakroom ne s'est pas présenté, au breakroom, le nom est sur le planning et personne n'est venu. Check-list du matin au breakroom, l'extra noté pour passage préventif.
- Tâches principales : aucune

### signal:073 — Le sol de la chambre 412 n'a pas été aspiré

- Date : 2025-10-12 03:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:073
- Statut : resolved
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:chambres-non-pretes — Chambres non prêtes à l'heure d'arrivée
- Plan : plan:rattrapage-chambre — Rattrapage d'une chambre non prête
- Exécution : exec:signal:signal:073
- Observations :
  - Le sol de la chambre 412 n'a pas été aspiré, en chambre 412, on voit encore les miettes au pied du lit. À chaque arrivée depuis octobre, la chambre au chambres retombe sur le check ménage n'est pas croisé avec l'heure d'arrivée.
- Tâches principales :
  - Prioriser le ménage de la chambre
  - Vérifier linge et équipements
  - Informer la réception
  - Confirmer la chambre prête

### signal:074 — Le sèche-cheveux de la chambre 355 ne chauffe plus

- Date : 2025-10-12 14:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:074
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le sèche-cheveux de la chambre 355 ne chauffe plus, en chambre 355, l'air sort froid. Ronde de octobre au chambres : le sèche-cheveux relevé avant qu'un client le voie.
- Tâches principales : aucune

### signal:075 — Le linge de la chambre 340 est encore humide

- Date : 2025-10-13 01:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:075
- Statut : resolved
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:linge — Linge manquant ou livré en retard
- Plan : plan:rupture-linge — Traitement d'une rupture de linge
- Exécution : exec:signal:signal:075
- Observations :
  - Le linge de la chambre 340 est encore humide, en chambre 340, les serviettes sont froides et mouillées. Récurrence depuis octobre au chambres : le linge à cause de les sacs d'enlèvement partent sans bordereau.
- Tâches principales :
  - Constater le stock manquant
  - Réaffecter le linge disponible
  - Relancer le prestataire linge
  - Confirmer le réassort

### signal:079 — La pause de l'équipe étages n'est pas calée au planning

- Date : 2025-10-14 21:00:00+02:00
- Lieu : breakroom
- Auteur : hotel
- Responsable : hotel
- Signal : signal:079
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La pause de l'équipe étages n'est pas calée au planning, au breakroom, chacun part quand il peut, le planning est vide.
- Tâches principales : aucune

### signal:080 — Un pictogramme interdit de fumer manque au palier des chambres

- Date : 2025-10-15 08:00:00+02:00
- Lieu : circulations_chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:080
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un pictogramme interdit de fumer manque au palier des chambres, au palier, l'emplacement est vide à côté de l'ascenseur. Ronde de octobre au circulations chambres : le pictogramme relevé avant qu'un client le voie.
- Tâches principales : aucune

### signal:083 — Le bureau de la chambre 615 est poussiéreux à l'arrivée

- Date : 2025-10-16 17:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:083
- Statut : resolved
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:chambres-non-pretes — Chambres non prêtes à l'heure d'arrivée
- Plan : plan:rattrapage-chambre — Rattrapage d'une chambre non prête
- Exécution : exec:signal:signal:083
- Observations :
  - Le bureau de la chambre 615 est poussiéreux à l'arrivée, en chambre 615, le client a écrit sur la poussière. À chaque arrivée depuis octobre, la chambre au chambres retombe sur la passation 14 h ne liste plus les départs tardifs.
- Tâches principales :
  - Prioriser le ménage de la chambre
  - Vérifier linge et équipements
  - Informer la réception
  - Confirmer la chambre prête

### signal:084 — La porte-fenêtre de la chambre 370 ferme mal

- Date : 2025-10-17 04:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:084
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La porte-fenêtre de la chambre 370 ferme mal, en chambre 370, le client a calé la poignée avec une chaise. Check-list du matin au chambres, la porte-fenêtre noté pour passage préventif.
- Tâches principales : aucune

### signal:085 — Il n'y a plus de drap de bain en chambre 404

- Date : 2025-10-17 15:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:085
- Statut : resolved
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:linge — Linge manquant ou livré en retard
- Plan : plan:rupture-linge — Traitement d'une rupture de linge
- Exécution : exec:signal:signal:085
- Observations :
  - Il n'y a plus de drap de bain en chambre 404, en chambre 404, seulement deux petites serviettes invité. Récurrence depuis octobre au chambres : le linge à cause de le geste de clôture n'est pas tenu dans le brief.
- Tâches principales :
  - Constater le stock manquant
  - Réaffecter le linge disponible
  - Relancer le prestataire linge
  - Confirmer le réassort

### signal:089 — Le planning du breakroom laisse un seul collègue sur les départs

- Date : 2025-10-19 11:00:00+02:00
- Lieu : breakroom
- Auteur : hotel
- Responsable : hotel
- Signal : signal:089
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le planning du breakroom laisse un seul collègue sur les départs, au breakroom, les départs de 11 h sont notés à une personne.
- Tâches principales : aucune

### signal:093 — Les poubelles de la chambre 707 n'ont pas été vidées

- Date : 2025-10-21 07:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:093
- Statut : resolved
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:chambres-non-pretes — Chambres non prêtes à l'heure d'arrivée
- Plan : plan:rattrapage-chambre — Rattrapage d'une chambre non prête
- Exécution : exec:signal:signal:093
- Observations :
  - Les poubelles de la chambre 707 n'ont pas été vidées, en chambre 707, le sac d'hier est encore dans la salle de bain. À chaque arrivée depuis octobre, la chambre au chambres retombe sur le geste de clôture n'est pas tenu dans le brief.
- Tâches principales :
  - Prioriser le ménage de la chambre
  - Vérifier linge et équipements
  - Informer la réception
  - Confirmer la chambre prête

### signal:094 — Le détecteur de la chambre 480 bippe sans raison

- Date : 2025-10-21 18:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:094
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le détecteur de la chambre 480 bippe sans raison, en chambre 480, le bip revient toutes les dix minutes. Contrôle fait au chambres avant le service, le détecteur était déjà signalé.
- Tâches principales : aucune

### signal:095 — Les taies de la chambre 510 sont parties au sale

- Date : 2025-10-22 05:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:095
- Statut : resolved
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:linge — Linge manquant ou livré en retard
- Plan : plan:rupture-linge — Traitement d'une rupture de linge
- Exécution : exec:signal:signal:095
- Observations :
  - Les taies de la chambre 510 sont parties au sale, en chambre 510, les oreillers sont sans taie. Récurrence depuis octobre au chambres : le linge à cause de le même écart revient faute de consigne d'étage.
- Tâches principales :
  - Constater le stock manquant
  - Réaffecter le linge disponible
  - Relancer le prestataire linge
  - Confirmer le réassort

### signal:099 — La feuille d'émargement du breakroom n'est pas signée depuis lundi

- Date : 2025-10-24 01:00:00+02:00
- Lieu : breakroom
- Auteur : hotel
- Responsable : hotel
- Signal : signal:099
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La feuille d'émargement du breakroom n'est pas signée depuis lundi, au breakroom, la feuille est blanche sur trois jours. Check-list du matin au breakroom, le planning noté pour passage préventif.
- Tâches principales : aucune

### signal:100 — Le plan d'évacuation du couloir des chambres est périmé

- Date : 2025-10-24 12:00:00+02:00
- Lieu : circulations_chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:100
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le plan d'évacuation du couloir des chambres est périmé, dans le couloir, le plan montre un escalier condamné. Contrôle fait au circulations chambres avant le service, le plan était déjà signalé.
- Tâches principales : aucune

### signal:102 — La chambre 118 est bruyante à cause du couloir

- Date : 2025-10-25 10:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:102
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La chambre 118 est bruyante à cause du couloir, en chambre 118, le client a mal dormi et le dit ce matin. Check-list du matin au chambres, la chambre noté pour passage préventif.
- Tâches principales : aucune

### signal:103 — Le lit de la chambre 801 n'est pas fait pour le check-in

- Date : 2025-10-25 21:00:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:103
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le lit de la chambre 801 n'est pas fait pour le check-in, en chambre 801, les draps de la nuit sont encore en place. Contrôle fait au chambres avant le service, la chambre était déjà signalé.
- Tâches principales : aucune

### signal:104 — La prise près du lit de la chambre 540 est morte

- Date : 2025-10-26 08:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:104
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La prise près du lit de la chambre 540 est morte, en chambre 540, le téléphone ne charge plus. Ronde de octobre au chambres : la prise relevé avant qu'un client le voie.
- Tâches principales : aucune

### signal:105 — Le plaid de la chambre 620 n'a pas été remis

- Date : 2025-10-26 19:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:105
- Statut : resolved
- Famille : Amélioration continue
- Activité : Hébergement et chambres
- Pattern : pattern:linge — Linge manquant ou livré en retard
- Plan : plan:rupture-linge — Traitement d'une rupture de linge
- Exécution : exec:signal:signal:105
- Observations :
  - Le plaid de la chambre 620 n'a pas été remis, en chambre 620, le fauteuil est nu. Récurrence depuis octobre au chambres : le linge à cause de l'écart blanchisserie n'est pas confronté le jour même.
- Tâches principales :
  - Constater le stock manquant
  - Réaffecter le linge disponible
  - Relancer le prestataire linge
  - Confirmer le réassort

### signal:108 — La chambre connectée vendue sur le site n'a pas de prise USB

- Date : 2025-10-28 04:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:108
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La chambre connectée vendue sur le site n'a pas de prise USB, en chambre 167, le client cherchait la prise promise sur le site. Check-list du matin au chambres, la réservation noté pour passage préventif.
- Tâches principales : aucune

### signal:109 — Une demande de congé du week-end n'est pas tranchée au planning

- Date : 2025-10-28 15:00:00+01:00
- Lieu : breakroom
- Auteur : hotel
- Responsable : hotel
- Signal : signal:109
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une demande de congé du week-end n'est pas tranchée au planning, au breakroom, le collègue ne sait pas s'il travaille samedi.
- Tâches principales : aucune

### signal:110 — La plaque de la chambre 390 est inversée avec la 391

- Date : 2025-10-29 02:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:110
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La plaque de la chambre 390 est inversée avec la 391, en chambre 390, le voisin a ouvert avec la mauvaise indication. Ronde de octobre au chambres : la plaque relevé avant qu'un client le voie.
- Tâches principales : aucune

### signal:112 — Le minibar de la chambre 305 est tiède

- Date : 2025-10-30 00:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:112
- Statut : resolved
- Famille : Qualité de service
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le minibar de la chambre 305 est tiède, en chambre 305, les boissons ne sont plus fraîches. L'écart sur le minibar se voit encore au service du chambres.
- Tâches principales : aucune

### signal:113 — La chambre 909 sent le produit et n'a pas été aérée

- Date : 2025-10-30 11:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:113
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La chambre 909 sent le produit et n'a pas été aérée, en chambre 909, la fenêtre est restée fermée après le ménage. Ronde de octobre au chambres : la chambre relevé avant qu'un client le voie.
- Tâches principales : aucune

### signal:114 — Le rideau de la chambre 660 est sorti du rail

- Date : 2025-10-30 22:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:114
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le rideau de la chambre 660 est sorti du rail, en chambre 660, le rail est visible sur un mètre. Check-list du matin au chambres, le rideau noté pour passage préventif.
- Tâches principales : aucune

### signal:115 — Le linge de lit manque sous le matelas de la chambre 730

- Date : 2025-10-31 09:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:115
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le linge de lit manque sous le matelas de la chambre 730, en chambre 730, le protège-matelas n'est pas là.
- Tâches principales : aucune

### signal:117 — Le livret de la chambre 150 a les anciens horaires de piscine

- Date : 2025-11-01 07:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:117
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le livret de la chambre 150 a les anciens horaires de piscine, en chambre 150, la piscine est indiquée fermée le matin. Check-list du matin au chambres, le livret noté pour passage préventif.
- Tâches principales : aucune

### signal:119 — Le tuteur prévu au planning est en repos le jour de l'accueil

- Date : 2025-11-02 05:00:00+01:00
- Lieu : breakroom
- Auteur : hotel
- Responsable : hotel
- Signal : signal:119
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le tuteur prévu au planning est en repos le jour de l'accueil, au breakroom, l'arrivée n'a personne pour la faire visiter.
- Tâches principales : aucune

### signal:122 — Le store de la chambre 512 reste bloqué en bas

- Date : 2025-11-03 14:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:122
- Statut : resolved
- Famille : Prévention
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le store de la chambre 512 reste bloqué en bas, en chambre 512, la pièce reste dans le noir en journée. Ronde de novembre au chambres : le store relevé avant qu'un client le voie.
- Tâches principales : aucune

### signal:123 — Un verre sale est resté sur la table de la chambre 107

- Date : 2025-11-04 01:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:123
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un verre sale est resté sur la table de la chambre 107, en chambre 107, le plateau du soir n'a pas été débarrassé. la chambre au chambres : le seuil d'alerte n'a pas déclenché le réassort.
- Tâches principales : aucune

### signal:124 — L'interrupteur de la chambre 770 est cassé

- Date : 2025-11-04 12:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:124
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'interrupteur de la chambre 770 est cassé, en chambre 770, la lumière du séjour ne s'éteint plus. Au chambres, l'interrupteur bloque encore la passation de novembre.
- Tâches principales : aucune

### signal:125 — Le linge propre manque au chariot du couloir des chambres

- Date : 2025-11-04 23:00:00+01:00
- Lieu : circulations_chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:125
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le linge propre manque au chariot du couloir des chambres, dans le couloir, le chariot ménage n'a plus de torchon propre.
- Tâches principales : aucune

### signal:128 — Le forfait romance de la chambre 160 n'a pas été préparé

- Date : 2025-11-06 08:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : hotel
- Signal : signal:128
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le forfait romance de la chambre 160 n'a pas été préparé, en chambre 160, ni pétales ni bouteille ne sont en place. Le geste prévu pour le forfait n'a pas été tenu au chambres.
- Tâches principales : aucune

### signal:129 — Les tailles de tenue manquent pour deux arrivées au breakroom

- Date : 2025-11-06 19:00:00+01:00
- Lieu : breakroom
- Auteur : hotel
- Responsable : hotel
- Signal : signal:129
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Hébergement et chambres
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les tailles de tenue manquent pour deux arrivées au breakroom, au breakroom, les nouveaux n'ont pas de veste à leur taille. la tenue au breakroom : le seuil d'alerte n'a pas déclenché le réassort.
- Tâches principales : aucune

## Réception

### signal:unassigned-lobby — Un client attend au lobby sans chambre identifiée

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
  - Un client tourne dans le lobby, sa réservation n'est pas encore identifiée.
- Tâches principales : aucune

### signal:groupe-deplace — La réservation du groupe du 20 n'a plus de prépa au lobby

- Date : 2026-09-10 11:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:groupe-deplace
- Statut : canceled
- Famille : Expérience client
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Motif d'annulation : Le client a déplacé la date, la préparation n'a plus lieu.
- Observations :
  - La réservation du groupe du 20 a été déplacée, plus de prépa à caler au lobby.
- Tâches principales : aucune

### signal:interesting-late-sunday — Des clients demandent un check-out tardif le dimanche de Super Sunday

- Date : 2026-09-15 16:10:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:interesting-late-sunday
- Statut : interesting
- Famille : Opportunité
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Plusieurs clients demandent un check-out tardif à la réception le dimanche de Super Sunday.
- Tâches principales : aucune

### signal:032 — Un client tourne dans le lobby sans trouver l'ascenseur

- Date : 2025-09-23 08:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:032
- Statut : resolved
- Famille : Qualité de service
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un client tourne dans le lobby sans trouver l'ascenseur, au lobby, sa valise bloque le passage depuis dix minutes. Prestation l'accueil au reception lobby : le standard du brief n'est pas tenu.
- Tâches principales : aucune

### signal:036 — La file au check-in du lobby dépasse dix minutes

- Date : 2025-09-25 04:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:036
- Statut : resolved
- Famille : Amélioration continue
- Activité : Réception
- Pattern : pattern:attente-checkin — Attente excessive au check-in
- Plan : plan:rattrapage-chambre — Rattrapage d'une chambre non prête
- Exécution : exec:signal:signal:036
- Observations :
  - La file au check-in du lobby dépasse dix minutes, au lobby, quatre clients attendent debout avec leurs valises. Depuis septembre, le check-in à reception lobby revient : personne n'a calé le contrôle après l'opération. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Prioriser le ménage de la chambre
  - Vérifier linge et équipements
  - Informer la réception
  - Confirmer la chambre prête

### signal:037 — L'affichage du lobby annonce encore l'happy hour d'hier

- Date : 2025-09-25 15:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:037
- Statut : resolved
- Famille : Qualité de service
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'affichage du lobby annonce encore l'happy hour d'hier, au lobby, l'écran n'a pas basculé sur le programme du jour. L'écart sur l'affichage se voit encore au service du reception lobby.
- Tâches principales : aucune

### signal:038 — Une réservation du site promet une vue que l'hôtel n'a pas

- Date : 2025-09-26 02:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:038
- Statut : resolved
- Famille : Qualité de service
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une réservation du site promet une vue que l'hôtel n'a pas, à la réception, le client montre la photo du site. Prestation la réservation au reception lobby : le standard du brief n'est pas tenu.
- Tâches principales : aucune

### signal:040 — La flèche vers les chambres dans le lobby pointe vers le bar

- Date : 2025-09-27 00:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:040
- Statut : resolved
- Famille : Qualité de service
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La flèche vers les chambres dans le lobby pointe vers le bar, au lobby, les arrivants partent du mauvais côté. L'écart sur la signalétique se voit encore au service du reception lobby.
- Tâches principales : aucune

### signal:041 — La caisse de la réception a un écart de vingt euros

- Date : 2025-09-27 11:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:041
- Statut : resolved
- Famille : Amélioration continue
- Activité : Réception
- Pattern : pattern:facturation-caisse — Anomalies de facturation ou de caisse à la réception
- Plan : plan:anomalie-cloture-caisse
- Exécution : exec:signal:signal:041
- Observations :
  - La caisse de la réception a un écart de vingt euros, à la réception, le comptage du matin ne tombe pas juste. Depuis septembre, la caisse à reception lobby revient : le geste de clôture n'est pas tenu dans le brief. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Constater la caisse sur place
  - Corriger la caisse
  - Confirmer que la caisse est rétabli

### signal:046 — Le check-in du lobby est bloqué, l'imprimante des clés rame

- Date : 2025-09-29 18:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:046
- Statut : resolved
- Famille : Amélioration continue
- Activité : Réception
- Pattern : pattern:attente-checkin — Attente excessive au check-in
- Plan : plan:rattrapage-chambre — Rattrapage d'une chambre non prête
- Exécution : exec:signal:signal:046
- Observations :
  - Le check-in du lobby est bloqué, l'imprimante des clés rame, au lobby, les cartes sortent vierges une fois sur deux. Depuis septembre, le check-in à reception lobby revient : la cause n'est pas écrite avant de relancer le prestataire. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Prioriser le ménage de la chambre
  - Vérifier linge et équipements
  - Informer la réception
  - Confirmer la chambre prête

### signal:047 — Le QR code du menu au lobby renvoie une page vide

- Date : 2025-09-30 05:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:047
- Statut : resolved
- Famille : Qualité de service
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le QR code du menu au lobby renvoie une page vide, au lobby, trois clients ont essayé sans ouvrir la carte. Prestation le menu au reception lobby : le standard du brief n'est pas tenu.
- Tâches principales : aucune

### signal:048 — Le code promo affiché au lobby n'est plus valable en caisse

- Date : 2025-09-30 16:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:048
- Statut : resolved
- Famille : Qualité de service
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le code promo affiché au lobby n'est plus valable en caisse, au lobby, le code est refusé au moment de payer. Au reception lobby, le promo allonge le service plus que la jauge prévue.
- Tâches principales : aucune

### signal:051 — Une taxe de séjour est en double sur la note à la réception

- Date : 2025-10-02 01:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:051
- Statut : resolved
- Famille : Amélioration continue
- Activité : Réception
- Pattern : pattern:facturation-caisse — Anomalies de facturation ou de caisse à la réception
- Plan : plan:anomalie-cloture-caisse
- Exécution : exec:signal:signal:051
- Observations :
  - Une taxe de séjour est en double sur la note à la réception, à la réception, le client compare avec son confirmation. Depuis octobre, la note à reception lobby revient : le même écart revient faute de consigne d'étage. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Constater la note sur place
  - Corriger la note
  - Confirmer que la note est rétabli

### signal:056 — Trois arrivées attendent debout dans le lobby

- Date : 2025-10-04 08:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:056
- Statut : resolved
- Famille : Amélioration continue
- Activité : Réception
- Pattern : pattern:attente-checkin — Attente excessive au check-in
- Plan : plan:rattrapage-chambre — Rattrapage d'une chambre non prête
- Exécution : exec:signal:signal:056
- Observations :
  - Trois arrivées attendent debout dans le lobby, au lobby, personne n'a encore été appelé au comptoir. Depuis octobre, le check-in à reception lobby revient : personne n'a calé le contrôle après l'opération. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Prioriser le ménage de la chambre
  - Vérifier linge et équipements
  - Informer la réception
  - Confirmer la chambre prête

### signal:057 — Les horaires de petit-déjeuner au lobby sont ceux d'avant

- Date : 2025-10-04 19:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:057
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les horaires de petit-déjeuner au lobby sont ceux d'avant, au lobby, le chevalet indique encore 6 h 30. Check-list du matin au reception lobby, l'affichage noté pour passage préventif.
- Tâches principales : aucune

### signal:058 — Un site a vendu un early check-in que la réception ne tient pas

- Date : 2025-10-05 06:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:058
- Statut : resolved
- Famille : Amélioration continue
- Activité : Réception
- Pattern : pattern:attente-checkin — Attente excessive au check-in
- Plan : plan:rattrapage-chambre — Rattrapage d'une chambre non prête
- Exécution : exec:signal:signal:058
- Observations :
  - Un site a vendu un early check-in que la réception ne tient pas, à la réception, l'arrivée de 9 h n'a pas de chambre libre. À chaque arrivée depuis octobre, la réservation au reception lobby retombe sur la cause n'est pas écrite avant de relancer le prestataire.
- Tâches principales :
  - Prioriser le ménage de la chambre
  - Vérifier linge et équipements
  - Informer la réception
  - Confirmer la chambre prête

### signal:060 — Le panneau piscine du lobby annonce une fermeture qui n'a pas lieu

- Date : 2025-10-06 04:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:060
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le panneau piscine du lobby annonce une fermeture qui n'a pas lieu, au lobby, des clients renoncent à descendre au bassin. Check-list du matin au reception lobby, le panneau noté pour passage préventif.
- Tâches principales : aucune

### signal:061 — Le paiement sans contact échoue à la caisse du lobby

- Date : 2025-10-06 15:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:061
- Statut : resolved
- Famille : Amélioration continue
- Activité : Réception
- Pattern : pattern:facturation-caisse — Anomalies de facturation ou de caisse à la réception
- Plan : plan:anomalie-cloture-caisse
- Exécution : exec:signal:signal:061
- Observations :
  - Le paiement sans contact échoue à la caisse du lobby, au lobby, trois cartes ont été refusées à la suite. Depuis octobre, le paiement à reception lobby revient : le geste de clôture n'est pas tenu dans le brief. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Constater le paiement sur place
  - Corriger le paiement
  - Confirmer que le paiement est rétabli

### signal:066 — Un client attend son check-in depuis vingt minutes au lobby

- Date : 2025-10-08 22:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:066
- Statut : resolved
- Famille : Amélioration continue
- Activité : Réception
- Pattern : pattern:attente-checkin — Attente excessive au check-in
- Plan : plan:rattrapage-chambre — Rattrapage d'une chambre non prête
- Exécution : exec:signal:signal:066
- Observations :
  - Un client attend son check-in depuis vingt minutes au lobby, au lobby, il a déjà demandé deux fois où en est sa chambre. Depuis octobre, le check-in à reception lobby revient : la cause n'est pas écrite avant de relancer le prestataire. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Prioriser le ménage de la chambre
  - Vérifier linge et équipements
  - Informer la réception
  - Confirmer la chambre prête

### signal:067 — Une affiche événement est restée au lobby après la date

- Date : 2025-10-09 09:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:067
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une affiche événement est restée au lobby après la date, au lobby, la date affichée est celle de la semaine passée. Contrôle fait au reception lobby avant le service, l'affiche était déjà signalé.
- Tâches principales : aucune

### signal:068 — Le forfait petit-déjeuner vendu en ligne n'est pas sur le dossier

- Date : 2025-10-09 20:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:068
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le forfait petit-déjeuner vendu en ligne n'est pas sur le dossier, à la réception, le client a le mail mais pas la prestation. Ronde de octobre au reception lobby : le forfait relevé avant qu'un client le voie.
- Tâches principales : aucune

### signal:070 — L'étiquette de l'ascenseur au lobby ne mentionne plus le rooftop

- Date : 2025-10-10 18:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:070
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'étiquette de l'ascenseur au lobby ne mentionne plus le rooftop, au lobby, on demande à la réception comment monter. Contrôle fait au reception lobby avant le service, la signalétique était déjà signalé.
- Tâches principales : aucune

### signal:071 — Un minibar est facturé deux fois à la réception

- Date : 2025-10-11 05:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:071
- Statut : resolved
- Famille : Amélioration continue
- Activité : Réception
- Pattern : pattern:facturation-caisse — Anomalies de facturation ou de caisse à la réception
- Plan : plan:anomalie-cloture-caisse
- Exécution : exec:signal:signal:071
- Observations :
  - Un minibar est facturé deux fois à la réception, à la réception, la ligne apparaît sur deux nuits identiques. Depuis octobre, la note à reception lobby revient : le même écart revient faute de consigne d'étage. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Constater la note sur place
  - Corriger la note
  - Confirmer que la note est rétabli

### signal:076 — La réception n'a plus de clés encodées pour le groupe

- Date : 2025-10-13 12:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:076
- Statut : canceled
- Famille : Amélioration continue
- Activité : Réception
- Pattern : pattern:attente-checkin — Attente excessive au check-in
- Plan : aucun
- Exécution : aucun
- Motif d'annulation : Le client a déplacé la date, la préparation n'a plus lieu. Sujet : La réception n'a plus de clés encodées pour le groupe.
- Observations :
  - La réception n'a plus de clés encodées pour le groupe, à la réception, le groupe de vingt attend dans le lobby. Depuis octobre, le check-in à reception lobby revient : personne n'a calé le contrôle après l'opération. C'est une faiblesse de processus à améliorer.
- Tâches principales : aucune

### signal:077 — Le message d'accueil au lobby cite le mauvais prénom

- Date : 2025-10-13 23:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:077
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le message d'accueil au lobby cite le mauvais prénom, au lobby, la carte porte le prénom d'un autre client. Ronde de octobre au reception lobby : l'accueil relevé avant qu'un client le voie.
- Tâches principales : aucune

### signal:078 — Une offre du site promet un spa que la réception ne peut pas honorer

- Date : 2025-10-14 10:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:078
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une offre du site promet un spa que la réception ne peut pas honorer, à la réception, le client demande le soin vendu sur le site. Check-list du matin au reception lobby, l'offre noté pour passage préventif.
- Tâches principales : aucune

### signal:081 — Le fond de caisse du matin ne correspond pas au relevé

- Date : 2025-10-15 19:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:081
- Statut : resolved
- Famille : Amélioration continue
- Activité : Réception
- Pattern : pattern:facturation-caisse — Anomalies de facturation ou de caisse à la réception
- Plan : plan:anomalie-cloture-caisse
- Exécution : exec:signal:signal:081
- Observations :
  - Le fond de caisse du matin ne correspond pas au relevé, à la réception, il manque le rouleau de pièces habituel. Depuis octobre, la caisse à reception lobby revient : le geste de clôture n'est pas tenu dans le brief. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Constater la caisse sur place
  - Corriger la caisse
  - Confirmer que la caisse est rétabli

### signal:086 — Le lobby est saturé, un car arrive en même temps

- Date : 2025-10-18 02:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:086
- Statut : resolved
- Famille : Amélioration continue
- Activité : Réception
- Pattern : pattern:attente-checkin — Attente excessive au check-in
- Plan : plan:rattrapage-chambre — Rattrapage d'une chambre non prête
- Exécution : exec:signal:signal:086
- Observations :
  - Le lobby est saturé, un car arrive en même temps, au lobby, les bagages du car bloquent l'accès au comptoir. Depuis octobre, le check-in à reception lobby revient : la cause n'est pas écrite avant de relancer le prestataire. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Prioriser le ménage de la chambre
  - Vérifier linge et équipements
  - Informer la réception
  - Confirmer la chambre prête

### signal:087 — Le panneau wifi du lobby donne un mot de passe périmé

- Date : 2025-10-18 13:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:087
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le panneau wifi du lobby donne un mot de passe périmé, au lobby, le code affiché ne connecte plus les téléphones. Check-list du matin au reception lobby, le wifi noté pour passage préventif.
- Tâches principales : aucune

### signal:088 — Le tarif du jour affiché au lobby ne correspond pas au PMS

- Date : 2025-10-19 00:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:088
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le tarif du jour affiché au lobby ne correspond pas au PMS, au lobby, l'ardoise est en dessous du prix encaissé. Contrôle fait au reception lobby avant le service, le tarif était déjà signalé.
- Tâches principales : aucune

### signal:090 — La signalétique du parking n'est pas visible depuis le lobby

- Date : 2025-10-19 22:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:090
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La signalétique du parking n'est pas visible depuis le lobby, au lobby, les clients avec voiture demandent la sortie. Check-list du matin au reception lobby, la signalétique noté pour passage préventif.
- Tâches principales : aucune

### signal:091 — Une empreinte bancaire n'a pas été libérée à la réception

- Date : 2025-10-20 09:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:091
- Statut : resolved
- Famille : Amélioration continue
- Activité : Réception
- Pattern : pattern:facturation-caisse — Anomalies de facturation ou de caisse à la réception
- Plan : plan:anomalie-cloture-caisse
- Exécution : exec:signal:signal:091
- Observations :
  - Une empreinte bancaire n'a pas été libérée à la réception, à la réception, le client parti hier voit encore le blocage. Depuis octobre, la caisse à reception lobby revient : le même écart revient faute de consigne d'étage. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Constater la caisse sur place
  - Corriger la caisse
  - Confirmer que la caisse est rétabli

### signal:096 — Le check-out du lobby s'allonge, la file touche la porte

- Date : 2025-10-22 16:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:096
- Statut : resolved
- Famille : Amélioration continue
- Activité : Réception
- Pattern : pattern:attente-checkin — Attente excessive au check-in
- Plan : plan:rattrapage-chambre — Rattrapage d'une chambre non prête
- Exécution : exec:signal:signal:096
- Observations :
  - Le check-out du lobby s'allonge, la file touche la porte, au lobby, les départs et les arrivées se mélangent. Depuis octobre, le check-out à reception lobby revient : personne n'a calé le contrôle après l'opération. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Prioriser le ménage de la chambre
  - Vérifier linge et équipements
  - Informer la réception
  - Confirmer la chambre prête

### signal:097 — La signalétique des ascenseurs au lobby est seulement en anglais

- Date : 2025-10-23 03:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:097
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La signalétique des ascenseurs au lobby est seulement en anglais, au lobby, les clients francophones demandent les étages. Contrôle fait au reception lobby avant le service, la signalétique était déjà signalé.
- Tâches principales : aucune

### signal:098 — Une réservation confirme une suite que l'hôtel n'a pas

- Date : 2025-10-23 14:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:098
- Statut : canceled
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Motif d'annulation : Le client a déplacé la date, la préparation n'a plus lieu. Sujet : Une réservation confirme une suite que l'hôtel n'a pas.
- Observations :
  - Une réservation confirme une suite que l'hôtel n'a pas, à la réception, le voucher parle d'une suite junior. Ronde de octobre au reception lobby : la réservation relevé avant qu'un client le voie.
- Tâches principales : aucune

### signal:101 — Un client conteste le petit-déjeuner sur sa note au lobby

- Date : 2025-10-24 23:00:00+02:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:101
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un client conteste le petit-déjeuner sur sa note au lobby, au lobby, il dit ne pas être descendu au buffet. Ronde de octobre au reception lobby : la note relevé avant qu'un client le voie.
- Tâches principales : aucune

### signal:106 — Une chambre n'est pas libre et le suivant attend au lobby

- Date : 2025-10-27 06:00:00+01:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:106
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une chambre n'est pas libre et le suivant attend au lobby, au lobby, le client suivant est assis depuis un quart d'heure. Contrôle fait au reception lobby avant le service, le check-in était déjà signalé.
- Tâches principales : aucune

### signal:107 — Un stop-trottoir du lobby parle d'une offre déjà finie

- Date : 2025-10-27 17:00:00+01:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:107
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un stop-trottoir du lobby parle d'une offre déjà finie, au lobby, l'offre affichée s'est arrêtée dimanche. Ronde de octobre au reception lobby : l'offre relevé avant qu'un client le voie.
- Tâches principales : aucune

### signal:111 — La facture du groupe n'est pas partie avant le départ

- Date : 2025-10-29 13:00:00+01:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:111
- Statut : canceled
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Motif d'annulation : Le client a déplacé la date, la préparation n'a plus lieu. Sujet : La facture du groupe n'est pas partie avant le départ.
- Observations :
  - La facture du groupe n'est pas partie avant le départ, à la réception, le responsable du groupe attend le document. Check-list du matin au reception lobby, la facture noté pour passage préventif.
- Tâches principales : aucune

### signal:116 — Le client du lobby n'a pas reçu son e-mail de pré-check-in

- Date : 2025-10-31 20:00:00+01:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:116
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le client du lobby n'a pas reçu son e-mail de pré-check-in, au lobby, il n'a pas le lien pour préparer son arrivée. Ronde de octobre au reception lobby : le check-in relevé avant qu'un client le voie.
- Tâches principales : aucune

### signal:118 — Un surclassement promis par téléphone n'est pas sur la réservation

- Date : 2025-11-01 18:00:00+01:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:118
- Statut : canceled
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Motif d'annulation : Le client a déplacé la date, la préparation n'a plus lieu. Sujet : Un surclassement promis par téléphone n'est pas sur la réservation.
- Observations :
  - Un surclassement promis par téléphone n'est pas sur la réservation, à la réception, rien dans le dossier ne parle de la chambre haute. Contrôle fait au reception lobby avant le service, la réservation était déjà signalé.
- Tâches principales : aucune

### signal:120 — Le bandeau du lobby n'indique pas le check-out à 11 h

- Date : 2025-11-02 16:00:00+01:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:120
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le bandeau du lobby n'indique pas le check-out à 11 h, à la réception, les départs demandent l'heure limite. Check-list du matin au reception lobby, le bandeau noté pour passage préventif.
- Tâches principales : aucune

### signal:121 — Un pourboire a été encaissé sur la mauvaise note

- Date : 2025-11-03 03:00:00+01:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:121
- Statut : resolved
- Famille : Prévention
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un pourboire a été encaissé sur la mauvaise note, à la réception, la ligne est sur le folio d'à côté. Contrôle fait au reception lobby avant le service, la caisse était déjà signalé.
- Tâches principales : aucune

### signal:126 — La réception cherche un lit bébé promis au check-in

- Date : 2025-11-05 10:00:00+01:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:126
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La réception cherche un lit bébé promis au check-in, à la réception, la famille est déjà au comptoir du lobby. le check-in au reception lobby : le seuil d'alerte n'a pas déclenché le réassort.
- Tâches principales : aucune

### signal:127 — L'écran du lobby affiche le programme d'un autre hôtel

- Date : 2025-11-05 21:00:00+01:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:127
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'écran du lobby affiche le programme d'un autre hôtel, au lobby, on voit le nom d'une autre maison du groupe. Au reception lobby, l'écran bloque encore la passation de novembre.
- Tâches principales : aucune

### signal:130 — Une flèche au sol du lobby est usée et ne se lit plus

- Date : 2025-11-07 06:00:00+01:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:130
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une flèche au sol du lobby est usée et ne se lit plus, au lobby, le marquage vers les ascenseurs a disparu. Au reception lobby, la flèche bloque encore la passation de novembre.
- Tâches principales : aucune

### signal:131 — Le ticket de caisse du lobby est illisible

- Date : 2025-11-07 17:00:00+01:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : hotel
- Signal : signal:131
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Réception
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le ticket de caisse du lobby est illisible, au lobby, le rouleau est trop clair pour être relu. Le geste prévu pour la caisse n'a pas été tenu au reception lobby.
- Tâches principales : aucune

## Petit-déjeuner

### signal:jus-orange — Il manque les jus d'orange au buffet à l'ouverture

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
  - Il manque encore les jus d'orange sur le buffet, deuxième fois cette semaine à l'ouverture.
  - En cuisine on n'a plus de bidons de jus pour le buffet de 7 h.
- Tâches principales : aucune

### signal:interesting-sans-gluten — Des clients cherchent une option sans gluten plus visible sur le buffet

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
- Observations :
  - Des clients cherchent une option sans gluten plus visible sur le buffet.
- Tâches principales : aucune

### signal:213 — Un client du buffet trouve le café froid à 8 h

- Date : 2025-12-15 07:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:213
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:proprete-buffet — Écarts de propreté sur le buffet et sa zone
- Plan : plan:remise-conformite-buffet — Remise en conformité du buffet
- Exécution : exec:signal:signal:213
- Observations :
  - Un client du buffet trouve le café froid à 8 h, au buffet, la verseuse est tiède depuis un moment. À chaque arrivée depuis décembre, le café au restaurant rdc retombe sur le geste de clôture n'est pas tenu dans le brief.
- Tâches principales :
  - Inspecter propreté et mise en place
  - Corriger les écarts visibles
  - Valider la zone client

### signal:214 — Le plan de travail du buffet est collant après le passage des enfants

- Date : 2025-12-15 18:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:214
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:proprete-buffet — Écarts de propreté sur le buffet et sa zone
- Plan : plan:remise-conformite-buffet — Remise en conformité du buffet
- Exécution : exec:signal:signal:214
- Observations :
  - Le plan de travail du buffet est collant après le passage des enfants, au buffet, le plan colle sous les couverts. On cherche à améliorer le processus : la cause n'est pas écrite avant de relancer le prestataire. Vu au restaurant rdc depuis décembre sur le buffet.
- Tâches principales :
  - Inspecter propreté et mise en place
  - Corriger les écarts visibles
  - Valider la zone client

### signal:215 — Les jus ne sont pas dressés au buffet à l'ouverture

- Date : 2025-12-16 05:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:215
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:ruptures-buffet — Ruptures récurrentes au buffet du petit-déjeuner
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:215
- Observations :
  - Les jus ne sont pas dressés au buffet à l'ouverture, au buffet, les carafes sont encore en cuisine. Récurrence depuis décembre au restaurant rdc : le buffet à cause de le chariot de secours reste en plonge.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:216 — Il manque un équipier au buffet pour le rush de 8 h 30

- Date : 2025-12-16 16:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:216
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:proprete-buffet — Écarts de propreté sur le buffet et sa zone
- Plan : plan:remise-conformite-buffet — Remise en conformité du buffet
- Exécution : exec:signal:signal:216
- Observations :
  - Il manque un équipier au buffet pour le rush de 8 h 30, au buffet, une seule personne tient le réassort. Depuis décembre, le buffet à restaurant rdc revient : personne n'a calé le contrôle après l'opération. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Inspecter propreté et mise en place
  - Corriger les écarts visibles
  - Valider la zone client

### signal:217 — La machine à café du buffet affiche une erreur et ne coule plus

- Date : 2025-12-17 03:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:217
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:equipements-cafe — Pannes des équipements café et buffet
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:217
- Observations :
  - La machine à café du buffet affiche une erreur et ne coule plus, au buffet, l'écran reste bloqué sur le code erreur. la machine à café au restaurant rdc : cause commune, le geste de clôture n'est pas tenu dans le brief. La récurrence date de décembre.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:218 — Les viennoiseries du buffet sont finies à 8 h 45

- Date : 2025-12-17 14:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:218
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:ruptures-buffet — Ruptures récurrentes au buffet du petit-déjeuner
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:218
- Observations :
  - Les viennoiseries du buffet sont finies à 8 h 45, au buffet, la corbeille est vide et le four est encore froid. À chaque arrivée depuis décembre, le buffet au restaurant rdc retombe sur la cause n'est pas écrite avant de relancer le prestataire.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:219 — Le lait du buffet est fini et le carton de réserve est vide

- Date : 2025-12-18 01:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:219
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:ruptures-buffet — Ruptures récurrentes au buffet du petit-déjeuner
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:219
- Observations :
  - Le lait du buffet est fini et le carton de réserve est vide, au buffet, plus rien pour le café ni les céréales. On cherche à améliorer le processus : le même écart revient faute de consigne d'étage. Vu au restaurant rdc depuis décembre sur le lait.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:220 — L'offre petit-déjeuner enfant vendue en ligne n'est pas au buffet

- Date : 2025-12-18 12:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:220
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:proprete-buffet — Écarts de propreté sur le buffet et sa zone
- Plan : plan:remise-conformite-buffet — Remise en conformité du buffet
- Exécution : exec:signal:signal:220
- Observations :
  - L'offre petit-déjeuner enfant vendue en ligne n'est pas au buffet, au buffet, le parent cherche le set annoncé. Récurrence depuis décembre au restaurant rdc : l'offre à cause de personne n'a calé le contrôle après l'opération.
- Tâches principales :
  - Inspecter propreté et mise en place
  - Corriger les écarts visibles
  - Valider la zone client

### signal:221 — La file du buffet bloque l'accès aux viennoiseries

- Date : 2025-12-18 23:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:221
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:ruptures-buffet — Ruptures récurrentes au buffet du petit-déjeuner
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:221
- Observations :
  - La file du buffet bloque l'accès aux viennoiseries, au buffet, on n'atteint plus le pain sans jouer des coudes. Depuis décembre, le buffet à restaurant rdc revient : le réassort n'est pas calé avant 7 h 30. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:222 — Des miettes couvrent le tapis devant le buffet

- Date : 2025-12-19 10:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:222
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:proprete-buffet — Écarts de propreté sur le buffet et sa zone
- Plan : plan:remise-conformite-buffet — Remise en conformité du buffet
- Exécution : exec:signal:signal:222
- Observations :
  - Des miettes couvrent le tapis devant le buffet, au buffet, le tapis n'a pas été passé depuis l'ouverture. le buffet au restaurant rdc : cause commune, la cause n'est pas écrite avant de relancer le prestataire. La récurrence date de décembre.
- Tâches principales :
  - Inspecter propreté et mise en place
  - Corriger les écarts visibles
  - Valider la zone client

### signal:223 — Le pain n'est pas tranché au buffet pour le premier client

- Date : 2025-12-19 21:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:223
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:ruptures-buffet — Ruptures récurrentes au buffet du petit-déjeuner
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:223
- Observations :
  - Le pain n'est pas tranché au buffet pour le premier client, au buffet, la corbeille est vide à 7 h 05. À chaque arrivée depuis décembre, le buffet au restaurant rdc retombe sur la substitution n'est pas prévue dans le brief.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:224 — Le planning du petit-déjeuner n'a personne à la plonge

- Date : 2025-12-20 08:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : communication
- Responsable : petit_dejeuner
- Signal : signal:224
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le planning du petit-déjeuner n'a personne à la plonge, au buffet, les bacs s'empilent sans personne pour les prendre. le planning au restaurant rdc demande encore un arbitrage entre les deux pôles.
- Tâches principales : aucune

### signal:225 — Le toaster du buffet reste froid

- Date : 2025-12-20 19:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:225
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:equipements-cafe — Pannes des équipements café et buffet
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:225
- Observations :
  - Le toaster du buffet reste froid, au buffet, le pain ressort blanc. Récurrence depuis décembre au restaurant rdc : le toaster à cause de le geste de clôture n'est pas tenu dans le brief.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:226 — Il n'y a plus de jus d'orange au buffet

- Date : 2025-12-21 06:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:226
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:ruptures-buffet — Ruptures récurrentes au buffet du petit-déjeuner
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:226
- Observations :
  - Il n'y a plus de jus d'orange au buffet, au buffet, la carafe est vide depuis le milieu du service. Depuis décembre, le jus à restaurant rdc revient : la commande fournisseur part trop tard le mercredi. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:227 — Il manque le beurre en portion pour le buffet

- Date : 2026-09-17 20:00:00+02:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:227
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:ruptures-buffet — Ruptures récurrentes au buffet du petit-déjeuner
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:227
- Observations :
  - Il manque le beurre en portion pour le buffet, au buffet, le seau à glace est vide. le beurre au restaurant rdc : cause commune, le geste de clôture n'est pas tenu dans le brief. La récurrence date de septembre.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:228 — Un bon petit-déjeuner est refusé à la caisse du buffet

- Date : 2025-12-22 04:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:228
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:proprete-buffet — Écarts de propreté sur le buffet et sa zone
- Plan : plan:remise-conformite-buffet — Remise en conformité du buffet
- Exécution : exec:signal:signal:228
- Observations :
  - Un bon petit-déjeuner est refusé à la caisse du buffet, au buffet, le client a le coupon et on ne sait pas le passer. À chaque arrivée depuis décembre, le bon au restaurant rdc retombe sur personne n'a calé le contrôle après l'opération.
- Tâches principales :
  - Inspecter propreté et mise en place
  - Corriger les écarts visibles
  - Valider la zone client

### signal:229 — Une famille n'a pas de chaise haute près du buffet

- Date : 2025-12-22 15:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:229
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une famille n'a pas de chaise haute près du buffet, au buffet, l'enfant est sur les genoux au milieu du passage.
- Tâches principales : aucune

### signal:230 — Le bac des couverts du buffet a une cuillère tombée au sol

- Date : 2025-12-23 02:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:230
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le bac des couverts du buffet a une cuillère tombée au sol, au buffet, personne ne l'a ramassée.
- Tâches principales : aucune

### signal:231 — Les étiquettes allergènes manquent sur le buffet

- Date : 2025-12-23 13:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:231
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les étiquettes allergènes manquent sur le buffet, au buffet, les plats chauds n'ont pas leur carte.
- Tâches principales : aucune

### signal:232 — Un extra du buffet ne s'est pas présenté

- Date : 2025-12-24 00:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:232
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un extra du buffet ne s'est pas présenté, au buffet, son poste œufs est vide.
- Tâches principales : aucune

### signal:233 — La presse à jus du buffet est bloquée

- Date : 2025-12-24 11:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:233
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:equipements-cafe — Pannes des équipements café et buffet
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:233
- Observations :
  - La presse à jus du buffet est bloquée, au buffet, le bras ne redescend plus. À chaque arrivée depuis décembre, la presse au restaurant rdc retombe sur le geste de clôture n'est pas tenu dans le brief.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:234 — Le yaourt nature du buffet est en rupture

- Date : 2025-12-24 22:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:234
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:ruptures-buffet — Ruptures récurrentes au buffet du petit-déjeuner
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:234
- Observations :
  - Le yaourt nature du buffet est en rupture, au buffet, le saladier est raclé. On cherche à améliorer le processus : le comptage de la veille n'est pas transmis à la cuisine. Vu au restaurant rdc depuis décembre sur le buffet.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:235 — Les dosettes de thé du buffet sont épuisées

- Date : 2025-12-25 09:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:235
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:ruptures-buffet — Ruptures récurrentes au buffet du petit-déjeuner
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:235
- Observations :
  - Les dosettes de thé du buffet sont épuisées, au buffet, il reste seulement les sachets ouverts. Récurrence depuis décembre au restaurant rdc : le thé à cause de le chariot de secours reste en plonge.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:236 — Le tarif buffet affiché à l'entrée n'est pas celui encaissé

- Date : 2025-12-25 20:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:236
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le tarif buffet affiché à l'entrée n'est pas celui encaissé, au buffet, l'ardoise et la caisse divergent de deux euros.
- Tâches principales : aucune

### signal:237 — Le buffet est bruyant et une table demande à être déplacée

- Date : 2025-12-26 07:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:237
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le buffet est bruyant et une table demande à être déplacée, au buffet, la table est collée au poste à œufs.
- Tâches principales : aucune

### signal:238 — La vitrine du buffet a des traces et masque les fruits

- Date : 2025-12-26 18:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:238
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La vitrine du buffet a des traces et masque les fruits, au buffet, on devine mal ce qu'il reste.
- Tâches principales : aucune

### signal:239 — La machine à café du buffet n'est pas amorcée

- Date : 2025-12-27 05:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:239
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:equipements-cafe — Pannes des équipements café et buffet
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:239
- Observations :
  - La machine à café du buffet n'est pas amorcée, au buffet, le premier café coule clair. On cherche à améliorer le processus : le même écart revient faute de consigne d'étage. Vu au restaurant rdc depuis décembre sur la machine.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:240 — La formation hygiène du buffet est reportée le jour du contrôle

- Date : 2025-12-27 16:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:240
- Statut : resolved
- Famille : Prévention
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La formation hygiène du buffet est reportée le jour du contrôle, au buffet, l'équipe n'a pas eu le rappel prévu.
- Tâches principales : aucune

### signal:241 — Le chauffe-assiettes du buffet a disjoncté

- Date : 2025-12-28 03:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:241
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:equipements-cafe — Pannes des équipements café et buffet
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:241
- Observations :
  - Le chauffe-assiettes du buffet a disjoncté, au buffet, les assiettes sont froides au toucher. Depuis décembre, le chauffe-assiettes à restaurant rdc revient : le geste de clôture n'est pas tenu dans le brief. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:242 — Les œufs du buffet ne sont pas réassortis

- Date : 2026-09-16 19:00:00+02:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:242
- Statut : resolved
- Famille : Amélioration continue
- Activité : Petit-déjeuner
- Pattern : pattern:ruptures-buffet — Ruptures récurrentes au buffet du petit-déjeuner
- Plan : plan:reassort-buffet-pdj — Réassort critique du buffet petit-déjeuner
- Exécution : exec:signal:signal:242
- Observations :
  - Les œufs du buffet ne sont pas réassortis, au buffet, le plat est vide alors que la salle est pleine. le buffet au restaurant rdc : cause commune, l'économat n'ouvre le stock qu'après la première rupture. La récurrence date de septembre.
- Tâches principales :
  - Constater la rupture au buffet
  - Vérifier le stock économat
  - Définir une substitution si nécessaire
  - Réassortir le buffet
  - Confirmer la remise en service

### signal:243 — La confiture d'orange du buffet n'a plus de recharge

- Date : 2025-12-29 01:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:243
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : pattern:ruptures-buffet — Ruptures récurrentes au buffet du petit-déjeuner
- Plan : aucun
- Exécution : aucun
- Observations :
  - La confiture d'orange du buffet n'a plus de recharge, au buffet, les coupelles sont vides.
- Tâches principales : aucune

### signal:244 — Une formule continentale vendue sur le site n'est pas identifiable au buffet

- Date : 2025-12-29 12:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:244
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une formule continentale vendue sur le site n'est pas identifiable au buffet, au buffet, on ne sait pas ce qui est inclus.
- Tâches principales : aucune

### signal:245 — Les œufs du buffet sont trop cuits dès la première tournée

- Date : 2025-12-29 23:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:245
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les œufs du buffet sont trop cuits dès la première tournée, au buffet, les blancs sont déjà secs à 7 h 40.
- Tâches principales : aucune

### signal:246 — Le sol sous le buffet à pain est gras

- Date : 2025-12-30 10:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:246
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le sol sous le buffet à pain est gras, au buffet, une flaque de beurre n'est pas essuyée.
- Tâches principales : aucune

### signal:247 — Les assiettes chaudes ne sont pas sorties pour le buffet

- Date : 2025-12-30 21:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:247
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les assiettes chaudes ne sont pas sorties pour le buffet, au buffet, on sert les œufs dans des assiettes froides.
- Tâches principales : aucune

### signal:248 — L'équipe du buffet enchaîne sans pause jusqu'à 11 h

- Date : 2025-12-31 08:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:248
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'équipe du buffet enchaîne sans pause jusqu'à 11 h, au buffet, personne n'a quitté le poste depuis l'ouverture.
- Tâches principales : aucune

### signal:249 — Le bac réfrigéré du buffet sonne, la température monte

- Date : 2025-12-31 19:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : maintenance
- Responsable : petit_dejeuner
- Signal : signal:249
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Petit-déjeuner
- Pattern : pattern:equipements-cafe — Pannes des équipements café et buffet
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le bac réfrigéré du buffet sonne, la température monte, au buffet, l'alarme du meuble froid ne s'arrête pas. Chacun a une partie de le bac au restaurant rdc, personne n'a clôturé.
- Tâches principales : aucune

### signal:250 — Le pain frais du buffet n'est pas revenu de la cuisine

- Date : 2026-01-01 06:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:250
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le pain frais du buffet n'est pas revenu de la cuisine, au buffet, il ne reste que les morceaux du premier envoi.
- Tâches principales : aucune

### signal:251 — Les capsules de café du buffet sont au dernier sachet

- Date : 2026-01-01 17:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:251
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les capsules de café du buffet sont au dernier sachet, au buffet, on compte les capsules qui restent.
- Tâches principales : aucune

### signal:252 — Le room service petit-déjeuner promis n'est pas ouvert

- Date : 2026-01-02 04:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : communication
- Responsable : petit_dejeuner
- Signal : signal:252
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le room service petit-déjeuner promis n'est pas ouvert, au buffet, un client de chambre demande un plateau qu'on ne fait pas. Chacun a une partie de le petit-déjeuner au restaurant rdc, personne n'a clôturé.
- Tâches principales : aucune

### signal:253 — Un client du buffet n'a pas d'alternative sans gluten

- Date : 2026-01-02 15:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:253
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un client du buffet n'a pas d'alternative sans gluten, au buffet, le pain habituel est le seul proposé.
- Tâches principales : aucune

### signal:254 — Les pinces du buffet traînent dans les plats

- Date : 2026-01-03 02:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:254
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les pinces du buffet traînent dans les plats, au buffet, une pince est tombée dans le yaourt.
- Tâches principales : aucune

### signal:255 — Le buffet sucré est prêt, le salé est encore en cuisine

- Date : 2026-01-03 13:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:255
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le buffet sucré est prêt, le salé est encore en cuisine, au buffet, le poste œufs est vide à l'ouverture.
- Tâches principales : aucune

### signal:256 — Le tuteur du nouvel équipier buffet est affecté en salle

- Date : 2026-01-04 00:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:256
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le tuteur du nouvel équipier buffet est affecté en salle, au buffet, le nouvel équipier est seul sur les jus.
- Tâches principales : aucune

### signal:257 — Le percolateur du buffet fuit sous le comptoir

- Date : 2026-01-04 11:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : maintenance
- Responsable : petit_dejeuner
- Signal : signal:257
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le percolateur du buffet fuit sous le comptoir, au buffet, une flaque grandit sous la machine. le percolateur au restaurant rdc demande encore un arbitrage entre les deux pôles.
- Tâches principales : aucune

### signal:258 — Les fruits coupés du buffet sont vides depuis vingt minutes

- Date : 2026-01-04 22:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:258
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les fruits coupés du buffet sont vides depuis vingt minutes, au buffet, le saladier de fruits n'a pas été rempli.
- Tâches principales : aucune

### signal:259 — Le sucre roux du buffet n'a pas été réassorti

- Date : 2026-01-05 09:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:259
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le sucre roux du buffet n'a pas été réassorti, au buffet, le pot est au fond.
- Tâches principales : aucune

### signal:260 — L'upsell brunch du dimanche n'est pas en place au buffet

- Date : 2026-01-05 20:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : petit_dejeuner
- Responsable : petit_dejeuner
- Signal : signal:260
- Statut : resolved
- Famille : Qualité de service
- Activité : Petit-déjeuner
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'upsell brunch du dimanche n'est pas en place au buffet, au buffet, la carte vendue en ligne n'est pas dressée.
- Tâches principales : aucune

## Restaurant, cuisine et salle

### signal:file-diner — La file du dîner dépasse le lobby depuis vingt minutes

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
  - La file du dîner dépasse le lobby depuis vingt minutes, les clients s'impatientent au restaurant.
- Tâches principales : aucune

### signal:unassigned-note — La note de la table 12 du restaurant ne correspond pas à la commande

- Date : 2026-09-22 09:05:00+02:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:unassigned-note
- Statut : open
- Famille : Qualité de service
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Routage : non qualifié
- Observations :
  - La note de la table 12 du restaurant ne correspond pas à la commande, le client attend en salle.
- Tâches principales : aucune

### signal:interesting-file-vendredi — La file du vendredi s'allonge avant 20 h, sous le seuil d'incident

- Date : 2026-09-12 20:05:00+02:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:interesting-file-vendredi
- Statut : interesting
- Famille : Opportunité
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La file du vendredi s'allonge avant 20 h, sans encore bloquer le restaurant.
- Tâches principales : aucune

### signal:132 — La table 12 du restaurant a reçu le plat d'une autre table

- Date : 2025-11-08 04:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:132
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:erreurs-service — Erreurs de service ou de commande
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:132
- Observations :
  - La table 12 du restaurant a reçu le plat d'une autre table, au restaurant, la table 12 a renvoyé l'assiette dès qu'elle est arrivée. la commande au restaurant rdc : cause commune, personne n'a calé le contrôle après l'opération. La récurrence date de novembre.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:133 — La table 7 du restaurant est encore collante au second service

- Date : 2025-11-08 15:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:133
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La table 7 du restaurant est encore collante au second service, au restaurant, le client pose sa main et la retire. Au restaurant rdc, la table bloque encore la passation de novembre.
- Tâches principales : aucune

### signal:134 — Les entrées du restaurant ne sont pas en place et la salle attend

- Date : 2025-11-09 02:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:134
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:attente-restaurant — Attente excessive au restaurant
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:134
- Observations :
  - Les entrées du restaurant ne sont pas en place et la salle attend, au restaurant, les premières tables patientent sans amuse-bouche. On cherche à améliorer le processus : la cause n'est pas écrite avant de relancer le prestataire. Vu au restaurant rdc depuis novembre sur la mise en place.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:135 — Le restaurant affiche vingt minutes d'attente et la file est dans l'entrée

- Date : 2025-11-09 13:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:135
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:attente-restaurant — Attente excessive au restaurant
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:135
- Observations :
  - Le restaurant affiche vingt minutes d'attente et la file est dans l'entrée, au restaurant, la file dépasse déjà le porte-manteau. Récurrence depuis novembre au restaurant rdc : l'accueil à cause de le même écart revient faute de consigne d'étage.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:137 — L'ardoise du restaurant affiche un plat déjà en rupture

- Date : 2025-11-10 11:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:137
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:ruptures-bar — Ruptures de stock bar ou restaurant
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:137
- Observations :
  - L'ardoise du restaurant affiche un plat déjà en rupture, au restaurant, trois tables l'ont commandé pour rien. l'ardoise au restaurant rdc : cause commune, le geste de clôture n'est pas tenu dans le brief. La récurrence date de novembre.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:138 — Il manque deux serveurs au briefing du restaurant

- Date : 2025-11-10 22:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:138
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Il manque deux serveurs au briefing du restaurant, au restaurant, le briefing démarre à effectif incomplet. le planning au restaurant rdc : le seuil d'alerte n'a pas déclenché le réassort.
- Tâches principales : aucune

### signal:139 — Le plat du jour du restaurant n'a pas été briefé au coup de feu

- Date : 2025-11-11 09:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:139
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le plat du jour du restaurant n'a pas été briefé au coup de feu, au restaurant, la salle ne sait pas le décrire. Au restaurant rdc, le menu bloque encore la passation de novembre.
- Tâches principales : aucune

### signal:140 — Le gin du bar est en rupture en plein service

- Date : 2025-11-11 20:00:00+01:00
- Lieu : bar_central
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:140
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:ruptures-bar — Ruptures de stock bar ou restaurant
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:140
- Observations :
  - Le gin du bar est en rupture en plein service, au bar, deux cocktails de la carte ne peuvent plus partir. Récurrence depuis novembre au bar central : le gin à cause de personne n'a calé le contrôle après l'opération.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:142 — La clôture de caisse du restaurant a un écart de quinze euros

- Date : 2025-11-12 18:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:142
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:cloture-caisse — Écarts lors des clôtures de caisse
- Plan : plan:anomalie-caisse — Analyse d'une anomalie de clôture de caisse
- Exécution : exec:signal:signal:142
- Observations :
  - La clôture de caisse du restaurant a un écart de quinze euros, au restaurant, le comptage du soir ne tombe pas. la caisse au restaurant rdc : cause commune, la cause n'est pas écrite avant de relancer le prestataire. La récurrence date de novembre.
- Tâches principales :
  - Isoler l'écart de caisse
  - Retracer les tickets
  - Documenter la cause
  - Valider la clôture corrigée

### signal:143 — Le steak de la table 4 au restaurant est saignant au lieu d'à point

- Date : 2025-11-13 05:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:143
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:erreurs-service — Erreurs de service ou de commande
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:143
- Observations :
  - Le steak de la table 4 au restaurant est saignant au lieu d'à point, au restaurant, la table 4 attend une nouvelle cuisson. À chaque arrivée depuis novembre, la cuisson au restaurant rdc retombe sur le même écart revient faute de consigne d'étage.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:144 — Des miettes restent sur la banquette du restaurant

- Date : 2025-11-13 16:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:144
- Statut : resolved
- Famille : Qualité de service
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Des miettes restent sur la banquette du restaurant, au restaurant, la banquette du fond n'a pas été reprise. Au restaurant rdc, la banquette allonge le service plus que la jauge prévue.
- Tâches principales : aucune

### signal:145 — Le pain n'est pas sur les tables du restaurant, les clients patientent

- Date : 2025-11-14 03:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:145
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:attente-restaurant — Attente excessive au restaurant
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:145
- Observations :
  - Le pain n'est pas sur les tables du restaurant, les clients patientent, au restaurant, trois tables ont déjà demandé le pain. Récurrence depuis novembre au restaurant rdc : le pain à cause de la mise en place des tables de huit n'est pas anticipée.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:146 — Une table de quatre attend debout au restaurant sans être placée

- Date : 2025-11-14 14:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:146
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:attente-restaurant — Attente excessive au restaurant
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:146
- Observations :
  - Une table de quatre attend debout au restaurant sans être placée, au restaurant, personne n'a pris leur nom. Depuis novembre, l'accueil à restaurant rdc revient : le runner n'est pas appelé avant que la file atteigne le lobby. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:148 — Le post du jour annonce un brunch que le restaurant ne fait pas

- Date : 2025-11-15 12:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:148
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le post du jour annonce un brunch que le restaurant ne fait pas, au restaurant, deux clients sont venus pour ce brunch. Au restaurant rdc, le menu bloque encore la passation de novembre.
- Tâches principales : aucune

### signal:149 — La plonge est seule ce soir, le planning du restaurant est incomplet

- Date : 2025-11-15 23:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:149
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:evacuations-cuisine — Évacuations lentes en cuisine ou plonge
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:149
- Observations :
  - La plonge est seule ce soir, le planning du restaurant est incomplet, au restaurant, personne n'est noté en renfort plonge. On cherche à améliorer le processus : le geste de clôture n'est pas tenu dans le brief. Vu au restaurant rdc depuis novembre sur le planning.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:150 — Une suggestion à l'ardoise du restaurant n'a pas de fiche technique

- Date : 2025-11-16 10:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:150
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une suggestion à l'ardoise du restaurant n'a pas de fiche technique, au restaurant, la cuisine et la salle ne disent pas la même garniture. l'ardoise au restaurant rdc : le seuil d'alerte n'a pas déclenché le réassort.
- Tâches principales : aucune

### signal:151 — Il ne reste plus de tonic au bar pour les commandes en cours

- Date : 2025-11-16 21:00:00+01:00
- Lieu : bar_central
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:151
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:ruptures-bar — Ruptures de stock bar ou restaurant
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:151
- Observations :
  - Il ne reste plus de tonic au bar pour les commandes en cours, au bar, le dernier bac est vide. Depuis novembre, le tonic à bar central revient : le même écart revient faute de consigne d'étage. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:152 — Le menu dégustation vendu sur le site n'est pas lancé en cuisine

- Date : 2025-11-17 08:00:00+01:00
- Lieu : cuisine
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:152
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le menu dégustation vendu sur le site n'est pas lancé en cuisine, en cuisine, la fiche du site n'a pas été mise en production. Le geste prévu pour le menu n'a pas été tenu au cuisine.
- Tâches principales : aucune

### signal:153 — Un ticket du restaurant est resté ouvert après le départ de la table

- Date : 2025-11-17 19:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:153
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:cloture-caisse — Écarts lors des clôtures de caisse
- Plan : plan:anomalie-caisse — Analyse d'une anomalie de clôture de caisse
- Exécution : exec:signal:signal:153
- Observations :
  - Un ticket du restaurant est resté ouvert après le départ de la table, au restaurant, la table 6 est vide et le ticket vit encore. À chaque arrivée depuis novembre, la caisse au restaurant rdc retombe sur le geste de clôture n'est pas tenu dans le brief.
- Tâches principales :
  - Isoler l'écart de caisse
  - Retracer les tickets
  - Documenter la cause
  - Valider la clôture corrigée

### signal:154 — L'addition de la table 8 au restaurant oublie le dessert offert

- Date : 2025-11-18 06:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:154
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:erreurs-service — Erreurs de service ou de commande
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:154
- Observations :
  - L'addition de la table 8 au restaurant oublie le dessert offert, au restaurant, la table 8 compare avec ce qui a été dit. On cherche à améliorer le processus : la cause n'est pas écrite avant de relancer le prestataire. Vu au restaurant rdc depuis novembre sur l'addition.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:155 — Le sol devant le passe du restaurant est gras

- Date : 2025-11-18 17:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:155
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le sol devant le passe du restaurant est gras, au restaurant, on glisse en apportant les assiettes. Le geste prévu pour le sol n'a pas été tenu au restaurant rdc.
- Tâches principales : aucune

### signal:156 — La plonge a une pile de bacs qui bloque le passe du restaurant

- Date : 2025-11-19 04:00:00+01:00
- Lieu : plonge_economat
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:156
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:evacuations-cuisine — Évacuations lentes en cuisine ou plonge
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:156
- Observations :
  - La plonge a une pile de bacs qui bloque le passe du restaurant, à la plonge, les bacs sales empêchent de sortir les plats. Depuis novembre, la plonge à plonge economat revient : personne n'a calé le contrôle après l'opération. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:157 — L'hôtesse du restaurant a perdu la réservation de 20 h

- Date : 2026-09-16 14:00:00+02:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:157
- Statut : canceled
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:attente-restaurant — Attente excessive au restaurant
- Plan : aucun
- Exécution : aucun
- Motif d'annulation : Le client a déplacé la date, la préparation n'a plus lieu. Sujet : L'hôtesse du restaurant a perdu la réservation de 20 h.
- Observations :
  - L'hôtesse du restaurant a perdu la réservation de 20 h, au restaurant, les clients montrent le mail et restent debout. la réservation au restaurant rdc : cause commune, le geste de clôture n'est pas tenu dans le brief. La récurrence date de septembre.
- Tâches principales : aucune

### signal:159 — Les allergènes ne sont pas affichés à l'entrée du restaurant

- Date : 2025-11-20 13:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:159
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les allergènes ne sont pas affichés à l'entrée du restaurant, au restaurant, une table les demande avant de s'asseoir. l'affichage au restaurant rdc : le seuil d'alerte n'a pas déclenché le réassort.
- Tâches principales : aucune

### signal:160 — Un extra salle ne s'est pas présenté pour le coup de feu

- Date : 2025-11-21 00:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:160
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un extra salle ne s'est pas présenté pour le coup de feu, au restaurant, son nom est sur le planning de 19 h. Au restaurant rdc, l'extra bloque encore la passation de novembre.
- Tâches principales : aucune

### signal:161 — Le dessert du menu enfant est en rupture sans alternative annoncée

- Date : 2025-11-21 11:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:161
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:ruptures-bar — Ruptures de stock bar ou restaurant
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:161
- Observations :
  - Le dessert du menu enfant est en rupture sans alternative annoncée, au restaurant, la table l'apprend au moment de commander. Depuis novembre, le menu à restaurant rdc revient : le geste de clôture n'est pas tenu dans le brief. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:162 — Les oranges à jus du bar sont finies avant le soir

- Date : 2025-11-21 22:00:00+01:00
- Lieu : bar_central
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:162
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:ruptures-bar — Ruptures de stock bar ou restaurant
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:162
- Observations :
  - Les oranges à jus du bar sont finies avant le soir, au bar, le presse est vide et la carte propose encore le jus. les oranges au bar central : cause commune, la cause n'est pas écrite avant de relancer le prestataire. La récurrence date de novembre.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:163 — Un bon cadeau restaurant est refusé en caisse, l'offre a expiré

- Date : 2025-11-22 09:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:163
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:cloture-caisse — Écarts lors des clôtures de caisse
- Plan : plan:anomalie-caisse — Analyse d'une anomalie de clôture de caisse
- Exécution : exec:signal:signal:163
- Observations :
  - Un bon cadeau restaurant est refusé en caisse, l'offre a expiré, au restaurant, le client a le bon en main. À chaque arrivée depuis novembre, l'offre au restaurant rdc retombe sur le même écart revient faute de consigne d'étage.
- Tâches principales :
  - Isoler l'écart de caisse
  - Retracer les tickets
  - Documenter la cause
  - Valider la clôture corrigée

### signal:164 — Le fond de caisse du bar ne correspond pas au comptage du matin

- Date : 2025-11-22 20:00:00+01:00
- Lieu : bar_central
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:164
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:cloture-caisse — Écarts lors des clôtures de caisse
- Plan : plan:anomalie-caisse — Analyse d'une anomalie de clôture de caisse
- Exécution : exec:signal:signal:164
- Observations :
  - Le fond de caisse du bar ne correspond pas au comptage du matin, au bar, il manque un rouleau par rapport à la veille. On cherche à améliorer le processus : personne n'a calé le contrôle après l'opération. Vu au bar central depuis novembre sur la caisse.
- Tâches principales :
  - Isoler l'écart de caisse
  - Retracer les tickets
  - Documenter la cause
  - Valider la clôture corrigée

### signal:165 — Le serveur du restaurant a encaissé la table 15 trop tôt

- Date : 2025-11-23 07:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:165
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:erreurs-service — Erreurs de service ou de commande
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:165
- Observations :
  - Le serveur du restaurant a encaissé la table 15 trop tôt, au restaurant, la table 15 n'avait pas fini le café. Récurrence depuis novembre au restaurant rdc : l'encaissement à cause de le geste de clôture n'est pas tenu dans le brief.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:166 — Les vitres de la salle du restaurant ont des traces de doigts

- Date : 2025-11-23 18:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:166
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les vitres de la salle du restaurant ont des traces de doigts, au restaurant, la lumière du soir les rend très visibles. Au restaurant rdc, les vitres bloque encore la passation de novembre.
- Tâches principales : aucune

### signal:167 — Les verres propres n'arrivent plus de la plonge vers le restaurant

- Date : 2025-11-24 05:00:00+01:00
- Lieu : plonge_economat
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:167
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:evacuations-cuisine — Évacuations lentes en cuisine ou plonge
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:167
- Observations :
  - Les verres propres n'arrivent plus de la plonge vers le restaurant, à la plonge, le panier à verres est encore dans la machine. la plonge au plonge economat : cause commune, le même écart revient faute de consigne d'étage. La récurrence date de novembre.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:168 — Le bar fait attendre les boissons plus longtemps que les plats

- Date : 2025-11-24 16:00:00+01:00
- Lieu : bar_central
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:168
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:attente-restaurant — Attente excessive au restaurant
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:168
- Observations :
  - Le bar fait attendre les boissons plus longtemps que les plats, au bar, deux verres commandés avec les entrées ne sont pas partis. À chaque arrivée depuis novembre, le bar au bar central retombe sur personne n'a calé le contrôle après l'opération.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:170 — Le menu ardoise du bar a encore les prix d'hier

- Date : 2025-11-25 14:00:00+01:00
- Lieu : bar_central
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:170
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:ruptures-bar — Ruptures de stock bar ou restaurant
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:170
- Observations :
  - Le menu ardoise du bar a encore les prix d'hier, au bar, le cocktail du jour n'est pas au tarif affiché. Récurrence depuis novembre au bar central : l'ardoise à cause de la cause n'est pas écrite avant de relancer le prestataire.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:171 — La formation caisse prévue pour le restaurant est sautée

- Date : 2025-11-26 01:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:171
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:cloture-caisse — Écarts lors des clôtures de caisse
- Plan : plan:anomalie-caisse — Analyse d'une anomalie de clôture de caisse
- Exécution : exec:signal:signal:171
- Observations :
  - La formation caisse prévue pour le restaurant est sautée, au restaurant, l'équipier devait être formé avant le service. Depuis novembre, la formation à restaurant rdc revient : le même écart revient faute de consigne d'étage. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Isoler l'écart de caisse
  - Retracer les tickets
  - Documenter la cause
  - Valider la clôture corrigée

### signal:172 — La carte du bar ne correspond plus aux sirops en place

- Date : 2025-11-26 12:00:00+01:00
- Lieu : bar_central
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:172
- Statut : resolved
- Famille : Qualité de service
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La carte du bar ne correspond plus aux sirops en place, au bar, deux sirops de la carte sont absents du poste. L'écart sur la carte se voit encore au service du bar central.
- Tâches principales : aucune

### signal:173 — Le sirop de passion du bar est vide et la carte le propose encore

- Date : 2025-11-26 23:00:00+01:00
- Lieu : bar_central
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:173
- Statut : resolved
- Famille : Qualité de service
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le sirop de passion du bar est vide et la carte le propose encore, au bar, le dernier litre est à la poubelle. Prestation le sirop au bar central : le standard du brief n'est pas tenu.
- Tâches principales : aucune

### signal:175 — Une annulation en caisse du restaurant n'a pas de motif

- Date : 2025-11-27 21:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:175
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:cloture-caisse — Écarts lors des clôtures de caisse
- Plan : plan:anomalie-caisse — Analyse d'une anomalie de clôture de caisse
- Exécution : exec:signal:signal:175
- Observations :
  - Une annulation en caisse du restaurant n'a pas de motif, au restaurant, la ligne est barrée sans commentaire. Récurrence depuis novembre au restaurant rdc : la caisse à cause de le même écart revient faute de consigne d'étage.
- Tâches principales :
  - Isoler l'écart de caisse
  - Retracer les tickets
  - Documenter la cause
  - Valider la clôture corrigée

### signal:176 — L'allergie arachide de la table 6 n'est pas arrivée en cuisine

- Date : 2025-11-28 08:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:176
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:erreurs-service — Erreurs de service ou de commande
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:176
- Observations :
  - L'allergie arachide de la table 6 n'est pas arrivée en cuisine, au restaurant, la table 6 a renvoyé l'entrée par précaution. Depuis novembre, l'allergie à restaurant rdc revient : personne n'a calé le contrôle après l'opération. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:177 — Un verre cassé n'a pas été entièrement ramassé au restaurant

- Date : 2025-11-28 19:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:177
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un verre cassé n'a pas été entièrement ramassé au restaurant, au restaurant, un éclat brille près de la porte. le sol au restaurant rdc : le seuil d'alerte n'a pas déclenché le réassort.
- Tâches principales : aucune

### signal:178 — L'économat n'a pas sorti les caisses pour le service du restaurant

- Date : 2025-11-29 06:00:00+01:00
- Lieu : plonge_economat
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:178
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:evacuations-cuisine — Évacuations lentes en cuisine ou plonge
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:178
- Observations :
  - L'économat n'a pas sorti les caisses pour le service du restaurant, à l'économat, les caisses du soir sont encore filmées. À chaque arrivée depuis novembre, l'économat au plonge economat retombe sur la cause n'est pas écrite avant de relancer le prestataire.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:179 — Aucun serveur ne prend la commande à la table 11 du restaurant

- Date : 2025-11-29 17:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:179
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:attente-restaurant — Attente excessive au restaurant
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:179
- Observations :
  - Aucun serveur ne prend la commande à la table 11 du restaurant, au restaurant, la table 11 a les menus ouverts depuis un moment. On cherche à améliorer le processus : l'ouverture de la deuxième rangée dépend d'un seul manager. Vu au restaurant rdc depuis novembre sur la commande.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:183 — Un plat végétarien promis au menu du restaurant n'est pas lancé

- Date : 2025-12-01 13:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : communication
- Responsable : restaurant
- Signal : signal:183
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un plat végétarien promis au menu du restaurant n'est pas lancé, au restaurant, la fiche est là mais le plat n'est pas au passe. Chacun a une partie de le menu au restaurant rdc, personne n'a clôturé.
- Tâches principales : aucune

### signal:184 — La bière pression du bar mousse trop, le fût est en fin

- Date : 2025-12-02 00:00:00+01:00
- Lieu : bar_central
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:184
- Statut : resolved
- Famille : Qualité de service
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La bière pression du bar mousse trop, le fût est en fin, au bar, on jette un verre sur deux. L'écart sur la bière se voit encore au service du bar central.
- Tâches principales : aucune

### signal:185 — Un code promo restaurant fait un total négatif en caisse

- Date : 2025-12-02 11:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:185
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un code promo restaurant fait un total négatif en caisse, au restaurant, la caisse bloque sur ce code. Le geste prévu pour le promo n'a pas été tenu au restaurant rdc.
- Tâches principales : aucune

### signal:186 — Le pourboire carte du restaurant n'est pas ventilé sur le bon service

- Date : 2025-12-02 22:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:186
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le pourboire carte du restaurant n'est pas ventilé sur le bon service, au restaurant, le montant est resté sur le service de midi. la caisse au restaurant rdc : le seuil d'alerte n'a pas déclenché le réassort.
- Tâches principales : aucune

### signal:187 — Le vin de la table 9 au restaurant n'est pas celui annoncé

- Date : 2025-12-03 09:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:187
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:erreurs-service — Erreurs de service ou de commande
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:187
- Observations :
  - Le vin de la table 9 au restaurant n'est pas celui annoncé, au restaurant, la table 9 a commandé le verre du mois. le vin au restaurant rdc : cause commune, le même écart revient faute de consigne d'étage. La récurrence date de décembre.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:188 — Les chaises du restaurant ont des taches de sauce

- Date : 2025-12-03 20:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : maintenance
- Responsable : restaurant
- Signal : signal:188
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les chaises du restaurant ont des taches de sauce, au restaurant, deux chaises de la rangée fenêtre sont marquées. les chaises au restaurant rdc demande encore un arbitrage entre les deux pôles.
- Tâches principales : aucune

### signal:189 — Il manque les assiettes chaudes, la plonge n'a pas suivi

- Date : 2025-12-04 07:00:00+01:00
- Lieu : plonge_economat
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:189
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:evacuations-cuisine — Évacuations lentes en cuisine ou plonge
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:189
- Observations :
  - Il manque les assiettes chaudes, la plonge n'a pas suivi, à la plonge, le chauffe-assiettes est vide en plein coup de feu. On cherche à améliorer le processus : le geste de clôture n'est pas tenu dans le brief. Vu au plonge economat depuis décembre sur la plonge.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:190 — La file du restaurant dépasse sur le lobby à 21 h

- Date : 2025-12-04 18:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:190
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:attente-restaurant — Attente excessive au restaurant
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:190
- Observations :
  - La file du restaurant dépasse sur le lobby à 21 h, au restaurant, les suivants attendent déjà dans le hall. Récurrence depuis décembre au restaurant rdc : l'accueil à cause de la cause n'est pas écrite avant de relancer le prestataire.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:192 — Le chevalet du restaurant indique un menu enfant qui n'est plus servi

- Date : 2025-12-05 16:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : communication
- Responsable : restaurant
- Signal : signal:192
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le chevalet du restaurant indique un menu enfant qui n'est plus servi, au restaurant, la table avec enfants est déçue. Chacun a une partie de le menu au restaurant rdc, personne n'a clôturé.
- Tâches principales : aucune

### signal:193 — Une pause n'est pas posée et l'équipe du restaurant décroche

- Date : 2025-12-06 03:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : hotel
- Responsable : restaurant
- Signal : signal:193
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une pause n'est pas posée et l'équipe du restaurant décroche, au restaurant, tout le monde est en salle depuis l'ouverture. Le pôle auteur et le responsable ne sont pas alignés sur le planning au restaurant rdc.
- Tâches principales : aucune

### signal:194 — Les prix du menu déjeuner au restaurant n'ont pas été mis à jour

- Date : 2025-12-06 14:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : maintenance
- Responsable : restaurant
- Signal : signal:194
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les prix du menu déjeuner au restaurant n'ont pas été mis à jour, au restaurant, l'ardoise et la caisse ne disent pas le même prix. le menu au restaurant rdc demande encore un arbitrage entre les deux pôles.
- Tâches principales : aucune

### signal:195 — Il manque le vin blanc au verre annoncé au bar

- Date : 2025-12-07 01:00:00+01:00
- Lieu : bar_central
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:195
- Statut : resolved
- Famille : Qualité de service
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Il manque le vin blanc au verre annoncé au bar, au bar, la bouteille ouverte est finie et la suivante n'est pas fraîche. Au bar central, le vin allonge le service plus que la jauge prévue.
- Tâches principales : aucune

### signal:196 — L'upsell dessert proposé en salle n'est plus au menu du restaurant

- Date : 2025-12-07 12:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : hotel
- Responsable : restaurant
- Signal : signal:196
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'upsell dessert proposé en salle n'est plus au menu du restaurant, au restaurant, la salle le propose encore. Le pôle auteur et le responsable ne sont pas alignés sur le menu au restaurant rdc.
- Tâches principales : aucune

### signal:197 — Deux encaissements du restaurant portent la même table

- Date : 2025-12-07 23:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:197
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Deux encaissements du restaurant portent la même table, au restaurant, la table 9 a deux tickets payés. Le geste prévu pour la caisse n'a pas été tenu au restaurant rdc.
- Tâches principales : aucune

### signal:198 — La table 18 du restaurant a été resservie avec les couverts sales

- Date : 2025-12-08 10:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:198
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:erreurs-service — Erreurs de service ou de commande
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:198
- Observations :
  - La table 18 du restaurant a été resservie avec les couverts sales, au restaurant, les couverts du plat précédent sont restés. À chaque arrivée depuis décembre, le service au restaurant rdc retombe sur la cause n'est pas écrite avant de relancer le prestataire.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:199 — Le tapis d'entrée du restaurant est noir de pas

- Date : 2025-12-08 21:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : hotel
- Responsable : restaurant
- Signal : signal:199
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le tapis d'entrée du restaurant est noir de pas, au restaurant, les clients le remarquent en entrant. Le pôle auteur et le responsable ne sont pas alignés sur le tapis au restaurant rdc.
- Tâches principales : aucune

### signal:200 — Le bac à couverts de la plonge est vide en plein service

- Date : 2025-12-09 08:00:00+01:00
- Lieu : plonge_economat
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:200
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:evacuations-cuisine — Évacuations lentes en cuisine ou plonge
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:200
- Observations :
  - Le bac à couverts de la plonge est vide en plein service, à la plonge, la salle attend des fourchettes propres. Récurrence depuis décembre au plonge economat : la plonge à cause de personne n'a calé le contrôle après l'opération.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:201 — Un client sans réservation attend depuis trente minutes au restaurant

- Date : 2025-12-09 19:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:201
- Statut : canceled
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:attente-restaurant — Attente excessive au restaurant
- Plan : aucun
- Exécution : aucun
- Motif d'annulation : Le client a déplacé la date, la préparation n'a plus lieu. Sujet : Un client sans réservation attend depuis trente minutes au restaurant.
- Observations :
  - Un client sans réservation attend depuis trente minutes au restaurant, au restaurant, il est toujours près de l'entrée. Depuis décembre, l'accueil à restaurant rdc revient : la mise en place des tables de huit n'est pas anticipée. C'est une faiblesse de processus à améliorer.
- Tâches principales : aucune

### signal:202 — Le four du passe en cuisine affiche une erreur

- Date : 2025-12-10 06:00:00+01:00
- Lieu : cuisine
- Auteur : hotel
- Responsable : restaurant
- Signal : signal:202
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le four du passe en cuisine affiche une erreur, en cuisine, le passe est ralenti depuis le milieu du service. Le pôle auteur et le responsable ne sont pas alignés sur le four au cuisine.
- Tâches principales : aucune

### signal:203 — L'écran du restaurant tourne une publicité d'un autre établissement

- Date : 2025-12-10 17:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : maintenance
- Responsable : restaurant
- Signal : signal:203
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'écran du restaurant tourne une publicité d'un autre établissement, au restaurant, on voit le nom d'une autre adresse. l'écran au restaurant rdc demande encore un arbitrage entre les deux pôles.
- Tâches principales : aucune

### signal:204 — Le planning du dimanche au restaurant affiche un effectif de semaine

- Date : 2025-12-11 04:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:204
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le planning du dimanche au restaurant affiche un effectif de semaine, au restaurant, il manque les deux renforts habituels du dimanche.
- Tâches principales : aucune

### signal:205 — La garniture du burger au restaurant a changé sans être dite en salle

- Date : 2025-12-11 15:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : hotel
- Responsable : restaurant
- Signal : signal:205
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La garniture du burger au restaurant a changé sans être dite en salle, au restaurant, la salle décrit encore l'ancienne version. Le pôle auteur et le responsable ne sont pas alignés sur le menu au restaurant rdc.
- Tâches principales : aucune

### signal:206 — Les dosettes café du restaurant sont au compte-gouttes

- Date : 2025-12-12 02:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : maintenance
- Responsable : restaurant
- Signal : signal:206
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les dosettes café du restaurant sont au compte-gouttes, au restaurant, il reste une poignée pour tout le service. le café au restaurant rdc demande encore un arbitrage entre les deux pôles.
- Tâches principales : aucune

### signal:207 — L'offre anniversaire du restaurant n'a pas le gâteau en réserve

- Date : 2025-12-12 13:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : communication
- Responsable : restaurant
- Signal : signal:207
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'offre anniversaire du restaurant n'a pas le gâteau en réserve, au restaurant, la table est là et la cuisine n'a pas le gâteau. Chacun a une partie de l'offre au restaurant rdc, personne n'a clôturé.
- Tâches principales : aucune

### signal:208 — La caisse du restaurant n'a pas été clôturée avant la passation

- Date : 2025-12-13 00:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:208
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La caisse du restaurant n'a pas été clôturée avant la passation, au restaurant, l'équipe du soir reprend une caisse encore ouverte.
- Tâches principales : aucune

### signal:209 — Le café de la table 3 au restaurant est arrivé décaféiné par erreur

- Date : 2025-12-13 11:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:209
- Statut : resolved
- Famille : Amélioration continue
- Activité : Restaurant, cuisine et salle
- Pattern : pattern:erreurs-service — Erreurs de service ou de commande
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:209
- Observations :
  - Le café de la table 3 au restaurant est arrivé décaféiné par erreur, au restaurant, la table 3 avait demandé un expresso. On cherche à améliorer le processus : le geste de clôture n'est pas tenu dans le brief. Vu au restaurant rdc depuis décembre sur le café.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:210 — Le comptoir du restaurant n'a pas été essuyé après le rush

- Date : 2025-12-13 22:00:00+01:00
- Lieu : restaurant_rdc
- Auteur : communication
- Responsable : restaurant
- Signal : signal:210
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le comptoir du restaurant n'a pas été essuyé après le rush, au restaurant, des ronds de verre sont encore là. Chacun a une partie de le comptoir au restaurant rdc, personne n'a clôturé.
- Tâches principales : aucune

### signal:211 — Une machine de la plonge est arrêtée et les plats restent au passe

- Date : 2025-12-14 09:00:00+01:00
- Lieu : plonge_economat
- Auteur : hotel
- Responsable : restaurant
- Signal : signal:211
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une machine de la plonge est arrêtée et les plats restent au passe, à la plonge, le voyant rouge est allumé depuis le début du service. Le pôle auteur et le responsable ne sont pas alignés sur la plonge au plonge economat.
- Tâches principales : aucune

### signal:212 — Des tables du restaurant attendent l'addition pour libérer la place

- Date : 2026-09-17 05:00:00+02:00
- Lieu : restaurant_rdc
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:212
- Statut : resolved
- Famille : Qualité de service
- Activité : Restaurant, cuisine et salle
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Des tables du restaurant attendent l'addition pour libérer la place, au restaurant, deux tables font signe depuis plusieurs minutes. Prestation l'addition au restaurant rdc : le standard du brief n'est pas tenu.
- Tâches principales : aucune

## Rooftop et piscine

### signal:interesting-table-rooftop — Les groupes du rooftop aimeraient garder la table après le dessert

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
- Observations :
  - Les groupes du rooftop aimeraient garder la table après le dessert, en fin de saison.
- Tâches principales : aucune

### signal:042 — L'eau de la piscine est trouble dès l'ouverture

- Date : 2025-09-27 22:00:00+02:00
- Lieu : piscine
- Auteur : hotel
- Responsable : hotel
- Signal : signal:042
- Statut : resolved
- Famille : Amélioration continue
- Activité : Rooftop et piscine
- Pattern : pattern:piscine — Incidents d'exploitation de la piscine
- Plan : plan:ouverture-saison-rooftop-piscine — Ouverture de saison rooftop et piscine
- Exécution : exec:signal:signal:042
- Observations :
  - L'eau de la piscine est trouble dès l'ouverture, à la piscine, on ne voit plus le fond du bassin. la piscine au piscine : cause commune, la cause n'est pas écrite avant de relancer le prestataire. La récurrence date de septembre.
- Tâches principales :
  - Inspecter les espaces rooftop et piscine
  - Réaliser les contrôles techniques et de sécurité
  - Préparer stocks et équipements
  - Mettre à jour la communication
  - Valider l'ouverture

### signal:052 — La ligne d'eau de la piscine déborde vers les transats

- Date : 2025-10-02 12:00:00+02:00
- Lieu : piscine
- Auteur : hotel
- Responsable : hotel
- Signal : signal:052
- Statut : resolved
- Famille : Amélioration continue
- Activité : Rooftop et piscine
- Pattern : pattern:piscine — Incidents d'exploitation de la piscine
- Plan : plan:ouverture-saison-rooftop-piscine — Ouverture de saison rooftop et piscine
- Exécution : exec:signal:signal:052
- Observations :
  - La ligne d'eau de la piscine déborde vers les transats, à la piscine, le dallage est glissant autour du bassin. la piscine au piscine : cause commune, personne n'a calé le contrôle après l'opération. La récurrence date de octobre.
- Tâches principales :
  - Inspecter les espaces rooftop et piscine
  - Réaliser les contrôles techniques et de sécurité
  - Préparer stocks et équipements
  - Mettre à jour la communication
  - Valider l'ouverture

### signal:062 — Un transat de la piscine a une latte cassée

- Date : 2025-10-07 02:00:00+02:00
- Lieu : piscine
- Auteur : hotel
- Responsable : hotel
- Signal : signal:062
- Statut : resolved
- Famille : Amélioration continue
- Activité : Rooftop et piscine
- Pattern : pattern:piscine — Incidents d'exploitation de la piscine
- Plan : plan:ouverture-saison-rooftop-piscine — Ouverture de saison rooftop et piscine
- Exécution : exec:signal:signal:062
- Observations :
  - Un transat de la piscine a une latte cassée, à la piscine, un client s'est pincé en s'asseyant. la piscine au piscine : cause commune, la cause n'est pas écrite avant de relancer le prestataire. La récurrence date de octobre.
- Tâches principales :
  - Inspecter les espaces rooftop et piscine
  - Réaliser les contrôles techniques et de sécurité
  - Préparer stocks et équipements
  - Mettre à jour la communication
  - Valider l'ouverture

### signal:072 — Le pédiluve de la piscine est à sec en milieu de journée

- Date : 2025-10-11 16:00:00+02:00
- Lieu : piscine
- Auteur : hotel
- Responsable : hotel
- Signal : signal:072
- Statut : resolved
- Famille : Amélioration continue
- Activité : Rooftop et piscine
- Pattern : pattern:piscine — Incidents d'exploitation de la piscine
- Plan : plan:ouverture-saison-rooftop-piscine — Ouverture de saison rooftop et piscine
- Exécution : exec:signal:signal:072
- Observations :
  - Le pédiluve de la piscine est à sec en milieu de journée, à la piscine, les nageurs entrent sans se rincer les pieds. la piscine au piscine : cause commune, personne n'a calé le contrôle après l'opération. La récurrence date de octobre.
- Tâches principales :
  - Inspecter les espaces rooftop et piscine
  - Réaliser les contrôles techniques et de sécurité
  - Préparer stocks et équipements
  - Mettre à jour la communication
  - Valider l'ouverture

### signal:082 — L'eau de la piscine est trop froide pour le premier bain

- Date : 2025-10-16 06:00:00+02:00
- Lieu : piscine
- Auteur : hotel
- Responsable : hotel
- Signal : signal:082
- Statut : resolved
- Famille : Amélioration continue
- Activité : Rooftop et piscine
- Pattern : pattern:piscine — Incidents d'exploitation de la piscine
- Plan : plan:ouverture-saison-rooftop-piscine — Ouverture de saison rooftop et piscine
- Exécution : exec:signal:signal:082
- Observations :
  - L'eau de la piscine est trop froide pour le premier bain, à la piscine, le thermomètre du bassin affiche 22 degrés. la piscine au piscine : cause commune, la cause n'est pas écrite avant de relancer le prestataire. La récurrence date de octobre.
- Tâches principales :
  - Inspecter les espaces rooftop et piscine
  - Réaliser les contrôles techniques et de sécurité
  - Préparer stocks et équipements
  - Mettre à jour la communication
  - Valider l'ouverture

### signal:092 — Les serviettes de la piscine sont restées au local fermé

- Date : 2025-10-20 20:00:00+02:00
- Lieu : piscine
- Auteur : hotel
- Responsable : hotel
- Signal : signal:092
- Statut : resolved
- Famille : Amélioration continue
- Activité : Rooftop et piscine
- Pattern : pattern:piscine — Incidents d'exploitation de la piscine
- Plan : plan:ouverture-saison-rooftop-piscine — Ouverture de saison rooftop et piscine
- Exécution : exec:signal:signal:092
- Observations :
  - Les serviettes de la piscine sont restées au local fermé, à la piscine, les clients sortent du bassin sans linge. la piscine au piscine : cause commune, personne n'a calé le contrôle après l'opération. La récurrence date de octobre.
- Tâches principales :
  - Inspecter les espaces rooftop et piscine
  - Réaliser les contrôles techniques et de sécurité
  - Préparer stocks et équipements
  - Mettre à jour la communication
  - Valider l'ouverture

### signal:136 — La sono du rooftop coupe pendant le service du soir

- Date : 2025-11-10 00:00:00+01:00
- Lieu : rooftop
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:136
- Statut : resolved
- Famille : Amélioration continue
- Activité : Rooftop et piscine
- Pattern : pattern:equipements-rooftop — Défaillances d'équipements du rooftop
- Plan : plan:ouverture-saison-rooftop-piscine — Ouverture de saison rooftop et piscine
- Exécution : exec:signal:signal:136
- Observations :
  - La sono du rooftop coupe pendant le service du soir, au rooftop, la musique s'arrête à chaque commande. Depuis novembre, la sono à rooftop revient : personne n'a calé le contrôle après l'opération. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Inspecter les espaces rooftop et piscine
  - Réaliser les contrôles techniques et de sécurité
  - Préparer stocks et équipements
  - Mettre à jour la communication
  - Valider l'ouverture

### signal:141 — Une table vendue en ligne pour le rooftop n'existe pas au plan de salle

- Date : 2025-11-12 07:00:00+01:00
- Lieu : rooftop
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:141
- Statut : resolved
- Famille : Amélioration continue
- Activité : Rooftop et piscine
- Pattern : pattern:equipements-rooftop — Défaillances d'équipements du rooftop
- Plan : plan:ouverture-saison-rooftop-piscine — Ouverture de saison rooftop et piscine
- Exécution : exec:signal:signal:141
- Observations :
  - Une table vendue en ligne pour le rooftop n'existe pas au plan de salle, au rooftop, le plan n'a pas cette table de six. Depuis novembre, la réservation à rooftop revient : le geste de clôture n'est pas tenu dans le brief. C'est une faiblesse de processus à améliorer.
- Tâches principales :
  - Inspecter les espaces rooftop et piscine
  - Réaliser les contrôles techniques et de sécurité
  - Préparer stocks et équipements
  - Mettre à jour la communication
  - Valider l'ouverture

### signal:147 — Une lampe chauffante du rooftop ne s'allume plus

- Date : 2025-11-15 01:00:00+01:00
- Lieu : rooftop
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:147
- Statut : resolved
- Famille : Amélioration continue
- Activité : Rooftop et piscine
- Pattern : pattern:equipements-rooftop — Défaillances d'équipements du rooftop
- Plan : plan:ouverture-saison-rooftop-piscine — Ouverture de saison rooftop et piscine
- Exécution : exec:signal:signal:147
- Observations :
  - Une lampe chauffante du rooftop ne s'allume plus, au rooftop, la table du fond a froid. la lampe au rooftop : cause commune, le même écart revient faute de consigne d'étage. La récurrence date de novembre.
- Tâches principales :
  - Inspecter les espaces rooftop et piscine
  - Réaliser les contrôles techniques et de sécurité
  - Préparer stocks et équipements
  - Mettre à jour la communication
  - Valider l'ouverture

### signal:158 — Le parasol du rooftop est coincé et la pluie arrive

- Date : 2025-11-20 02:00:00+01:00
- Lieu : rooftop
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:158
- Statut : resolved
- Famille : Amélioration continue
- Activité : Rooftop et piscine
- Pattern : pattern:equipements-rooftop — Défaillances d'équipements du rooftop
- Plan : plan:ouverture-saison-rooftop-piscine — Ouverture de saison rooftop et piscine
- Exécution : exec:signal:signal:158
- Observations :
  - Le parasol du rooftop est coincé et la pluie arrive, au rooftop, on ne couvre plus deux tables. À chaque arrivée depuis novembre, le parasol au rooftop retombe sur la cause n'est pas écrite avant de relancer le prestataire.
- Tâches principales :
  - Inspecter les espaces rooftop et piscine
  - Réaliser les contrôles techniques et de sécurité
  - Préparer stocks et équipements
  - Mettre à jour la communication
  - Valider l'ouverture

### signal:169 — Le frigo du bar rooftop sonne en alarme

- Date : 2025-11-25 03:00:00+01:00
- Lieu : rooftop
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:169
- Statut : resolved
- Famille : Amélioration continue
- Activité : Rooftop et piscine
- Pattern : pattern:equipements-rooftop — Défaillances d'équipements du rooftop
- Plan : plan:ouverture-saison-rooftop-piscine — Ouverture de saison rooftop et piscine
- Exécution : exec:signal:signal:169
- Observations :
  - Le frigo du bar rooftop sonne en alarme, au rooftop, l'alarme revient toutes les cinq minutes. On cherche à améliorer le processus : le geste de clôture n'est pas tenu dans le brief. Vu au rooftop depuis novembre sur le frigo.
- Tâches principales :
  - Inspecter les espaces rooftop et piscine
  - Réaliser les contrôles techniques et de sécurité
  - Préparer stocks et équipements
  - Mettre à jour la communication
  - Valider l'ouverture

### signal:180 — La prise du terminal de paiement du rooftop est morte

- Date : 2025-11-30 04:00:00+01:00
- Lieu : rooftop
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:180
- Statut : resolved
- Famille : Amélioration continue
- Activité : Rooftop et piscine
- Pattern : pattern:equipements-rooftop — Défaillances d'équipements du rooftop
- Plan : plan:ouverture-saison-rooftop-piscine — Ouverture de saison rooftop et piscine
- Exécution : exec:signal:signal:180
- Observations :
  - La prise du terminal de paiement du rooftop est morte, au rooftop, on descend encaisser au restaurant. Récurrence depuis novembre au rooftop : la prise à cause de personne n'a calé le contrôle après l'opération.
- Tâches principales :
  - Inspecter les espaces rooftop et piscine
  - Réaliser les contrôles techniques et de sécurité
  - Préparer stocks et équipements
  - Mettre à jour la communication
  - Valider l'ouverture

### signal:181 — Une story du restaurant promet une table au rooftop qui n'est pas ouverte

- Date : 2025-11-30 15:00:00+01:00
- Lieu : rooftop
- Auteur : maintenance
- Responsable : restaurant
- Signal : signal:181
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Rooftop et piscine
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une story du restaurant promet une table au rooftop qui n'est pas ouverte, au rooftop, le client montre la publication de ce matin. Le pôle auteur et le responsable ne sont pas alignés sur la story au rooftop.
- Tâches principales : aucune

### signal:182 — Personne n'est au planning pour tenir le rooftop ce soir

- Date : 2025-12-01 02:00:00+01:00
- Lieu : rooftop
- Auteur : maintenance
- Responsable : restaurant
- Signal : signal:182
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Rooftop et piscine
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Personne n'est au planning pour tenir le rooftop ce soir, au rooftop, le chef de rang est déjà pris en salle. le planning au rooftop demande encore un arbitrage entre les deux pôles.
- Tâches principales : aucune

### signal:191 — L'éclairage de l'escalier du rooftop reste éteint

- Date : 2025-12-05 05:00:00+01:00
- Lieu : rooftop
- Auteur : maintenance
- Responsable : restaurant
- Signal : signal:191
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Rooftop et piscine
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'éclairage de l'escalier du rooftop reste éteint, au rooftop, les clients descendent à la lampe du téléphone. l'escalier au rooftop demande encore un arbitrage entre les deux pôles.
- Tâches principales : aucune

### signal:299 — La piscine n'avait pas son volet à l'ouverture

- Date : 2026-01-23 17:00:00+01:00
- Lieu : piscine
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:299
- Statut : resolved
- Famille : Expérience client
- Activité : Rooftop et piscine
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La piscine n'avait pas son volet à l'ouverture, à la piscine, le bassin est resté découvert.
  - La piscine n'avait pas son volet à l'ouverture : l'accueil événement le voit aussi. à la piscine, le bassin est resté découvert. Séjour impacté au piscine : le volet reste le point d'irritation.
- Tâches principales : aucune

### signal:307 — L'issue de secours du rooftop a le ferme-porte trop dur

- Date : 2026-01-27 09:00:00+01:00
- Lieu : rooftop
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:307
- Statut : resolved
- Famille : Expérience client
- Activité : Rooftop et piscine
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'issue de secours du rooftop a le ferme-porte trop dur, au rooftop, la porte se referme trop violemment.
  - L'issue de secours du rooftop a le ferme-porte trop dur : l'accueil événement le voit aussi. au rooftop, la porte se referme trop violemment. Le client le vit au rooftop autour de l'issue.
- Tâches principales : aucune

### signal:316 — Le wifi du rooftop lâche dès que la salle est pleine

- Date : 2026-01-31 12:00:00+01:00
- Lieu : rooftop
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:316
- Statut : resolved
- Famille : Expérience client
- Activité : Rooftop et piscine
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le wifi du rooftop lâche dès que la salle est pleine, au rooftop, les clients n'ouvrent plus leurs mails.
  - Le wifi du rooftop lâche dès que la salle est pleine : le client vient de le redire au lobby. au rooftop, les clients n'ouvrent plus leurs mails. Le client le vit au rooftop autour de le wifi.
- Tâches principales : aucune

### signal:319 — Le rooftop était encore alimenté à la fermeture technique

- Date : 2026-02-01 21:00:00+01:00
- Lieu : rooftop
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:319
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Rooftop et piscine
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le rooftop était encore alimenté à la fermeture technique, au rooftop, les prises étaient sous tension.
  - Le rooftop était encore alimenté à la fermeture technique : je le vois aussi au passage d'étage. au rooftop, les prises étaient sous tension.
- Tâches principales : aucune

### signal:320 — Le prestataire piscine a laissé le local produits ouvert

- Date : 2026-02-02 08:00:00+01:00
- Lieu : piscine
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:320
- Statut : resolved
- Famille : Expérience client
- Activité : Rooftop et piscine
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le prestataire piscine a laissé le local produits ouvert, à la piscine, les bidons sont accessibles.
  - Le prestataire piscine a laissé le local produits ouvert : la réception a la même info à l'instant. à la piscine, les bidons sont accessibles. Séjour impacté au piscine : le prestataire reste le point d'irritation.
- Tâches principales : aucune

### signal:330 — L'intervention toiture est reportée alors que le rooftop goutte

- Date : 2026-02-06 22:00:00+01:00
- Lieu : rooftop
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:330
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Rooftop et piscine
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'intervention toiture est reportée alors que le rooftop goutte, au rooftop, une goutte tombe près de la prise.
  - L'intervention toiture est reportée alors que le rooftop goutte : maintenance confirme sur place. au rooftop, une goutte tombe près de la prise.
- Tâches principales : aucune

### signal:347 — Le partenaire du rooftop n'a pas confirmé samedi

- Date : 2026-02-14 17:00:00+01:00
- Lieu : rooftop
- Auteur : communication
- Responsable : communication
- Signal : signal:347
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Rooftop et piscine
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le partenaire du rooftop n'a pas confirmé samedi, au rooftop, le créneau musique est encore vide.
  - Le partenaire du rooftop n'a pas confirmé samedi : l'accueil événement le voit aussi. au rooftop, le créneau musique est encore vide.
- Tâches principales : aucune

### signal:357 — Les sous-titres de la vidéo rooftop sont ceux d'une autre ville

- Date : 2026-02-19 07:00:00+01:00
- Lieu : rooftop
- Auteur : communication
- Responsable : communication
- Signal : signal:357
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Rooftop et piscine
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les sous-titres de la vidéo rooftop sont ceux d'une autre ville, au rooftop, le texte parle d'une adresse qui n'est pas Nice.
  - Les sous-titres de la vidéo rooftop sont ceux d'une autre ville : le brief de shift retombe sur le même écart. au rooftop, le texte parle d'une adresse qui n'est pas Nice.
- Tâches principales : aucune

## Maintenance

### signal:borne-2 — La borne 2 ne démarre plus la charge

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
  - La borne 2 du parking ne démarre plus la charge, un badge clignote rouge.
- Tâches principales : aucune

### signal:interesting-wifi-4e — Le wifi du 4e a décroché dix minutes, sans nouvel incident

- Date : 2026-09-08 19:05:00+02:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:interesting-wifi-4e
- Statut : interesting
- Famille : Incident opérationnel
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le wifi du 4e a décroché dix minutes en chambre, plus aucun retour depuis.
- Tâches principales : aucune

### signal:261 — La clim de la chambre 104 ne refroidit plus

- Date : 2026-01-06 07:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:261
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : aucun
- Exécution : aucun
- Observations :
  - La clim de la chambre 104 ne refroidit plus, en chambre 104, l'air sort tiède malgré la consigne. Chacun a une partie de la climatisation au chambres, personne n'a clôturé.
- Tâches principales : aucune

### signal:262 — L'applique de la chambre 111 reste éteinte

- Date : 2026-01-06 18:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:262
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : pattern:eclairage — Défauts d'éclairage dans les chambres et circulations
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'applique de la chambre 111 reste éteinte, en chambre 111, le mur du lit reste noir. Le pôle auteur et le responsable ne sont pas alignés sur l'éclairage au chambres.
- Tâches principales : aucune

### signal:263 — Le siphon de la chambre 121 fuit sous le lavabo

- Date : 2026-01-07 05:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:263
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : pattern:fuites — Petites fuites sanitaires récurrentes
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le siphon de la chambre 121 fuit sous le lavabo, en chambre 121, le meuble est mouillé. la fuite au chambres demande encore un arbitrage entre les deux pôles.
- Tâches principales : aucune

### signal:264 — La poignée de la chambre 125 tourne dans le vide

- Date : 2026-01-07 16:00:00+01:00
- Lieu : chambres
- Auteur : communication
- Responsable : maintenance
- Signal : signal:264
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La poignée de la chambre 125 tourne dans le vide, en chambre 125, il faut tirer la porte pour fermer. Chacun a une partie de la poignée au chambres, personne n'a clôturé.
- Tâches principales : aucune

### signal:265 — L'unité de clim de la chambre 402 ne démarre plus

- Date : 2026-01-08 03:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:265
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'unité de clim de la chambre 402 ne démarre plus, en chambre 402, aucun souffle ne sort. Le pôle auteur et le responsable ne sont pas alignés sur la climatisation au chambres.
- Tâches principales : aucune

### signal:266 — Le wifi de la chambre 129 ne dépasse pas une barre

- Date : 2026-01-08 14:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:266
- Statut : resolved
- Famille : Qualité de service
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le wifi de la chambre 129 ne dépasse pas une barre, en chambre 129, la visio coupe sans arrêt. Prestation le wifi au chambres : le standard du brief n'est pas tenu.
- Tâches principales : aucune

### signal:267 — L'alarme de la porte de service du parking sonne sans ouverture

- Date : 2026-01-09 01:00:00+01:00
- Lieu : parking
- Auteur : communication
- Responsable : maintenance
- Signal : signal:267
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'alarme de la porte de service du parking sonne sans ouverture, au parking, la sirène repart toute seule. Chacun a une partie de l'alarme au parking, personne n'a clôturé.
- Tâches principales : aucune

### signal:268 — La borne 5 n'a plus de badge invité en réserve

- Date : 2026-01-09 12:00:00+01:00
- Lieu : bornes_electriques
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:268
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : pattern:bornes — Indisponibilité des bornes électriques
- Plan : aucun
- Exécution : aucun
- Observations :
  - La borne 5 n'a plus de badge invité en réserve, sur la borne 5, on ne peut plus dépanner un client. Le pôle auteur et le responsable ne sont pas alignés sur la borne au bornes electriques.
- Tâches principales : aucune

### signal:269 — La ronde d'ouverture a trouvé le local technique déverrouillé

- Date : 2026-01-09 23:00:00+01:00
- Lieu : locaux_techniques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:269
- Statut : resolved
- Famille : Prévention
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La ronde d'ouverture a trouvé le local technique déverrouillé, au local technique, la porte n'était pas condamnée.
- Tâches principales : aucune

### signal:270 — Le prestataire CVC n'est pas venu pour la chambre annoncée

- Date : 2026-01-10 10:00:00+01:00
- Lieu : chambres
- Auteur : communication
- Responsable : maintenance
- Signal : signal:270
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le prestataire CVC n'est pas venu pour la chambre annoncée, en chambre 280, personne n'est passé sur le créneau. Chacun a une partie de le prestataire au chambres, personne n'a clôturé.
- Tâches principales : aucune

### signal:271 — La clim de la chambre 116 souffle chaud

- Date : 2026-01-10 21:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:271
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : aucun
- Exécution : aucun
- Observations :
  - La clim de la chambre 116 souffle chaud, en chambre 116, le client a ouvert la fenêtre. Le pôle auteur et le responsable ne sont pas alignés sur la climatisation au chambres.
- Tâches principales : aucune

### signal:272 — Le plafonnier du couloir des chambres clignote

- Date : 2026-01-11 08:00:00+01:00
- Lieu : circulations_chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:272
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : pattern:eclairage — Défauts d'éclairage dans les chambres et circulations
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le plafonnier du couloir des chambres clignote, dans le couloir, la lumière saute toutes les secondes. l'éclairage au circulations chambres demande encore un arbitrage entre les deux pôles.
- Tâches principales : aucune

### signal:273 — La chasse de la chambre 158 goutte en continu

- Date : 2026-01-11 19:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:273
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : pattern:fuites — Petites fuites sanitaires récurrentes
- Plan : aucun
- Exécution : aucun
- Observations :
  - La chasse de la chambre 158 goutte en continu, en chambre 158, on entend l'eau toute la nuit. Chacun a une partie de la chasse au chambres, personne n'a clôturé.
- Tâches principales : aucune

### signal:274 — Une plinthe est décollée dans le couloir des chambres

- Date : 2026-01-12 06:00:00+01:00
- Lieu : circulations_chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:274
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une plinthe est décollée dans le couloir des chambres, dans le couloir, on voit le jour sous la plinthe. Le pôle auteur et le responsable ne sont pas alignés sur la plinthe au circulations chambres.
- Tâches principales : aucune

### signal:275 — Le ventilateur de clim en chambre 418 vibre

- Date : 2026-01-12 17:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:275
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le ventilateur de clim en chambre 418 vibre, en chambre 418, le meuble tremble quand la clim tourne. la climatisation au chambres demande encore un arbitrage entre les deux pôles.
- Tâches principales : aucune

### signal:276 — La borne wifi du couloir des chambres est éteinte

- Date : 2026-01-13 04:00:00+01:00
- Lieu : circulations_chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:276
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : pattern:bornes — Indisponibilité des bornes électriques
- Plan : aucun
- Exécution : aucun
- Observations :
  - La borne wifi du couloir des chambres est éteinte, dans le couloir, le boîtier n'a plus de voyant. Chacun a une partie de le wifi au circulations chambres, personne n'a clôturé.
- Tâches principales : aucune

### signal:277 — Un extincteur du couloir des chambres est décroché

- Date : 2026-01-13 15:00:00+01:00
- Lieu : circulations_chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:277
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un extincteur du couloir des chambres est décroché, dans le couloir, il est posé au sol. Le pôle auteur et le responsable ne sont pas alignés sur l'extincteur au circulations chambres.
- Tâches principales : aucune

### signal:278 — Les ampoules de rechange manquent au local technique

- Date : 2026-01-14 02:00:00+01:00
- Lieu : locaux_techniques
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:278
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : pattern:eclairage — Défauts d'éclairage dans les chambres et circulations
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les ampoules de rechange manquent au local technique, au local technique, le bac ampoules est vide. les ampoules au locaux techniques demande encore un arbitrage entre les deux pôles.
- Tâches principales : aucune

### signal:279 — Le parking n'était pas éclairé à la ronde de 6 h

- Date : 2026-01-14 13:00:00+01:00
- Lieu : parking
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:279
- Statut : resolved
- Famille : Prévention
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le parking n'était pas éclairé à la ronde de 6 h, au parking, les rampes étaient noires.
- Tâches principales : aucune

### signal:280 — Le prestataire ascenseur a décalé sans prévenir le lobby

- Date : 2026-01-15 00:00:00+01:00
- Lieu : reception_lobby
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:280
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le prestataire ascenseur a décalé sans prévenir le lobby, au lobby, les clients attendent un ascenseur toujours arrêté. Le pôle auteur et le responsable ne sont pas alignés sur le prestataire au reception lobby.
- Tâches principales : aucune

### signal:281 — Le split de la chambre 132 s'arrête tout seul

- Date : 2026-01-15 11:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:281
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le split de la chambre 132 s'arrête tout seul, en chambre 132, la clim repart puis coupe au bout de dix minutes. la climatisation au chambres demande encore un arbitrage entre les deux pôles.
- Tâches principales : aucune

### signal:282 — La lampe de bureau de la chambre 230 est grillée

- Date : 2026-01-15 22:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:282
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : pattern:eclairage — Défauts d'éclairage dans les chambres et circulations
- Plan : aucun
- Exécution : aucun
- Observations :
  - La lampe de bureau de la chambre 230 est grillée, en chambre 230, l'ampoule ne réagit plus. Chacun a une partie de l'éclairage au chambres, personne n'a clôturé.
- Tâches principales : aucune

### signal:283 — Un joint de douche fuit dans la chambre 233

- Date : 2026-01-16 09:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:283
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : pattern:fuites — Petites fuites sanitaires récurrentes
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un joint de douche fuit dans la chambre 233, en chambre 233, l'eau passe sur le carrelage. Le pôle auteur et le responsable ne sont pas alignés sur la fuite au chambres.
- Tâches principales : aucune

### signal:284 — Le joint de silicone est noirci autour de la baignoire de la chambre 240

- Date : 2026-01-16 20:00:00+01:00
- Lieu : chambres
- Auteur : restaurant
- Responsable : maintenance
- Signal : signal:284
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le joint de silicone est noirci autour de la baignoire de la chambre 240, en chambre 240, le joint part en miettes. le joint au chambres demande encore un arbitrage entre les deux pôles.
- Tâches principales : aucune

### signal:285 — La clim de la chambre 431 se coupe au bout de dix minutes

- Date : 2026-01-17 07:00:00+01:00
- Lieu : chambres
- Auteur : hotel
- Responsable : maintenance
- Signal : signal:285
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : Maintenance
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : aucun
- Exécution : aucun
- Observations :
  - La clim de la chambre 431 se coupe au bout de dix minutes, en chambre 431, il faut la relancer sans cesse. Chacun a une partie de la climatisation au chambres, personne n'a clôturé.
- Tâches principales : aucune

### signal:286 — Le réseau du back-office coupe toutes les cinq minutes

- Date : 2026-01-17 18:00:00+01:00
- Lieu : back_office_administratif
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:286
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le réseau du back-office coupe toutes les cinq minutes, au back-office, les dossiers se ferment tout seuls. Le client le vit au back office administratif autour de le réseau.
- Tâches principales : aucune

### signal:287 — Le bloc de secours du couloir des chambres ne passe pas au test

- Date : 2026-01-18 05:00:00+01:00
- Lieu : circulations_chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:287
- Statut : resolved
- Famille : Prévention
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le bloc de secours du couloir des chambres ne passe pas au test, au couloir, la led reste éteinte pendant le test. Ronde de janvier au circulations chambres : le bloc de secours relevé avant qu'un client le voie.
- Tâches principales : aucune

### signal:288 — Il n'y a plus de joints siphon dans le stock du local technique

- Date : 2026-01-18 16:00:00+01:00
- Lieu : locaux_techniques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:288
- Statut : resolved
- Famille : Qualité de service
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Il n'y a plus de joints siphon dans le stock du local technique, au local technique, la boîte est vide. Au locaux techniques, les joints allonge le service plus que la jauge prévue.
- Tâches principales : aucune

### signal:289 — Une fenêtre du local technique est restée ouverte toute la nuit

- Date : 2026-01-19 03:00:00+01:00
- Lieu : locaux_techniques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:289
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une fenêtre du local technique est restée ouverte toute la nuit, au local technique, le bureau était froid à l'ouverture. Le client le vit au locaux techniques autour de la fenêtre.
- Tâches principales : aucune

### signal:290 — Le contrat vitrerie n'a pas traité les traces du lobby

- Date : 2026-01-19 14:00:00+01:00
- Lieu : reception_lobby
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:290
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le contrat vitrerie n'a pas traité les traces du lobby, au lobby, les vitres sont telles qu'hier.
- Tâches principales : aucune

### signal:291 — La clim de la chambre 148 fait un bruit de roulement

- Date : 2026-01-20 01:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:291
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : aucun
- Exécution : aucun
- Observations :
  - La clim de la chambre 148 fait un bruit de roulement, en chambre 148, le bruit empêche de dormir.
- Tâches principales : aucune

### signal:292 — L'éclairage du parking reste allumé en plein jour

- Date : 2026-01-20 12:00:00+01:00
- Lieu : parking
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:292
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : pattern:eclairage — Défauts d'éclairage dans les chambres et circulations
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'éclairage du parking reste allumé en plein jour, au parking, les réglettes ne s'éteignent plus. Le client le vit au parking autour de l'éclairage.
- Tâches principales : aucune

### signal:293 — Le robinet de la chambre 248 suinte sur le meuble

- Date : 2026-01-20 23:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:293
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : pattern:fuites — Petites fuites sanitaires récurrentes
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le robinet de la chambre 248 suinte sur le meuble, en chambre 248, le bois gonfle déjà.
- Tâches principales : aucune

### signal:294 — Une dalle du local technique sonne creux

- Date : 2026-01-21 10:00:00+01:00
- Lieu : locaux_techniques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:294
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une dalle du local technique sonne creux, au local technique, le carreau bouge sous le pied. À l'accueil on entend encore la dalle pour le locaux techniques.
- Tâches principales : aucune

### signal:295 — L'air de la chambre 455 reste chaud malgré la clim

- Date : 2026-01-21 21:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:295
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'air de la chambre 455 reste chaud malgré la clim, en chambre 455, la consigne à 21 ne change rien.
- Tâches principales : aucune

### signal:296 — L'imprimante de la réception ne voit plus le réseau

- Date : 2026-01-22 08:00:00+01:00
- Lieu : reception_lobby
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:296
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'imprimante de la réception ne voit plus le réseau, à la réception, les confirmations ne s'impriment plus. Séjour impacté au reception lobby : le réseau reste le point d'irritation.
- Tâches principales : aucune

### signal:297 — La caméra du lobby est floue depuis hier

- Date : 2026-01-22 19:00:00+01:00
- Lieu : reception_lobby
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:297
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La caméra du lobby est floue depuis hier, au lobby, on ne distingue plus le comptoir.
- Tâches principales : aucune

### signal:298 — Les piles des télécommandes sont vides au local technique

- Date : 2026-01-23 06:00:00+01:00
- Lieu : locaux_techniques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:298
- Statut : resolved
- Famille : Qualité de service
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les piles des télécommandes sont vides au local technique, au local technique, aucune pile neuve pour les chambres.
- Tâches principales : aucune

### signal:300 — Un technicien borne est passé sans laisser de bon au local technique

- Date : 2026-01-24 04:00:00+01:00
- Lieu : locaux_techniques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:300
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : pattern:bornes — Indisponibilité des bornes électriques
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un technicien borne est passé sans laisser de bon au local technique, au local technique, aucune fiche n'a été déposée.
  - Un technicien borne est passé sans laisser de bon au local technique : le client vient de le redire au lobby. au local technique, aucune fiche n'a été déposée. À l'accueil on entend encore le prestataire pour le locaux techniques.
- Tâches principales : aucune

### signal:301 — La télécommande clim de la chambre 163 ne change plus la température

- Date : 2026-01-24 15:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:301
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : aucun
- Exécution : aucun
- Observations :
  - La télécommande clim de la chambre 163 ne change plus la température, en chambre 163, l'écran de la télécommande reste figé.
  - La télécommande clim de la chambre 163 ne change plus la température : le brief de shift retombe sur le même écart. en chambre 163, l'écran de la télécommande reste figé.
- Tâches principales : aucune

### signal:302 — La réglette du local technique ne s'allume plus

- Date : 2026-01-25 02:00:00+01:00
- Lieu : locaux_techniques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:302
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : pattern:eclairage — Défauts d'éclairage dans les chambres et circulations
- Plan : aucun
- Exécution : aucun
- Observations :
  - La réglette du local technique ne s'allume plus, au local technique, on travaille à la lampe torche.
  - La réglette du local technique ne s'allume plus : le responsable de zone vient de le valider. au local technique, on travaille à la lampe torche. Séjour impacté au locaux techniques : l'éclairage reste le point d'irritation.
- Tâches principales : aucune

### signal:303 — Une fuite apparaît au plafond de la chambre 265

- Date : 2026-01-25 13:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:303
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : pattern:fuites — Petites fuites sanitaires récurrentes
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une fuite apparaît au plafond de la chambre 265, en chambre 265, la tache est au-dessus du lit.
  - Une fuite apparaît au plafond de la chambre 265 : je le vois aussi au passage d'étage. en chambre 265, la tache est au-dessus du lit.
- Tâches principales : aucune

### signal:304 — La porte de service vers le parking ferme mal

- Date : 2026-01-26 00:00:00+01:00
- Lieu : parking
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:304
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La porte de service vers le parking ferme mal, au parking, la porte reste entrebâillée.
  - La porte de service vers le parking ferme mal : la réception a la même info à l'instant. au parking, la porte reste entrebâillée. Le client le vit au parking autour de la porte.
- Tâches principales : aucune

### signal:305 — La borne 2 du parking ne lance plus la charge

- Date : 2026-01-26 11:00:00+01:00
- Lieu : bornes_electriques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:305
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : pattern:bornes — Indisponibilité des bornes électriques
- Plan : aucun
- Exécution : aucun
- Observations :
  - La borne 2 du parking ne lance plus la charge, sur la borne 2, le câble est branché et rien ne démarre.
  - La borne 2 du parking ne lance plus la charge : cuisine et salle ont le même constat. sur la borne 2, le câble est branché et rien ne démarre. Séjour impacté au bornes electriques : la borne reste le point d'irritation.
- Tâches principales : aucune

### signal:306 — Le terminal du bar n'a plus de réseau

- Date : 2026-01-26 22:00:00+01:00
- Lieu : bar_central
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:306
- Statut : resolved
- Famille : Qualité de service
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le terminal du bar n'a plus de réseau, au bar, les paiements reviennent en erreur.
  - Le terminal du bar n'a plus de réseau : maintenance confirme sur place. au bar, les paiements reviennent en erreur. Au bar central, le réseau allonge le service plus que la jauge prévue.
- Tâches principales : aucune

### signal:308 — Le stock de filtres du local technique est à zéro

- Date : 2026-01-27 20:00:00+01:00
- Lieu : locaux_techniques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:308
- Statut : resolved
- Famille : Qualité de service
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le stock de filtres du local technique est à zéro, au local technique, la dernière étagère est vide.
  - Le stock de filtres du local technique est à zéro : le client vient de le redire au lobby. au local technique, la dernière étagère est vide. Prestation les filtres au locaux techniques : le standard du brief n'est pas tenu.
- Tâches principales : aucune

### signal:309 — La borne 1 était hors service dès la première ronde

- Date : 2026-01-28 07:00:00+01:00
- Lieu : bornes_electriques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:309
- Statut : resolved
- Famille : Prévention
- Activité : Maintenance
- Pattern : pattern:bornes — Indisponibilité des bornes électriques
- Plan : aucun
- Exécution : aucun
- Observations :
  - La borne 1 était hors service dès la première ronde, sur la borne 1, l'écran était déjà en défaut à 6 h.
  - La borne 1 était hors service dès la première ronde : le brief de shift retombe sur le même écart. sur la borne 1, l'écran était déjà en défaut à 6 h.
- Tâches principales : aucune

### signal:310 — Le prestataire sécurité n'a pas fait la levée de doute promise au lobby

- Date : 2026-01-28 18:00:00+01:00
- Lieu : reception_lobby
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:310
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le prestataire sécurité n'a pas fait la levée de doute promise au lobby, au lobby, l'alarme est retombée sans visite.
  - Le prestataire sécurité n'a pas fait la levée de doute promise au lobby : le responsable de zone vient de le valider. au lobby, l'alarme est retombée sans visite.
- Tâches principales : aucune

### signal:311 — La clim de la chambre 175 goutte sur le parquet

- Date : 2026-01-29 05:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:311
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : aucun
- Exécution : aucun
- Observations :
  - La clim de la chambre 175 goutte sur le parquet, en chambre 175, une flaque est sous l'unité.
  - La clim de la chambre 175 goutte sur le parquet : je le vois aussi au passage d'étage. en chambre 175, une flaque est sous l'unité.
- Tâches principales : aucune

### signal:312 — Le spot de la salle de bain en chambre 255 est mort

- Date : 2026-01-29 16:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:312
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : pattern:eclairage — Défauts d'éclairage dans les chambres et circulations
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le spot de la salle de bain en chambre 255 est mort, en chambre 255, le miroir est dans le noir.
  - Le spot de la salle de bain en chambre 255 est mort : la réception a la même info à l'instant. en chambre 255, le miroir est dans le noir.
- Tâches principales : aucune

### signal:313 — Le flexible de douche de la chambre 301 fuit à la connexion

- Date : 2026-01-30 03:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:313
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le flexible de douche de la chambre 301 fuit à la connexion, en chambre 301, l'eau coule le long du flexible.
  - Le flexible de douche de la chambre 301 fuit à la connexion : cuisine et salle ont le même constat. en chambre 301, l'eau coule le long du flexible.
- Tâches principales : aucune

### signal:314 — Un carreau est fêlé dans la douche de la chambre 275

- Date : 2026-01-30 14:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:314
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un carreau est fêlé dans la douche de la chambre 275, en chambre 275, la fissure part du siphon.
  - Un carreau est fêlé dans la douche de la chambre 275 : maintenance confirme sur place. en chambre 275, la fissure part du siphon.
- Tâches principales : aucune

### signal:315 — L'écran de la borne 4 reste noir

- Date : 2026-01-31 01:00:00+01:00
- Lieu : bornes_electriques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:315
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'écran de la borne 4 reste noir, sur la borne 4, aucun voyant ne s'allume.
  - L'écran de la borne 4 reste noir : l'accueil événement le voit aussi. sur la borne 4, aucun voyant ne s'allume. À l'accueil on entend encore la borne pour le bornes electriques.
- Tâches principales : aucune

### signal:317 — Le registre de sécurité du local technique n'est pas à jour

- Date : 2026-01-31 23:00:00+01:00
- Lieu : locaux_techniques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:317
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le registre de sécurité du local technique n'est pas à jour, au local technique, la dernière ligne date du mois dernier.
  - Le registre de sécurité du local technique n'est pas à jour : le brief de shift retombe sur le même écart. au local technique, la dernière ligne date du mois dernier. Séjour impacté au locaux techniques : le registre reste le point d'irritation.
- Tâches principales : aucune

### signal:318 — Les gants jetables manquent au local technique

- Date : 2026-02-01 10:00:00+01:00
- Lieu : locaux_techniques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:318
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les gants jetables manquent au local technique, au local technique, l'équipe n'a plus de boîte ouverte.
  - Les gants jetables manquent au local technique : le responsable de zone vient de le valider. au local technique, l'équipe n'a plus de boîte ouverte.
- Tâches principales : aucune

### signal:321 — L'air de la clim en chambre 188 est trop faible

- Date : 2026-02-02 19:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:321
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'air de la clim en chambre 188 est trop faible, en chambre 188, on sent à peine le souffle.
  - L'air de la clim en chambre 188 est trop faible : cuisine et salle ont le même constat. en chambre 188, on sent à peine le souffle.
- Tâches principales : aucune

### signal:322 — L'escalier vers les chambres est dans le noir sur un palier

- Date : 2026-02-03 06:00:00+01:00
- Lieu : circulations_chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:322
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : pattern:eclairage — Défauts d'éclairage dans les chambres et circulations
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'escalier vers les chambres est dans le noir sur un palier, dans l'escalier, le palier du 2e n'a plus de lumière.
  - L'escalier vers les chambres est dans le noir sur un palier : maintenance confirme sur place. dans l'escalier, le palier du 2e n'a plus de lumière.
- Tâches principales : aucune

### signal:323 — L'eau chaude met trois minutes à arriver en chambre 322

- Date : 2026-02-03 17:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:323
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'eau chaude met trois minutes à arriver en chambre 322, en chambre 322, le client laisse couler longtemps.
  - L'eau chaude met trois minutes à arriver en chambre 322 : l'accueil événement le voit aussi. en chambre 322, le client laisse couler longtemps.
- Tâches principales : aucune

### signal:324 — La peinture du palier des chambres s'écaille

- Date : 2026-02-04 04:00:00+01:00
- Lieu : circulations_chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:324
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La peinture du palier des chambres s'écaille, au palier, des écailles tombent au sol.
  - La peinture du palier des chambres s'écaille : le client vient de le redire au lobby. au palier, des écailles tombent au sol.
- Tâches principales : aucune

### signal:325 — La borne 1 affiche un défaut de terre

- Date : 2026-02-04 15:00:00+01:00
- Lieu : bornes_electriques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:325
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La borne 1 affiche un défaut de terre, sur la borne 1, le message reste affiché.
  - La borne 1 affiche un défaut de terre : le brief de shift retombe sur le même écart. sur la borne 1, le message reste affiché.
- Tâches principales : aucune

### signal:326 — Un switch du local technique a un voyant rouge

- Date : 2026-02-05 02:00:00+01:00
- Lieu : locaux_techniques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:326
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un switch du local technique a un voyant rouge, au local technique, le switch clignote en erreur.
  - Un switch du local technique a un voyant rouge : le responsable de zone vient de le valider. au local technique, le switch clignote en erreur.
- Tâches principales : aucune

### signal:327 — Un détecteur de la chambre 505 bippe par intermittence

- Date : 2026-02-05 13:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:327
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un détecteur de la chambre 505 bippe par intermittence, en chambre 505, le client a appelé deux fois cette nuit.
  - Un détecteur de la chambre 505 bippe par intermittence : je le vois aussi au passage d'étage. en chambre 505, le client a appelé deux fois cette nuit.
- Tâches principales : aucune

### signal:328 — Un colis prestataire attend depuis deux jours au local technique

- Date : 2026-02-06 00:00:00+01:00
- Lieu : locaux_techniques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:328
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un colis prestataire attend depuis deux jours au local technique, au local technique, le carton n'a pas été ouvert.
  - Un colis prestataire attend depuis deux jours au local technique : la réception a la même info à l'instant. au local technique, le carton n'a pas été ouvert.
- Tâches principales : aucune

### signal:329 — La porte du local technique côté poubelles n'était pas condamnée

- Date : 2026-02-06 11:00:00+01:00
- Lieu : locaux_techniques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:329
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La porte du local technique côté poubelles n'était pas condamnée, près du local technique, la porte battait.
  - La porte du local technique côté poubelles n'était pas condamnée : cuisine et salle ont le même constat. près du local technique, la porte battait.
- Tâches principales : aucune

### signal:331 — La clim de la chambre 196 sent le brûlé au démarrage

- Date : 2026-02-07 09:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:331
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : pattern:clim-chambres — Dysfonctionnements de climatisation dans les chambres
- Plan : aucun
- Exécution : aucun
- Observations :
  - La clim de la chambre 196 sent le brûlé au démarrage, en chambre 196, l'odeur arrive dès qu'on l'allume.
  - La clim de la chambre 196 sent le brûlé au démarrage : l'accueil événement le voit aussi. en chambre 196, l'odeur arrive dès qu'on l'allume.
- Tâches principales : aucune

### signal:332 — La lampe de chevet de la chambre 366 ne s'allume plus

- Date : 2026-02-07 20:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:332
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La lampe de chevet de la chambre 366 ne s'allume plus, en chambre 366, seul le plafonnier fonctionne.
  - La lampe de chevet de la chambre 366 ne s'allume plus : le client vient de le redire au lobby. en chambre 366, seul le plafonnier fonctionne.
- Tâches principales : aucune

### signal:333 — Le lavabo de la chambre 348 s'évacue très lentement

- Date : 2026-02-08 07:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:333
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le lavabo de la chambre 348 s'évacue très lentement, en chambre 348, l'eau stagne plusieurs minutes.
  - Le lavabo de la chambre 348 s'évacue très lentement : le brief de shift retombe sur le même écart. en chambre 348, l'eau stagne plusieurs minutes.
- Tâches principales : aucune

### signal:334 — Le seuil de la chambre 360 accroche et la porte racle

- Date : 2026-02-08 18:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:334
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le seuil de la chambre 360 accroche et la porte racle, en chambre 360, la porte ne ferme plus à fond.
  - Le seuil de la chambre 360 accroche et la porte racle : le responsable de zone vient de le valider. en chambre 360, la porte ne ferme plus à fond.
- Tâches principales : aucune

### signal:335 — Un câble de la borne 3 est bloqué dans la trappe

- Date : 2026-02-09 05:00:00+01:00
- Lieu : bornes_electriques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:335
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un câble de la borne 3 est bloqué dans la trappe, sur la borne 3, on ne peut plus le ranger.
  - Un câble de la borne 3 est bloqué dans la trappe : je le vois aussi au passage d'étage. sur la borne 3, on ne peut plus le ranger.
- Tâches principales : aucune

### signal:336 — La clé de la chambre 505 ne synchronise plus

- Date : 2026-02-09 16:00:00+01:00
- Lieu : chambres
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:336
- Statut : resolved
- Famille : Expérience client
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La clé de la chambre 505 ne synchronise plus, en chambre 505, la carte est refusée une fois sur deux.
  - La clé de la chambre 505 ne synchronise plus : la réception a la même info à l'instant. en chambre 505, la carte est refusée une fois sur deux.
- Tâches principales : aucune

### signal:337 — La barre anti-panique du parking accroche

- Date : 2026-02-10 03:00:00+01:00
- Lieu : parking
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:337
- Statut : resolved
- Famille : Qualité de service
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La barre anti-panique du parking accroche, au parking, il faut forcer pour ouvrir.
  - La barre anti-panique du parking accroche : cuisine et salle ont le même constat. au parking, il faut forcer pour ouvrir. L'écart sur la barre se voit encore au service du parking.
- Tâches principales : aucune

### signal:338 — Les étiquettes de consignation manquent au local technique

- Date : 2026-02-10 14:00:00+01:00
- Lieu : locaux_techniques
- Auteur : maintenance
- Responsable : maintenance
- Signal : signal:338
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Maintenance
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les étiquettes de consignation manquent au local technique, au local technique, on ne peut plus marquer un équipement arrêté.
  - Les étiquettes de consignation manquent au local technique : maintenance confirme sur place. au local technique, on ne peut plus marquer un équipement arrêté.
- Tâches principales : aucune

## Communication et avis

### signal:avis-attente-pdj — Trois avis de la semaine parlent de l'attente au petit-déjeuner

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
  - Trois avis de la semaine parlent de l'attente au petit-déjeuner, le back-office doit répondre.
- Tâches principales : aucune

### signal:interesting-brunch — Les avis citent le brunch du dimanche, piste d'offre avant Super Sunday

- Date : 2026-09-11 15:40:00+02:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:interesting-brunch
- Statut : interesting
- Famille : Opportunité
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les avis citent le brunch du dimanche, une offre à travailler au bureau avant Super Sunday.
- Tâches principales : aucune

### signal:339 — Un avis Google parle d'une attente au check-in sans réponse

- Date : 2026-02-11 01:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:339
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : pattern:avis-negatifs — Thèmes négatifs récurrents dans les avis clients
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un avis Google parle d'une attente au check-in sans réponse, au back-office, le commentaire est en ligne depuis hier.
  - Un avis Google parle d'une attente au check-in sans réponse : l'accueil événement le voit aussi. au back-office, le commentaire est en ligne depuis hier.
- Tâches principales : aucune

### signal:340 — Un avis décrit des draps tâchés et la réponse est vide

- Date : 2026-02-11 12:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:340
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : pattern:avis-negatifs — Thèmes négatifs récurrents dans les avis clients
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un avis décrit des draps tâchés et la réponse est vide, au back-office, le brouillon de réponse n'a pas été publié.
  - Un avis décrit des draps tâchés et la réponse est vide : le client vient de le redire au lobby. au back-office, le brouillon de réponse n'a pas été publié.
- Tâches principales : aucune

### signal:341 — La campagne locale ne distingue plus Nice des autres maisons

- Date : 2026-02-11 23:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:341
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La campagne locale ne distingue plus Nice des autres maisons, au back-office, le visuel pourrait être celui de Lyon.
  - La campagne locale ne distingue plus Nice des autres maisons : le brief de shift retombe sur le même écart. au back-office, le visuel pourrait être celui de Lyon.
- Tâches principales : aucune

### signal:342 — La communauté demande l'horaire piscine et la réponse auto est fausse

- Date : 2026-02-12 10:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:342
- Statut : resolved
- Famille : Expérience client
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La communauté demande l'horaire piscine et la réponse auto est fausse, au back-office, le message automatique dit piscine fermée le matin.
  - La communauté demande l'horaire piscine et la réponse auto est fausse : le responsable de zone vient de le valider. au back-office, le message automatique dit piscine fermée le matin. À l'accueil on entend encore la communauté pour le back office administratif.
- Tâches principales : aucune

### signal:343 — La newsletter annonce un tarif chambre que le site ne pratique plus

- Date : 2026-02-12 21:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:343
- Statut : resolved
- Famille : Expérience client
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La newsletter annonce un tarif chambre que le site ne pratique plus, au back-office, le tarif du mail est déjà périmé.
  - La newsletter annonce un tarif chambre que le site ne pratique plus : je le vois aussi au passage d'étage. au back-office, le tarif du mail est déjà périmé.
- Tâches principales : aucune

### signal:344 — Un client fidèle n'a pas eu de retour après un avis sur la clim

- Date : 2026-02-13 08:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:344
- Statut : canceled
- Famille : Expérience client
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Motif d'annulation : L'avis a été retiré par le client avant la réponse. Sujet : Un client fidèle n'a pas eu de retour après un avis sur la clim.
- Observations :
  - Un client fidèle n'a pas eu de retour après un avis sur la clim, au back-office, sa fiche n'a aucune relance.
  - Un client fidèle n'a pas eu de retour après un avis sur la clim : la réception a la même info à l'instant. au back-office, sa fiche n'a aucune relance. Séjour impacté au back office administratif : l'avis reste le point d'irritation.
- Tâches principales : aucune

### signal:345 — La vidéo du lobby en ligne montre l'ancien comptoir

- Date : 2026-02-13 19:00:00+01:00
- Lieu : reception_lobby
- Auteur : communication
- Responsable : communication
- Signal : signal:345
- Statut : resolved
- Famille : Expérience client
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La vidéo du lobby en ligne montre l'ancien comptoir, au lobby, le comptoir filmé n'est plus celui d'aujourd'hui.
  - La vidéo du lobby en ligne montre l'ancien comptoir : cuisine et salle ont le même constat. au lobby, le comptoir filmé n'est plus celui d'aujourd'hui.
- Tâches principales : aucune

### signal:346 — Les avis de la semaine reviennent sur l'attente au restaurant

- Date : 2026-02-14 06:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:346
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : pattern:avis-negatifs — Thèmes négatifs récurrents dans les avis clients
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les avis de la semaine reviennent sur l'attente au restaurant, au back-office, quatre notes citent la même attente.
  - Les avis de la semaine reviennent sur l'attente au restaurant : maintenance confirme sur place. au back-office, quatre notes citent la même attente.
- Tâches principales : aucune

### signal:348 — La page chambres du site affiche une superficie fausse

- Date : 2026-02-15 04:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:348
- Statut : resolved
- Famille : Expérience client
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La page chambres du site affiche une superficie fausse, au back-office, la fiche en ligne ne correspond pas au plan.
  - La page chambres du site affiche une superficie fausse : le client vient de le redire au lobby. au back-office, la fiche en ligne ne correspond pas au plan.
- Tâches principales : aucune

### signal:349 — L'office de tourisme a une fiche avec l'ancien numéro

- Date : 2026-02-15 15:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:349
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'office de tourisme a une fiche avec l'ancien numéro, au back-office, le numéro affiché ne sonne plus ici.
  - L'office de tourisme a une fiche avec l'ancien numéro : le brief de shift retombe sur le même écart. au back-office, le numéro affiché ne sonne plus ici.
- Tâches principales : aucune

### signal:350 — Le taux de réponse aux avis est tombé sous le seuil du lundi

- Date : 2026-02-16 02:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:350
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : pattern:avis-negatifs — Thèmes négatifs récurrents dans les avis clients
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le taux de réponse aux avis est tombé sous le seuil du lundi, au back-office, le tableau du lundi est dans le rouge.
  - Le taux de réponse aux avis est tombé sous le seuil du lundi : le responsable de zone vient de le valider. au back-office, le tableau du lundi est dans le rouge.
- Tâches principales : aucune

### signal:351 — Trois avis Instagram répètent le bruit dans les chambres

- Date : 2026-02-16 13:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:351
- Statut : resolved
- Famille : Expérience client
- Activité : Communication et avis
- Pattern : pattern:avis-negatifs — Thèmes négatifs récurrents dans les avis clients
- Plan : aucun
- Exécution : aucun
- Observations :
  - Trois avis Instagram répètent le bruit dans les chambres, au back-office, les trois messages disent la même chose.
  - Trois avis Instagram répètent le bruit dans les chambres : je le vois aussi au passage d'étage. au back-office, les trois messages disent la même chose.
- Tâches principales : aucune

### signal:352 — La photo de couverture montre un rooftop qui n'est plus meublé ainsi

- Date : 2026-02-17 00:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:352
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La photo de couverture montre un rooftop qui n'est plus meublé ainsi, au back-office, l'image en ligne date d'avant le réagencement.
  - La photo de couverture montre un rooftop qui n'est plus meublé ainsi : la réception a la même info à l'instant. au back-office, l'image en ligne date d'avant le réagencement.
- Tâches principales : aucune

### signal:353 — Une story montre le bar sans la mention prévue

- Date : 2026-02-17 11:00:00+01:00
- Lieu : bar_central
- Auteur : communication
- Responsable : communication
- Signal : signal:353
- Statut : resolved
- Famille : Qualité de service
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une story montre le bar sans la mention prévue, au bar, la publication est en ligne sans le partenariat.
  - Une story montre le bar sans la mention prévue : cuisine et salle ont le même constat. au bar, la publication est en ligne sans le partenariat. Prestation la story au bar central : le standard du brief n'est pas tenu.
- Tâches principales : aucune

### signal:354 — Un concours en story a promis un surclassement non validé

- Date : 2026-02-17 22:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:354
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un concours en story a promis un surclassement non validé, au back-office, le gagnant a déjà écrit pour sa chambre.
  - Un concours en story a promis un surclassement non validé : maintenance confirme sur place. au back-office, le gagnant a déjà écrit pour sa chambre.
- Tâches principales : aucune

### signal:355 — L'offre groupes envoyée hier cite un atelier déjà privatisé

- Date : 2026-02-18 09:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:355
- Statut : canceled
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Motif d'annulation : Le client a déplacé la date, la préparation n'a plus lieu. Sujet : L'offre groupes envoyée hier cite un atelier déjà privatisé.
- Observations :
  - L'offre groupes envoyée hier cite un atelier déjà privatisé, au back-office, l'atelier 1 est complet ce jour-là.
  - L'offre groupes envoyée hier cite un atelier déjà privatisé : l'accueil événement le voit aussi. au back-office, l'atelier 1 est complet ce jour-là.
- Tâches principales : aucune

### signal:356 — La base a envoyé un code expiré à un séjour en cours

- Date : 2026-02-18 20:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:356
- Statut : resolved
- Famille : Expérience client
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La base a envoyé un code expiré à un séjour en cours, au back-office, le client l'a montré à la réception ce matin.
  - La base a envoyé un code expiré à un séjour en cours : le client vient de le redire au lobby. au back-office, le client l'a montré à la réception ce matin.
- Tâches principales : aucune

### signal:358 — Un avis détaillé décrit une chambre non prête et il n'est pas traité

- Date : 2026-02-19 18:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:358
- Statut : resolved
- Famille : Expérience client
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un avis détaillé décrit une chambre non prête et il n'est pas traité, au back-office, il est en tête du tableau depuis deux jours.
  - Un avis détaillé décrit une chambre non prête et il n'est pas traité : le responsable de zone vient de le valider. au back-office, il est en tête du tableau depuis deux jours.
- Tâches principales : aucune

### signal:359 — Une collaboration café est annoncée alors que le produit n'est pas livré

- Date : 2026-02-20 05:00:00+01:00
- Lieu : bar_central
- Auteur : communication
- Responsable : communication
- Signal : signal:359
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une collaboration café est annoncée alors que le produit n'est pas livré, au bar, le café annoncé n'est pas en stock.
  - Une collaboration café est annoncée alors que le produit n'est pas livré : je le vois aussi au passage d'étage. au bar, le café annoncé n'est pas en stock.
- Tâches principales : aucune

### signal:360 — Le module de réservation du site bloque sur les dates de novembre

- Date : 2026-02-20 16:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:360
- Statut : canceled
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Motif d'annulation : Le client a déplacé la date, la préparation n'a plus lieu. Sujet : Le module de réservation du site bloque sur les dates de novembre.
- Observations :
  - Le module de réservation du site bloque sur les dates de novembre, au back-office, le test de réservation tourne sans fin.
  - Le module de réservation du site bloque sur les dates de novembre : la réception a la même info à l'instant. au back-office, le test de réservation tourne sans fin.
- Tâches principales : aucune

### signal:361 — Un article local cite un spa que l'hôtel n'a pas

- Date : 2026-02-21 03:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:361
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un article local cite un spa que l'hôtel n'a pas, au back-office, le papier est paru ce matin.
  - Un article local cite un spa que l'hôtel n'a pas : cuisine et salle ont le même constat. au back-office, le papier est paru ce matin.
- Tâches principales : aucune

### signal:362 — Les clics vers la réservation baissent depuis le nouveau visuel

- Date : 2026-02-21 14:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:362
- Statut : canceled
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Motif d'annulation : Le client a déplacé la date, la préparation n'a plus lieu. Sujet : Les clics vers la réservation baissent depuis le nouveau visuel.
- Observations :
  - Les clics vers la réservation baissent depuis le nouveau visuel, au back-office, la courbe descend depuis jeudi.
  - Les clics vers la réservation baissent depuis le nouveau visuel : maintenance confirme sur place. au back-office, la courbe descend depuis jeudi.
- Tâches principales : aucune

### signal:363 — Un avis récent cite le petit-déjeuner froid et personne n'a répondu

- Date : 2026-02-22 01:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:363
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un avis récent cite le petit-déjeuner froid et personne n'a répondu, au back-office, la notification est encore non lue.
  - Un avis récent cite le petit-déjeuner froid et personne n'a répondu : l'accueil événement le voit aussi. au back-office, la notification est encore non lue.
- Tâches principales : aucune

### signal:364 — Le ton des réponses aux avis est plus sec que la promesse de marque

- Date : 2026-02-22 12:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:364
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le ton des réponses aux avis est plus sec que la promesse de marque, au back-office, deux réponses publiées cette semaine sont sèches.
  - Le ton des réponses aux avis est plus sec que la promesse de marque : le client vient de le redire au lobby. au back-office, deux réponses publiées cette semaine sont sèches.
- Tâches principales : aucune

### signal:365 — Le lien de réservation de la story du jour est cassé

- Date : 2026-02-22 23:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:365
- Statut : canceled
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Motif d'annulation : Le client a déplacé la date, la préparation n'a plus lieu. Sujet : Le lien de réservation de la story du jour est cassé.
- Observations :
  - Le lien de réservation de la story du jour est cassé, au back-office, le clic tombe sur une page erreur.
  - Le lien de réservation de la story du jour est cassé : le brief de shift retombe sur le même écart. au back-office, le clic tombe sur une page erreur.
- Tâches principales : aucune

### signal:366 — Les messages privés sur une nuit bruyante restent sans réponse

- Date : 2026-02-23 10:00:00+01:00
- Lieu : back_office_administratif
- Auteur : communication
- Responsable : communication
- Signal : signal:366
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Communication et avis
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les messages privés sur une nuit bruyante restent sans réponse, au back-office, trois messages datent d'hier soir.
  - Les messages privés sur une nuit bruyante restent sans réponse : le responsable de zone vient de le valider. au back-office, trois messages datent d'hier soir.
- Tâches principales : aucune

## Ateliers et Studios

### signal:clickshare-atelier-2 — Le ClickShare de l'Atelier 2 ne détecte aucun écran

- Date : 2026-09-18 09:20:00+02:00
- Lieu : atelier_2
- Auteur : maintenance
- Responsable : evenements_privatisations
- Signal : signal:clickshare-atelier-2
- Statut : in_progress
- Famille : Coordination cross-pôles
- Activité : Ateliers et Studios
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : plan:preparation-evenement-dj — Préparation d'un événement DJ
- Exécution : exec:signal:signal:clickshare-atelier-2
- Observations :
  - Le ClickShare de l'Atelier 2 ne détecte aucun écran depuis ce matin.
  - Maintenance : HDMI et réseau testés, toujours pas d'image en Atelier 2.
  - L'accueil du séminaire a le même écran noir à l'ouverture de salle.
- Tâches principales :
  - Valider le run technique
  - Préparer scène et sono
  - Organiser bar et service
  - Publier et afficher la communication
  - Accueillir et clôturer

### signal:interesting-studios — Des sociétés demandent le Studio 1 pour des demi-journées

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
- Observations :
  - Des sociétés demandent le Studio 1 pour des demi-journées, pas seulement les Ateliers.
- Tâches principales : aucune

### signal:interesting-clickshare-atelier-1 — Le ClickShare de l'Atelier 1 a clignoté, sans nouvel incident

- Date : 2026-09-08 10:35:00+02:00
- Lieu : atelier_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:interesting-clickshare-atelier-1
- Statut : interesting
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le ClickShare de l'Atelier 1 a clignoté une fois pendant un test. Aucun nouvel incident depuis.
- Tâches principales : aucune

### signal:367 — Le ClickShare de l'atelier 2 ne détecte plus l'ordinateur

- Date : 2026-09-17 00:00:00+02:00
- Lieu : atelier_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:367
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le ClickShare de l'atelier 2 ne détecte plus l'ordinateur, à l'atelier 2, le client a déjà essayé deux ordinateurs.
  - Le ClickShare de l'atelier 2 ne détecte plus l'ordinateur : je le vois aussi au passage d'étage. à l'atelier 2, le client a déjà essayé deux ordinateurs.
- Tâches principales : aucune

### signal:368 — Le retour écran de l'atelier 2 a dix secondes de décalage

- Date : 2026-02-24 08:00:00+01:00
- Lieu : atelier_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:368
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le retour écran de l'atelier 2 a dix secondes de décalage, à l'atelier 2, la voix et l'image ne vont plus ensemble.
  - Le retour écran de l'atelier 2 a dix secondes de décalage : la réception a la même info à l'instant. à l'atelier 2, la voix et l'image ne vont plus ensemble.
- Tâches principales : aucune

### signal:369 — Les flèches vers l'atelier 1 ont été retirées trop tôt

- Date : 2026-02-24 19:00:00+01:00
- Lieu : atelier_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:369
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : pattern:signaletique-event — Défauts de signalétique événementielle
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les flèches vers l'atelier 1 ont été retirées trop tôt, vers l'atelier 1, les invités demandent leur chemin au lobby.
  - Les flèches vers l'atelier 1 ont été retirées trop tôt : cuisine et salle ont le même constat. vers l'atelier 1, les invités demandent leur chemin au lobby.
- Tâches principales : aucune

### signal:371 — La plaque Studio 2 est encore celle du brief de mai

- Date : 2026-02-25 17:00:00+01:00
- Lieu : atelier_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:371
- Statut : resolved
- Famille : Inefficacité de processus
- Activité : Ateliers et Studios
- Pattern : pattern:signaletique-event — Défauts de signalétique événementielle
- Plan : aucun
- Exécution : aucun
- Observations :
  - La plaque Studio 2 est encore celle du brief de mai, sur la porte Studio 2 le titre de mai est resté. atelier 2.
  - La plaque Studio 2 est encore celle du brief de mai : l'accueil événement le voit aussi. sur la porte Studio 2 le titre de mai est resté.
- Tâches principales : aucune

### signal:372 — L'acompte de l'atelier 1 n'apparaît pas sur la fiche client

- Date : 2026-02-26 04:00:00+01:00
- Lieu : atelier_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:372
- Statut : resolved
- Famille : Expérience client
- Activité : Ateliers et Studios
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'acompte de l'atelier 1 n'apparaît pas sur la fiche client, à l'atelier 1, la comptabilité ne voit pas le virement.
  - L'acompte de l'atelier 1 n'apparaît pas sur la fiche client : le client vient de le redire au lobby. à l'atelier 1, la comptabilité ne voit pas le virement.
- Tâches principales : aucune

### signal:373 — L'écran de l'atelier 1 reste noir à dix minutes du brief

- Date : 2026-02-26 15:00:00+01:00
- Lieu : atelier_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:373
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'écran de l'atelier 1 reste noir à dix minutes du brief, à l'atelier 1, le client est déjà assis.
  - L'écran de l'atelier 1 reste noir à dix minutes du brief : le brief de shift retombe sur le même écart. à l'atelier 1, le client est déjà assis.
- Tâches principales : aucune

### signal:374 — Personne n'entend le distant dans l'atelier 1, le micro est muet

- Date : 2026-02-27 02:00:00+01:00
- Lieu : atelier_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:374
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : aucun
- Exécution : aucun
- Observations :
  - Personne n'entend le distant dans l'atelier 1, le micro est muet, à l'atelier 1, la visio est ouverte sans son.
  - Personne n'entend le distant dans l'atelier 1, le micro est muet : le responsable de zone vient de le valider. à l'atelier 1, la visio est ouverte sans son.
- Tâches principales : aucune

### signal:375 — Le chevalet d'accueil cite le mauvais nom pour l'atelier 2

- Date : 2026-02-27 13:00:00+01:00
- Lieu : atelier_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:375
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : pattern:signaletique-event — Défauts de signalétique événementielle
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le chevalet d'accueil cite le mauvais nom pour l'atelier 2, à l'atelier 2, la société ne se reconnaît pas.
  - Le chevalet d'accueil cite le mauvais nom pour l'atelier 2 : je le vois aussi au passage d'étage. à l'atelier 2, la société ne se reconnaît pas.
- Tâches principales : aucune

### signal:376 — Une option rooftop vendue avec le studio 2 n'est pas sur la fiche

- Date : 2026-02-28 00:00:00+01:00
- Lieu : studio_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:376
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une option rooftop vendue avec le studio 2 n'est pas sur la fiche, au studio 2, le rooftop n'est pas préparé.
  - Une option rooftop vendue avec le studio 2 n'est pas sur la fiche : la réception a la même info à l'instant. au studio 2, le rooftop n'est pas préparé.
- Tâches principales : aucune

### signal:377 — Il manque un technicien son sur le studio 1 demain

- Date : 2026-02-28 11:00:00+01:00
- Lieu : studio_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:377
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Il manque un technicien son sur le studio 1 demain, au studio 1, le créneau technique est vide.
  - Il manque un technicien son sur le studio 1 demain : cuisine et salle ont le même constat. au studio 1, le créneau technique est vide.
- Tâches principales : aucune

### signal:378 — Des bouteilles du studio 2 ont été facturées en double

- Date : 2026-02-28 22:00:00+01:00
- Lieu : studio_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:378
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Des bouteilles du studio 2 ont été facturées en double, au studio 2, le client a comparé avec le bon de sortie.
  - Des bouteilles du studio 2 ont été facturées en double : maintenance confirme sur place. au studio 2, le client a comparé avec le bon de sortie.
- Tâches principales : aucune

### signal:379 — Le micro de l'atelier 2 grésille dès qu'on monte le son

- Date : 2026-03-01 09:00:00+01:00
- Lieu : atelier_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:379
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le micro de l'atelier 2 grésille dès qu'on monte le son, à l'atelier 2, la voix devient inaudible.
  - Le micro de l'atelier 2 grésille dès qu'on monte le son : l'accueil événement le voit aussi. à l'atelier 2, la voix devient inaudible.
- Tâches principales : aucune

### signal:380 — Le ClickShare de l'atelier 1 affiche un code qui ne marche pas

- Date : 2026-03-01 20:00:00+01:00
- Lieu : atelier_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:380
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le ClickShare de l'atelier 1 affiche un code qui ne marche pas, à l'atelier 1, le code à l'écran est refusé.
  - Le ClickShare de l'atelier 1 affiche un code qui ne marche pas : le client vient de le redire au lobby. à l'atelier 1, le code à l'écran est refusé.
- Tâches principales : aucune

### signal:381 — La signalétique du studio 1 pointe vers le breakroom

- Date : 2026-03-02 07:00:00+01:00
- Lieu : studio_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:381
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : pattern:signaletique-event — Défauts de signalétique événementielle
- Plan : aucun
- Exécution : aucun
- Observations :
  - La signalétique du studio 1 pointe vers le breakroom, au studio 1, un groupe est parti du mauvais côté.
  - La signalétique du studio 1 pointe vers le breakroom : le brief de shift retombe sur le même écart. au studio 1, un groupe est parti du mauvais côté.
- Tâches principales : aucune

### signal:382 — Le nom du client sur le contrat de l'atelier 2 est inexact

- Date : 2026-03-02 18:00:00+01:00
- Lieu : atelier_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:382
- Statut : resolved
- Famille : Expérience client
- Activité : Ateliers et Studios
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le nom du client sur le contrat de l'atelier 2 est inexact, à l'atelier 2, la raison sociale ne correspond pas.
  - Le nom du client sur le contrat de l'atelier 2 est inexact : le responsable de zone vient de le valider. à l'atelier 2, la raison sociale ne correspond pas.
- Tâches principales : aucune

### signal:383 — La pause équipe de l'atelier 1 tombe pendant le discours

- Date : 2026-03-03 05:00:00+01:00
- Lieu : atelier_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:383
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La pause équipe de l'atelier 1 tombe pendant le discours, à l'atelier 1, la salle serait sans personne à ce moment-là.
  - La pause équipe de l'atelier 1 tombe pendant le discours : je le vois aussi au passage d'étage. à l'atelier 1, la salle serait sans personne à ce moment-là.
- Tâches principales : aucune

### signal:385 — Le wifi invité de l'atelier 1 coupe pendant la visio

- Date : 2026-03-04 03:00:00+01:00
- Lieu : atelier_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:385
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le wifi invité de l'atelier 1 coupe pendant la visio, à l'atelier 1, l'appel saute toutes les minutes.
  - Le wifi invité de l'atelier 1 coupe pendant la visio : cuisine et salle ont le même constat. à l'atelier 1, l'appel saute toutes les minutes.
- Tâches principales : aucune

### signal:386 — La sono du studio 2 sature sur la voix du présentateur

- Date : 2026-03-04 14:00:00+01:00
- Lieu : studio_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:386
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : aucun
- Exécution : aucun
- Observations :
  - La sono du studio 2 sature sur la voix du présentateur, au studio 2, les premières rangées se bouchent les oreilles.
  - La sono du studio 2 sature sur la voix du présentateur : maintenance confirme sur place. au studio 2, les premières rangées se bouchent les oreilles.
- Tâches principales : aucune

### signal:387 — Les badges invités de l'atelier 2 n'ont pas le bon logo

- Date : 2026-03-05 01:00:00+01:00
- Lieu : atelier_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:387
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : pattern:signaletique-event — Défauts de signalétique événementielle
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les badges invités de l'atelier 2 n'ont pas le bon logo, à l'atelier 2, le client l'a remarqué à l'accueil.
  - Les badges invités de l'atelier 2 n'ont pas le bon logo : l'accueil événement le voit aussi. à l'atelier 2, le client l'a remarqué à l'accueil.
- Tâches principales : aucune

### signal:388 — La salle du studio 1 est proposée en même temps à deux options

- Date : 2026-03-05 12:00:00+01:00
- Lieu : studio_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:388
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La salle du studio 1 est proposée en même temps à deux options, au studio 1, deux commerciaux ont confirmé le même créneau.
  - La salle du studio 1 est proposée en même temps à deux options : le client vient de le redire au lobby. au studio 1, deux commerciaux ont confirmé le même créneau.
- Tâches principales : aucune

### signal:390 — Un avoir de l'atelier 2 est resté en brouillon après l'annulation

- Date : 2026-03-06 10:00:00+01:00
- Lieu : atelier_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:390
- Statut : resolved
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Un avoir de l'atelier 2 est resté en brouillon après l'annulation, à l'atelier 2, le client attend le document.
  - Un avoir de l'atelier 2 est resté en brouillon après l'annulation : le responsable de zone vient de le valider. à l'atelier 2, le client attend le document.
- Tâches principales : aucune

### signal:391 — La télécommande de l'écran au studio 1 est introuvable

- Date : 2026-09-08 06:59:59+02:00
- Lieu : studio_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:391
- Statut : open
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : aucun
- Exécution : aucun
- Observations :
  - La télécommande de l'écran au studio 1 est introuvable, au studio 1, l'écran reste sur la mauvaise source.
  - La télécommande de l'écran au studio 1 est introuvable : je le vois aussi au passage d'étage. au studio 1, l'écran reste sur la mauvaise source.
- Tâches principales : aucune

### signal:392 — L'enregistrement demandé au studio 1 n'a pas démarré

- Date : 2026-09-08 07:59:59+02:00
- Lieu : studio_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:392
- Statut : open
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - L'enregistrement demandé au studio 1 n'a pas démarré, au studio 1, le voyant enregistrement est éteint.
  - L'enregistrement demandé au studio 1 n'a pas démarré : la réception a la même info à l'instant. au studio 1, le voyant enregistrement est éteint.
- Tâches principales : aucune

### signal:393 — Le programme affiché au studio 2 a une heure de décalage

- Date : 2026-09-08 08:59:59+02:00
- Lieu : studio_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:393
- Statut : open
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : pattern:signaletique-event — Défauts de signalétique événementielle
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le programme affiché au studio 2 a une heure de décalage, au studio 2, les participants arrivent sur le mauvais créneau.
  - Le programme affiché au studio 2 a une heure de décalage : cuisine et salle ont le même constat. au studio 2, les participants arrivent sur le mauvais créneau.
- Tâches principales : aucune

### signal:394 — Le forfait papier de l'atelier 1 n'est pas sorti du stock

- Date : 2026-09-08 09:59:59+02:00
- Lieu : atelier_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:394
- Statut : open
- Famille : Qualité de service
- Activité : Ateliers et Studios
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le forfait papier de l'atelier 1 n'est pas sorti du stock, à l'atelier 1, les tables n'ont ni bloc ni stylo.
  - Le forfait papier de l'atelier 1 n'est pas sorti du stock : maintenance confirme sur place. à l'atelier 1, les tables n'ont ni bloc ni stylo. L'écart sur le forfait se voit encore au service du atelier 1.
- Tâches principales : aucune

### signal:395 — Le briefing de l'atelier 2 n'a pas d'heure au planning

- Date : 2026-09-08 10:59:59+02:00
- Lieu : atelier_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:395
- Statut : open
- Famille : Inefficacité de processus
- Activité : Ateliers et Studios
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le briefing de l'atelier 2 n'a pas d'heure au planning, à l'atelier 2, l'équipe arrive sans savoir quand on se parle.
  - Le briefing de l'atelier 2 n'a pas d'heure au planning : l'accueil événement le voit aussi. à l'atelier 2, l'équipe arrive sans savoir quand on se parle.
- Tâches principales : aucune

### signal:396 — La caution de l'atelier 1 n'a pas été rendue au client parti

- Date : 2026-09-08 11:59:59+02:00
- Lieu : atelier_1
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:396
- Statut : open
- Famille : Expérience client
- Activité : Ateliers et Studios
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La caution de l'atelier 1 n'a pas été rendue au client parti, à l'atelier 1, l'empreinte est encore bloquée.
  - La caution de l'atelier 1 n'a pas été rendue au client parti : le client vient de le redire au lobby. à l'atelier 1, l'empreinte est encore bloquée.
- Tâches principales : aucune

### signal:397 — Le câble HDMI de l'atelier 2 est trop court pour la table

- Date : 2026-09-08 12:59:59+02:00
- Lieu : atelier_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:397
- Statut : open
- Famille : Incident opérationnel
- Activité : Ateliers et Studios
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le câble HDMI de l'atelier 2 est trop court pour la table, à l'atelier 2, l'ordinateur ne joint pas l'écran.
  - Le câble HDMI de l'atelier 2 est trop court pour la table : le brief de shift retombe sur le même écart. à l'atelier 2, l'ordinateur ne joint pas l'écran.
- Tâches principales : aucune

## DJ sets

### signal:prepa-lienders — Le ClickShare de l'Atelier 1 reste à tester pour TIM LIENDERSS

- Date : 2026-09-19 10:00:00+02:00
- Lieu : atelier_1
- Auteur : maintenance
- Responsable : evenements_privatisations
- Signal : signal:prepa-lienders
- Statut : in_progress
- Famille : Coordination cross-pôles
- Activité : DJ sets
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : plan:preparation-evenement-dj — Préparation d'un événement DJ
- Exécution : exec:signal:signal:prepa-lienders
- Observations :
  - Le ClickShare de l'Atelier 1 reste à tester pour le DJ set TIM LIENDERSS du 26.
  - Maintenance doit valider HDMI et sono avant l'accueil du 24.
- Tâches principales :
  - Valider le run technique
  - Préparer scène et sono
  - Organiser bar et service
  - Publier et afficher la communication
  - Accueillir et clôturer

## Super Sunday

### signal:super-sunday-jauge — Le planning du Studio 1 n'a pas d'accueil dédié pour Super Sunday

- Date : 2026-09-18 15:10:00+02:00
- Lieu : studio_1
- Auteur : rh
- Responsable : evenements_privatisations
- Signal : signal:super-sunday-jauge
- Statut : open
- Famille : Coordination cross-pôles
- Activité : Super Sunday
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Pour Super Sunday le 27, le Studio 1 n'a toujours pas d'accueil dédié au planning.
- Tâches principales : aucune

## La Bringue à Mémé

### signal:bringue-signaletique — La signalétique de l'Atelier 2 pour La Bringue n'était pas calée

- Date : 2026-09-04 11:20:00+02:00
- Lieu : atelier_2
- Auteur : communication
- Responsable : evenements_privatisations
- Signal : signal:bringue-signaletique
- Statut : resolved
- Famille : Coordination cross-pôles
- Activité : La Bringue à Mémé
- Pattern : pattern:signaletique-event — Défauts de signalétique événementielle
- Plan : aucun
- Exécution : aucun
- Observations :
  - La signalétique de l'Atelier 2 pour La Bringue du 15 octobre n'était pas calée.
- Tâches principales : aucune

### signal:370 — Le fléchage Bringue de l'Atelier 2 s'arrête au vestiaire

- Date : 2026-02-25 06:00:00+01:00
- Lieu : atelier_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:370
- Statut : resolved
- Famille : Incident opérationnel
- Activité : La Bringue à Mémé
- Pattern : pattern:signaletique-event — Défauts de signalétique événementielle
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le fléchage Bringue de l'Atelier 2 s'arrête au vestiaire, en Atelier 2 plus de flèche après le vestiaire.
  - Le fléchage Bringue de l'Atelier 2 s'arrête au vestiaire : maintenance confirme sur place. en Atelier 2 plus de flèche après le vestiaire.
- Tâches principales : aucune

## Mama Club Sonore

### signal:club-sonore-sono — La sono de l'Atelier 1 pour Mama Club Sonore n'avait pas été testée

- Date : 2026-08-20 16:00:00+02:00
- Lieu : atelier_1
- Auteur : maintenance
- Responsable : evenements_privatisations
- Signal : signal:club-sonore-sono
- Statut : resolved
- Famille : Prévention
- Activité : Mama Club Sonore
- Pattern : pattern:audiovisuel-ateliers — Fiabilité audiovisuelle et réseau des Ateliers
- Plan : aucun
- Exécution : aucun
- Observations :
  - La sono de l'Atelier 1 pour Mama Club Sonore du 22 octobre n'avait pas été testée.
- Tâches principales : aucune

## Séminaires

### signal:horizon-azur-brief — Le brief de l'Atelier 1 pour le séminaire Horizon Azur n'est pas figé

- Date : 2026-09-16 09:40:00+02:00
- Lieu : atelier_1
- Auteur : evenements_privatisations
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

### signal:389 — Deux maîtres d'hôtel du rooftop sont posés sur le même séminaire

- Date : 2026-03-05 23:00:00+01:00
- Lieu : rooftop
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:389
- Statut : canceled
- Famille : Incident opérationnel
- Activité : Séminaires
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Motif d'annulation : La réservation a été annulée, la salle est libérée. Sujet : Deux maîtres d'hôtel du rooftop sont posés sur le même séminaire.
- Observations :
  - Deux maîtres d'hôtel du rooftop sont posés sur le même séminaire, au rooftop, le planning compte deux fois la même personne.
  - Deux maîtres d'hôtel du rooftop sont posés sur le même séminaire : le brief de shift retombe sur le même écart. au rooftop, le planning compte deux fois la même personne.
- Tâches principales : aucune

## Privatisations

### signal:privatisation-ateliers — Une privatisation de l'Atelier 2 demande un devis demi-journée

- Date : 2026-09-12 14:15:00+02:00
- Lieu : atelier_2
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:privatisation-ateliers
- Statut : open
- Famille : Coordination cross-pôles
- Activité : Privatisations
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Une privatisation de l'Atelier 2 demande un devis demi-journée, sans brief encore.
- Tâches principales : aucune

### signal:174 — La privatisation vendue pour le bar n'a pas de fiche de groupe

- Date : 2025-11-27 10:00:00+01:00
- Lieu : bar_central
- Auteur : restaurant
- Responsable : restaurant
- Signal : signal:174
- Statut : canceled
- Famille : Qualité de service
- Activité : Privatisations
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Motif d'annulation : Le client a déplacé la date, la préparation n'a plus lieu. Sujet : La privatisation vendue pour le bar n'a pas de fiche de groupe.
- Observations :
  - La privatisation vendue pour le bar n'a pas de fiche de groupe, au bar, on ne sait pas le nombre ni l'heure. Au bar central, la privatisation allonge le service plus que la jauge prévue.
- Tâches principales : aucune

### signal:384 — La facture de privatisation du rooftop n'a pas le bon nombre de personnes

- Date : 2026-03-03 16:00:00+01:00
- Lieu : rooftop
- Auteur : evenements_privatisations
- Responsable : evenements_privatisations
- Signal : signal:384
- Statut : canceled
- Famille : Incident opérationnel
- Activité : Privatisations
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Motif d'annulation : La réservation a été annulée, la salle est libérée. Sujet : La facture de privatisation du rooftop n'a pas le bon nombre de personnes.
- Observations :
  - La facture de privatisation du rooftop n'a pas le bon nombre de personnes, au rooftop, on avait noté 40 personnes et la facture en compte 55.
  - La facture de privatisation du rooftop n'a pas le bon nombre de personnes : la réception a la même info à l'instant. au rooftop, on avait noté 40 personnes et la facture en compte 55.
- Tâches principales : aucune

## Staffing et RH

### signal:extras-dimanche — Le planning du dimanche 27 est encore à deux extras près

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
  - Le planning du dimanche 27 Super Sunday est encore à deux extras près, affiché au breakroom.
- Tâches principales : aucune

### signal:interesting-extras-sunday — Les extras hésitent sur les Super Sunday, le planning n'est pas en trou

- Date : 2026-09-09 17:15:00+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:interesting-extras-sunday
- Statut : interesting
- Famille : Opportunité
- Activité : Staffing et RH
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - Les extras hésitent sur les Super Sunday, le planning affiché au breakroom n'est pas encore en trou.
- Tâches principales : aucune

### signal:398 — Deux postes de réception sont ouverts et aucun candidat n'est convoqué

- Date : 2026-09-08 13:59:59+02:00
- Lieu : back_office_administratif
- Auteur : rh
- Responsable : rh
- Signal : signal:398
- Statut : open
- Famille : Inefficacité de processus
- Activité : Staffing et RH
- Pattern : pattern:sous-effectif — Sous-effectif ou besoin de formation récurrent
- Plan : aucun
- Exécution : aucun
- Observations :
  - Deux postes de réception sont ouverts et aucun candidat n'est convoqué, au bureau, les annonces sont en ligne sans créneau d'entretien.
  - Deux postes de réception sont ouverts et aucun candidat n'est convoqué : le responsable de zone vient de le valider. au bureau, les annonces sont en ligne sans créneau d'entretien. Le geste prévu pour le recrutement n'a pas été tenu au back office administratif.
- Tâches principales : aucune

### signal:399 — Le planning de la semaine prochaine a trois trous au petit-déjeuner

- Date : 2026-09-08 14:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:399
- Statut : open
- Famille : Inefficacité de processus
- Activité : Staffing et RH
- Pattern : pattern:sous-effectif — Sous-effectif ou besoin de formation récurrent
- Plan : aucun
- Exécution : aucun
- Observations :
  - Le planning de la semaine prochaine a trois trous au petit-déjeuner, au breakroom, les cases du matin sont vides.
  - Le planning de la semaine prochaine a trois trous au petit-déjeuner : je le vois aussi au passage d'étage. au breakroom, les cases du matin sont vides.
- Tâches principales : aucune

### signal:400 — La session caisse de mardi au breakroom n'a aucun inscrit

- Date : 2026-09-08 15:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:400
- Statut : open
- Famille : Inefficacité de processus
- Activité : Staffing et RH
- Pattern : aucun
- Plan : aucun
- Exécution : aucun
- Observations :
  - La session caisse de mardi au breakroom n'a aucun inscrit, au breakroom, la salle est réservée pour personne.
  - La session caisse de mardi au breakroom n'a aucun inscrit : la réception a la même info à l'instant. au breakroom, la salle est réservée pour personne. Au breakroom, la formation bloque encore la passation de septembre.
- Tâches principales : aucune

### signal:401 — Le rituel du lundi au breakroom a été sauté deux semaines de suite

- Date : 2026-09-08 16:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:401
- Statut : in_progress
- Famille : Incident opérationnel
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:401
- Observations :
  - Le rituel du lundi au breakroom a été sauté deux semaines de suite, au breakroom, l'équipe demande si le point existe encore.
  - Le rituel du lundi au breakroom a été sauté deux semaines de suite : cuisine et salle ont le même constat. au breakroom, l'équipe demande si le point existe encore.
  - Le rituel du lundi au breakroom a été sauté deux semaines de suite : maintenance confirme sur place. au breakroom, l'équipe demande si le point existe encore.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:402 — Une prime de dimanche n'est pas sur le récap de paie

- Date : 2026-09-08 17:59:59+02:00
- Lieu : back_office_administratif
- Auteur : rh
- Responsable : rh
- Signal : signal:402
- Statut : in_progress
- Famille : Incident opérationnel
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:402
- Observations :
  - Une prime de dimanche n'est pas sur le récap de paie, au bureau, le dimanche travaillé n'apparaît pas.
  - Une prime de dimanche n'est pas sur le récap de paie : maintenance confirme sur place. au bureau, le dimanche travaillé n'apparaît pas.
  - Une prime de dimanche n'est pas sur le récap de paie : l'accueil événement le voit aussi. au bureau, le dimanche travaillé n'apparaît pas.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:403 — L'équipe du soir dit ne plus tenir les coupures

- Date : 2026-09-08 18:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:403
- Statut : in_progress
- Famille : Incident opérationnel
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:403
- Observations :
  - L'équipe du soir dit ne plus tenir les coupures, au breakroom, trois personnes ont le même créneau coupé.
  - L'équipe du soir dit ne plus tenir les coupures : l'accueil événement le voit aussi. au breakroom, trois personnes ont le même créneau coupé.
  - L'équipe du soir dit ne plus tenir les coupures : le client vient de le redire au lobby. au breakroom, trois personnes ont le même créneau coupé.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:404 — Un retard répété au brief du matin n'a pas été dit

- Date : 2026-09-08 19:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:404
- Statut : in_progress
- Famille : Incident opérationnel
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:404
- Observations :
  - Un retard répété au brief du matin n'a pas été dit, au breakroom, la même personne arrive après le point.
  - Un retard répété au brief du matin n'a pas été dit : le client vient de le redire au lobby. au breakroom, la même personne arrive après le point.
  - Un retard répété au brief du matin n'a pas été dit : le brief de shift retombe sur le même écart. au breakroom, la même personne arrive après le point.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:405 — Quatre visites médicales sont dépassées sur le tableau du breakroom

- Date : 2026-09-08 20:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:405
- Statut : in_progress
- Famille : Incident opérationnel
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:405
- Observations :
  - Quatre visites médicales sont dépassées sur le tableau du breakroom, au breakroom, les dates en rouge datent du mois dernier.
  - Quatre visites médicales sont dépassées sur le tableau du breakroom : le brief de shift retombe sur le même écart. au breakroom, les dates en rouge datent du mois dernier.
  - Quatre visites médicales sont dépassées sur le tableau du breakroom : le responsable de zone vient de le valider. au breakroom, les dates en rouge datent du mois dernier.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:406 — L'agence d'intérim n'a personne pour la plonge de samedi

- Date : 2026-09-08 21:59:59+02:00
- Lieu : back_office_administratif
- Auteur : rh
- Responsable : rh
- Signal : signal:406
- Statut : in_progress
- Famille : Incident opérationnel
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:incident-service-resto — Traitement d'un incident de service restaurant
- Exécution : exec:signal:signal:406
- Observations :
  - L'agence d'intérim n'a personne pour la plonge de samedi, au bureau, l'agence a répondu par la négative ce matin.
  - L'agence d'intérim n'a personne pour la plonge de samedi : le responsable de zone vient de le valider. au bureau, l'agence a répondu par la négative ce matin.
  - L'agence d'intérim n'a personne pour la plonge de samedi : je le vois aussi au passage d'étage. au bureau, l'agence a répondu par la négative ce matin.
- Tâches principales :
  - Accueillir et calmer le service concerné
  - Corriger commande ou attente
  - Informer le manager de shift
  - Clôturer l'incident

### signal:407 — L'essai d'une femme de chambre s'arrête, le poste est de nouveau vide

- Date : 2026-09-08 22:59:59+02:00
- Lieu : back_office_administratif
- Auteur : rh
- Responsable : rh
- Signal : signal:407
- Statut : in_progress
- Famille : Inefficacité de processus
- Activité : Staffing et RH
- Pattern : pattern:sous-effectif — Sous-effectif ou besoin de formation récurrent
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:407
- Observations :
  - L'essai d'une femme de chambre s'arrête, le poste est de nouveau vide, au bureau, il faut relancer le recrutement étages.
  - L'essai d'une femme de chambre s'arrête, le poste est de nouveau vide : je le vois aussi au passage d'étage. au bureau, il faut relancer le recrutement étages.
  - L'essai d'une femme de chambre s'arrête, le poste est de nouveau vide : la réception a la même info à l'instant. au bureau, il faut relancer le recrutement étages.
  - L'essai d'une femme de chambre s'arrête, le poste est de nouveau vide : cuisine et salle ont le même constat. au bureau, il faut relancer le recrutement étages. Le geste prévu pour le poste n'a pas été tenu au back office administratif.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:408 — Le planning du soir au restaurant est affiché sans chef de rang

- Date : 2026-09-08 23:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:408
- Statut : in_progress
- Famille : Inefficacité de processus
- Activité : Staffing et RH
- Pattern : pattern:sous-effectif — Sous-effectif ou besoin de formation récurrent
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:408
- Observations :
  - Le planning du soir au restaurant est affiché sans chef de rang, au breakroom, la ligne restaurant du soir n'a pas de responsable.
  - Le planning du soir au restaurant est affiché sans chef de rang : la réception a la même info à l'instant. au breakroom, la ligne restaurant du soir n'a pas de responsable.
  - Le planning du soir au restaurant est affiché sans chef de rang : cuisine et salle ont le même constat. au breakroom, la ligne restaurant du soir n'a pas de responsable.
  - Le planning du soir au restaurant est affiché sans chef de rang : maintenance confirme sur place. au breakroom, la ligne restaurant du soir n'a pas de responsable.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:409 — Le module incendie est en retard pour quatre équipiers

- Date : 2026-09-09 00:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:409
- Statut : in_progress
- Famille : Incident opérationnel
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:409
- Observations :
  - Le module incendie est en retard pour quatre équipiers, au breakroom, les quatre noms sont encore en rouge.
  - Le module incendie est en retard pour quatre équipiers : cuisine et salle ont le même constat. au breakroom, les quatre noms sont encore en rouge.
  - Le module incendie est en retard pour quatre équipiers : maintenance confirme sur place. au breakroom, les quatre noms sont encore en rouge.
  - Le module incendie est en retard pour quatre équipiers : l'accueil événement le voit aussi. au breakroom, les quatre noms sont encore en rouge.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:410 — Une tension entre salle et cuisine n'a pas été reprise en brief

- Date : 2026-09-09 01:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:410
- Statut : in_progress
- Famille : Incident opérationnel
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:410
- Observations :
  - Une tension entre salle et cuisine n'a pas été reprise en brief, au breakroom, le sujet est resté sur la table hier.
  - Une tension entre salle et cuisine n'a pas été reprise en brief : maintenance confirme sur place. au breakroom, le sujet est resté sur la table hier.
  - Une tension entre salle et cuisine n'a pas été reprise en brief : l'accueil événement le voit aussi. au breakroom, le sujet est resté sur la table hier.
  - Une tension entre salle et cuisine n'a pas été reprise en brief : le client vient de le redire au lobby. au breakroom, le sujet est resté sur la table hier.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:411 — Un avenant d'heures n'est pas signé avant la paie de vendredi

- Date : 2026-09-09 02:59:59+02:00
- Lieu : back_office_administratif
- Auteur : rh
- Responsable : rh
- Signal : signal:411
- Statut : in_progress
- Famille : Prévention
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:411
- Observations :
  - Un avenant d'heures n'est pas signé avant la paie de vendredi, au bureau, le document est encore dans la bannette.
  - Un avenant d'heures n'est pas signé avant la paie de vendredi : l'accueil événement le voit aussi. au bureau, le document est encore dans la bannette.
  - Un avenant d'heures n'est pas signé avant la paie de vendredi : le client vient de le redire au lobby. au bureau, le document est encore dans la bannette.
  - Un avenant d'heures n'est pas signé avant la paie de vendredi : le brief de shift retombe sur le même écart. au bureau, le document est encore dans la bannette. Check-list du matin au back office administratif, l'avenant noté pour passage préventif.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:412 — Il n'y a plus d'eau fraîche dans le breakroom en plein service

- Date : 2026-09-09 03:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:412
- Statut : in_progress
- Famille : Incident opérationnel
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:412
- Observations :
  - Il n'y a plus d'eau fraîche dans le breakroom en plein service, au breakroom, la fontaine est vide depuis ce midi.
  - Il n'y a plus d'eau fraîche dans le breakroom en plein service : le client vient de le redire au lobby. au breakroom, la fontaine est vide depuis ce midi.
  - Il n'y a plus d'eau fraîche dans le breakroom en plein service : le brief de shift retombe sur le même écart. au breakroom, la fontaine est vide depuis ce midi.
  - Il n'y a plus d'eau fraîche dans le breakroom en plein service : le responsable de zone vient de le valider. au breakroom, la fontaine est vide depuis ce midi.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:413 — Une tenue hors charte est revenue trois services de suite

- Date : 2026-09-09 04:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:413
- Statut : in_progress
- Famille : Incident opérationnel
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:413
- Observations :
  - Une tenue hors charte est revenue trois services de suite, au breakroom, les baskets sont encore là ce matin.
  - Une tenue hors charte est revenue trois services de suite : le brief de shift retombe sur le même écart. au breakroom, les baskets sont encore là ce matin.
  - Une tenue hors charte est revenue trois services de suite : le responsable de zone vient de le valider. au breakroom, les baskets sont encore là ce matin.
  - Une tenue hors charte est revenue trois services de suite : je le vois aussi au passage d'étage. au breakroom, les baskets sont encore là ce matin.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:414 — Le registre du personnel affiché au bureau n'est pas à jour

- Date : 2026-09-09 05:59:59+02:00
- Lieu : back_office_administratif
- Auteur : rh
- Responsable : rh
- Signal : signal:414
- Statut : in_progress
- Famille : Incident opérationnel
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:414
- Observations :
  - Le registre du personnel affiché au bureau n'est pas à jour, au bureau, deux départs y figurent encore.
  - Le registre du personnel affiché au bureau n'est pas à jour : le responsable de zone vient de le valider. au bureau, deux départs y figurent encore.
  - Le registre du personnel affiché au bureau n'est pas à jour : je le vois aussi au passage d'étage. au bureau, deux départs y figurent encore.
  - Le registre du personnel affiché au bureau n'est pas à jour : la réception a la même info à l'instant. au bureau, deux départs y figurent encore.
  - Le registre du personnel affiché au bureau n'est pas à jour : cuisine et salle ont le même constat. au bureau, deux départs y figurent encore.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:415 — Un intérimaire s'est présenté au breakroom sans dossier d'accueil

- Date : 2026-09-09 06:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:415
- Statut : in_progress
- Famille : Expérience client
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:415
- Observations :
  - Un intérimaire s'est présenté au breakroom sans dossier d'accueil, au breakroom, il n'a ni badge ni tuteur.
  - Un intérimaire s'est présenté au breakroom sans dossier d'accueil : je le vois aussi au passage d'étage. au breakroom, il n'a ni badge ni tuteur.
  - Un intérimaire s'est présenté au breakroom sans dossier d'accueil : la réception a la même info à l'instant. au breakroom, il n'a ni badge ni tuteur.
  - Un intérimaire s'est présenté au breakroom sans dossier d'accueil : cuisine et salle ont le même constat. au breakroom, il n'a ni badge ni tuteur.
  - Un intérimaire s'est présenté au breakroom sans dossier d'accueil : maintenance confirme sur place. au breakroom, il n'a ni badge ni tuteur.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:416 — Le vivier d'extras cuisine est à sec pour le week-end

- Date : 2026-09-09 07:59:59+02:00
- Lieu : back_office_administratif
- Auteur : rh
- Responsable : rh
- Signal : signal:416
- Statut : in_progress
- Famille : Inefficacité de processus
- Activité : Staffing et RH
- Pattern : pattern:sous-effectif — Sous-effectif ou besoin de formation récurrent
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:416
- Observations :
  - Le vivier d'extras cuisine est à sec pour le week-end, au bureau, plus aucun nom disponible samedi.
  - Le vivier d'extras cuisine est à sec pour le week-end : la réception a la même info à l'instant. au bureau, plus aucun nom disponible samedi.
  - Le vivier d'extras cuisine est à sec pour le week-end : cuisine et salle ont le même constat. au bureau, plus aucun nom disponible samedi.
  - Le vivier d'extras cuisine est à sec pour le week-end : maintenance confirme sur place. au bureau, plus aucun nom disponible samedi.
  - Le vivier d'extras cuisine est à sec pour le week-end : l'accueil événement le voit aussi. au bureau, plus aucun nom disponible samedi. Le geste prévu pour le vivier n'a pas été tenu au back office administratif.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:417 — Les repos ne sont pas posés sur le planning étages de dimanche

- Date : 2026-09-09 08:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:417
- Statut : in_progress
- Famille : Inefficacité de processus
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:417
- Observations :
  - Les repos ne sont pas posés sur le planning étages de dimanche, au breakroom, tout le monde apparaît travaillé dimanche.
  - Les repos ne sont pas posés sur le planning étages de dimanche : cuisine et salle ont le même constat. au breakroom, tout le monde apparaît travaillé dimanche.
  - Les repos ne sont pas posés sur le planning étages de dimanche : maintenance confirme sur place. au breakroom, tout le monde apparaît travaillé dimanche.
  - Les repos ne sont pas posés sur le planning étages de dimanche : l'accueil événement le voit aussi. au breakroom, tout le monde apparaît travaillé dimanche.
  - Les repos ne sont pas posés sur le planning étages de dimanche : le client vient de le redire au lobby. au breakroom, tout le monde apparaît travaillé dimanche.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:418 — Un tuteur formation est en congé le jour de l'intégration

- Date : 2026-09-09 09:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:418
- Statut : in_progress
- Famille : Incident opérationnel
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:418
- Observations :
  - Un tuteur formation est en congé le jour de l'intégration, au breakroom, l'arrivée de jeudi n'a pas d'accompagnant.
  - Un tuteur formation est en congé le jour de l'intégration : maintenance confirme sur place. au breakroom, l'arrivée de jeudi n'a pas d'accompagnant.
  - Un tuteur formation est en congé le jour de l'intégration : l'accueil événement le voit aussi. au breakroom, l'arrivée de jeudi n'a pas d'accompagnant.
  - Un tuteur formation est en congé le jour de l'intégration : le client vient de le redire au lobby. au breakroom, l'arrivée de jeudi n'a pas d'accompagnant.
  - Un tuteur formation est en congé le jour de l'intégration : le brief de shift retombe sur le même écart. au breakroom, l'arrivée de jeudi n'a pas d'accompagnant.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:419 — Les départs de la semaine n'ont pas eu un mot au breakroom

- Date : 2026-09-09 10:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:419
- Statut : in_progress
- Famille : Incident opérationnel
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:419
- Observations :
  - Les départs de la semaine n'ont pas eu un mot au breakroom, au breakroom, deux collègues partent sans avoir été salués.
  - Les départs de la semaine n'ont pas eu un mot au breakroom : l'accueil événement le voit aussi. au breakroom, deux collègues partent sans avoir été salués.
  - Les départs de la semaine n'ont pas eu un mot au breakroom : le client vient de le redire au lobby. au breakroom, deux collègues partent sans avoir été salués.
  - Les départs de la semaine n'ont pas eu un mot au breakroom : le brief de shift retombe sur le même écart. au breakroom, deux collègues partent sans avoir été salués.
  - Les départs de la semaine n'ont pas eu un mot au breakroom : le responsable de zone vient de le valider. au breakroom, deux collègues partent sans avoir été salués.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue

### signal:420 — Un équipier ne retrouve pas son bulletin dans le coffre du breakroom

- Date : 2026-09-09 11:59:59+02:00
- Lieu : breakroom
- Auteur : rh
- Responsable : rh
- Signal : signal:420
- Statut : in_progress
- Famille : Incident opérationnel
- Activité : Staffing et RH
- Pattern : aucun
- Plan : plan:runtime-rh-routines — Routines planning RH
- Exécution : exec:signal:signal:420
- Observations :
  - Un équipier ne retrouve pas son bulletin dans le coffre du breakroom, au breakroom, l'enveloppe n'est pas dans le casier.
  - Un équipier ne retrouve pas son bulletin dans le coffre du breakroom : le client vient de le redire au lobby. au breakroom, l'enveloppe n'est pas dans le casier.
  - Un équipier ne retrouve pas son bulletin dans le coffre du breakroom : le brief de shift retombe sur le même écart. au breakroom, l'enveloppe n'est pas dans le casier.
  - Un équipier ne retrouve pas son bulletin dans le coffre du breakroom : le responsable de zone vient de le valider. au breakroom, l'enveloppe n'est pas dans le casier.
  - Un équipier ne retrouve pas son bulletin dans le coffre du breakroom : je le vois aussi au passage d'étage. au breakroom, l'enveloppe n'est pas dans le casier.
- Tâches principales :
  - Préparer le planning
  - Valider le staffing
  - Clôturer la revue
