"""
=============================================================================
CascadeAgent — Modélisation d'effets cascade réseau urbain
=============================================================================
Agent qui modélise comment un incident sur un chantier peut se propager
en cascade à travers le réseau urbain (détours, congestion, accumulation
d'usagers vulnérables sur des itinéraires alternatifs non sécurisés).

Concept "réseau 3.7 km²":
  Un chantier moyen à Montréal impacte un rayon de ~1.1 km
  → Surface π×1.1² ≈ 3.8 km² d'influence
  → Les détours créent des corridors de transfert de risque

Le CascadeAgent modélise 3 types d'effets cascade:
  1. CASCADE TRAFIC    — détours → congestion → risque piétons
  2. CASCADE PIÉTONS   — trottoirs fermés → traversées dangereuses
  3. CASCADE CYCLISTES — pistes cyclables déviées → partage voie auto

Inputs:
  - CIFSConnector (entraves + géoloc)
  - CoactivityAgent (clusters)
  - UrbanFlowAgent (flux temps réel)

Outputs:
  - Zones de transfert de risque → NudgeAgent
  - Corridors impactés → SafetyGraph
  - Score cascade → UrbanRiskScoringEngine

Conformité: Charte AgenticX5 | Primauté de la vie
=============================================================================
"""

import logging
import math
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CascadeNode:
    """Nœud dans le réseau de cascade"""
    id: str
    latitude: float
    longitude: float
    type_node: str                      # chantier | intersection | corridor | deviation
    risk_received: float = 0.0         # Risque reçu par propagation
    risk_emitted: float = 0.0          # Risque émis vers le réseau
    flux_detourne: int = 0             # Nombre d'usagers détournés
    distance_source_m: float = 0.0     # Distance au chantier source


@dataclass
class CascadeCorridor:
    """Corridor de transfert de risque"""
    corridor_id: str
    source_chantier: str
    nodes: List[CascadeNode] = field(default_factory=list)
    type_cascade: str = "trafic"       # trafic | pietons | cyclistes
    length_m: float = 0.0
    risk_transfer: float = 0.0         # Risque transféré (0-1)
    users_redirected: int = 0
    severity: str = "green"


@dataclass
class CascadeReport:
    """Rapport complet de modélisation cascade"""
    zone_id: str
    corridors: List[CascadeCorridor] = field(default_factory=list)
    total_users_redirected: int = 0
    max_cascade_depth: int = 0         # Profondeur max de propagation
    cascade_score: float = 0.0        # Score global (0-100)
    severity: str = "green"
    requires_hitl: bool = False
    risk_hotspots: List[Dict] = field(default_factory=list)
    timestamp: str = ""


class CascadeAgent:
    """
    Agent de modélisation des effets cascade dans le réseau urbain.
    
    Simule la propagation du risque quand un chantier modifie les
    flux normaux de circulation et crée des zones de transfert
    de risque pour les usagers vulnérables.
    """

    AGENT_ID = "cascade-agent"
    AGENT_VERSION = "1.0.0"

    # Paramètres du modèle de propagation
    INFLUENCE_RADIUS_M = 1100          # Rayon d'influence d'un chantier
    PROPAGATION_DECAY = 0.7            # Atténuation par nœud de propagation
    MAX_CASCADE_DEPTH = 4              # Profondeur max de cascade
    NETWORK_AREA_KM2 = 3.7            # Zone d'influence type

    # Ratios de déviation par type d'usager (% détournés)
    DEVIATION_RATIOS = {
        "pietons": {"fermeture_trottoir": 0.90, "occupation_chaussee": 0.40, "detour": 0.60},
        "cyclistes": {"fermeture_piste": 0.85, "occupation_chaussee": 0.50, "detour": 0.70},
        "automobilistes": {"fermeture": 0.95, "occupation_chaussee": 0.30, "detour": 0.80},
    }

    def __init__(self):
        self._last_report: Optional[CascadeReport] = None
        logger.info(f"🌊 CascadeAgent v{self.AGENT_VERSION} initialisé")

    def model_cascade(
        self,
        chantiers: List[Dict],
        flux_pietons: int = 2000,
        flux_cyclistes: int = 500,
        zone_id: str = "MTL",
    ) -> CascadeReport:
        """
        Modélise les effets cascade pour un ensemble de chantiers.
        
        Pipeline:
        1. Pour chaque chantier, calculer la zone d'influence
        2. Modéliser les corridors de déviation
        3. Estimer les usagers redirigés
        4. Calculer le transfert de risque
        5. Identifier les hotspots
        """
        report = CascadeReport(
            zone_id=zone_id,
            timestamp=datetime.now().isoformat(),
        )

        for chantier in chantiers:
            lat = chantier.get("latitude")
            lon = chantier.get("longitude")
            if not lat or not lon:
                continue

            # Modéliser les 3 types de cascade
            for cascade_type in ["trafic", "pietons", "cyclistes"]:
                corridor = self._model_corridor(chantier, cascade_type, flux_pietons, flux_cyclistes)
                if corridor:
                    report.corridors.append(corridor)

        # Agrégation
        if report.corridors:
            report.total_users_redirected = sum(c.users_redirected for c in report.corridors)
            report.max_cascade_depth = max(len(c.nodes) for c in report.corridors)
            report.cascade_score = self._compute_cascade_score(report)
            report.severity = self._get_severity(report.cascade_score)
            report.requires_hitl = report.severity in ("orange", "red")
            report.risk_hotspots = self._identify_hotspots(report)

        self._last_report = report

        logger.info(
            f"🌊 Cascade: {len(report.corridors)} corridors | "
            f"{report.total_users_redirected} usagers redirigés | "
            f"Score: {report.cascade_score:.1f} | Sévérité: {report.severity}"
        )

        return report

    def _model_corridor(
        self, chantier: Dict, cascade_type: str,
        flux_pietons: int, flux_cyclistes: int,
    ) -> Optional[CascadeCorridor]:
        """Modélise un corridor de déviation pour un type de cascade."""
        chantier_id = chantier.get("id", "unknown")
        lat = chantier["latitude"]
        lon = chantier["longitude"]
        type_entrave = (chantier.get("type_entrave", "") or "").lower()

        # Déterminer le ratio de déviation
        if cascade_type == "pietons":
            base_flux = flux_pietons
            ratio_key = "fermeture_trottoir" if "fermeture" in type_entrave else "occupation_chaussee"
            ratio = self.DEVIATION_RATIOS["pietons"].get(ratio_key, 0.3)
        elif cascade_type == "cyclistes":
            base_flux = flux_cyclistes
            ratio_key = "fermeture_piste" if "fermeture" in type_entrave else "occupation_chaussee"
            ratio = self.DEVIATION_RATIOS["cyclistes"].get(ratio_key, 0.3)
        else:
            base_flux = flux_pietons + flux_cyclistes
            ratio = self.DEVIATION_RATIOS["automobilistes"].get(
                "fermeture" if "fermeture" in type_entrave else "occupation_chaussee", 0.3
            )

        users_redirected = int(base_flux * ratio)
        if users_redirected < 10:
            return None

        # Simuler les nœuds de propagation
        nodes = []
        risk_current = chantier.get("impact_score", 5.0) / 10.0

        for depth in range(1, self.MAX_CASCADE_DEPTH + 1):
            distance = depth * (self.INFLUENCE_RADIUS_M / self.MAX_CASCADE_DEPTH)
            risk_current *= self.PROPAGATION_DECAY

            # Nœuds de déviation dans les 4 directions cardinales
            for direction, (dlat, dlon) in enumerate([
                (0.001 * depth, 0), (0, 0.001 * depth),
                (-0.001 * depth, 0), (0, -0.001 * depth),
            ]):
                if direction > 0 and depth > 2:
                    continue  # Limiter la ramification

                node = CascadeNode(
                    id=f"{chantier_id}-{cascade_type}-D{depth}-{direction}",
                    latitude=lat + dlat,
                    longitude=lon + dlon,
                    type_node="deviation" if depth == 1 else "corridor",
                    risk_received=risk_current,
                    risk_emitted=risk_current * self.PROPAGATION_DECAY,
                    flux_detourne=int(users_redirected * (self.PROPAGATION_DECAY ** depth)),
                    distance_source_m=distance,
                )
                nodes.append(node)

            if risk_current < 0.05:
                break

        corridor = CascadeCorridor(
            corridor_id=f"COR-{chantier_id}-{cascade_type}",
            source_chantier=chantier_id,
            nodes=nodes,
            type_cascade=cascade_type,
            length_m=max(n.distance_source_m for n in nodes) if nodes else 0,
            risk_transfer=nodes[0].risk_received if nodes else 0,
            users_redirected=users_redirected,
        )

        corridor.severity = self._corridor_severity(corridor)
        return corridor

    def _compute_cascade_score(self, report: CascadeReport) -> float:
        """Score cascade global (0-100)."""
        if not report.corridors:
            return 0.0

        # Composantes du score
        user_score = min(40, report.total_users_redirected / 100)
        corridor_score = min(30, len(report.corridors) * 5)
        depth_score = min(15, report.max_cascade_depth * 4)
        risk_score = min(15, sum(c.risk_transfer for c in report.corridors) * 20)

        return round(user_score + corridor_score + depth_score + risk_score, 1)

    def _identify_hotspots(self, report: CascadeReport) -> List[Dict]:
        """Identifie les points chauds de convergence de risque."""
        hotspots = []

        # Grouper les nœuds par proximité
        all_nodes = []
        for corridor in report.corridors:
            all_nodes.extend(corridor.nodes)

        # Trouver les intersections de corridors
        for i, n1 in enumerate(all_nodes):
            convergence = 0
            total_risk = n1.risk_received

            for j, n2 in enumerate(all_nodes):
                if i != j:
                    dist = self._haversine_m(n1.latitude, n1.longitude, n2.latitude, n2.longitude)
                    if dist < 100:  # 100m
                        convergence += 1
                        total_risk += n2.risk_received

            if convergence >= 2:
                hotspots.append({
                    "latitude": n1.latitude,
                    "longitude": n1.longitude,
                    "convergence": convergence,
                    "total_risk": round(total_risk, 3),
                    "flux_detourne": n1.flux_detourne,
                })

        # Dédupliquer et trier
        unique = []
        for h in sorted(hotspots, key=lambda x: x["total_risk"], reverse=True):
            if not any(
                self._haversine_m(h["latitude"], h["longitude"], u["latitude"], u["longitude"]) < 50
                for u in unique
            ):
                unique.append(h)

        return unique[:10]

    @staticmethod
    def _get_severity(score: float) -> str:
        if score >= 75:
            return "red"
        elif score >= 50:
            return "orange"
        elif score >= 25:
            return "yellow"
        return "green"

    @staticmethod
    def _corridor_severity(corridor: CascadeCorridor) -> str:
        if corridor.users_redirected >= 1000 and corridor.risk_transfer >= 0.5:
            return "red"
        elif corridor.users_redirected >= 500 or corridor.risk_transfer >= 0.4:
            return "orange"
        elif corridor.users_redirected >= 200:
            return "yellow"
        return "green"

    # =========================================================================
    # EXPORT SAFETYGRAPH
    # =========================================================================

    def to_safety_graph_nodes(self) -> List[Dict[str, Any]]:
        """Export SafetyGraph — corridors + hotspots."""
        if not self._last_report:
            return []

        nodes = []

        # Corridors
        for cor in self._last_report.corridors:
            nodes.append({
                "type": "CascadeCorridor",
                "id": f"cascade-{cor.corridor_id.lower()}",
                "properties": {
                    "source_chantier": cor.source_chantier,
                    "type_cascade": cor.type_cascade,
                    "length_m": cor.length_m,
                    "risk_transfer": cor.risk_transfer,
                    "users_redirected": cor.users_redirected,
                    "severity": cor.severity,
                },
            })

        # Hotspots
        for i, hs in enumerate(self._last_report.risk_hotspots):
            nodes.append({
                "type": "CascadeHotspot",
                "id": f"hotspot-{i + 1:03d}",
                "properties": hs,
            })

        return nodes

    def query(self, question: str) -> str:
        """Interface RAG."""
        if not self._last_report:
            return "Aucune modélisation cascade disponible."

        r = self._last_report
        return (
            f"Cascade {r.zone_id}: {len(r.corridors)} corridors de déviation, "
            f"{r.total_users_redirected} usagers redirigés, "
            f"score cascade {r.cascade_score:.1f}/100, "
            f"{len(r.risk_hotspots)} hotspots identifiés. "
            f"Sévérité: {r.severity}."
        )

    @staticmethod
    def _haversine_m(lat1, lon1, lat2, lon2) -> float:
        R = 6371000
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
