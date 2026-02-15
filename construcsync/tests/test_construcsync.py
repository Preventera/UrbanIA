"""
=============================================================================
Tests — ConstrucSync Municipal
=============================================================================
Suite de tests pytest pour les 4 agents ConstrucSync:
  - PermitOptimizerAgent
  - TerritoryPlannerAgent
  - ImpactSimulatorAgent
  - StakeholderSyncAgent
=============================================================================
"""

import sys
import os
import pytest

# Ajouter le chemin source
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ═══════════════════════════════════════════════════════════════════════════
# PERMIT OPTIMIZER
# ═══════════════════════════════════════════════════════════════════════════

class TestPermitOptimizer:
    def test_import(self):
        from agents.permit_optimizer_agent import PermitOptimizerAgent
        agent = PermitOptimizerAgent()
        assert agent.AGENT_ID == "permit-optimizer"

    def test_evaluate_simple_permit(self):
        from agents.permit_optimizer_agent import PermitOptimizerAgent, PermitRequest
        agent = PermitOptimizerAgent()
        permit = PermitRequest(
            permit_id="TEST-001",
            applicant="TestCo",
            rue="Rue Test",
            arrondissement="Verdun",
            latitude=45.4500,
            longitude=-73.5700,
            type_travaux="telecom",
            date_debut_demandee="2025-06-01",
            date_fin_demandee="2025-06-15",
            duree_jours=14,
            emprise_type="stationnement",
        )
        decision = agent.evaluate_permit(permit)
        assert decision.permit_id == "TEST-001"
        assert decision.requires_hitl is True  # Toujours HITL
        assert 0 <= decision.risk_score <= 100
        assert decision.severity in ("green", "yellow", "orange", "red")

    def test_urgent_permit_auto_approve(self):
        from agents.permit_optimizer_agent import PermitOptimizerAgent, PermitRequest, Recommendation
        agent = PermitOptimizerAgent()
        permit = PermitRequest(
            permit_id="URG-001",
            applicant="Ville MTL",
            rue="Bris aqueduc",
            urgence=True,
        )
        decision = agent.evaluate_permit(permit)
        assert decision.recommendation == Recommendation.APPROVE
        assert decision.requires_hitl is True
        assert len(decision.conditions) >= 3

    def test_high_coactivity_defers(self):
        from agents.permit_optimizer_agent import PermitOptimizerAgent, PermitRequest
        agent = PermitOptimizerAgent()
        # Créer des chantiers actifs très proches
        active = [
            {"id": f"CH-{i}", "rue": f"Rue {i}", "latitude": 45.5050 + i * 0.0001,
             "longitude": -73.5700, "type_entrave": "fermeture"}
            for i in range(5)
        ]
        permit = PermitRequest(
            permit_id="HIGH-001",
            rue="Rue Test",
            latitude=45.5051,
            longitude=-73.5700,
            type_travaux="demolition",
            emprise_type="fermeture_complete",
            impact_pietons=True,
            impact_cyclistes=True,
            impact_transport=True,
            duree_jours=60,
            arrondissement="Ville-Marie",
            date_debut_demandee="2025-06-01",
            date_fin_demandee="2025-07-31",
        )
        decision = agent.evaluate_permit(permit, active_chantiers=active)
        # Devrait avoir un score élevé
        assert decision.risk_score >= 40
        assert decision.conflict_analysis.conflicts_found >= 1

    def test_territory_capacity(self):
        from agents.permit_optimizer_agent import PermitOptimizerAgent
        agent = PermitOptimizerAgent()
        assert agent.TERRITORY_CAPACITY["Ville-Marie"] == 15
        assert agent.TERRITORY_CAPACITY["Anjou"] == 4

    def test_risk_thresholds(self):
        from agents.permit_optimizer_agent import PermitOptimizerAgent
        agent = PermitOptimizerAgent()
        assert agent._get_severity(10) == "green"
        assert agent._get_severity(40) == "yellow"
        assert agent._get_severity(60) == "orange"
        assert agent._get_severity(80) == "red"

    def test_haversine(self):
        from agents.permit_optimizer_agent import PermitOptimizerAgent
        # Montréal centre → ~111m pour 0.001° lat
        dist = PermitOptimizerAgent._haversine_m(45.5, -73.57, 45.501, -73.57)
        assert 100 < dist < 120

    def test_mitigation_generation(self):
        from agents.permit_optimizer_agent import (
            PermitOptimizerAgent, PermitRequest, ConflictAnalysis,
        )
        agent = PermitOptimizerAgent()
        permit = PermitRequest(
            permit_id="MIT-001", rue="Test",
            impact_pietons=True, impact_cyclistes=True,
            impact_transport=True, emprise_type="fermeture_complete",
            duree_jours=45,
        )
        conflicts = ConflictAnalysis(
            permit_id="MIT-001", conflicts_found=4,
            coactivity_score=70, vulnerable_users_exposed=800,
        )
        mitigations = agent._generate_mitigation(permit, conflicts)
        assert len(mitigations) >= 5
        # Doit contenir des conditions piétons, cyclistes, PMR, transport
        all_text = " ".join(mitigations).lower()
        assert "piéton" in all_text or "pietons" in all_text.replace("é", "e")
        assert "cyclable" in all_text or "cycliste" in all_text
        assert "coordination" in all_text

    def test_optimal_window(self):
        from agents.permit_optimizer_agent import PermitOptimizerAgent, PermitRequest
        agent = PermitOptimizerAgent()
        permit = PermitRequest(
            permit_id="WIN-001", rue="Test",
            date_debut_demandee="2025-06-01",
            date_fin_demandee="2025-06-15",
            duree_jours=14,
            latitude=45.5, longitude=-73.57,
        )
        window = agent._find_optimal_window(permit, [])
        assert "start" in window
        assert "end" in window

    def test_query_interface(self):
        from agents.permit_optimizer_agent import PermitOptimizerAgent
        agent = PermitOptimizerAgent()
        result = agent.query("état du territoire")
        assert "territoire" in result.lower() or "permit" in result.lower()

    def test_safety_graph_export(self):
        from agents.permit_optimizer_agent import PermitOptimizerAgent, PermitRequest
        agent = PermitOptimizerAgent()
        permit = PermitRequest(permit_id="SG-001", rue="Test")
        agent.evaluate_permit(permit)
        nodes = agent.to_safety_graph_nodes()
        assert len(nodes) >= 1
        assert nodes[0]["type"] == "PermitDecision"


# ═══════════════════════════════════════════════════════════════════════════
# TERRITORY PLANNER
# ═══════════════════════════════════════════════════════════════════════════

class TestTerritoryPlanner:
    def test_import(self):
        from agents.territory_planner_agent import TerritoryPlannerAgent
        agent = TerritoryPlannerAgent()
        assert agent.AGENT_ID == "territory-planner"

    def test_capacities(self):
        from agents.territory_planner_agent import TerritoryPlannerAgent
        agent = TerritoryPlannerAgent()
        assert len(agent.CAPACITIES) >= 19
        assert agent.CAPACITIES["Ville-Marie"] == 15

    def test_corridors(self):
        from agents.territory_planner_agent import CORRIDORS_STRATEGIQUES
        assert len(CORRIDORS_STRATEGIQUES) == 10
        stc = next(c for c in CORRIDORS_STRATEGIQUES if c.corridor_id == "COR-STC")
        assert stc.name == "Sainte-Catherine"
        assert stc.priority == 10

    def test_seasonal_constraints(self):
        from agents.territory_planner_agent import SEASONAL_CONSTRAINTS
        assert len(SEASONAL_CONSTRAINTS) == 4
        hiver = next(s for s in SEASONAL_CONSTRAINTS if s.period == "hiver")
        assert hiver.risk_modifier == 1.3
        assert 12 in hiver.months

    def test_generate_report(self):
        from agents.territory_planner_agent import TerritoryPlannerAgent
        agent = TerritoryPlannerAgent()
        report = agent.generate_report(active_permits=[], planned_permits=[])
        assert report.total_zones >= 19
        assert len(report.heatmap) >= 19
        assert len(report.recommendations) >= 1

    def test_saturation_detection(self):
        from agents.territory_planner_agent import TerritoryPlannerAgent
        agent = TerritoryPlannerAgent()
        # Simuler 20 chantiers à Anjou (capacité 4)
        active = [{"arrondissement": "Anjou"} for _ in range(5)]
        report = agent.generate_report(active_permits=active, planned_permits=[])
        anjou = next(z for z in report.zones if z.arrondissement == "Anjou")
        assert anjou.utilization_pct > 100
        assert anjou.status == "saturated"

    def test_corridor_check(self):
        from agents.territory_planner_agent import TerritoryPlannerAgent
        agent = TerritoryPlannerAgent()
        corridor = agent.check_corridor_availability("Sainte-Catherine")
        assert corridor is not None
        assert corridor.type_corridor == "pieton"

    def test_corridor_not_found(self):
        from agents.territory_planner_agent import TerritoryPlannerAgent
        agent = TerritoryPlannerAgent()
        corridor = agent.check_corridor_availability("Rue Obscure Inexistante")
        assert corridor is None

    def test_seasonal_modifier(self):
        from agents.territory_planner_agent import TerritoryPlannerAgent
        agent = TerritoryPlannerAgent()
        modifier = agent.get_seasonal_modifier()
        assert 1.0 <= modifier <= 1.3

    def test_safety_graph_export(self):
        from agents.territory_planner_agent import TerritoryPlannerAgent
        agent = TerritoryPlannerAgent()
        agent.generate_report([], [])
        nodes = agent.to_safety_graph_nodes()
        assert len(nodes) >= 19  # zones + corridors
        types = {n["type"] for n in nodes}
        assert "TerritoryZone" in types
        assert "StrategicCorridor" in types


# ═══════════════════════════════════════════════════════════════════════════
# IMPACT SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════

class TestImpactSimulator:
    def test_import(self):
        from agents.impact_simulator_stakeholder_sync import ImpactSimulatorAgent
        agent = ImpactSimulatorAgent()
        assert agent.AGENT_ID == "impact-simulator"

    def test_simulate_basic(self):
        from agents.impact_simulator_stakeholder_sync import ImpactSimulatorAgent
        agent = ImpactSimulatorAgent()
        report = agent.simulate(
            permit_id="SIM-TEST",
            zone_id="VM-01",
            current_score=50.0,
            current_chantiers=5,
            flux_pietons=2000,
            flux_cyclistes=400,
            permit_impact={
                "type_travaux": "voirie",
                "emprise_type": "fermeture_complete",
                "duree_jours": 30,
                "impact_pietons": True,
                "impact_cyclistes": True,
            },
        )
        assert len(report.scenarios) == 3
        names = {s.name for s in report.scenarios}
        assert "sans_chantier" in names
        assert "avec_chantier" in names
        assert "reporté_30j" in names

    def test_delta_risk_positive(self):
        from agents.impact_simulator_stakeholder_sync import ImpactSimulatorAgent
        agent = ImpactSimulatorAgent()
        report = agent.simulate(
            permit_id="DELTA-TEST",
            zone_id="VM-01",
            current_score=50.0,
            current_chantiers=8,
            flux_pietons=3000,
            flux_cyclistes=600,
            permit_impact={
                "type_travaux": "demolition",
                "emprise_type": "fermeture_complete",
                "duree_jours": 60,
                "impact_pietons": True,
                "impact_cyclistes": True,
            },
        )
        assert report.delta_risk > 0  # Le chantier ajoute du risque

    def test_deferred_lower_risk(self):
        from agents.impact_simulator_stakeholder_sync import ImpactSimulatorAgent
        agent = ImpactSimulatorAgent()
        report = agent.simulate(
            permit_id="DEF-TEST",
            zone_id="VM-01",
            current_score=70.0,
            current_chantiers=10,
            flux_pietons=4000,
            flux_cyclistes=800,
            permit_impact={
                "type_travaux": "aqueduc",
                "emprise_type": "fermeture_complete",
                "duree_jours": 45,
                "impact_pietons": True,
                "impact_cyclistes": True,
            },
        )
        with_score = next(s for s in report.scenarios if s.name == "avec_chantier").score_urbania
        defer_score = next(s for s in report.scenarios if s.name == "reporté_30j").score_urbania
        # Reporté devrait avoir un score inférieur ou égal
        assert defer_score <= with_score + 5  # Marge de tolérance

    def test_incident_estimation(self):
        from agents.impact_simulator_stakeholder_sync import ImpactSimulatorAgent
        agent = ImpactSimulatorAgent()
        report = agent.simulate(
            permit_id="INC-TEST",
            zone_id="VM-01",
            current_score=60.0,
            current_chantiers=6,
            flux_pietons=3000,
            flux_cyclistes=500,
            permit_impact={
                "type_travaux": "voirie",
                "emprise_type": "fermeture_complete",
                "duree_jours": 30,
                "impact_pietons": True,
                "impact_cyclistes": True,
            },
        )
        with_scenario = next(s for s in report.scenarios if s.name == "avec_chantier")
        assert with_scenario.estimated_incidents >= 0
        assert with_scenario.pietons_redirected > 0


# ═══════════════════════════════════════════════════════════════════════════
# STAKEHOLDER SYNC
# ═══════════════════════════════════════════════════════════════════════════

class TestStakeholderSync:
    def test_import(self):
        from agents.impact_simulator_stakeholder_sync import StakeholderSyncAgent
        agent = StakeholderSyncAgent()
        assert agent.AGENT_ID == "stakeholder-sync"

    def test_generate_plan_voirie(self):
        from agents.impact_simulator_stakeholder_sync import StakeholderSyncAgent
        agent = StakeholderSyncAgent()
        plan = agent.generate_plan(
            permit_id="PLAN-001",
            type_travaux="voirie",
            severity="yellow",
            conditions=["Signalisation avancée", "Corridor piéton"],
            date_debut="2025-06-15",
        )
        assert plan.plan_id == "PLAN-PLAN-001"
        assert plan.status == "active"
        assert len(plan.stakeholders) >= 5  # voirie template
        assert len(plan.tasks) >= 3

    def test_red_severity_adds_urgences(self):
        from agents.impact_simulator_stakeholder_sync import StakeholderSyncAgent
        agent = StakeholderSyncAgent()
        plan = agent.generate_plan(
            permit_id="RED-001",
            type_travaux="default",
            severity="red",
            conditions=[],
            date_debut="2025-06-15",
        )
        stakeholder_ids = {s.id for s in plan.stakeholders}
        assert "SH-SPVM" in stakeholder_ids
        assert "SH-SIM" in stakeholder_ids
        assert "SH-USANTE" in stakeholder_ids
        assert "SH-RES" in stakeholder_ids

    def test_aqueduc_includes_service_eau(self):
        from agents.impact_simulator_stakeholder_sync import StakeholderSyncAgent
        agent = StakeholderSyncAgent()
        plan = agent.generate_plan(
            permit_id="AQ-001",
            type_travaux="aqueduc",
            severity="yellow",
            conditions=[],
            date_debut="2025-06-15",
        )
        stakeholder_ids = {s.id for s in plan.stakeholders}
        assert "SH-EAU" in stakeholder_ids

    def test_timeline_sorted(self):
        from agents.impact_simulator_stakeholder_sync import StakeholderSyncAgent
        agent = StakeholderSyncAgent()
        plan = agent.generate_plan(
            permit_id="TL-001",
            type_travaux="voirie",
            severity="orange",
            conditions=["Condition A", "Condition B"],
            date_debut="2025-07-01",
        )
        dates = [entry["date"] for entry in plan.timeline]
        assert dates == sorted(dates)

    def test_coordination_meeting_high_severity(self):
        from agents.impact_simulator_stakeholder_sync import StakeholderSyncAgent
        agent = StakeholderSyncAgent()
        plan = agent.generate_plan(
            permit_id="MEET-001",
            type_travaux="voirie",
            severity="red",
            conditions=[],
            date_debut="2025-06-15",
        )
        actions = [t.action for t in plan.tasks]
        assert any("coordination" in a.lower() for a in actions)

    def test_query_interface(self):
        from agents.impact_simulator_stakeholder_sync import StakeholderSyncAgent
        agent = StakeholderSyncAgent()
        result = agent.query("test")
        assert "stakeholder" in result.lower()

    def test_safety_graph_export(self):
        from agents.impact_simulator_stakeholder_sync import StakeholderSyncAgent
        agent = StakeholderSyncAgent()
        agent.generate_plan("SG-001", "voirie", "yellow", [], "2025-06-15")
        nodes = agent.to_safety_graph_nodes()
        assert len(nodes) >= 1
        assert nodes[0]["type"] == "CoordinationPlan"


# ═══════════════════════════════════════════════════════════════════════════
# INTÉGRATION CROSS-AGENTS
# ═══════════════════════════════════════════════════════════════════════════

class TestIntegration:
    def test_full_pipeline(self):
        """Pipeline complet: évaluer → simuler → coordonner"""
        from agents.permit_optimizer_agent import PermitOptimizerAgent, PermitRequest
        from agents.impact_simulator_stakeholder_sync import ImpactSimulatorAgent, StakeholderSyncAgent

        optimizer = PermitOptimizerAgent()
        simulator = ImpactSimulatorAgent()
        sync = StakeholderSyncAgent()

        # 1. Évaluer
        permit = PermitRequest(
            permit_id="FULL-001",
            rue="Sainte-Catherine",
            arrondissement="Ville-Marie",
            latitude=45.5088,
            longitude=-73.5694,
            type_travaux="voirie",
            emprise_type="fermeture_complete",
            impact_pietons=True,
            impact_cyclistes=True,
            date_debut_demandee="2025-07-01",
            date_fin_demandee="2025-08-01",
            duree_jours=31,
        )
        decision = optimizer.evaluate_permit(permit)
        assert decision.requires_hitl is True

        # 2. Simuler
        report = simulator.simulate(
            permit_id="FULL-001",
            zone_id="VM-01",
            current_score=65.0,
            current_chantiers=8,
            flux_pietons=4200,
            flux_cyclistes=600,
            permit_impact={
                "type_travaux": "voirie",
                "emprise_type": "fermeture_complete",
                "duree_jours": 31,
                "impact_pietons": True,
                "impact_cyclistes": True,
            },
        )
        assert report.delta_risk > 0

        # 3. Coordonner
        plan = sync.generate_plan(
            permit_id="FULL-001",
            type_travaux="voirie",
            severity=decision.severity,
            conditions=decision.conditions + decision.mitigation_required,
            date_debut="2025-07-01",
        )
        assert plan.status == "active"
        assert len(plan.stakeholders) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
