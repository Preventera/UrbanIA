"""
=============================================================================
AX5 UrbanIA — API FastAPI
=============================================================================
API principale pour la suite de sécurité prédictive urbaine.
Expose les scores de risque, alertes et données des 3 couches.

Endpoints:
  /health              → Santé de l'API
  /api/v1/score/{zone} → Score risque urbain composite
  /api/v1/alerts       → Alertes actives
  /api/v1/cnesst/query → Requête RAG données CNESST
  /api/v1/saaq/query   → Requête RAG données SAAQ
  /api/v1/sources      → Statut des 9 sources de données
=============================================================================
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agents.cnesst_lesions_agent import CNESSTLesionsRAGAgent
from src.agents.saaq_workzone_agent import SAAQWorkZoneAgent
from src.models.urban_risk_score import UrbanRiskScoringEngine

logger = logging.getLogger(__name__)

# =============================================================================
# MODELS
# =============================================================================

class ScoreResponse(BaseModel):
    zone_id: str
    score: float
    severity: str
    requires_hitl: bool
    couche1_cnesst: float
    couche2_saaq: float
    couche3_mtl: float
    confidence: str
    sources_used: list
    target_profiles: list


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    source: str
    agent_id: str


# =============================================================================
# APP LIFECYCLE
# =============================================================================

agents = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise les agents au démarrage."""
    logger.info("🚀 AX5 UrbanIA API — Démarrage")

    # Initialiser les agents
    agents["cnesst"] = CNESSTLesionsRAGAgent()
    agents["saaq"] = SAAQWorkZoneAgent()
    agents["scoring"] = UrbanRiskScoringEngine()

    # Charger les données si disponibles
    try:
        agents["cnesst"].load_csv_files()
        agents["cnesst"].compute_urban_risk_export()
        logger.info("✅ CNESSTLesionsRAGAgent chargé")
    except Exception as e:
        logger.warning(f"⚠️ CNESST non chargé: {e}")

    try:
        agents["saaq"].load_csv_files()
        agents["saaq"].build_risk_profiles()
        logger.info("✅ SAAQWorkZoneAgent chargé")
    except Exception as e:
        logger.warning(f"⚠️ SAAQ non chargé: {e}")

    yield

    logger.info("🛑 AX5 UrbanIA API — Arrêt")


# =============================================================================
# APP
# =============================================================================

app = FastAPI(
    title="AX5 UrbanIA API",
    description=(
        "Suite de sécurité prédictive urbaine par IA agentique. "
        "Protéger les gens AUTOUR des chantiers."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Santé de l'API et statut des agents."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "agents": {
            "cnesst": agents.get("cnesst") is not None,
            "saaq": agents.get("saaq") is not None,
            "scoring": agents.get("scoring") is not None,
        },
    }


@app.get("/api/v1/score/{zone_id}", response_model=ScoreResponse)
async def get_risk_score(zone_id: str):
    """
    Calcule le score de risque urbain composite pour une zone.
    Combine les 3 couches: CNESST + SAAQ + MTL.
    """
    scoring = agents.get("scoring")
    if not scoring:
        raise HTTPException(500, "Moteur de scoring non disponible")

    cnesst_agent = agents.get("cnesst")
    saaq_agent = agents.get("saaq")

    cnesst_data = None
    if cnesst_agent and cnesst_agent._loaded:
        profile = cnesst_agent.risk_profiles.get("23")
        if profile:
            cnesst_data = {
                "urban_risk_score": profile.urban_risk_score,
                "taux_tms_pct": profile.taux_tms,
                "trend_yoy_pct": profile.trend_yoy,
            }

    saaq_data = None
    if saaq_agent and saaq_agent._loaded:
        mtl_profile = saaq_agent.risk_profiles.get("montréal")
        if mtl_profile:
            saaq_data = {
                "risk_score": mtl_profile.risk_score,
                "accidents_pietons": mtl_profile.accidents_pietons,
                "accidents_cyclistes": mtl_profile.accidents_cyclistes,
                "accidents_mortels_graves": mtl_profile.accidents_mortels_graves,
                "accidents_veh_lourds": mtl_profile.accidents_veh_lourds,
            }

    # TODO: Intégrer données temps réel MTL (Couche 3)
    mtl_data = {
        "flux_pietons": 0,
        "flux_cyclistes": 0,
        "entraves_actives": 0,
        "sources_active": [],
    }

    score = scoring.compute_score(zone_id, cnesst_data, saaq_data, mtl_data)

    return ScoreResponse(
        zone_id=score.zone_id,
        score=score.score,
        severity=score.severity,
        requires_hitl=score.requires_hitl,
        couche1_cnesst=score.couche1_cnesst,
        couche2_saaq=score.couche2_saaq,
        couche3_mtl=score.couche3_mtl,
        confidence=score.confidence,
        sources_used=score.sources_used or [],
        target_profiles=score.target_profiles or [],
    )


@app.post("/api/v1/cnesst/query", response_model=QueryResponse)
async def query_cnesst(req: QueryRequest):
    """Requête RAG sur les données CNESST Construction."""
    agent = agents.get("cnesst")
    if not agent:
        raise HTTPException(503, "CNESSTLesionsRAGAgent non disponible")

    answer = agent.query(req.question)
    return QueryResponse(
        answer=answer,
        source="CNESST données ouvertes (2016-2022)",
        agent_id=agent.AGENT_ID,
    )


@app.post("/api/v1/saaq/query", response_model=QueryResponse)
async def query_saaq(req: QueryRequest):
    """Requête RAG sur les données SAAQ zone travaux."""
    agent = agents.get("saaq")
    if not agent:
        raise HTTPException(503, "SAAQWorkZoneAgent non disponible")

    answer = agent.query(req.question)
    return QueryResponse(
        answer=answer,
        source="SAAQ données ouvertes (2020-2022)",
        agent_id=agent.AGENT_ID,
    )


@app.get("/api/v1/sources")
async def list_sources():
    """Liste les 9 sources de données et leur statut."""
    sources = [
        {"id": 1, "name": "Entraves CIFS", "couche": 3, "type": "operationnelle", "status": "planned"},
        {"id": 2, "name": "Comptages piétons", "couche": 3, "type": "operationnelle", "status": "planned"},
        {"id": 3, "name": "Comptages vélos", "couche": 3, "type": "operationnelle", "status": "planned"},
        {"id": 4, "name": "Capteurs Bluetooth", "couche": 3, "type": "operationnelle", "status": "planned"},
        {"id": 5, "name": "Permis AGIR", "couche": 3, "type": "operationnelle", "status": "planned"},
        {"id": 6, "name": "Météo Canada", "couche": 3, "type": "operationnelle", "status": "planned"},
        {"id": 7, "name": "Stations Bixi", "couche": 3, "type": "operationnelle", "status": "planned"},
    ]

    cnesst = agents.get("cnesst")
    if cnesst and cnesst._loaded:
        profile = cnesst.risk_profiles.get("23")
        sources.append({
            "id": 8, "name": "CNESST Lésions", "couche": 1, "type": "probante",
            "status": "active", "records": profile.total_lesions if profile else 0,
        })
    else:
        sources.append({"id": 8, "name": "CNESST Lésions", "couche": 1, "type": "probante", "status": "inactive"})

    saaq = agents.get("saaq")
    if saaq and saaq._loaded:
        gp = saaq.risk_profiles.get("global")
        sources.append({
            "id": 9, "name": "SAAQ Zone travaux", "couche": 2, "type": "probante",
            "status": "active", "records": gp.total_accidents if gp else 0,
        })
    else:
        sources.append({"id": 9, "name": "SAAQ Zone travaux", "couche": 2, "type": "probante", "status": "inactive"})

    return {"sources": sources, "total": len(sources), "active": sum(1 for s in sources if s.get("status") == "active")}
