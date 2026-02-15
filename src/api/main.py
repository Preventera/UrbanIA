"""
=============================================================================
AX5 UrbanIA — API FastAPI v0.2.0
=============================================================================
API avec intégration complète des 3 couches:
  Couche 1: CNESSTLesionsRAGAgent (54 403 lésions)
  Couche 2: SAAQWorkZoneAgent (8 173 accidents zone travaux)
  Couche 3: UrbanFlowAgent (7 sources MTL temps réel)

Nouveaux endpoints:
  /api/v1/snapshot    → Snapshot complet situation urbaine
  /api/v1/weather     → Conditions météo + facteur risque
  /api/v1/entraves    → Entraves CIFS actives
  /api/v1/graph/stats → Stats du SafetyGraph
  /api/v1/refresh     → Rafraîchir toutes les couches
=============================================================================
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agents.cnesst_lesions_agent import CNESSTLesionsRAGAgent
from src.agents.saaq_workzone_agent import SAAQWorkZoneAgent
from src.agents.urban_flow_agent import UrbanFlowAgent
from src.models.urban_risk_score import UrbanRiskScoringEngine
from src.graph.safety_graph import SafetyGraphManager

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
    logger.info("🚀 AX5 UrbanIA API v0.2.0 — Démarrage")

    # Agents Couche 1 + 2
    agents["cnesst"] = CNESSTLesionsRAGAgent()
    agents["saaq"] = SAAQWorkZoneAgent()

    # Agent Couche 3
    agents["urban_flow"] = UrbanFlowAgent()

    # Scoring engine
    agents["scoring"] = UrbanRiskScoringEngine()

    # SafetyGraph
    agents["graph"] = SafetyGraphManager()
    agents["graph"].connect()

    # Charger données probantes
    for name, agent in [("cnesst", agents["cnesst"]), ("saaq", agents["saaq"])]:
        try:
            agent.load_csv_files()
            if name == "cnesst":
                agent.compute_urban_risk_export()
            else:
                agent.build_risk_profiles()
            logger.info(f"✅ {name} chargé")
        except Exception as e:
            logger.warning(f"⚠️ {name}: {e}")

    yield

    # Shutdown
    await agents["urban_flow"].close()
    agents["graph"].close()
    logger.info("🛑 AX5 UrbanIA API — Arrêt")


# =============================================================================
# APP
# =============================================================================

app = FastAPI(
    title="AX5 UrbanIA API",
    description="Sécurité prédictive urbaine — 3 couches, 9 sources, 1 SafetyGraph",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# =============================================================================
# ENDPOINTS — CORE
# =============================================================================

@app.get("/health")
async def health():
    graph = agents.get("graph")
    return {
        "status": "ok",
        "version": "0.2.0",
        "agents": {
            "cnesst": getattr(agents.get("cnesst"), "_loaded", False),
            "saaq": getattr(agents.get("saaq"), "_loaded", False),
            "urban_flow": agents.get("urban_flow") is not None,
            "scoring": agents.get("scoring") is not None,
            "graph": graph.is_connected() if graph else False,
        },
    }


@app.get("/api/v1/score/{zone_id}", response_model=ScoreResponse)
async def get_risk_score(zone_id: str):
    """Score risque urbain composite pour une zone (3 couches)."""
    scoring = agents["scoring"]
    cnesst = agents["cnesst"]
    saaq = agents["saaq"]
    urban_flow = agents["urban_flow"]

    # Couche 1
    cnesst_data = None
    if getattr(cnesst, "_loaded", False):
        p = cnesst.risk_profiles.get("23")
        if p:
            cnesst_data = {"urban_risk_score": p.urban_risk_score, "taux_tms_pct": p.taux_tms, "trend_yoy_pct": p.trend_yoy}

    # Couche 2
    saaq_data = None
    if getattr(saaq, "_loaded", False):
        mp = saaq.risk_profiles.get("montréal")
        if mp:
            saaq_data = {
                "risk_score": mp.risk_score, "accidents_pietons": mp.accidents_pietons,
                "accidents_cyclistes": mp.accidents_cyclistes,
                "accidents_mortels_graves": mp.accidents_mortels_graves,
                "accidents_veh_lourds": mp.accidents_veh_lourds,
            }

    # Couche 3
    mtl_data = urban_flow.get_zone_data_for_scoring(zone_id)

    score = scoring.compute_score(zone_id, cnesst_data, saaq_data, mtl_data)

    return ScoreResponse(
        zone_id=score.zone_id, score=score.score, severity=score.severity,
        requires_hitl=score.requires_hitl, couche1_cnesst=score.couche1_cnesst,
        couche2_saaq=score.couche2_saaq, couche3_mtl=score.couche3_mtl,
        confidence=score.confidence, sources_used=score.sources_used or [],
        target_profiles=score.target_profiles or [],
    )


# =============================================================================
# ENDPOINTS — COUCHE 3
# =============================================================================

@app.get("/api/v1/snapshot")
async def get_urban_snapshot():
    """Snapshot complet de la situation urbaine Montréal."""
    agent = agents["urban_flow"]
    snapshot = await agent.collect_all_sources()

    return {
        "timestamp": snapshot.timestamp,
        "total_entraves": snapshot.total_entraves,
        "total_zones_coactivite": snapshot.total_zones_coactivite,
        "weather": {"factor": snapshot.weather_factor, "condition": snapshot.weather_condition},
        "sources": {"active": snapshot.sources_active, "total": snapshot.sources_total},
        "zones": [
            {
                "zone_id": z.zone_id, "arrondissement": z.arrondissement,
                "exposure_score": z.exposure_score, "entraves": z.entraves_actives,
                "flux_pietons": z.flux_pietons, "flux_cyclistes": z.flux_cyclistes,
                "coactivity_factor": z.coactivity_factor,
            }
            for z in snapshot.zones
        ],
    }


@app.get("/api/v1/weather")
async def get_weather():
    """Conditions météo + facteur de risque."""
    weather = agents["urban_flow"].weather
    current = await weather.fetch_current()
    return weather.get_risk_factor()


@app.get("/api/v1/entraves")
async def get_entraves():
    """Entraves CIFS actives."""
    cifs = agents["urban_flow"].cifs
    summary = await cifs.get_summary()
    return {
        "total": summary.total_entraves,
        "par_arrondissement": summary.par_arrondissement,
        "par_type": summary.par_type,
        "zones_coactivite": summary.zones_coactivite,
        "timestamp": summary.timestamp,
    }


# =============================================================================
# ENDPOINTS — RAG
# =============================================================================

@app.post("/api/v1/cnesst/query", response_model=QueryResponse)
async def query_cnesst(req: QueryRequest):
    agent = agents["cnesst"]
    return QueryResponse(answer=agent.query(req.question), source="CNESST (2016-2022)", agent_id=agent.AGENT_ID)


@app.post("/api/v1/saaq/query", response_model=QueryResponse)
async def query_saaq(req: QueryRequest):
    agent = agents["saaq"]
    return QueryResponse(answer=agent.query(req.question), source="SAAQ (2020-2022)", agent_id=agent.AGENT_ID)


@app.post("/api/v1/urban/query", response_model=QueryResponse)
async def query_urban(req: QueryRequest):
    agent = agents["urban_flow"]
    return QueryResponse(answer=agent.query(req.question), source="MTL temps réel", agent_id=agent.AGENT_ID)


# =============================================================================
# ENDPOINTS — ADMIN
# =============================================================================

@app.get("/api/v1/sources")
async def list_sources():
    sources = []
    cnesst = agents["cnesst"]
    saaq = agents["saaq"]
    uf = agents["urban_flow"]

    # Couche 3 sources
    c3_sources = ["Entraves CIFS", "Comptages piétons", "Comptages vélos",
                   "Capteurs Bluetooth", "Permis AGIR", "Météo Canada", "Stations Bixi"]
    for i, name in enumerate(c3_sources, 1):
        sources.append({"id": i, "name": name, "couche": 3, "status": "active" if i in [1, 6] else "planned"})

    # Couche 1
    p = cnesst.risk_profiles.get("23") if getattr(cnesst, "_loaded", False) else None
    sources.append({"id": 8, "name": "CNESST Lésions", "couche": 1,
                     "status": "active" if p else "inactive", "records": p.total_lesions if p else 0})

    # Couche 2
    gp = saaq.risk_profiles.get("global") if getattr(saaq, "_loaded", False) else None
    sources.append({"id": 9, "name": "SAAQ Zone travaux", "couche": 2,
                     "status": "active" if gp else "inactive", "records": gp.total_accidents if gp else 0})

    return {"sources": sources, "total": 9, "active": sum(1 for s in sources if s.get("status") == "active")}


@app.get("/api/v1/graph/stats")
async def graph_stats():
    return agents["graph"].get_stats()


@app.post("/api/v1/refresh")
async def refresh_all():
    """Rafraîchit les 3 couches du SafetyGraph."""
    graph = agents["graph"]
    results = await graph.refresh_all_layers(
        cnesst_agent=agents["cnesst"],
        saaq_agent=agents["saaq"],
        urban_flow_agent=agents["urban_flow"],
    )
    return {"status": "refreshed", "results": results}
