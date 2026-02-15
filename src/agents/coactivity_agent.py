"""
=============================================================================
CoactivityAgent — Détection de coactivité inter-chantiers
=============================================================================
Agent qui détecte les situations de coactivité dangereuse lorsque
plusieurs chantiers sont actifs simultanément dans un rayon restreint.

La coactivité est le facteur multiplicateur de risque le plus critique:
- 2 chantiers < 300m → ×1.3
- 3 chantiers < 300m → ×1.5
- 4+ chantiers < 300m → ×2.0 (HITL obligatoire)

Inputs:
  - CIFSConnector (entraves actives géolocalisées)
  - Permis AGIR (chantiers planifiés)
  - SafetyGraph (historique zones à risque)

Outputs:
  - Alertes coactivité → NudgeAgent
  - Zones cluster → SafetyGraph
  - Facteur multiplicateur → UrbanRiskScoringEngine

Conformité: Charte AgenticX5 | Primauté de la vie | HITL ≥ orange
=============================================================================
"""

import logging
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class Chantier:
    """Chantier géolocalisé (fusion CIFS + AGIR)"""
    id: str
    rue: str
    latitude: float
    longitude: float
    type_travaux: str = ""
    date_debut: str = ""
    date_fin: str = ""
    arrondissement: str = ""
    source: str = "cifs"              # cifs | agir
    impact_score: float = 5.0


@dataclass
class ClusterCoactivite:
    """Cluster de chantiers en situation de coactivité"""
    cluster_id: str
    center_lat: float
    center_lon: float
    chantiers: List[Chantier] = field(default_factory=list)
    radius_m: float = 300.0
    risk_multiplier: float = 1.0
    severity: str = "green"
    requires_hitl: bool = False
    rues_impactees: List[str] = field(default_factory=list)
    usagers_exposes: Dict[str, int] = field(default_factory=dict)
    alert_message: str = ""
    timestamp: str = ""

    @property
    def count(self) -> int:
        return len(self.chantiers)


@dataclass
class CoactivityReport:
    """Rapport complet de coactivité pour une zone"""
    zone_id: str
    total_chantiers: int = 0
    total_clusters: int = 0
    clusters: List[ClusterCoactivite] = field(default_factory=list)
    max_risk_multiplier: float = 1.0
    global_severity: str = "green"
    requires_hitl: bool = False
    timestamp: str = ""


class CoactivityAgent:
    """
    Agent de détection de coactivité inter-chantiers.
    
    Analyse spatiale des chantiers actifs pour identifier les zones
    où la concentration de travaux simultanés crée un risque accru
    pour les usagers vulnérables (piétons, cyclistes, PMR).
    """

    AGENT_ID = "coactivity-agent"
    AGENT_VERSION = "1.0.0"

    # Seuils de coactivité
    RADIUS_M = 300          # Rayon de détection (mètres)
    MIN_CLUSTER_SIZE = 2    # Minimum pour déclencher une alerte

    # Multiplicateurs de risque par taille de cluster
    RISK_MULTIPLIERS = {
        2: 1.3,     # 2 chantiers → risque modéré
        3: 1.5,     # 3 chantiers → risque élevé
        4: 1.8,     # 4 chantiers → risque très élevé
        5: 2.0,     # 5+ chantiers → critique
    }

    # Facteurs aggravants par type de travaux
    TYPE_AGGRAVANTS = {
        "fermeture": 1.3,
        "excavation": 1.25,
        "demolition": 1.4,
        "grue": 1.35,
        "detour": 1.2,
        "occupation_chaussee": 1.1,
    }

    def __init__(self):
        self._last_report: Optional[CoactivityReport] = None
        logger.info(f"⚠️ CoactivityAgent v{self.AGENT_VERSION} initialisé")

    def analyze(self, chantiers: List[Chantier], zone_id: str = "MTL") -> CoactivityReport:
        """
        Analyse de coactivité sur une liste de chantiers géolocalisés.
        
        Pipeline:
        1. Filtrer les chantiers avec coordonnées valides
        2. Clustering spatial (DBSCAN simplifié)
        3. Calcul des multiplicateurs de risque
        4. Identification des usagers exposés
        5. Génération des alertes
        """
        report = CoactivityReport(
            zone_id=zone_id,
            total_chantiers=len(chantiers),
            timestamp=datetime.now().isoformat(),
        )

        # Filtrer chantiers géolocalisés
        geo_chantiers = [c for c in chantiers if c.latitude and c.longitude]
        if len(geo_chantiers) < self.MIN_CLUSTER_SIZE:
            self._last_report = report
            return report

        # Clustering spatial
        clusters = self._spatial_clustering(geo_chantiers)
        report.total_clusters = len(clusters)

        # Calcul des risques par cluster
        for cluster in clusters:
            cluster.risk_multiplier = self._compute_risk_multiplier(cluster)
            cluster.severity = self._get_severity(cluster)
            cluster.requires_hitl = cluster.severity in ("orange", "red")
            cluster.usagers_exposes = self._estimate_exposed_users(cluster)
            cluster.alert_message = self._generate_alert_message(cluster)
            cluster.timestamp = report.timestamp

        report.clusters = sorted(clusters, key=lambda c: c.risk_multiplier, reverse=True)

        if clusters:
            report.max_risk_multiplier = max(c.risk_multiplier for c in clusters)
            report.global_severity = max(
                (c.severity for c in clusters),
                key=lambda s: ["green", "yellow", "orange", "red"].index(s)
            )
            report.requires_hitl = any(c.requires_hitl for c in clusters)

        self._last_report = report

        logger.info(
            f"⚠️ Coactivité: {report.total_clusters} clusters détectés | "
            f"Max ×{report.max_risk_multiplier} | Sévérité: {report.global_severity}"
        )

        return report

    def get_zone_multiplier(self, arrondissement: str) -> float:
        """Retourne le multiplicateur de coactivité pour un arrondissement."""
        if not self._last_report:
            return 1.0

        # Trouver le cluster le plus risqué dans cet arrondissement
        max_mult = 1.0
        for cluster in self._last_report.clusters:
            for chantier in cluster.chantiers:
                if chantier.arrondissement == arrondissement:
                    max_mult = max(max_mult, cluster.risk_multiplier)
                    break

        return max_mult

    # =========================================================================
    # CLUSTERING SPATIAL
    # =========================================================================

    def _spatial_clustering(self, chantiers: List[Chantier]) -> List[ClusterCoactivite]:
        """
        Clustering spatial simplifié (DBSCAN-like).
        Regroupe les chantiers situés à moins de RADIUS_M mètres.
        """
        n = len(chantiers)
        visited = [False] * n
        clusters = []
        cluster_count = 0

        for i in range(n):
            if visited[i]:
                continue

            # Trouver tous les voisins
            neighbors = [i]
            for j in range(n):
                if i != j and not visited[j]:
                    dist = self._haversine_m(
                        chantiers[i].latitude, chantiers[i].longitude,
                        chantiers[j].latitude, chantiers[j].longitude,
                    )
                    if dist <= self.RADIUS_M:
                        neighbors.append(j)

            if len(neighbors) >= self.MIN_CLUSTER_SIZE:
                cluster_count += 1
                cluster_chantiers = [chantiers[idx] for idx in neighbors]

                # Marquer comme visités
                for idx in neighbors:
                    visited[idx] = True

                # Calculer le centre du cluster
                center_lat = sum(c.latitude for c in cluster_chantiers) / len(cluster_chantiers)
                center_lon = sum(c.longitude for c in cluster_chantiers) / len(cluster_chantiers)

                cluster = ClusterCoactivite(
                    cluster_id=f"CLU-{cluster_count:03d}",
                    center_lat=center_lat,
                    center_lon=center_lon,
                    chantiers=cluster_chantiers,
                    rues_impactees=list(set(c.rue for c in cluster_chantiers if c.rue)),
                )
                clusters.append(cluster)

        return clusters

    # =========================================================================
    # CALCULS DE RISQUE
    # =========================================================================

    def _compute_risk_multiplier(self, cluster: ClusterCoactivite) -> float:
        """Calcule le multiplicateur de risque d'un cluster."""
        count = cluster.count

        # Base: multiplicateur par taille
        if count >= 5:
            base = self.RISK_MULTIPLIERS[5]
        else:
            base = self.RISK_MULTIPLIERS.get(count, 1.0)

        # Aggravation par types de travaux dangereux
        type_bonus = 1.0
        for chantier in cluster.chantiers:
            t = (chantier.type_travaux or "").lower()
            for key, factor in self.TYPE_AGGRAVANTS.items():
                if key in t:
                    type_bonus = max(type_bonus, factor)
                    break

        # Score final plafonné à 2.5
        return round(min(2.5, base * type_bonus), 2)

    @staticmethod
    def _get_severity(cluster: ClusterCoactivite) -> str:
        """Détermine la sévérité du cluster."""
        m = cluster.risk_multiplier
        if m >= 2.0:
            return "red"
        elif m >= 1.5:
            return "orange"
        elif m >= 1.3:
            return "yellow"
        return "green"

    @staticmethod
    def _estimate_exposed_users(cluster: ClusterCoactivite) -> Dict[str, int]:
        """Estime les usagers exposés autour du cluster."""
        # Estimation basée sur la densité urbaine Montréal
        # et le nombre de rues impactées
        n_rues = len(cluster.rues_impactees)
        hour = datetime.now().hour
        is_peak = 7 <= hour <= 9 or 16 <= hour <= 18

        base_factor = 1.5 if is_peak else 1.0

        return {
            "pietons": int(n_rues * 150 * base_factor),
            "cyclistes": int(n_rues * 40 * base_factor),
            "pmr": int(n_rues * 8 * base_factor),
            "automobilistes": int(n_rues * 300 * base_factor),
            "transport_commun": int(n_rues * 80 * base_factor),
        }

    @staticmethod
    def _generate_alert_message(cluster: ClusterCoactivite) -> str:
        """Génère un message d'alerte pour le cluster."""
        rues = ", ".join(cluster.rues_impactees[:3])
        suffix = f" et {len(cluster.rues_impactees) - 3} autres" if len(cluster.rues_impactees) > 3 else ""

        if cluster.severity == "red":
            return (
                f"🔴 COACTIVITÉ CRITIQUE — {cluster.count} chantiers simultanés "
                f"dans un rayon de 300m ({rues}{suffix}). "
                f"Risque ×{cluster.risk_multiplier}. HITL OBLIGATOIRE."
            )
        elif cluster.severity == "orange":
            return (
                f"🟠 COACTIVITÉ ÉLEVÉE — {cluster.count} chantiers à proximité "
                f"({rues}{suffix}). Risque ×{cluster.risk_multiplier}. Validation requise."
            )
        elif cluster.severity == "yellow":
            return (
                f"🟡 Coactivité détectée — {cluster.count} chantiers "
                f"({rues}{suffix}). Risque ×{cluster.risk_multiplier}."
            )
        return ""

    # =========================================================================
    # EXPORT
    # =========================================================================

    def to_safety_graph_nodes(self) -> List[Dict[str, Any]]:
        """Génère les nœuds SafetyGraph pour les clusters de coactivité."""
        if not self._last_report:
            return []

        nodes = []
        for cluster in self._last_report.clusters:
            nodes.append({
                "type": "CoactivityCluster",
                "id": f"coact-{cluster.cluster_id.lower()}",
                "properties": {
                    "center_lat": cluster.center_lat,
                    "center_lon": cluster.center_lon,
                    "chantier_count": cluster.count,
                    "risk_multiplier": cluster.risk_multiplier,
                    "severity": cluster.severity,
                    "requires_hitl": cluster.requires_hitl,
                    "rues": "|".join(cluster.rues_impactees),
                    "pietons_exposes": cluster.usagers_exposes.get("pietons", 0),
                    "cyclistes_exposes": cluster.usagers_exposes.get("cyclistes", 0),
                    "timestamp": cluster.timestamp,
                },
            })

        return nodes

    def query(self, question: str) -> str:
        """Interface RAG."""
        if not self._last_report:
            return "Aucune analyse de coactivité disponible."

        r = self._last_report
        q = question.lower()

        if "cluster" in q or "zone" in q:
            if not r.clusters:
                return "Aucun cluster de coactivité détecté."
            lines = [f"{c.cluster_id}: {c.count} chantiers, ×{c.risk_multiplier} ({c.severity})" for c in r.clusters]
            return f"{len(r.clusters)} clusters:\n" + "\n".join(lines)

        return (
            f"Coactivité {r.zone_id}: {r.total_chantiers} chantiers analysés, "
            f"{r.total_clusters} clusters détectés, "
            f"multiplicateur max ×{r.max_risk_multiplier}, "
            f"sévérité globale: {r.global_severity}."
        )

    @staticmethod
    def _haversine_m(lat1, lon1, lat2, lon2) -> float:
        """Distance en mètres entre deux points GPS."""
        R = 6371000
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
