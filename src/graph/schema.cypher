// =============================================================================
// AX5 URBANIA — SAFETYGRAPH SCHEMA (FalkorDB)
// Version: 1.0.0
// Date: 2026-02-15
// Purpose: Graphe de connaissances unifié 3 couches (CNESST + SAAQ + MTL)
// =============================================================================

// =============================================================================
// 1. COUCHE 1 — NŒUDS CNESST (SUR le chantier)
// =============================================================================

// Profil de risque par type de chantier Construction SCIAN 23
CREATE (:ProfilRisqueChantier {
    id: STRING,                    // "cnesst-construction-23"
    scian_code: STRING,            // "23", "236", "237", "238"
    scian_label: STRING,           // "Construction (tous)"
    total_lesions: INTEGER,        // 54 403
    urban_risk_score: FLOAT,       // Score moyen 0-10
    taux_tms_pct: FLOAT,          // 26.0%
    taux_machine_pct: FLOAT,      // 5.3%
    trend_yoy_pct: FLOAT,         // +53.1%
    source: STRING,                // "CNESST données ouvertes"
    agent_id: STRING               // "cnesst-lesions-rag"
})

// Score de risque urbain exporté par genre d'accident
CREATE (:ScoreRisqueUrbain {
    id: STRING,                    // "urban-risk-frappe-par-objet"
    genre_accident: STRING,        // "FRAPPE PAR UN OBJET"
    count: INTEGER,                // 7 847
    pct_total: FLOAT,             // 14.4%
    urban_risk_score: INTEGER,     // 9 (sur 10)
    impact_urbain: STRING          // "Risque direct chute objets sur piétons"
})

// Profil agent causal → signature de chantier
CREATE (:ProfilAgentCausal {
    id: STRING,                    // "agent-echelles"
    agent_causal: STRING,          // "ECHELLES"
    count: INTEGER,                // 1 218
    chantier_profil: STRING,       // "travaux_hauteur"
    urban_implication: STRING      // "Zone exclusion piéton r=15m"
})

// Tendance TMS (série temporelle)
CREATE (:TendanceTMS {
    id: STRING,                    // "tms-2022"
    year: INTEGER,
    tms_count: INTEGER,
    growth_pct: FLOAT
})

// =============================================================================
// 2. COUCHE 2 — NŒUDS SAAQ (EN TRANSIT zone travaux)
// =============================================================================

// Profil zone travaux par région
CREATE (:WorkZoneRiskProfile {
    id: STRING,                    // "saaq-workzone-montreal"
    region: STRING,                // "Montréal (06)"
    total_accidents: INTEGER,      // 2 995
    accidents_pietons: INTEGER,    // 108
    accidents_cyclistes: INTEGER,  // 91
    accidents_mortels_graves: INTEGER, // 24
    accidents_veh_lourds: INTEGER, // nombre
    risk_score: FLOAT,            // Score pondéré gravité
    peak_hours: STRING,           // "12:00-15:59,08:00-11:59"
    source: STRING,                // "SAAQ données ouvertes"
    agent_id: STRING               // "saaq-workzone-rag"
})

// Usager vulnérable en zone travaux
CREATE (:VulnerableUser {
    id: STRING,                    // "vu-pieton-mtl"
    type: STRING,                  // "pieton", "cycliste", "pmr"
    region: STRING,
    accidents_count: INTEGER,
    severity_distribution: STRING  // JSON des gravités
})

// =============================================================================
// 3. COUCHE 3 — NŒUDS MTL (AUTOUR du chantier)
// =============================================================================

// Zone urbaine surveillée
CREATE (:UrbanZone {
    id: STRING,                    // "zone-ville-marie-01"
    arrondissement: STRING,        // "Ville-Marie"
    latitude: FLOAT,
    longitude: FLOAT,
    radius_m: INTEGER,             // 500
    active_chantiers: INTEGER,
    flux_pietons_jour: INTEGER,
    flux_cyclistes_jour: INTEGER,
    score_risque_composite: FLOAT  // Score calibré 3 couches
})

// Entrave CIFS (chantier actif)
CREATE (:EntraveCIFS {
    id: STRING,
    type_entrave: STRING,          // "occupation_chaussee", "fermeture"
    rue: STRING,
    date_debut: DATE,
    date_fin: DATE,
    latitude: FLOAT,
    longitude: FLOAT,
    impact_score: FLOAT
})

// Source de données
CREATE (:DataSource {
    id: STRING,                    // "cnesst", "saaq", "cifs", etc.
    name: STRING,
    type: STRING,                  // "probante", "operationnelle"
    refresh_rate: STRING,          // "annuel", "temps_reel"
    total_records: INTEGER,
    couche: INTEGER                // 1, 2, ou 3
})

// =============================================================================
// 4. NŒUDS TRANSVERSAUX
// =============================================================================

// Alerte générée
CREATE (:Alert {
    id: STRING,
    timestamp: DATETIME,
    zone_id: STRING,
    severity: STRING,              // "green", "yellow", "orange", "red"
    score: FLOAT,
    target_profiles: STRING,       // "pieton,cycliste,pmr"
    message: STRING,
    requires_hitl: BOOLEAN,
    sources_used: STRING           // "cnesst,saaq,cifs,meteo"
})

// Profil usager (anonymisé)
CREATE (:UserProfile {
    id: STRING,                    // "P01" à "P09"
    label: STRING,                 // "Piéton"
    vulnerability_score: INTEGER,  // 0-10
    alert_channels: STRING         // "app_mobile,panneau_dynamique"
})

// =============================================================================
// 5. RELATIONS
// =============================================================================

// Couche 1 → SafetyGraph
// (p:ProfilRisqueChantier)-[:EXPORTS_RISK_TO]->(z:UrbanZone)
// (s:ScoreRisqueUrbain)-[:CALIBRATES]->(a:Alert)
// (a:ProfilAgentCausal)-[:MAPS_TO]->(e:EntraveCIFS)

// Couche 2 → SafetyGraph
// (w:WorkZoneRiskProfile)-[:INFORMS]->(z:UrbanZone)
// (v:VulnerableUser)-[:EXPOSED_IN]->(z:UrbanZone)
// (w:WorkZoneRiskProfile)-[:CROSS_REFERENCES]->(p:ProfilRisqueChantier)

// Couche 3 → SafetyGraph
// (e:EntraveCIFS)-[:LOCATED_IN]->(z:UrbanZone)
// (z:UrbanZone)-[:GENERATES]->(a:Alert)
// (a:Alert)-[:TARGETS]->(u:UserProfile)

// Sources
// (d:DataSource)-[:FEEDS]->(p:ProfilRisqueChantier)  // CNESST → Couche 1
// (d:DataSource)-[:FEEDS]->(w:WorkZoneRiskProfile)    // SAAQ → Couche 2
// (d:DataSource)-[:FEEDS]->(e:EntraveCIFS)            // CIFS → Couche 3

// =============================================================================
// 6. INDEXES
// =============================================================================

CREATE INDEX FOR (p:ProfilRisqueChantier) ON (p.id)
CREATE INDEX FOR (p:ProfilRisqueChantier) ON (p.scian_code)
CREATE INDEX FOR (s:ScoreRisqueUrbain) ON (s.id)
CREATE INDEX FOR (w:WorkZoneRiskProfile) ON (w.id)
CREATE INDEX FOR (w:WorkZoneRiskProfile) ON (w.region)
CREATE INDEX FOR (v:VulnerableUser) ON (v.type)
CREATE INDEX FOR (z:UrbanZone) ON (z.id)
CREATE INDEX FOR (z:UrbanZone) ON (z.arrondissement)
CREATE INDEX FOR (e:EntraveCIFS) ON (e.id)
CREATE INDEX FOR (a:Alert) ON (a.timestamp)
CREATE INDEX FOR (a:Alert) ON (a.severity)
CREATE INDEX FOR (u:UserProfile) ON (u.id)
CREATE INDEX FOR (d:DataSource) ON (d.id)

// Full-text search
CREATE INDEX FOR (z:UrbanZone) ON (z.arrondissement)
CREATE INDEX FOR (e:EntraveCIFS) ON (e.rue)

// =============================================================================
// 7. CONSTRAINTS
// =============================================================================

CREATE CONSTRAINT FOR (p:ProfilRisqueChantier) REQUIRE p.id IS UNIQUE
CREATE CONSTRAINT FOR (s:ScoreRisqueUrbain) REQUIRE s.id IS UNIQUE
CREATE CONSTRAINT FOR (w:WorkZoneRiskProfile) REQUIRE w.id IS UNIQUE
CREATE CONSTRAINT FOR (z:UrbanZone) REQUIRE z.id IS UNIQUE
CREATE CONSTRAINT FOR (e:EntraveCIFS) REQUIRE e.id IS UNIQUE
CREATE CONSTRAINT FOR (a:Alert) REQUIRE a.id IS UNIQUE
CREATE CONSTRAINT FOR (u:UserProfile) REQUIRE u.id IS UNIQUE
CREATE CONSTRAINT FOR (d:DataSource) REQUIRE d.id IS UNIQUE
