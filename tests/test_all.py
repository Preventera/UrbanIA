"""
=============================================================================
Tests AX5 UrbanIA — Suite complète
=============================================================================
pytest tests/
=============================================================================
"""

import pytest
from datetime import datetime


# =========================================================================
# TESTS CNESST AGENT
# =========================================================================

class TestCNESSTAgent:
    """Tests pour CNESSTLesionsRAGAgent."""

    def test_import(self):
        from src.agents.cnesst_lesions_agent import CNESSTLesionsRAGAgent
        agent = CNESSTLesionsRAGAgent()
        assert agent.AGENT_ID == "cnesst-lesions-rag"
        assert agent.SOURCE_PRIORITY == 8

    def test_urban_risk_score_mapping(self):
        from src.utils.constants import GENRE_URBAN_RISK_SCORE
        assert GENRE_URBAN_RISK_SCORE["ACCIDENT DE LA ROUTE"] == 10
        assert GENRE_URBAN_RISK_SCORE["FRAPPE PAR OBJET"] == 9
        assert GENRE_URBAN_RISK_SCORE["CHUTE A UN NIVEAU INFERIEUR"] == 7
        assert GENRE_URBAN_RISK_SCORE["EFFORT EXCESSIF"] == 2

    def test_scian_construction_filter(self):
        from src.utils.constants import SCIAN_CONSTRUCTION
        assert "23" in SCIAN_CONSTRUCTION
        assert "236" in SCIAN_CONSTRUCTION
        assert "238" in SCIAN_CONSTRUCTION

    def test_query_interface(self):
        from src.agents.cnesst_lesions_agent import CNESSTLesionsRAGAgent
        agent = CNESSTLesionsRAGAgent()
        result = agent.query("TMS construction")
        assert isinstance(result, str)
        assert len(result) > 0


# =========================================================================
# TESTS SAAQ AGENT
# =========================================================================

class TestSAAQAgent:
    """Tests pour SAAQWorkZoneAgent."""

    def test_import(self):
        from src.agents.saaq_workzone_agent import SAAQWorkZoneAgent
        agent = SAAQWorkZoneAgent()
        assert agent.AGENT_ID == "saaq-workzone-rag"
        assert agent.SOURCE_PRIORITY == 9

    def test_gravite_weights(self):
        from src.utils.constants import SAAQ_GRAVITE_POIDS
        assert SAAQ_GRAVITE_POIDS["Mortel"] == 10.0 or SAAQ_GRAVITE_POIDS.get("mortel_grave", 10.0) == 10.0

    def test_query_interface(self):
        from src.agents.saaq_workzone_agent import SAAQWorkZoneAgent
        agent = SAAQWorkZoneAgent()
        result = agent.query("piétons Montréal")
        assert isinstance(result, str)


# =========================================================================
# TESTS SCORING ENGINE
# =========================================================================

class TestScoringEngine:
    """Tests pour UrbanRiskScoringEngine."""

    def test_import(self):
        from src.models.urban_risk_score import UrbanRiskScoringEngine
        engine = UrbanRiskScoringEngine()
        assert engine is not None

    def test_score_range(self):
        from src.models.urban_risk_score import UrbanRiskScoringEngine
        engine = UrbanRiskScoringEngine()

        cnesst = {"urban_risk_score": 7.0, "taux_tms_pct": 26.0, "trend_yoy_pct": 8.0}
        saaq = {"risk_score": 6.5, "accidents_pietons": 108, "accidents_cyclistes": 91, "accidents_mortels_graves": 24}
        mtl = {"flux_pietons": 2000, "flux_cyclistes": 500, "entraves_actives": 5, "coactivity_factor": 1.3, "weather_factor": 1.0}

        result = engine.compute_score("VM-01", cnesst, saaq, mtl)
        assert 0 <= result.score <= 100
        assert result.severity in ("green", "yellow", "orange", "red")
        assert isinstance(result.requires_hitl, bool)

    def test_severity_hitl(self):
        from src.utils.constants import ALERT_THRESHOLDS
        assert ALERT_THRESHOLDS["green"][0] == 0
        assert ALERT_THRESHOLDS["red"][0] == 85

    def test_no_data_fallback(self):
        from src.models.urban_risk_score import UrbanRiskScoringEngine
        engine = UrbanRiskScoringEngine()
        result = engine.compute_score("TEST-01", None, None, None)
        assert result.score >= 0
        assert result.confidence in ("low", "medium", "high")


# =========================================================================
# TESTS COACTIVITY AGENT
# =========================================================================

class TestCoactivityAgent:
    """Tests pour CoactivityAgent."""

    def test_import(self):
        from src.agents.coactivity_agent import CoactivityAgent
        agent = CoactivityAgent()
        assert agent.AGENT_ID == "coactivity-agent"

    def test_no_chantiers(self):
        from src.agents.coactivity_agent import CoactivityAgent
        agent = CoactivityAgent()
        report = agent.analyze([], "TEST")
        assert report.total_clusters == 0
        assert report.max_risk_multiplier == 1.0

    def test_cluster_detection(self):
        from src.agents.coactivity_agent import CoactivityAgent, Chantier

        agent = CoactivityAgent()
        # 3 chantiers très proches (même intersection)
        chantiers = [
            Chantier(id="C1", rue="Sainte-Catherine", latitude=45.5000, longitude=-73.5700),
            Chantier(id="C2", rue="Peel", latitude=45.5002, longitude=-73.5698),
            Chantier(id="C3", rue="Stanley", latitude=45.4998, longitude=-73.5702),
        ]

        report = agent.analyze(chantiers, "VM-01")
        assert report.total_clusters >= 1
        assert report.max_risk_multiplier >= 1.3

    def test_no_cluster_distant(self):
        from src.agents.coactivity_agent import CoactivityAgent, Chantier

        agent = CoactivityAgent()
        # Chantiers éloignés
        chantiers = [
            Chantier(id="C1", rue="Rue A", latitude=45.50, longitude=-73.57),
            Chantier(id="C2", rue="Rue B", latitude=45.55, longitude=-73.60),
        ]

        report = agent.analyze(chantiers, "MTL")
        assert report.total_clusters == 0

    def test_risk_multiplier_scaling(self):
        from src.agents.coactivity_agent import CoactivityAgent
        agent = CoactivityAgent()
        assert agent.RISK_MULTIPLIERS[2] < agent.RISK_MULTIPLIERS[3]
        assert agent.RISK_MULTIPLIERS[3] < agent.RISK_MULTIPLIERS[5]


# =========================================================================
# TESTS CASCADE AGENT
# =========================================================================

class TestCascadeAgent:
    """Tests pour CascadeAgent."""

    def test_import(self):
        from src.agents.cascade_agent import CascadeAgent
        agent = CascadeAgent()
        assert agent.AGENT_ID == "cascade-agent"
        assert agent.NETWORK_AREA_KM2 == 3.7

    def test_empty_cascade(self):
        from src.agents.cascade_agent import CascadeAgent
        agent = CascadeAgent()
        report = agent.model_cascade([], zone_id="TEST")
        assert report.cascade_score == 0
        assert len(report.corridors) == 0

    def test_cascade_with_chantier(self):
        from src.agents.cascade_agent import CascadeAgent
        agent = CascadeAgent()

        chantiers = [
            {"id": "C1", "latitude": 45.500, "longitude": -73.570, "type_entrave": "fermeture", "impact_score": 8},
        ]

        report = agent.model_cascade(chantiers, flux_pietons=2000, flux_cyclistes=500)
        assert len(report.corridors) > 0
        assert report.total_users_redirected > 0

    def test_propagation_decay(self):
        from src.agents.cascade_agent import CascadeAgent
        assert 0 < CascadeAgent.PROPAGATION_DECAY < 1.0


# =========================================================================
# TESTS NUDGE AGENT
# =========================================================================

class TestNudgeAgent:
    """Tests pour NudgeAgent."""

    def test_import(self):
        from src.agents.nudge_agent import NudgeAgent, PROFILES
        agent = NudgeAgent()
        assert agent.AGENT_ID == "nudge-agent"
        assert len(PROFILES) == 9

    def test_profiles_vulnerability(self):
        from src.agents.nudge_agent import PROFILES
        assert PROFILES["pmr"].vulnerability_score == 10
        assert PROFILES["pieton"].vulnerability_score == 10
        assert PROFILES["cycliste"].vulnerability_score == 9
        assert PROFILES["coordonnateur"].vulnerability_score == 0

    def test_targeting_red(self):
        from src.agents.nudge_agent import NudgeAgent
        agent = NudgeAgent()
        assert len(agent.TARGETING["red"]) == 9  # Tous les profils

    def test_targeting_green(self):
        from src.agents.nudge_agent import NudgeAgent
        agent = NudgeAgent()
        assert agent.TARGETING["green"] == ["coordonnateur"]

    def test_campaign_red(self):
        from src.agents.nudge_agent import NudgeAgent
        agent = NudgeAgent()

        campaign = agent.generate_campaign(
            zone_id="VM-01",
            severity="red",
            trigger="coactivity",
            context={"rues": ["Sainte-Catherine", "Peel"], "score": 92, "chantiers": 5},
        )

        assert campaign.total_nudges > 0
        assert len(campaign.profiles_cibled) == 9
        # Vérifier que les nudges HITL sont marqués
        hitl_nudges = [n for n in campaign.nudges if n.requires_hitl]
        assert len(hitl_nudges) == campaign.total_nudges  # Tous en red

    def test_campaign_green(self):
        from src.agents.nudge_agent import NudgeAgent
        agent = NudgeAgent()

        campaign = agent.generate_campaign(
            zone_id="ME-01", severity="green", trigger="monitoring",
            context={"rues": ["Ontario"], "score": 25, "chantiers": 1},
        )
        assert campaign.profiles_cibled == ["coordonnateur"]

    def test_accessible_flag_pmr(self):
        from src.agents.nudge_agent import NudgeAgent
        agent = NudgeAgent()

        campaign = agent.generate_campaign(
            zone_id="VM-01", severity="orange", trigger="test",
            context={"rues": ["Test"], "score": 70, "chantiers": 3},
        )

        pmr_nudges = [n for n in campaign.nudges if n.profile_id == "pmr"]
        assert all(n.accessible for n in pmr_nudges)

    def test_bilingual(self):
        from src.agents.nudge_agent import NudgeAgent
        agent_en = NudgeAgent(langue="en")
        campaign = agent_en.generate_campaign(
            zone_id="VM-01", severity="red", trigger="test",
            context={"rues": ["Peel"], "score": 90, "chantiers": 4},
        )
        assert campaign.total_nudges > 0


# =========================================================================
# TESTS CONNECTORS
# =========================================================================

class TestConnectors:
    """Tests pour les connecteurs Couche 3."""

    def test_cifs_import(self):
        from src.connectors.cifs_connector import CIFSConnector
        c = CIFSConnector()
        assert c.SOURCE_ID == "cifs"
        assert c.COUCHE == 3

    def test_weather_import(self):
        from src.connectors.weather_connector import WeatherConnector
        c = WeatherConnector()
        assert c.SOURCE_ID == "meteo"
        assert c.RISK_FACTORS["verglas"] == 1.4

    def test_weather_default(self):
        from src.connectors.weather_connector import WeatherConnector
        c = WeatherConnector()
        default = c._get_default_conditions()
        assert -30 <= default.temperature <= 40

    def test_pedestrian_import(self):
        from src.connectors.pedestrian_connector import PedestrianConnector
        c = PedestrianConnector()
        assert c.SOURCE_ID == "pietons"
        assert len(c.STATIONS_REFERENCE) > 0

    def test_cycling_import(self):
        from src.connectors.cycling_bluetooth_bixi import CyclingConnector
        c = CyclingConnector()
        assert c.SOURCE_ID == "velos"

    def test_bluetooth_import(self):
        from src.connectors.cycling_bluetooth_bixi import BluetoothConnector
        c = BluetoothConnector()
        assert c.SOURCE_ID == "bluetooth"

    def test_bixi_import(self):
        from src.connectors.cycling_bluetooth_bixi import BixiConnector
        c = BixiConnector()
        assert c.SOURCE_ID == "bixi"

    def test_mtl_client(self):
        from src.connectors.mtl_opendata import MTLOpenDataClient
        client = MTLOpenDataClient()
        assert client.base_url.startswith("https://")


# =========================================================================
# TESTS SAFETYGRAPH
# =========================================================================

class TestSafetyGraph:
    """Tests pour SafetyGraphManager."""

    def test_import(self):
        from src.graph.safety_graph import SafetyGraphManager
        gm = SafetyGraphManager()
        assert gm.GRAPH_NAME == "AX5_UrbanIA_SafetyGraph"
        assert not gm.is_connected()  # Pas de FalkorDB en test

    def test_offline_inject(self):
        from src.graph.safety_graph import SafetyGraphManager
        gm = SafetyGraphManager()
        nodes = [{"type": "Test", "id": "t1", "properties": {"value": 42}}]
        count = gm.inject_nodes(nodes, "test")
        assert count == 0  # Mode offline


# =========================================================================
# TESTS URBAN FLOW AGENT
# =========================================================================

class TestUrbanFlowAgent:
    """Tests pour UrbanFlowAgent."""

    def test_import(self):
        from src.agents.urban_flow_agent import UrbanFlowAgent
        agent = UrbanFlowAgent()
        assert agent.AGENT_ID == "urban-flow-agent"
        assert agent.COUCHE == 3

    def test_pilot_arrondissements(self):
        from src.agents.urban_flow_agent import UrbanFlowAgent
        agent = UrbanFlowAgent()
        assert "Ville-Marie" in agent.PILOT_ARRONDISSEMENTS
        assert len(agent.PILOT_ARRONDISSEMENTS) == 6

    def test_time_factor(self):
        from src.agents.urban_flow_agent import UrbanFlowAgent
        # Vérifier que le facteur horaire est raisonnable
        factor = UrbanFlowAgent._get_time_factor()
        assert 0.5 <= factor <= 1.5

    def test_flux_estimation(self):
        from src.agents.urban_flow_agent import UrbanFlowAgent
        flux = UrbanFlowAgent._estimate_flux_by_hour(12)
        assert flux["pietons"] > 0
        assert flux["cyclistes"] > 0
        assert flux["pietons"] > flux["cyclistes"]  # Toujours plus de piétons


# =========================================================================
# TESTS CONSTANTS
# =========================================================================

class TestConstants:
    """Tests pour les constantes."""

    def test_alert_thresholds(self):
        from src.utils.constants import ALERT_THRESHOLDS
        assert ALERT_THRESHOLDS["green"] == (0, 40)
        assert ALERT_THRESHOLDS["yellow"] == (40, 65)
        assert ALERT_THRESHOLDS["orange"] == (65, 85)
        assert ALERT_THRESHOLDS["red"] == (85, 100)

    def test_user_profiles_count(self):
        from src.utils.constants import USER_PROFILES
        assert len(USER_PROFILES) == 9

    def test_mtl_sources_count(self):
        from src.utils.constants import MTL_SOURCES
        assert len(MTL_SOURCES) == 7

    def test_skills_c23(self):
        from src.utils.constants import SKILLS_C23
        assert len(SKILLS_C23) == 9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
