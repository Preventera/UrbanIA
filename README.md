# 🏙️ AX5 UrbanIA

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![FalkorDB](https://img.shields.io/badge/FalkorDB-Graph-blue.svg)](https://falkordb.com)
[![Claude 4.5](https://img.shields.io/badge/LLM-Claude%204.5-orange.svg)](https://anthropic.com)

**Suite de sécurité prédictive urbaine par IA agentique — Protéger les gens AUTOUR des chantiers**

> Premier système au monde qui croise lésions professionnelles (CNESST), accidents routiers en zone de travaux (SAAQ) et flux urbains temps réel pour prédire le risque piéton/cycliste autour des chantiers de construction.

---

## 🎯 Mission

Transformer la sécurité urbaine autour des chantiers de construction en passant d'un mode **réactif** (cônes orange, signalisation statique) à un mode **prédictif** (alertes calibrées sur données probantes, nudges ciblés par profil d'usager).

## ✨ Proposition de valeur

| Ce qui existe | Ce qu'AX5 UrbanIA apporte |
|---|---|
| Signalisation statique identique pour tous | Alertes différenciées pour 9 profils d'usagers |
| Données de sécurité cloisonnées | SafetyGraph unifié croisant 9 sources |
| Réaction après incident | Prédiction calibrée sur 54 403 lésions + 8 173 accidents zone travaux |
| Score de risque théorique | Score fondé sur sinistralité réelle CNESST + SAAQ |

## 🏗️ Architecture 3 Couches

```
┌─────────────────────────────────────────────────────────────────┐
│                    AX5 UrbanIA — SafetyGraph Unifié             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  COUCHE 1 — SUR le chantier (CNESST)                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 54 403 lésions Construction (2016-2022)                  │   │
│  │ CNESSTLesionsRAGAgent → Profils risque par type chantier │   │
│  │ Source: donneesquebec.ca | 13 colonnes | 7 fichiers CSV  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          ↕ SafetyGraph                          │
│  COUCHE 2 — EN TRANSIT à travers la zone (SAAQ SafeFleet)      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 8 173 accidents zone travaux routiers (2020-2022)        │   │
│  │ SAAQWorkZoneAgent → Risque piéton/cycliste par zone      │   │
│  │ Source: SAAQ données ouvertes | 25 colonnes | 303K total │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          ↕ SafetyGraph                          │
│  COUCHE 3 — AUTOUR du chantier (7 sources MTL)                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Entraves CIFS | Flux piétons | Comptages vélos           │   │
│  │ Capteurs Bluetooth | Permis AGIR | Météo | Bixi          │   │
│  │ UrbanFlowAgent → Exposition temps réel par zone          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  SORTIE: Score risque urbain calibré → Alertes 9 profils       │
│  Piéton | Cycliste | PMR | Automobiliste | TC | Livraison |    │
│  Urgence | Résident | Coordonnateur AGIR                       │
└─────────────────────────────────────────────────────────────────┘
```

## 🤖 Agents Spécialisés

| Agent | Source | Fonction | Priorité |
|-------|--------|----------|----------|
| `CNESSTLesionsRAGAgent` | 8ᵉ source RAG | Profils risque par type chantier SCIAN 23 | P0 |
| `SAAQWorkZoneAgent` | 9ᵉ source RAG | Risque piéton/cycliste zone travaux | P0 |
| `UrbanFlowAgent` | 7 sources MTL | Exposition temps réel flux urbains | P0 |
| `CoactivityAgent` | SafetyGraph | Détection coactivité inter-chantiers | P1 |
| `CascadeAgent` | SafetyGraph | Modélisation cascade réseau 3.7 km² | P1 |
| `NudgeAgent` | 9 profils | Communication différenciée par profil | P2 |

## 📊 Données intégrées

### Sources probantes (calibration)

| # | Source | Type | Volume | Colonne clé |
|---|--------|------|--------|-------------|
| 8 | CNESST Lésions | CSV ouvert | 54 403 Construction / 769K total | GENRE, AGENT_CAUSAL, NATURE_LESION |
| 9 | SAAQ Zone travaux | CSV ouvert | 8 173 zone travaux / 303K total | CD_ZON_TRAVX_ROUTR, IND_PIETON |

### Sources opérationnelles (temps réel MTL)

| # | Source | API | Fréquence |
|---|--------|-----|-----------|
| 1 | Entraves CIFS | donnees.montreal.ca | Temps réel |
| 2 | Comptages piétons | donnees.montreal.ca | Horaire |
| 3 | Comptages vélos | donnees.montreal.ca | Horaire |
| 4 | Capteurs Bluetooth | donnees.montreal.ca | 15 min |
| 5 | Permis AGIR | donnees.montreal.ca | Quotidien |
| 6 | Météo | api.weather.gc.ca | Horaire |
| 7 | Bixi stations | donnees.montreal.ca | 5 min |

## 📁 Structure du projet

```
AX5-UrbanIA/
├── src/
│   ├── agents/                     # Agents agentiques
│   │   ├── cnesst_lesions_agent.py # 8ᵉ source RAG - lésions professionnelles
│   │   ├── saaq_workzone_agent.py  # 9ᵉ source RAG - accidents zone travaux
│   │   ├── urban_flow_agent.py     # 7 sources MTL temps réel
│   │   ├── coactivity_agent.py     # Détection coactivité inter-chantiers
│   │   ├── cascade_agent.py        # Cascade réseau topologique
│   │   └── nudge_agent.py          # Communication 9 profils
│   ├── connectors/                 # Connecteurs données
│   │   ├── cnesst_connector.py     # Ingestion CSV CNESST
│   │   ├── saaq_connector.py       # Ingestion CSV SAAQ
│   │   ├── mtl_opendata.py         # API données ouvertes Montréal
│   │   ├── weather_connector.py    # API météo Canada
│   │   └── cifs_connector.py       # Entraves CIFS temps réel
│   ├── graph/                      # SafetyGraph
│   │   ├── schema.cypher           # Schéma FalkorDB
│   │   ├── safety_graph.py         # Gestionnaire SafetyGraph unifié
│   │   └── scoring.py              # Calcul score risque urbain
│   ├── api/                        # API FastAPI
│   │   ├── main.py                 # App FastAPI
│   │   ├── routes/                 # Endpoints
│   │   └── middleware/             # Auth, logging, CORS
│   ├── models/                     # Modèles prédictifs
│   │   ├── risk_profile.py         # Profil risque par type chantier
│   │   ├── urban_risk_score.py     # Score risque urbain composite
│   │   └── alert_thresholds.py     # Seuils alerte orange/rouge
│   └── utils/                      # Utilitaires
│       ├── constants.py            # Constantes SCIAN, régions, seuils
│       └── logging_config.py       # Configuration logging
├── data/
│   ├── cnesst/                     # CSV CNESST (gitignored, trop gros)
│   ├── saaq/                       # CSV SAAQ (gitignored, trop gros)
│   └── mtl_sources/                # Cache données MTL
├── config/
│   ├── settings.py                 # Configuration centralisée
│   ├── agents.yaml                 # Configuration agents
│   └── alert_rules.yaml            # Règles d'alerte par profil
├── dashboards/
│   └── urbania_dashboard.html      # Dashboard principal
├── docs/
│   ├── architecture_integration.md # Architecture 3 couches
│   ├── cnesst_data_schema.md       # Schéma 13 colonnes CNESST
│   ├── saaq_data_schema.md         # Schéma 25 colonnes SAAQ
│   └── comite_aviseur/             # Documents comité aviseur
├── tests/
│   ├── test_cnesst_agent.py
│   ├── test_saaq_agent.py
│   └── test_scoring.py
├── scripts/
│   ├── download_cnesst.py          # Téléchargement CSV CNESST
│   ├── download_saaq.py            # Téléchargement CSV SAAQ
│   └── seed_graph.py               # Initialisation SafetyGraph
├── .gitignore
├── .env.example
├── requirements.txt
├── pyproject.toml
├── docker-compose.yml
├── Dockerfile
├── LICENSE
└── README.md
```

## 🚀 Installation

```bash
# Cloner
git clone https://github.com/Preventera/UrbanIA.git
cd UrbanIA

# Environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Dépendances
pip install -r requirements.txt

# Configuration
cp .env.example .env
# Éditer .env avec vos clés API

# Télécharger données ouvertes
python scripts/download_cnesst.py
python scripts/download_saaq.py

# Initialiser SafetyGraph
docker-compose up -d falkordb
python scripts/seed_graph.py

# Lancer l'API
uvicorn src.api.main:app --reload
```

## 🐳 Docker

```bash
docker-compose up -d
# API: http://localhost:8000
# FalkorDB: http://localhost:6379
# Dashboard: http://localhost:3000
```

## 📈 KPIs cibles (Pilote MTL 90 jours)

| Indicateur | Baseline | Cible Phase 1 | Cible Phase 3 |
|------------|----------|---------------|---------------|
| Temps anticipation risque | 0 min | 30 min | 2h |
| Couverture prédictive zones | 0% | 40% | 85% |
| Précision alertes | N/A | 70% | 90% |
| Profils usagers actifs | 0/9 | 3/9 | 9/9 |
| Sources données intégrées | 0/9 | 4/9 | 9/9 |

## 🔒 Conformité & Éthique

- ✅ **Charte AgenticX5** : Primauté de la vie, HITL obligatoire
- ✅ **Loi 25 Québec** : Protection données personnelles
- ✅ **ISO 45001** : SST compatible
- ✅ **LSST / RSST / CSTC** : Réglementation SST Québec
- ✅ **Charte montréalaise** : Alignement droits et responsabilités

## 🔗 Écosystème AgenticX5

| Produit | Fonction | Lien SafetyGraph |
|---------|----------|-----------------|
| **HUGO / SafeTwinX5** | Sécurité SUR le chantier | Score conformité → UrbanIA |
| **SafeFleet-Hub** | Sécurité véhicules lourds | Accidents zone travaux → UrbanIA |
| **SafetyAgentic** | Pipeline ingestion données | BehaviorX + CNESST ABC → UrbanIA |
| **ConsultX5** | Consultation SST IA | 41 skills C23 → calibration agents |

## 📄 Licence

MIT License — voir [LICENSE](LICENSE)

## 📧 Contact

**GenAISafety / Preventera**
CAISO — Chief AI Strategy Officer
Québec, Canada

---

*AX5 UrbanIA — Le risque ne s'arrête pas à la clôture orange.*
