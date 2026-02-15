# AX5 UrbanIA — Sécurité prédictive urbaine par IA agentique

**GenAISafety / Preventera** | Pilote Montréal

> Orchestrateur agentique 3 couches qui croise 9 sources de données pour prédire et prévenir les incidents autour des chantiers urbains, protéger les usagers vulnérables et guider la coordination terrain.

---

## Architecture 3 couches

| Couche | Scope | Source | Agent | Données |
|--------|-------|--------|-------|---------|
| **C1 — SUR** le chantier | Lésions professionnelles | CNESST | `CNESSTLesionsRAGAgent` | 54 403 lésions Construction (2016-2022) |
| **C2 — EN TRANSIT** | Accidents zone de travaux | SAAQ | `SAAQWorkZoneAgent` | 8 173 accidents zone travaux (2020-2022) |
| **C3 — AUTOUR** | Flux urbains temps réel | MTL Open Data | `UrbanFlowAgent` | 7 sources temps réel |

### Score composite

```
Score = (C1 × 0.35 + C2 × 0.25 + C3 × 0.40) × Météo × Coactivité × Heure
```

Sévérité: 🟢 Normal (0-40) | 🟡 Attention (40-65) | 🟠 Élevé (65-85) | 🔴 Critique (85-100)

HITL obligatoire ≥ orange (Charte AgenticX5)

---

## Agents

### Couche 1 — CNESST
- **CNESSTLesionsRAGAgent** — 54 403 lésions, profils risque par SCIAN, 51.6% à composante urbaine, tendance TMS +79%

### Couche 2 — SAAQ
- **SAAQWorkZoneAgent** — 8 173 accidents zone travaux, 190 piétons, 119 cyclistes, croisement CNESST

### Couche 3 — MTL temps réel
- **UrbanFlowAgent** — Orchestre les 7 sources, score d'exposition par zone

### Agents avancés
- **CoactivityAgent** — Détection clusters de chantiers simultanés (<300m), multiplicateur de risque ×1.3 à ×2.5
- **CascadeAgent** — Modélisation effets cascade réseau 3.7 km² (détours → transfert de risque)
- **NudgeAgent** — Communication différenciée 9 profils usagers × 5 canaux × 2 langues

### Scoring
- **UrbanRiskScoringEngine** — Score composite 0-100 avec modulation météo/coactivité/heure

---

## Sources de données (9)

### Couche 3 — Connecteurs MTL
| # | Source | Connecteur | Refresh |
|---|--------|-----------|---------|
| 1 | Entraves CIFS | `cifs_connector.py` | Temps réel |
| 2 | Comptages piétons | `pedestrian_connector.py` | Horaire |
| 3 | Comptages vélos | `cycling_bluetooth_bixi.py` | Horaire |
| 4 | Capteurs Bluetooth | `cycling_bluetooth_bixi.py` | 15 min |
| 5 | Permis AGIR | Planifié | Quotidien |
| 6 | Météo Canada | `weather_connector.py` | Horaire |
| 7 | Stations Bixi | `cycling_bluetooth_bixi.py` | 5 min |

### Couche 1 & 2
| # | Source | Agent | Refresh |
|---|--------|-------|---------|
| 8 | CNESST Lésions | `cnesst_lesions_agent.py` | Annuel |
| 9 | SAAQ Zone travaux | `saaq_workzone_agent.py` | Annuel |

---

## SafetyGraph

Graphe de connaissances unifié (FalkorDB) qui croise les 3 couches:

```
ProfilRisqueChantier ──EXPORTS_RISK_TO──→ UrbanZone
WorkZoneRiskProfile ──CALIBRATES──→ UrbanZone
CoactivityCluster ──AMPLIFIES──→ UrbanZone
CascadeCorridor ──TRANSFERS_RISK_TO──→ CascadeHotspot
Alert ──TARGETS──→ UserProfile (×9)
```

---

## 9 profils usagers

| Profil | Vulnérabilité | Canaux |
|--------|:---:|--------|
| PMR | 10 | Push, SMS, Affichage |
| Piéton | 10 | Push, Affichage |
| Cycliste | 9 | Push, Affichage |
| Transport commun | 7 | Push, Affichage |
| Résident | 6 | Push, Email |
| Livraison | 5 | SMS, Push |
| Automobiliste | 4 | SMS, Affichage |
| Urgence | 3 | Radio, Dashboard |
| Coordonnateur AGIR | 0 | Dashboard, Email |

---

## API Endpoints

### Core
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/health` | Santé API + statut agents |
| GET | `/api/v1/score/{zone_id}` | Score risque composite |
| GET | `/api/v1/sources` | Liste 9 sources + statuts |

### Couche 3
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/snapshot` | Snapshot situation urbaine |
| GET | `/api/v1/weather` | Météo + facteur risque |
| GET | `/api/v1/entraves` | Entraves CIFS actives |

### RAG
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/cnesst/query` | Requête RAG CNESST |
| POST | `/api/v1/saaq/query` | Requête RAG SAAQ |
| POST | `/api/v1/urban/query` | Requête RAG MTL |

### Admin
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/graph/stats` | Stats SafetyGraph |
| POST | `/api/v1/refresh` | Rafraîchir 3 couches |

---

## Installation

```bash
# Cloner
git clone https://github.com/Preventera/UrbanIA.git
cd UrbanIA

# Dépendances
pip install -r requirements.txt

# Données CNESST + SAAQ
# Copier les CSV dans data/cnesst/ et data/saaq/

# Infrastructure
docker compose up -d    # FalkorDB + PostGIS

# Initialiser le SafetyGraph
python -m scripts.seed_graph

# Lancer l'API
uvicorn src.api.main:app --reload

# Tests
pytest tests/ -v
```

---

## Structure du projet

```
AX5-UrbanIA/
├── config/
│   ├── settings.py              # Configuration centralisée
│   └── agents.yaml              # Configuration agents
├── dashboards/
│   └── AX5-UrbanIA-Dashboard.jsx # Dashboard React 5 onglets
├── data/
│   ├── cnesst/                  # CSV CNESST (2016-2022)
│   ├── saaq/                    # CSV SAAQ (2020-2022)
│   └── mtl_sources/             # Cache données MTL
├── scripts/
│   ├── download_cnesst.py
│   ├── download_saaq.py
│   └── seed_graph.py            # Init SafetyGraph
├── src/
│   ├── agents/
│   │   ├── cnesst_lesions_agent.py    # C1 — 54 403 lésions
│   │   ├── saaq_workzone_agent.py     # C2 — 8 173 accidents
│   │   ├── urban_flow_agent.py        # C3 — 7 sources MTL
│   │   ├── coactivity_agent.py        # Détection coactivité
│   │   ├── cascade_agent.py           # Effets cascade réseau
│   │   └── nudge_agent.py             # 9 profils × 5 canaux
│   ├── api/
│   │   └── main.py                    # FastAPI v0.2.0
│   ├── connectors/
│   │   ├── mtl_opendata.py            # Client CKAN MTL
│   │   ├── cifs_connector.py          # Entraves temps réel
│   │   ├── weather_connector.py       # Env. Canada
│   │   ├── pedestrian_connector.py    # Comptages piétons
│   │   └── cycling_bluetooth_bixi.py  # Vélos + BT + Bixi
│   ├── graph/
│   │   ├── schema.cypher              # Schema FalkorDB
│   │   └── safety_graph.py            # SafetyGraph Manager
│   ├── models/
│   │   └── urban_risk_score.py        # Scoring composite
│   └── utils/
│       └── constants.py               # Mappings & seuils
├── tests/
│   └── test_all.py                    # Suite de tests
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Conformité

- **Charte AgenticX5** — Primauté de la vie, HITL obligatoire ≥ orange
- **ISO 45001** — Cadre SST
- **CNESST** — Conformité loi SST Québec
- **RGPD / Loi 25** — Données personnelles

---

## Croisement unique

```
34 100 événements (2020-2022)
= 54 403 lésions CNESST × 8 173 accidents SAAQ
× 7 sources temps réel MTL
```

**Aucun compétiteur ne croise ces 3 couches.**

---

*GenAISafety / Preventera — AX5 UrbanIA v0.2.0*
