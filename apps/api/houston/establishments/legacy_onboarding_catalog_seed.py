"""Historical v1 OnboardingCatalog seed rows (migration 0007 only)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _SeedRow:
    module_label: str
    module_key: str
    domain_label: str
    domain_key: str
    subject_label: str
    subject_key: str


SEED_ROWS: tuple[_SeedRow, ...] = (
    _SeedRow("Hôtel", "hotel", "Hébergement", "hotel__hebergement", "Expérience client / satisfaction", "hotel__hebergement__experience_client_satisfaction"),
    _SeedRow("Hôtel", "hotel", "Hébergement", "hotel__hebergement", "Propreté des chambres", "hotel__hebergement__proprete_des_chambres"),
    _SeedRow("Hôtel", "hotel", "Hébergement", "hotel__hebergement", "Maintenance & équipements", "hotel__hebergement__maintenance_equipements"),
    _SeedRow("Hôtel", "hotel", "Hébergement", "hotel__hebergement", "Linge & dotations", "hotel__hebergement__linge_dotations"),
    _SeedRow("Hôtel", "hotel", "Hébergement", "hotel__hebergement", "Check-in / Check-out", "hotel__hebergement__check_in_check_out"),
    _SeedRow("Hôtel", "hotel", "Hébergement", "hotel__hebergement", "Communication / commercialisation", "hotel__hebergement__communication_commercialisation"),
    _SeedRow("Hôtel", "hotel", "Hébergement", "hotel__hebergement", "RH & planning", "hotel__hebergement__rh_planning"),
    _SeedRow("Hôtel", "hotel", "Réception & Hall", "hotel__reception_hall", "Expérience client / satisfaction", "hotel__reception_hall__experience_client_satisfaction"),
    _SeedRow("Hôtel", "hotel", "Réception & Hall", "hotel__reception_hall", "Propreté & présentation", "hotel__reception_hall__proprete_presentation"),
    _SeedRow("Hôtel", "hotel", "Réception & Hall", "hotel__reception_hall", "Maintenance", "hotel__reception_hall__maintenance"),
    _SeedRow("Hôtel", "hotel", "Réception & Hall", "hotel__reception_hall", "Signalétique", "hotel__reception_hall__signaletique"),
    _SeedRow("Hôtel", "hotel", "Parties communes", "hotel__parties_communes", "Propreté", "hotel__parties_communes__proprete"),
    _SeedRow("Hôtel", "hotel", "Parties communes", "hotel__parties_communes", "Maintenance", "hotel__parties_communes__maintenance"),
    _SeedRow("Hôtel", "hotel", "Parties communes", "hotel__parties_communes", "Expérience client / satisfaction", "hotel__parties_communes__experience_client_satisfaction"),
    _SeedRow("Hôtel", "hotel", "Espaces bien-être (spa/piscine)", "hotel__espaces_bien_etre_spa_piscine", "Expérience client", "hotel__espaces_bien_etre_spa_piscine__experience_client"),
    _SeedRow("Hôtel", "hotel", "Espaces bien-être (spa/piscine)", "hotel__espaces_bien_etre_spa_piscine", "Propreté & hygiène", "hotel__espaces_bien_etre_spa_piscine__proprete_hygiene"),
    _SeedRow("Hôtel", "hotel", "Espaces bien-être (spa/piscine)", "hotel__espaces_bien_etre_spa_piscine", "Maintenance équipements", "hotel__espaces_bien_etre_spa_piscine__maintenance_equipements"),
    _SeedRow("Hôtel", "hotel", "Espaces bien-être (spa/piscine)", "hotel__espaces_bien_etre_spa_piscine", "Conformité sanitaire", "hotel__espaces_bien_etre_spa_piscine__conformite_sanitaire"),
    _SeedRow("Hôtel", "hotel", "Espaces bien-être (spa/piscine)", "hotel__espaces_bien_etre_spa_piscine", "Communication / commercialisation", "hotel__espaces_bien_etre_spa_piscine__communication_commercialisation"),
    _SeedRow("Hôtel", "hotel", "Espaces bien-être (spa/piscine)", "hotel__espaces_bien_etre_spa_piscine", "RH & planning", "hotel__espaces_bien_etre_spa_piscine__rh_planning"),
    _SeedRow("Hôtel", "hotel", "Administration & back-office", "hotel__administration_back_office", "RH & planning", "hotel__administration_back_office__rh_planning"),
    _SeedRow("Hôtel", "hotel", "Administration & back-office", "hotel__administration_back_office", "Conformité légale", "hotel__administration_back_office__conformite_legale"),
    _SeedRow("Hôtel", "hotel", "Administration & back-office", "hotel__administration_back_office", "Facturation & caisse", "hotel__administration_back_office__facturation_caisse"),
    _SeedRow("Hôtel", "hotel", "Administration & back-office", "hotel__administration_back_office", "Communication direction", "hotel__administration_back_office__communication_direction"),
    _SeedRow("Hôtel", "hotel", "Administration & back-office", "hotel__administration_back_office", "Fournisseurs & stocks", "hotel__administration_back_office__fournisseurs_stocks"),
    _SeedRow("Hôtel", "hotel", "Petit déjeuner", "hotel__petit_dejeuner", "Expérience client", "hotel__petit_dejeuner__experience_client"),
    _SeedRow("Hôtel", "hotel", "Petit déjeuner", "hotel__petit_dejeuner", "Propreté & hygiène", "hotel__petit_dejeuner__proprete_hygiene"),
    _SeedRow("Hôtel", "hotel", "Petit déjeuner", "hotel__petit_dejeuner", "Maintenance équipements", "hotel__petit_dejeuner__maintenance_equipements"),
    _SeedRow("Hôtel", "hotel", "Petit déjeuner", "hotel__petit_dejeuner", "Commercialisation", "hotel__petit_dejeuner__commercialisation"),
    _SeedRow("Restaurant", "restaurant", "Salle", "restaurant__salle", "Expérience client / satisfaction", "restaurant__salle__experience_client_satisfaction"),
    _SeedRow("Restaurant", "restaurant", "Salle", "restaurant__salle", "Propreté", "restaurant__salle__proprete"),
    _SeedRow("Restaurant", "restaurant", "Salle", "restaurant__salle", "Mise en place", "restaurant__salle__mise_en_place"),
    _SeedRow("Restaurant", "restaurant", "Salle", "restaurant__salle", "Service & accueil", "restaurant__salle__service_accueil"),
    _SeedRow("Restaurant", "restaurant", "Salle", "restaurant__salle", "Maintenance", "restaurant__salle__maintenance"),
    _SeedRow("Restaurant", "restaurant", "Salle", "restaurant__salle", "Communication", "restaurant__salle__communication"),
    _SeedRow("Restaurant", "restaurant", "Salle", "restaurant__salle", "RH & planning", "restaurant__salle__rh_planning"),
    _SeedRow("Restaurant", "restaurant", "Salle", "restaurant__salle", "Menu", "restaurant__salle__menu"),
    _SeedRow("Restaurant", "restaurant", "Cuisine", "restaurant__cuisine", "Hygiène & conformité HACCP", "restaurant__cuisine__hygiene_conformite_haccp"),
    _SeedRow("Restaurant", "restaurant", "Cuisine", "restaurant__cuisine", "Contrôle DLC / réception", "restaurant__cuisine__controle_dlc_reception"),
    _SeedRow("Restaurant", "restaurant", "Cuisine", "restaurant__cuisine", "Qualité produit", "restaurant__cuisine__qualite_produit"),
    _SeedRow("Restaurant", "restaurant", "Cuisine", "restaurant__cuisine", "Stocks & approvisionnement", "restaurant__cuisine__stocks_approvisionnement"),
    _SeedRow("Restaurant", "restaurant", "Cuisine", "restaurant__cuisine", "Maintenance équipements", "restaurant__cuisine__maintenance_equipements"),
    _SeedRow("Restaurant", "restaurant", "Cuisine", "restaurant__cuisine", "RH & planning", "restaurant__cuisine__rh_planning"),
    _SeedRow("Restaurant", "restaurant", "Bar", "restaurant__bar", "Expérience client", "restaurant__bar__experience_client"),
    _SeedRow("Restaurant", "restaurant", "Bar", "restaurant__bar", "Stocks & approvisionnement", "restaurant__bar__stocks_approvisionnement"),
    _SeedRow("Restaurant", "restaurant", "Bar", "restaurant__bar", "Propreté", "restaurant__bar__proprete"),
    _SeedRow("Restaurant", "restaurant", "Bar", "restaurant__bar", "Maintenance équipements", "restaurant__bar__maintenance_equipements"),
    _SeedRow("Restaurant", "restaurant", "Bar", "restaurant__bar", "Conformité", "restaurant__bar__conformite"),
    _SeedRow("Restaurant", "restaurant", "Livraison (Uber Eats / Deliveroo)", "restaurant__livraison_uber_eats_deliveroo", "Emballages & présentation", "restaurant__livraison_uber_eats_deliveroo__emballages_presentation"),
    _SeedRow("Restaurant", "restaurant", "Livraison (Uber Eats / Deliveroo)", "restaurant__livraison_uber_eats_deliveroo", "Performance opérationnelle", "restaurant__livraison_uber_eats_deliveroo__performance_operationnelle"),
    _SeedRow("Restaurant", "restaurant", "Livraison (Uber Eats / Deliveroo)", "restaurant__livraison_uber_eats_deliveroo", "Gestion tablette & plateforme", "restaurant__livraison_uber_eats_deliveroo__gestion_tablette_plateforme"),
    _SeedRow("Restaurant", "restaurant", "Livraison (Uber Eats / Deliveroo)", "restaurant__livraison_uber_eats_deliveroo", "Stocks dédiés livraison", "restaurant__livraison_uber_eats_deliveroo__stocks_dedies_livraison"),
    _SeedRow("Restaurant", "restaurant", "Livraison (Uber Eats / Deliveroo)", "restaurant__livraison_uber_eats_deliveroo", "Gestion SAV", "restaurant__livraison_uber_eats_deliveroo__gestion_sav"),
    _SeedRow("Restaurant", "restaurant", "Événements & privatisations", "restaurant__evenements_privatisations", "Préparation & logistique", "restaurant__evenements_privatisations__preparation_logistique"),
    _SeedRow("Restaurant", "restaurant", "Événements & privatisations", "restaurant__evenements_privatisations", "Expérience client", "restaurant__evenements_privatisations__experience_client"),
    _SeedRow("Restaurant", "restaurant", "Événements & privatisations", "restaurant__evenements_privatisations", "Communication / commercialisation", "restaurant__evenements_privatisations__communication_commercialisation"),
    _SeedRow("Restaurant", "restaurant", "Événements & privatisations", "restaurant__evenements_privatisations", "RH & planning", "restaurant__evenements_privatisations__rh_planning"),
    _SeedRow("Restaurant", "restaurant", "Événements & privatisations", "restaurant__evenements_privatisations", "Facturation", "restaurant__evenements_privatisations__facturation"),
    _SeedRow("Restaurant", "restaurant", "Administration", "restaurant__administration", "RH & planning", "restaurant__administration__rh_planning"),
    _SeedRow("Restaurant", "restaurant", "Administration", "restaurant__administration", "Conformité légale", "restaurant__administration__conformite_legale"),
    _SeedRow("Restaurant", "restaurant", "Administration", "restaurant__administration", "Caisse & facturation", "restaurant__administration__caisse_facturation"),
    _SeedRow("Restaurant", "restaurant", "Administration", "restaurant__administration", "Fournisseurs", "restaurant__administration__fournisseurs"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Surface de vente", "retail_commerce__surface_de_vente", "Expérience client", "retail_commerce__surface_de_vente__experience_client"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Surface de vente", "retail_commerce__surface_de_vente", "Merchandising & facing", "retail_commerce__surface_de_vente__merchandising_facing"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Surface de vente", "retail_commerce__surface_de_vente", "Propreté", "retail_commerce__surface_de_vente__proprete"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Surface de vente", "retail_commerce__surface_de_vente", "Sécurité & antivol", "retail_commerce__surface_de_vente__securite_antivol"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Surface de vente", "retail_commerce__surface_de_vente", "Maintenance", "retail_commerce__surface_de_vente__maintenance"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Surface de vente", "retail_commerce__surface_de_vente", "Signalétique & prix", "retail_commerce__surface_de_vente__signaletique_prix"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Surface de vente", "retail_commerce__surface_de_vente", "RH & planning", "retail_commerce__surface_de_vente__rh_planning"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Caisse & encaissement", "retail_commerce__caisse_encaissement", "Expérience client", "retail_commerce__caisse_encaissement__experience_client"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Caisse & encaissement", "retail_commerce__caisse_encaissement", "Conformité caisse", "retail_commerce__caisse_encaissement__conformite_caisse"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Caisse & encaissement", "retail_commerce__caisse_encaissement", "Temps d'attente", "retail_commerce__caisse_encaissement__temps_d_attente"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Caisse & encaissement", "retail_commerce__caisse_encaissement", "Erreurs de caisse", "retail_commerce__caisse_encaissement__erreurs_de_caisse"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Caisse & encaissement", "retail_commerce__caisse_encaissement", "RH & planning", "retail_commerce__caisse_encaissement__rh_planning"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Réserve & stocks", "retail_commerce__reserve_stocks", "Gestion des stocks", "retail_commerce__reserve_stocks__gestion_des_stocks"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Réserve & stocks", "retail_commerce__reserve_stocks", "Réception commandes", "retail_commerce__reserve_stocks__reception_commandes"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Réserve & stocks", "retail_commerce__reserve_stocks", "Conformité DLC", "retail_commerce__reserve_stocks__conformite_dlc"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Réserve & stocks", "retail_commerce__reserve_stocks", "Propreté & organisation", "retail_commerce__reserve_stocks__proprete_organisation"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Réserve & stocks", "retail_commerce__reserve_stocks", "Maintenance", "retail_commerce__reserve_stocks__maintenance"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Réserve & stocks", "retail_commerce__reserve_stocks", "RH & planning", "retail_commerce__reserve_stocks__rh_planning"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Administration", "retail_commerce__administration", "RH & planning", "retail_commerce__administration__rh_planning"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Administration", "retail_commerce__administration", "Conformité légale", "retail_commerce__administration__conformite_legale"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Administration", "retail_commerce__administration", "Communication direction", "retail_commerce__administration__communication_direction"),
    _SeedRow("Retail / Commerce", "retail_commerce", "Administration", "retail_commerce__administration", "Fournisseurs", "retail_commerce__administration__fournisseurs"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Espaces de travail ouverts", "coworking_bureau__espaces_de_travail_ouverts", "Expérience membre", "coworking_bureau__espaces_de_travail_ouverts__experience_membre"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Espaces de travail ouverts", "coworking_bureau__espaces_de_travail_ouverts", "Propreté & organisation", "coworking_bureau__espaces_de_travail_ouverts__proprete_organisation"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Espaces de travail ouverts", "coworking_bureau__espaces_de_travail_ouverts", "Maintenance mobilier & équipements", "coworking_bureau__espaces_de_travail_ouverts__maintenance_mobilier_equipements"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Espaces de travail ouverts", "coworking_bureau__espaces_de_travail_ouverts", "Connexion & IT", "coworking_bureau__espaces_de_travail_ouverts__connexion_it"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Espaces de travail ouverts", "coworking_bureau__espaces_de_travail_ouverts", "Ambiance & nuisances", "coworking_bureau__espaces_de_travail_ouverts__ambiance_nuisances"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Espaces de travail ouverts", "coworking_bureau__espaces_de_travail_ouverts", "Commercialisation", "coworking_bureau__espaces_de_travail_ouverts__commercialisation"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Salles de réunion", "coworking_bureau__salles_de_reunion", "Disponibilité & réservation", "coworking_bureau__salles_de_reunion__disponibilite_reservation"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Salles de réunion", "coworking_bureau__salles_de_reunion", "Propreté", "coworking_bureau__salles_de_reunion__proprete"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Salles de réunion", "coworking_bureau__salles_de_reunion", "Maintenance AV", "coworking_bureau__salles_de_reunion__maintenance_av"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Salles de réunion", "coworking_bureau__salles_de_reunion", "Expérience membre", "coworking_bureau__salles_de_reunion__experience_membre"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Salles de réunion", "coworking_bureau__salles_de_reunion", "Commercialisation", "coworking_bureau__salles_de_reunion__commercialisation"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Cuisine & espaces communs", "coworking_bureau__cuisine_espaces_communs", "Propreté & hygiène", "coworking_bureau__cuisine_espaces_communs__proprete_hygiene"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Cuisine & espaces communs", "coworking_bureau__cuisine_espaces_communs", "Stocks consommables", "coworking_bureau__cuisine_espaces_communs__stocks_consommables"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Cuisine & espaces communs", "coworking_bureau__cuisine_espaces_communs", "Maintenance équipements", "coworking_bureau__cuisine_espaces_communs__maintenance_equipements"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Accueil & communauté", "coworking_bureau__accueil_communaute", "Expérience membre", "coworking_bureau__accueil_communaute__experience_membre"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Accueil & communauté", "coworking_bureau__accueil_communaute", "Onboarding nouveaux membres", "coworking_bureau__accueil_communaute__onboarding_nouveaux_membres"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Accueil & communauté", "coworking_bureau__accueil_communaute", "Communication & événements", "coworking_bureau__accueil_communaute__communication_evenements"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Accueil & communauté", "coworking_bureau__accueil_communaute", "Sécurité & accès", "coworking_bureau__accueil_communaute__securite_acces"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Administration", "coworking_bureau__administration", "RH & planning", "coworking_bureau__administration__rh_planning"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Administration", "coworking_bureau__administration", "Facturation membres", "coworking_bureau__administration__facturation_membres"),
    _SeedRow("Coworking / Bureau", "coworking_bureau", "Administration", "coworking_bureau__administration", "Conformité légale", "coworking_bureau__administration__conformite_legale"),
    _SeedRow("Salle de sport", "salle_de_sport", "Plateau cardio & musculation", "salle_de_sport__plateau_cardio_musculation", "Propreté & hygiène", "salle_de_sport__plateau_cardio_musculation__proprete_hygiene"),
    _SeedRow("Salle de sport", "salle_de_sport", "Plateau cardio & musculation", "salle_de_sport__plateau_cardio_musculation", "Maintenance équipements", "salle_de_sport__plateau_cardio_musculation__maintenance_equipements"),
    _SeedRow("Salle de sport", "salle_de_sport", "Plateau cardio & musculation", "salle_de_sport__plateau_cardio_musculation", "Sécurité", "salle_de_sport__plateau_cardio_musculation__securite"),
    _SeedRow("Salle de sport", "salle_de_sport", "Plateau cardio & musculation", "salle_de_sport__plateau_cardio_musculation", "Expérience membre", "salle_de_sport__plateau_cardio_musculation__experience_membre"),
    _SeedRow("Salle de sport", "salle_de_sport", "Plateau cardio & musculation", "salle_de_sport__plateau_cardio_musculation", "Signalétique", "salle_de_sport__plateau_cardio_musculation__signaletique"),
    _SeedRow("Salle de sport", "salle_de_sport", "Studios cours collectifs", "salle_de_sport__studios_cours_collectifs", "Propreté", "salle_de_sport__studios_cours_collectifs__proprete"),
    _SeedRow("Salle de sport", "salle_de_sport", "Studios cours collectifs", "salle_de_sport__studios_cours_collectifs", "Maintenance équipements", "salle_de_sport__studios_cours_collectifs__maintenance_equipements"),
    _SeedRow("Salle de sport", "salle_de_sport", "Studios cours collectifs", "salle_de_sport__studios_cours_collectifs", "Planning & cours", "salle_de_sport__studios_cours_collectifs__planning_cours"),
    _SeedRow("Salle de sport", "salle_de_sport", "Studios cours collectifs", "salle_de_sport__studios_cours_collectifs", "Expérience membre", "salle_de_sport__studios_cours_collectifs__experience_membre"),
    _SeedRow("Salle de sport", "salle_de_sport", "Vestiaires & sanitaires", "salle_de_sport__vestiaires_sanitaires", "Propreté & hygiène", "salle_de_sport__vestiaires_sanitaires__proprete_hygiene"),
    _SeedRow("Salle de sport", "salle_de_sport", "Vestiaires & sanitaires", "salle_de_sport__vestiaires_sanitaires", "Maintenance", "salle_de_sport__vestiaires_sanitaires__maintenance"),
    _SeedRow("Salle de sport", "salle_de_sport", "Vestiaires & sanitaires", "salle_de_sport__vestiaires_sanitaires", "Sécurité", "salle_de_sport__vestiaires_sanitaires__securite"),
    _SeedRow("Salle de sport", "salle_de_sport", "Vestiaires & sanitaires", "salle_de_sport__vestiaires_sanitaires", "Conformité sanitaire", "salle_de_sport__vestiaires_sanitaires__conformite_sanitaire"),
    _SeedRow("Salle de sport", "salle_de_sport", "Accueil & réception", "salle_de_sport__accueil_reception", "Expérience membre", "salle_de_sport__accueil_reception__experience_membre"),
    _SeedRow("Salle de sport", "salle_de_sport", "Accueil & réception", "salle_de_sport__accueil_reception", "Abonnements & inscriptions", "salle_de_sport__accueil_reception__abonnements_inscriptions"),
    _SeedRow("Salle de sport", "salle_de_sport", "Accueil & réception", "salle_de_sport__accueil_reception", "Communication", "salle_de_sport__accueil_reception__communication"),
    _SeedRow("Salle de sport", "salle_de_sport", "Accueil & réception", "salle_de_sport__accueil_reception", "Sécurité & accès", "salle_de_sport__accueil_reception__securite_acces"),
    _SeedRow("Salle de sport", "salle_de_sport", "Accueil & réception", "salle_de_sport__accueil_reception", "Commercialisation", "salle_de_sport__accueil_reception__commercialisation"),
    _SeedRow("Salle de sport", "salle_de_sport", "Administration", "salle_de_sport__administration", "RH & planning", "salle_de_sport__administration__rh_planning"),
    _SeedRow("Salle de sport", "salle_de_sport", "Administration", "salle_de_sport__administration", "Conformité légale", "salle_de_sport__administration__conformite_legale"),
    _SeedRow("Salle de sport", "salle_de_sport", "Administration", "salle_de_sport__administration", "Fournisseurs", "salle_de_sport__administration__fournisseurs"),
    _SeedRow("Salle de sport", "salle_de_sport", "Administration", "salle_de_sport__administration", "Communication direction", "salle_de_sport__administration__communication_direction"),
    _SeedRow("Loisirs", "loisirs", "Acceuil site", "loisirs__accueil_site", "Expérience client", "loisirs__accueil_site__experience_client"),
    _SeedRow("Loisirs", "loisirs", "Acceuil site", "loisirs__accueil_site", "Propreté", "loisirs__accueil_site__proprete"),
    _SeedRow("Loisirs", "loisirs", "Acceuil site", "loisirs__accueil_site", "Sécurité & accès", "loisirs__accueil_site__securite_acces"),
    _SeedRow("Loisirs", "loisirs", "Acceuil site", "loisirs__accueil_site", "Signalétique", "loisirs__accueil_site__signaletique"),
    _SeedRow("Loisirs", "loisirs", "Acceuil site", "loisirs__accueil_site", "Gestion des files", "loisirs__accueil_site__gestion_des_files"),
    _SeedRow("Loisirs", "loisirs", "Acceuil site", "loisirs__accueil_site", "Commercialisation B2C", "loisirs__accueil_site__commercialisation_b2c"),
    _SeedRow("Loisirs", "loisirs", "Acceuil site", "loisirs__accueil_site", "Événements", "loisirs__accueil_site__evenements"),
    _SeedRow("Loisirs", "loisirs", "Acceuil site", "loisirs__accueil_site", "Communication", "loisirs__accueil_site__communication"),
    _SeedRow("Loisirs", "loisirs", "Acceuil site", "loisirs__accueil_site", "Commercialisation événements", "loisirs__accueil_site__commercialisation_evenements"),
    _SeedRow("Loisirs", "loisirs", "Activités & attractions", "loisirs__activites_attractions", "Sécurité", "loisirs__activites_attractions__securite"),
    _SeedRow("Loisirs", "loisirs", "Activités & attractions", "loisirs__activites_attractions", "Maintenance équipements", "loisirs__activites_attractions__maintenance_equipements"),
    _SeedRow("Loisirs", "loisirs", "Activités & attractions", "loisirs__activites_attractions", "Expérience client", "loisirs__activites_attractions__experience_client"),
    _SeedRow("Loisirs", "loisirs", "Activités & attractions", "loisirs__activites_attractions", "Conformité réglementaire", "loisirs__activites_attractions__conformite_reglementaire"),
    _SeedRow("Loisirs", "loisirs", "Activités & attractions", "loisirs__activites_attractions", "RH & planning", "loisirs__activites_attractions__rh_planning"),
    _SeedRow("Loisirs", "loisirs", "Restauration sur site", "loisirs__restauration_sur_site", "Expérience client", "loisirs__restauration_sur_site__experience_client"),
    _SeedRow("Loisirs", "loisirs", "Restauration sur site", "loisirs__restauration_sur_site", "Hygiène & HACCP", "loisirs__restauration_sur_site__hygiene_haccp"),
    _SeedRow("Loisirs", "loisirs", "Restauration sur site", "loisirs__restauration_sur_site", "Stocks", "loisirs__restauration_sur_site__stocks"),
    _SeedRow("Loisirs", "loisirs", "Restauration sur site", "loisirs__restauration_sur_site", "Propreté", "loisirs__restauration_sur_site__proprete"),
    _SeedRow("Loisirs", "loisirs", "Restauration sur site", "loisirs__restauration_sur_site", "Maintenance", "loisirs__restauration_sur_site__maintenance"),
    _SeedRow("Loisirs", "loisirs", "Espaces techniques", "loisirs__espaces_techniques", "Maintenance son & lumière", "loisirs__espaces_techniques__maintenance_son_lumiere"),
    _SeedRow("Loisirs", "loisirs", "Espaces techniques", "loisirs__espaces_techniques", "Sécurité technique", "loisirs__espaces_techniques__securite_technique"),
    _SeedRow("Loisirs", "loisirs", "Espaces techniques", "loisirs__espaces_techniques", "Conformité ERP", "loisirs__espaces_techniques__conformite_erp"),
    _SeedRow("Loisirs", "loisirs", "Espaces techniques", "loisirs__espaces_techniques", "Gestion des prestataires", "loisirs__espaces_techniques__gestion_des_prestataires"),
    _SeedRow("Loisirs", "loisirs", "Administration", "loisirs__administration", "RH & planning", "loisirs__administration__rh_planning"),
    _SeedRow("Loisirs", "loisirs", "Administration", "loisirs__administration", "Billetterie & caisse", "loisirs__administration__billetterie_caisse"),
    _SeedRow("Loisirs", "loisirs", "Administration", "loisirs__administration", "Conformité légale", "loisirs__administration__conformite_legale"),
    _SeedRow("Loisirs", "loisirs", "Administration", "loisirs__administration", "Fournisseurs", "loisirs__administration__fournisseurs"),
)


def catalog_module_rows() -> list[dict[str, str]]:
    seen: dict[str, str] = {}
    for row in SEED_ROWS:
        seen.setdefault(row.module_key, row.module_label)
    return [{"key": key, "label": label} for key, label in seen.items()]


def catalog_domain_rows() -> list[dict[str, str]]:
    seen: dict[str, dict[str, str]] = {}
    for row in SEED_ROWS:
        seen.setdefault(
            row.domain_key,
            {"key": row.domain_key, "label": row.domain_label, "module_key": row.module_key},
        )
    return list(seen.values())


def catalog_subject_rows() -> list[dict[str, str]]:
    return [
        {"key": row.subject_key, "label": row.subject_label, "domain_key": row.domain_key}
        for row in SEED_ROWS
    ]
