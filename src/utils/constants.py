"""
AX5 UrbanIA — Constantes et mappings fondamentaux
Calibré sur 54 403 lésions CNESST + 8 173 accidents SAAQ zone travaux
"""

# =============================================================
# SCIAN 23 — Sous-secteurs Construction
# =============================================================
SCIAN_CONSTRUCTION = {
    "23": "Construction (tous)",
    "236": "Construction de bâtiments résidentiels",
    "237": "Travaux de génie civil",
    "238": "Entrepreneurs spécialisés",
    "238110": "Coulage béton et fondations",
    "238120": "Charpenterie",
    "238130": "Travaux d'acier de charpente",
    "238140": "Maçonnerie",
    "238150": "Travaux de vitrage",
    "238160": "Toiture",
    "238210": "Électricité",
    "238220": "Plomberie, chauffage, climatisation",
    "238310": "Finition bâtiments",
    "238910": "Préparation de sites",
    "238990": "Autres entrepreneurs spécialisés",
}

# =============================================================
# GENRE d'accident CNESST → Score risque urbain exporté (0-10)
# =============================================================
GENRE_URBAN_RISK_SCORE = {
    "ACCIDENT DE LA ROUTE": 10,
    "FRAPPE PAR UN OBJET": 9,
    "CHUTE A UN NIVEAU INFERIEUR": 7,
    "COINCE,ECRASE PAR EQUIPEMENT,OBJET": 6,
    "HEURTER UN OBJET": 5,
    "CHUTE AU MEME NIVEAU": 4,
    "REACTION DU CORPS": 2,
    "EFFORT EXCESSIF": 2,
    "EXPOSIT. SUBSTANCES NOCIVES,ENVIRONN.": 3,
    "CONTACT AVEC OBJET CHAUD OU FROID": 3,
    "CONTACT AVEC COURANT ELECTRIQUE": 4,
    "GENRE NON CLASSIFIE": 3,
}

# =============================================================
# AGENT CAUSAL CNESST → Profil chantier
# =============================================================
AGENT_CAUSAL_CHANTIER_PROFIL = {
    "ECHELLES": "travaux_hauteur",
    "MATERIAUX CONSTRUC.-ELEMENTS SOLIDES": "levage_grutage",
    "VEHICULES ROUTIERS MOTORISES": "travaux_routiers",
    "PLANCHERS,PASSAGES,SURFACES DE SOL": "excavation_terrassement",
    "OUTILS A MAIN-NON MECANIQUES": "finition",
    "DECHETS,REBUTS,DEBRIS": "demolition",
    "PIECE DE MACHINE,D'OUTIL,ELECTRIQUE": "equipement_lourd",
    "STRUCTURES,SURFACES-EXTERIEUR": "structure",
}

# =============================================================
# GENRE SAAQ → Type collision urbaine
# =============================================================
SAAQ_GENRE_ACCIDENT = {
    "véhicule": "collision_vehicule",
    "objet fixe": "collision_objet_fixe",
    "piéton": "collision_pieton",
    "cycliste": "collision_cycliste",
    "sans collision": "sans_collision",
    "animal": "collision_animal",
    "autre": "autre",
}

# =============================================================
# GRAVITÉ SAAQ → Poids scoring
# =============================================================
SAAQ_GRAVITE_POIDS = {
    "Mortel ou grave": 10.0,
    "Léger": 5.0,
    "Dommages matériels seulement": 1.0,
    "Dommages matériels inférieurs au seuil de rapportage": 0.5,
}

# =============================================================
# 9 PROFILS USAGERS UrbanIA
# =============================================================
USER_PROFILES = {
    "pieton": {
        "id": "P01",
        "label": "Piéton",
        "vulnerability": 10,
        "alert_channels": ["app_mobile", "panneau_dynamique"],
    },
    "cycliste": {
        "id": "P02",
        "label": "Cycliste",
        "vulnerability": 9,
        "alert_channels": ["app_velo", "panneau_piste"],
    },
    "pmr": {
        "id": "P03",
        "label": "Personne à mobilité réduite",
        "vulnerability": 10,
        "alert_channels": ["app_mobile", "notification_accompagnant"],
    },
    "automobiliste": {
        "id": "P04",
        "label": "Automobiliste",
        "vulnerability": 4,
        "alert_channels": ["waze_integration", "panneau_variable"],
    },
    "transport_commun": {
        "id": "P05",
        "label": "Usager transport en commun",
        "vulnerability": 7,
        "alert_channels": ["stm_api", "arret_dynamique"],
    },
    "livraison": {
        "id": "P06",
        "label": "Livreur / logistique",
        "vulnerability": 5,
        "alert_channels": ["fleet_api", "app_mobile"],
    },
    "urgence": {
        "id": "P07",
        "label": "Services d'urgence",
        "vulnerability": 3,
        "alert_channels": ["cad_integration", "corridor_prioritaire"],
    },
    "resident": {
        "id": "P08",
        "label": "Résident riverain",
        "vulnerability": 6,
        "alert_channels": ["app_mobile", "email", "sms"],
    },
    "coordonnateur_agir": {
        "id": "P09",
        "label": "Coordonnateur AGIR (Ville)",
        "vulnerability": 0,
        "alert_channels": ["dashboard", "rapport_automatise"],
    },
}

# =============================================================
# SEUILS D'ALERTE
# =============================================================
ALERT_THRESHOLDS = {
    "green": {"min": 0, "max": 40, "label": "Normal", "action": "Surveillance standard"},
    "yellow": {"min": 40, "max": 65, "label": "Attention", "action": "Vigilance accrue"},
    "orange": {"min": 65, "max": 85, "label": "Élevé", "action": "Alertes ciblées + HITL"},
    "red": {"min": 85, "max": 100, "label": "Critique", "action": "Intervention immédiate + HITL obligatoire"},
}

# =============================================================
# SKILLS CONSTRUCTION C23 (lien AgenticX5/HUGO)
# =============================================================
SKILLS_C23 = {
    "C23-R01": "Chutes de hauteur",
    "C23-R02": "Excavation et tranchées",
    "C23-R03": "Grues et levage",
    "C23-R04": "Échafaudages",
    "C23-R05": "Démolition",
    "C23-R06": "Travaux routiers",
    "C23-CO01": "Code sécurité travaux construction (CSTC)",
    "C23-CO02": "Programme de prévention maître d'œuvre",
    "C23-PSY01": "Santé psychologique chantier",
}

# =============================================================
# 7 SOURCES DONNÉES OUVERTES MONTRÉAL
# =============================================================
MTL_SOURCES = {
    "cifs": {
        "name": "Entraves CIFS",
        "dataset": "entraves",
        "refresh": "temps_reel",
        "url": "https://donnees.montreal.ca/dataset/entraves",
    },
    "pietons": {
        "name": "Comptages piétons",
        "dataset": "comptage-pietons",
        "refresh": "horaire",
        "url": "https://donnees.montreal.ca/dataset/comptage-pietons",
    },
    "velos": {
        "name": "Comptages vélos",
        "dataset": "velos-comptage",
        "refresh": "horaire",
        "url": "https://donnees.montreal.ca/dataset/velos-comptage",
    },
    "bluetooth": {
        "name": "Capteurs Bluetooth",
        "dataset": "bluetooth",
        "refresh": "15min",
        "url": "https://donnees.montreal.ca/dataset/bluetooth",
    },
    "agir": {
        "name": "Permis AGIR",
        "dataset": "permis-agir",
        "refresh": "quotidien",
        "url": "https://donnees.montreal.ca/dataset/permis-agir",
    },
    "meteo": {
        "name": "Météo",
        "source": "api.weather.gc.ca",
        "refresh": "horaire",
        "url": "https://api.weather.gc.ca",
    },
    "bixi": {
        "name": "Stations Bixi",
        "dataset": "bixi",
        "refresh": "5min",
        "url": "https://donnees.montreal.ca/dataset/bixi",
    },
}
