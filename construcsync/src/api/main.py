"""
=============================================================================
ConstrucSync Municipal — API FastAPI
=============================================================================
API de planification et coordination des chantiers municipaux.
Se positionne EN AMONT d'UrbanIA dans la chaîne de valeur.

Endpoints:
  POST /api/v1/permits/evaluate     → Évaluer une demande de permis
  POST /api/v1/permits/simulate     → Simuler l'impact avant autorisation
  GET  /api/v1/territory/snapshot   → État du territoire
  GET  /api/v1/territory/corridors  → Corridors stratégiques
  POST /api/v1/coordination/plan    → Générer plan de coordination
  GET  /api/v1/seasonal             → Contraintes saisonnières
  POST /api/v1/permits/query        → Requête RAG
  GET  /api/v1/health               → Santé du service

Conformité: Charte AgenticX5 | HITL obligatoire sur toute décision permis
=============================================================================
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.permit_optimizer_agent import (
    PermitOptimizerAgent, PermitRequest, PermitStatus,
)
from agents.territory_planner_agent import (
    TerritoryPlannerAgent, SEASONAL_CONSTRAINTS,
)
from agents.impact_simulator_stakeholder_sync import (
    ImpactSimulatorAgent, StakeholderSyncAgent,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# AGENTS GLOBAUX
# ═══════════════════════════════════════════════════════════════════════════

permit_optimizer: Optional[PermitOptimizerAgent] = None
territory_planner: Optional[TerritoryPlannerAgent] = None
impact_simulator: Optional[ImpactSimulatorAgent] = None
stakeholder_sync: Optional[StakeholderSyncAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global permit_optimizer, territory_planner, impact_simulator, stakeholder_sync

    logger.info("🏗️ ConstrucSync Municipal — Initialisation agents...")
    permit_optimizer = PermitOptimizerAgent()
    territory_planner = TerritoryPlannerAgent()
    impact_simulator = ImpactSimulatorAgent()
    stakeholder_sync = StakeholderSyncAgent()
    logger.info("✅ 4 agents ConstrucSync opérationnels")

    yield

    logger.info("🛑 ConstrucSync — Arrêt")


# ═══════════════════════════════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="AX5 ConstrucSync Municipal",
    description=(
        "Orchestrateur de planification et coordination des chantiers municipaux. "
        "Se positionne EN AMONT d'UrbanIA pour prévenir la coactivité."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════
# MODÈLES API
# ═══════════════════════════════════════════════════════════════════════════

class PermitEvaluationRequest(BaseModel):
    permit_id: str
    applicant: str = ""
    rue: str
    de_rue: str = ""
    a_rue: str = ""
    arrondissement: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    type_travaux: str = ""
    date_debut: str = ""
    date_fin: str = ""
    duree_jours: int = 30
    emprise_type: str = "occupation_partielle"
    impact_pietons: bool = False
    impact_cyclistes: bool = False
    impact_transport: bool = False
    urgence: bool = False
    active_chantiers: List[dict] = Field(default_factory=list)
    historical_data: Optional[dict] = None


class SimulationRequest(BaseModel):
    permit_id: str
    zone_id: str = ""
    current_score: float = 50.0
    current_chantiers: int = 5
    flux_pietons: int = 2000
    flux_cyclistes: int = 400
    type_travaux: str = ""
    emprise_type: str = "occupation_partielle"
    duree_jours: int = 30
    impact_pietons: bool = True
    impact_cyclistes: bool = False


class CoordinationRequest(BaseModel):
    permit_id: str
    type_travaux: str = ""
    severity: str = "yellow"
    conditions: List[str] = Field(default_factory=list)
    date_debut: str = ""


class QueryRequest(BaseModel):
    question: str
    agent: str = "permit_optimizer"


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/health")
async def health():
    return {
        "status": "operational",
        "service": "AX5 ConstrucSync Municipal",
        "version": "1.0.0",
        "agents": {
            "permit_optimizer": permit_optimizer is not None,
            "territory_planner": territory_planner is not None,
            "impact_simulator": impact_simulator is not None,
            "stakeholder_sync": stakeholder_sync is not None,
        },
        "position": "EN AMONT d'UrbanIA — planification pré-autorisation",
    }


@app.post("/api/v1/permits/evaluate")
async def evaluate_permit(req: PermitEvaluationRequest):
    """Évalue une demande de permis et produit une recommandation."""
    if not permit_optimizer:
        raise HTTPException(503, "PermitOptimizer non initialisé")

    permit = PermitRequest(
        permit_id=req.permit_id,
        applicant=req.applicant,
        rue=req.rue,
        de_rue=req.de_rue,
        a_rue=req.a_rue,
        arrondissement=req.arrondissement,
        latitude=req.latitude,
        longitude=req.longitude,
        type_travaux=req.type_travaux,
        date_debut_demandee=req.date_debut,
        date_fin_demandee=req.date_fin,
        duree_jours=req.duree_jours,
        emprise_type=req.emprise_type,
        impact_pietons=req.impact_pietons,
        impact_cyclistes=req.impact_cyclistes,
        impact_transport=req.impact_transport,
        urgence=req.urgence,
    )

    decision = permit_optimizer.evaluate_permit(
        permit,
        active_chantiers=req.active_chantiers,
        historical_data=req.historical_data,
    )

    # Vérifier corridors stratégiques
    corridor_info = None
    if territory_planner:
        corridor = territory_planner.check_corridor_availability(req.rue)
        if corridor:
            corridor_info = {
                "corridor_id": corridor.corridor_id,
                "name": corridor.name,
                "type": corridor.type_corridor,
                "priority": corridor.priority,
                "current_chantiers": corridor.current_chantiers,
                "max_simultaneous": corridor.max_simultaneous_chantiers,
                "saturated": corridor.current_chantiers >= corridor.max_simultaneous_chantiers,
            }

    return {
        "permit_id": decision.permit_id,
        "recommendation": decision.recommendation.value,
        "risk_score": decision.risk_score,
        "severity": decision.severity,
        "requires_hitl": decision.requires_hitl,
        "reasoning": decision.reasoning,
        "conditions": decision.conditions,
        "mitigation_required": decision.mitigation_required,
        "optimal_window": decision.optimal_window,
        "conflict_analysis": {
            "conflicts_found": decision.conflict_analysis.conflicts_found,
            "nearby_active": decision.conflict_analysis.nearby_active,
            "nearby_planned": decision.conflict_analysis.nearby_planned,
            "coactivity_score": decision.conflict_analysis.coactivity_score,
            "vulnerable_users_exposed": decision.conflict_analysis.vulnerable_users_exposed,
        } if decision.conflict_analysis else None,
        "strategic_corridor": corridor_info,
        "charte_agenticx5": "HITL obligatoire — aucune décision de permis sans validation humaine",
    }


@app.post("/api/v1/permits/simulate")
async def simulate_impact(req: SimulationRequest):
    """Simule l'impact d'un chantier AVANT autorisation."""
    if not impact_simulator:
        raise HTTPException(503, "ImpactSimulator non initialisé")

    report = impact_simulator.simulate(
        permit_id=req.permit_id,
        zone_id=req.zone_id,
        current_score=req.current_score,
        current_chantiers=req.current_chantiers,
        flux_pietons=req.flux_pietons,
        flux_cyclistes=req.flux_cyclistes,
        permit_impact={
            "type_travaux": req.type_travaux,
            "emprise_type": req.emprise_type,
            "duree_jours": req.duree_jours,
            "impact_pietons": req.impact_pietons,
            "impact_cyclistes": req.impact_cyclistes,
        },
    )

    return {
        "simulation_id": report.simulation_id,
        "permit_id": report.permit_id,
        "scenarios": [
            {
                "name": s.name,
                "score_urbania": s.score_urbania,
                "cascade_score": s.cascade_score,
                "coactivity_multiplier": s.coactivity_multiplier,
                "users_impacted": s.users_impacted,
                "pietons_redirected": s.pietons_redirected,
                "cyclistes_redirected": s.cyclistes_redirected,
                "estimated_incidents": s.estimated_incidents,
            }
            for s in report.scenarios
        ],
        "delta_risk": report.delta_risk,
        "delta_users": report.delta_users,
        "optimal_scenario": report.optimal_scenario,
        "recommendation": report.recommendation,
    }


@app.get("/api/v1/territory/snapshot")
async def territory_snapshot():
    """État du territoire."""
    if not territory_planner:
        raise HTTPException(503, "TerritoryPlanner non initialisé")

    report = territory_planner.generate_report(
        active_permits=[],
        planned_permits=[],
    )

    return {
        "date": report.date,
        "total_zones": report.total_zones,
        "zones_saturees": report.zones_saturees,
        "corridors_impactes": report.corridors_impactes,
        "seasonal_constraints": report.seasonal_constraints,
        "recommendations": report.recommendations,
        "heatmap": report.heatmap,
        "zones": [
            {
                "arrondissement": z.arrondissement,
                "max_chantiers": z.max_chantiers,
                "active_chantiers": z.active_chantiers,
                "utilization_pct": z.utilization_pct,
                "status": z.status,
            }
            for z in report.zones
        ],
    }


@app.get("/api/v1/territory/corridors")
async def strategic_corridors():
    """Corridors stratégiques."""
    if not territory_planner:
        raise HTTPException(503, "TerritoryPlanner non initialisé")

    from agents.territory_planner_agent import CORRIDORS_STRATEGIQUES

    return {
        "total": len(CORRIDORS_STRATEGIQUES),
        "corridors": [
            {
                "id": c.corridor_id,
                "name": c.name,
                "type": c.type_corridor,
                "priority": c.priority,
                "max_simultaneous": c.max_simultaneous_chantiers,
                "current": c.current_chantiers,
                "arrondissements": c.arrondissements,
                "protected": c.protected,
            }
            for c in CORRIDORS_STRATEGIQUES
        ],
    }


@app.post("/api/v1/coordination/plan")
async def coordination_plan(req: CoordinationRequest):
    """Génère un plan de coordination pour un chantier."""
    if not stakeholder_sync:
        raise HTTPException(503, "StakeholderSync non initialisé")

    plan = stakeholder_sync.generate_plan(
        permit_id=req.permit_id,
        type_travaux=req.type_travaux,
        severity=req.severity,
        conditions=req.conditions,
        date_debut=req.date_debut,
    )

    return {
        "plan_id": plan.plan_id,
        "permit_id": plan.permit_id,
        "stakeholders": [
            {"id": s.id, "name": s.name, "role": s.role, "canal": s.notification_canal}
            for s in plan.stakeholders
        ],
        "tasks_count": len(plan.tasks),
        "tasks": [
            {"id": t.task_id, "action": t.action, "deadline": t.deadline, "stakeholder": t.stakeholder_id}
            for t in plan.tasks
        ],
        "timeline": plan.timeline,
        "status": plan.status,
    }


@app.get("/api/v1/seasonal")
async def seasonal_constraints():
    """Contraintes saisonnières actuelles."""
    modifier = 1.0
    active_constraints = []
    current_season = ""

    from datetime import datetime
    month = datetime.now().month

    for sc in SEASONAL_CONSTRAINTS:
        if month in sc.months:
            modifier = sc.risk_modifier
            active_constraints = sc.constraints
            current_season = sc.period
            break

    return {
        "current_season": current_season,
        "risk_modifier": modifier,
        "constraints": active_constraints,
        "all_seasons": [
            {"period": sc.period, "months": sc.months, "modifier": sc.risk_modifier, "rules_count": len(sc.constraints)}
            for sc in SEASONAL_CONSTRAINTS
        ],
    }


@app.post("/api/v1/permits/query")
async def query_rag(req: QueryRequest):
    """Requête RAG aux agents ConstrucSync."""
    agents_map = {
        "permit_optimizer": permit_optimizer,
        "territory_planner": territory_planner,
        "impact_simulator": impact_simulator,
        "stakeholder_sync": stakeholder_sync,
    }

    agent = agents_map.get(req.agent)
    if not agent:
        raise HTTPException(400, f"Agent inconnu: {req.agent}")

    return {"agent": req.agent, "question": req.question, "answer": agent.query(req.question)}
