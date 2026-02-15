"""
=============================================================================
SafetyGraph Manager — Graphe de connaissances unifié 3 couches
=============================================================================
Gère le SafetyGraph FalkorDB qui unifie les 3 couches de données:
  Couche 1 (CNESST) → ProfilRisqueChantier, ScoreRisqueUrbain
  Couche 2 (SAAQ)   → WorkZoneRiskProfile, VulnerableUser
  Couche 3 (MTL)    → UrbanZone, EntraveCIFS

Le SafetyGraph est le point de convergence qui permet au
UrbanRiskScoringEngine de produire des scores calibrés sur
54 403 lésions + 8 173 accidents + flux temps réel.

Conformité: Charte AgenticX5 | Primauté de la vie | Traçabilité 100%
=============================================================================
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# FalkorDB import conditionnel
try:
    from falkordb import FalkorDB
    FALKORDB_AVAILABLE = True
except ImportError:
    FALKORDB_AVAILABLE = False
    logger.warning("⚠️ FalkorDB non installé. pip install falkordb")


class SafetyGraphManager:
    """
    Gestionnaire du SafetyGraph unifié pour AX5 UrbanIA.
    
    Responsabilités:
    1. Connexion à FalkorDB
    2. Chargement du schema.cypher
    3. Injection des nœuds depuis les 3 agents
    4. Requêtes traversales inter-couches
    5. Traçabilité des sources (audit)
    """

    GRAPH_NAME = "AX5_UrbanIA_SafetyGraph"

    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
        self._db = None
        self._graph = None
        self._connected = False
        logger.info(f"🧠 SafetyGraphManager initialisé | {host}:{port}")

    # =========================================================================
    # CONNEXION
    # =========================================================================

    def connect(self) -> bool:
        """Connexion à FalkorDB."""
        if not FALKORDB_AVAILABLE:
            logger.warning("⚠️ FalkorDB non disponible — mode offline")
            return False

        try:
            self._db = FalkorDB(host=self.host, port=self.port)
            self._graph = self._db.select_graph(self.GRAPH_NAME)
            self._connected = True
            logger.info(f"✅ Connecté à FalkorDB | Graphe: {self.GRAPH_NAME}")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Connexion FalkorDB échouée: {e}")
            self._connected = False
            return False

    def is_connected(self) -> bool:
        return self._connected

    # =========================================================================
    # INJECTION DES NŒUDS
    # =========================================================================

    def inject_nodes(self, nodes: List[Dict[str, Any]], source: str) -> int:
        """
        Injecte une liste de nœuds dans le SafetyGraph.
        
        Args:
            nodes: Liste de nœuds [{type, id, properties}]
            source: Identifiant de l'agent source
            
        Returns:
            Nombre de nœuds injectés
        """
        if not self._connected:
            logger.info(f"📝 [Offline] {len(nodes)} nœuds {source} en attente d'injection")
            return 0

        injected = 0
        for node in nodes:
            try:
                node_type = node["type"]
                node_id = node["id"]
                props = node.get("properties", {})

                # Ajouter métadonnées de traçabilité
                props["_source"] = source
                props["_injected_at"] = datetime.now().isoformat()
                props["_graph_version"] = "1.0.0"

                # Construire la requête Cypher MERGE
                props_str = ", ".join(
                    f'{k}: "{v}"' if isinstance(v, str)
                    else f"{k}: {v}"
                    for k, v in props.items()
                    if v is not None
                )

                query = f'MERGE (n:{node_type} {{id: "{node_id}"}}) SET n += {{{props_str}}}'
                self._graph.query(query)
                injected += 1

            except Exception as e:
                logger.error(f"  ❌ Injection échouée pour {node.get('id')}: {e}")

        logger.info(f"🔗 {injected}/{len(nodes)} nœuds injectés depuis {source}")
        return injected

    def create_relationships(self, relationships: List[Dict[str, str]]) -> int:
        """
        Crée des relations entre nœuds.
        
        Args:
            relationships: [{from_id, to_id, rel_type, properties}]
        """
        if not self._connected:
            return 0

        created = 0
        for rel in relationships:
            try:
                query = (
                    f'MATCH (a {{id: "{rel["from_id"]}"}}) '
                    f'MATCH (b {{id: "{rel["to_id"]}"}}) '
                    f'MERGE (a)-[:{rel["rel_type"]}]->(b)'
                )
                self._graph.query(query)
                created += 1
            except Exception as e:
                logger.error(f"  ❌ Relation échouée: {e}")

        return created

    # =========================================================================
    # REQUÊTES INTER-COUCHES
    # =========================================================================

    def get_zone_risk_context(self, zone_id: str) -> Dict[str, Any]:
        """
        Récupère le contexte de risque complet pour une zone,
        en traversant les 3 couches du SafetyGraph.
        
        Retourne toutes les données nécessaires au scoring composite.
        """
        context = {
            "zone_id": zone_id,
            "couche1_cnesst": None,
            "couche2_saaq": None,
            "couche3_mtl": None,
        }

        if not self._connected:
            return context

        try:
            # Couche 1: Profil risque chantier
            result = self._graph.query(
                'MATCH (p:ProfilRisqueChantier) '
                'WHERE p.scian_code = "23" '
                'RETURN p.urban_risk_score, p.taux_tms_pct, p.trend_yoy_pct '
                'LIMIT 1'
            )
            if result.result_set:
                row = result.result_set[0]
                context["couche1_cnesst"] = {
                    "urban_risk_score": row[0],
                    "taux_tms_pct": row[1],
                    "trend_yoy_pct": row[2],
                }

            # Couche 2: Profil zone travaux Montréal
            result = self._graph.query(
                'MATCH (w:WorkZoneRiskProfile) '
                'WHERE w.region CONTAINS "Montr" '
                'RETURN w.accidents_pietons, w.accidents_cyclistes, '
                'w.accidents_mortels_graves, w.risk_score '
                'LIMIT 1'
            )
            if result.result_set:
                row = result.result_set[0]
                context["couche2_saaq"] = {
                    "accidents_pietons": row[0],
                    "accidents_cyclistes": row[1],
                    "accidents_mortels_graves": row[2],
                    "risk_score": row[3],
                }

            # Couche 3: Zone urbaine
            result = self._graph.query(
                f'MATCH (z:UrbanZone) '
                f'WHERE z.id = "zone-{zone_id.lower()}" '
                f'RETURN z.entraves_actives, z.flux_pietons, '
                f'z.flux_cyclistes, z.exposure_score '
                f'LIMIT 1'
            )
            if result.result_set:
                row = result.result_set[0]
                context["couche3_mtl"] = {
                    "entraves_actives": row[0],
                    "flux_pietons": row[1],
                    "flux_cyclistes": row[2],
                    "exposure_score": row[3],
                }

        except Exception as e:
            logger.error(f"  ❌ Requête inter-couches échouée: {e}")

        return context

    def get_stats(self) -> Dict[str, Any]:
        """Statistiques du SafetyGraph."""
        if not self._connected:
            return {"connected": False, "mode": "offline"}

        stats = {"connected": True, "graph": self.GRAPH_NAME}

        try:
            for node_type in ["ProfilRisqueChantier", "WorkZoneRiskProfile", "UrbanZone", "Alert"]:
                result = self._graph.query(f"MATCH (n:{node_type}) RETURN count(n)")
                stats[node_type] = result.result_set[0][0] if result.result_set else 0
        except Exception as e:
            logger.error(f"  ❌ Stats échouées: {e}")

        return stats

    # =========================================================================
    # PIPELINE COMPLET
    # =========================================================================

    async def refresh_all_layers(
        self,
        cnesst_agent=None,
        saaq_agent=None,
        urban_flow_agent=None,
    ) -> Dict[str, int]:
        """
        Rafraîchit les 3 couches du SafetyGraph.
        
        Pipeline complet:
        1. Injecte les nœuds CNESST (Couche 1)
        2. Injecte les nœuds SAAQ (Couche 2)
        3. Collecte données MTL et injecte (Couche 3)
        4. Crée les relations inter-couches
        """
        results = {"couche1": 0, "couche2": 0, "couche3": 0, "relations": 0}

        # Couche 1 — CNESST
        if cnesst_agent:
            nodes = cnesst_agent.to_safety_graph_nodes()
            results["couche1"] = self.inject_nodes(nodes, "cnesst-lesions-rag")

        # Couche 2 — SAAQ
        if saaq_agent:
            nodes = saaq_agent.to_safety_graph_nodes()
            results["couche2"] = self.inject_nodes(nodes, "saaq-workzone-rag")

        # Couche 3 — MTL (collecte temps réel + injection)
        if urban_flow_agent:
            await urban_flow_agent.collect_all_sources()
            nodes = urban_flow_agent.to_safety_graph_nodes()
            results["couche3"] = self.inject_nodes(nodes, "urban-flow-agent")

        # Relations inter-couches
        if self._connected:
            relations = [
                # CNESST → zones UrbanIA
                {"from_id": "cnesst-construction-23", "to_id": f"zone-{z.zone_id.lower()}", "rel_type": "EXPORTS_RISK_TO"}
                for z in (urban_flow_agent._last_snapshot.zones if urban_flow_agent and urban_flow_agent._last_snapshot else [])
            ]
            results["relations"] = self.create_relationships(relations)

        total = sum(results.values())
        logger.info(
            f"🧠 SafetyGraph rafraîchi: {total} opérations | "
            f"C1={results['couche1']} C2={results['couche2']} C3={results['couche3']}"
        )

        return results

    def close(self):
        """Ferme la connexion."""
        if self._db:
            try:
                self._db.close()
            except Exception:
                pass
        self._connected = False
