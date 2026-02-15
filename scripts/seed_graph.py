"""
=============================================================================
Seed SafetyGraph — Initialisation complète du graphe 3 couches
=============================================================================
Script exécutable qui:
1. Connecte FalkorDB
2. Charge le schema.cypher (indexes + constraints)
3. Injecte les nœuds Couche 1 (CNESST)
4. Injecte les nœuds Couche 2 (SAAQ)
5. Collecte Couche 3 (MTL temps réel) et injecte
6. Crée les relations inter-couches
7. Vérifie l'intégrité du graphe

Usage:
  python -m scripts.seed_graph
  python -m scripts.seed_graph --skip-c3   # sans collecte temps réel
=============================================================================
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_schema(graph, schema_path: str = "src/graph/schema.cypher"):
    """Charge et exécute le schema Cypher."""
    path = Path(schema_path)
    if not path.exists():
        logger.error(f"❌ Schema introuvable: {schema_path}")
        return False

    content = path.read_text(encoding="utf-8")

    # Séparer les commandes (par ';')
    commands = [cmd.strip() for cmd in content.split(";") if cmd.strip()]

    executed = 0
    for cmd in commands:
        # Ignorer les commentaires purs
        lines = [l for l in cmd.split("\n") if not l.strip().startswith("//") and l.strip()]
        if not lines:
            continue

        clean = "\n".join(lines)
        if not clean.strip():
            continue

        try:
            graph.query(clean)
            executed += 1
        except Exception as e:
            # Ignorer les erreurs de contraintes déjà existantes
            if "already exists" in str(e).lower() or "already indexed" in str(e).lower():
                continue
            logger.warning(f"  ⚠️ {str(e)[:80]}")

    logger.info(f"📋 Schema chargé: {executed} commandes exécutées")
    return True


async def seed_couche1(graph_manager, data_dir: str = "data/cnesst"):
    """Injecte les données CNESST (Couche 1)."""
    from src.agents.cnesst_lesions_agent import CNESSTLesionsRAGAgent

    agent = CNESSTLesionsRAGAgent()

    try:
        agent.load_csv_files(data_dir)
        agent.compute_urban_risk_export()
        nodes = agent.to_safety_graph_nodes()
        count = graph_manager.inject_nodes(nodes, "cnesst-lesions-rag")
        logger.info(f"✅ Couche 1: {count} nœuds CNESST injectés")
        return count
    except FileNotFoundError:
        logger.warning("⚠️ CSV CNESST non trouvés dans data/cnesst/ — Couche 1 vide")
        return 0
    except Exception as e:
        logger.error(f"❌ Couche 1: {e}")
        return 0


async def seed_couche2(graph_manager, data_dir: str = "data/saaq"):
    """Injecte les données SAAQ (Couche 2)."""
    from src.agents.saaq_workzone_agent import SAAQWorkZoneAgent

    agent = SAAQWorkZoneAgent()

    try:
        agent.load_csv_files(data_dir)
        agent.build_risk_profiles()
        nodes = agent.to_safety_graph_nodes()
        count = graph_manager.inject_nodes(nodes, "saaq-workzone-rag")
        logger.info(f"✅ Couche 2: {count} nœuds SAAQ injectés")
        return count
    except FileNotFoundError:
        logger.warning("⚠️ CSV SAAQ non trouvés dans data/saaq/ — Couche 2 vide")
        return 0
    except Exception as e:
        logger.error(f"❌ Couche 2: {e}")
        return 0


async def seed_couche3(graph_manager, skip: bool = False):
    """Collecte et injecte les données MTL temps réel (Couche 3)."""
    if skip:
        logger.info("⏭️ Couche 3 ignorée (--skip-c3)")
        return 0

    from src.agents.urban_flow_agent import UrbanFlowAgent

    agent = UrbanFlowAgent()

    try:
        await agent.collect_all_sources()
        nodes = agent.to_safety_graph_nodes()
        count = graph_manager.inject_nodes(nodes, "urban-flow-agent")
        logger.info(f"✅ Couche 3: {count} nœuds MTL injectés")
        await agent.close()
        return count
    except Exception as e:
        logger.error(f"❌ Couche 3: {e}")
        await agent.close()
        return 0


def create_data_source_nodes(graph_manager):
    """Crée les nœuds DataSource pour les 9 sources."""
    sources = [
        {"id": "src-cifs", "name": "Entraves CIFS", "couche": 3, "refresh": "temps_reel"},
        {"id": "src-pietons", "name": "Comptages piétons", "couche": 3, "refresh": "horaire"},
        {"id": "src-velos", "name": "Comptages vélos", "couche": 3, "refresh": "horaire"},
        {"id": "src-bluetooth", "name": "Capteurs Bluetooth", "couche": 3, "refresh": "15min"},
        {"id": "src-agir", "name": "Permis AGIR", "couche": 3, "refresh": "quotidien"},
        {"id": "src-meteo", "name": "Météo Canada", "couche": 3, "refresh": "horaire"},
        {"id": "src-bixi", "name": "Stations Bixi", "couche": 3, "refresh": "5min"},
        {"id": "src-cnesst", "name": "CNESST Lésions", "couche": 1, "refresh": "annuel"},
        {"id": "src-saaq", "name": "SAAQ Zone travaux", "couche": 2, "refresh": "annuel"},
    ]

    nodes = [
        {"type": "DataSource", "id": s["id"], "properties": {
            "name": s["name"], "couche": s["couche"], "refresh": s["refresh"],
        }}
        for s in sources
    ]

    return graph_manager.inject_nodes(nodes, "seed-script")


def verify_graph(graph_manager):
    """Vérifie l'intégrité du SafetyGraph."""
    stats = graph_manager.get_stats()
    logger.info("=" * 50)
    logger.info("📊 VÉRIFICATION SAFETYGRAPH")
    logger.info("=" * 50)

    for key, val in stats.items():
        if key not in ("connected", "graph", "mode"):
            status = "✅" if val > 0 else "⚪"
            logger.info(f"  {status} {key}: {val}")

    logger.info("=" * 50)
    return stats


async def main():
    parser = argparse.ArgumentParser(description="Initialisation SafetyGraph AX5 UrbanIA")
    parser.add_argument("--host", default="localhost", help="Hôte FalkorDB")
    parser.add_argument("--port", type=int, default=6379, help="Port FalkorDB")
    parser.add_argument("--skip-c3", action="store_true", help="Ignorer la collecte Couche 3")
    parser.add_argument("--schema-only", action="store_true", help="Charger uniquement le schema")
    args = parser.parse_args()

    from src.graph.safety_graph import SafetyGraphManager

    logger.info("🧠 Initialisation SafetyGraph AX5 UrbanIA")
    logger.info(f"   FalkorDB: {args.host}:{args.port}")

    gm = SafetyGraphManager(host=args.host, port=args.port)

    if not gm.connect():
        logger.error("❌ Impossible de se connecter à FalkorDB")
        logger.info("   → docker compose up -d falkordb")
        sys.exit(1)

    # Schema
    load_schema(gm._graph)

    if args.schema_only:
        logger.info("✅ Schema chargé. Terminé.")
        gm.close()
        return

    # DataSource nodes
    create_data_source_nodes(gm)

    # 3 couches
    c1 = await seed_couche1(gm)
    c2 = await seed_couche2(gm)
    c3 = await seed_couche3(gm, skip=args.skip_c3)

    # Vérification
    verify_graph(gm)

    total = c1 + c2 + c3
    logger.info(f"🎯 Total: {total} nœuds injectés (C1={c1}, C2={c2}, C3={c3})")

    gm.close()


if __name__ == "__main__":
    asyncio.run(main())
