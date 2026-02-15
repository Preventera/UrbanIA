"""
=============================================================================
TerritoryPlannerAgent — Planification spatiale du territoire municipal
=============================================================================
Agent qui maintient une vue d'ensemble du territoire et planifie
la distribution spatiale et temporelle des chantiers pour minimiser
l'impact cumulé sur les usagers et les services municipaux.

Fonctions:
  1. Carte de chaleur du territoire (densité chantiers par zone)
  2. Calendrier territorial (timeline multi-chantiers)
  3. Détection des corridors stratégiques à protéger
  4. Saisonnalité (hiver = contraintes gel, été = festivals)
  5. Coordination inter-arrondissements
  6. Rapport hebdomadaire pour le Bureau des permis

Inputs:
  - PermitOptimizerAgent (permis actifs + planifiés)
  - CIFSConnector (entraves temps réel)
  - Calendrier municipal (événements)
  - Réseau cyclable / piétonnier structurant

Conformité: Charte AgenticX5 | HITL obligatoire
=============================================================================
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ZoneCapacity:
    """Capacité d'une zone du territoire"""
    zone_id: str
    arrondissement: str
    max_chantiers: int
    active_chantiers: int = 0
    planned_chantiers: int = 0
    utilization_pct: float = 0.0
    status: str = "available"          # available | busy | saturated | blocked
    corridors_proteges: List[str] = field(default_factory=list)
    next_available: str = ""


@dataclass
class StrategicCorridor:
    """Corridor stratégique à protéger (artère piétonne, piste cyclable structurante)"""
    corridor_id: str
    name: str
    type_corridor: str                  # pieton | cyclable | transport | urgence
    arrondissements: List[str] = field(default_factory=list)
    priority: int = 5                   # 1-10
    max_simultaneous_chantiers: int = 1
    current_chantiers: int = 0
    protected: bool = True


@dataclass
class SeasonalConstraint:
    """Contrainte saisonnière"""
    period: str                         # hiver | printemps | ete | automne
    months: List[int] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    risk_modifier: float = 1.0


@dataclass
class TerritoryReport:
    """Rapport territorial hebdomadaire"""
    date: str
    total_zones: int = 0
    zones: List[ZoneCapacity] = field(default_factory=list)
    zones_saturees: int = 0
    corridors_impactes: int = 0
    seasonal_constraints: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    heatmap: Dict[str, float] = field(default_factory=dict)  # arrondissement → utilisation%


# Corridors stratégiques Montréal
CORRIDORS_STRATEGIQUES = [
    StrategicCorridor("COR-STC", "Sainte-Catherine", "pieton", ["Ville-Marie"], priority=10, max_simultaneous_chantiers=1),
    StrategicCorridor("COR-REV-SD", "REV Saint-Denis", "cyclable", ["Ville-Marie", "Le Plateau-Mont-Royal"], priority=9, max_simultaneous_chantiers=1),
    StrategicCorridor("COR-REV-PL", "REV Peel", "cyclable", ["Ville-Marie"], priority=9, max_simultaneous_chantiers=1),
    StrategicCorridor("COR-CANAL", "Canal Lachine", "cyclable", ["Le Sud-Ouest", "Lachine"], priority=8, max_simultaneous_chantiers=1),
    StrategicCorridor("COR-MR", "Mont-Royal", "pieton", ["Le Plateau-Mont-Royal"], priority=8, max_simultaneous_chantiers=2),
    StrategicCorridor("COR-BERRI", "Berri / Station centrale", "transport", ["Ville-Marie"], priority=10, max_simultaneous_chantiers=1),
    StrategicCorridor("COR-GUY", "Guy-Concordia", "transport", ["Ville-Marie"], priority=8, max_simultaneous_chantiers=1),
    StrategicCorridor("COR-NOTREDAME", "Notre-Dame", "urgence", ["Ville-Marie", "Mercier-Hochelaga-Maisonneuve"], priority=10, max_simultaneous_chantiers=1),
    StrategicCorridor("COR-RENE", "René-Lévesque", "urgence", ["Ville-Marie"], priority=10, max_simultaneous_chantiers=1),
    StrategicCorridor("COR-MASSON", "Masson", "pieton", ["Rosemont-La Petite-Patrie"], priority=7, max_simultaneous_chantiers=2),
]

# Contraintes saisonnières Montréal
SEASONAL_CONSTRAINTS = [
    SeasonalConstraint("hiver", [12, 1, 2, 3], [
        "Gel du sol — excavation limitée",
        "Déneigement prioritaire — emprises réduites",
        "Visibilité réduite — signalisation lumineuse obligatoire",
        "Risque verglas piétons — corridors chauffés si fermeture trottoir",
    ], risk_modifier=1.3),
    SeasonalConstraint("printemps", [4, 5], [
        "Dégel — structures temporaires fragiles",
        "Nids-de-poule — coordination voirie prioritaire",
        "Reprise cyclisme — protection pistes obligatoire",
    ], risk_modifier=1.1),
    SeasonalConstraint("ete", [6, 7, 8], [
        "Festivals et événements — coordination calendrier culturel",
        "Terrasses — emprises piétonnes protégées",
        "Tourisme — signalisation bilingue obligatoire",
        "Canicule — pauses obligatoires travailleurs",
    ], risk_modifier=1.15),
    SeasonalConstraint("automne", [9, 10, 11], [
        "Rentrée scolaire — zones scolaires protégées",
        "Pluies — drainage chantier obligatoire",
        "Feuilles mortes — visibilité signalisation",
    ], risk_modifier=1.05),
]


class TerritoryPlannerAgent:
    """
    Agent de planification spatiale du territoire municipal.
    
    Maintient la carte de chaleur du territoire et identifie
    les zones saturées, les corridors stratégiques à protéger
    et les contraintes saisonnières.
    """

    AGENT_ID = "territory-planner"
    AGENT_VERSION = "1.0.0"

    # Capacité par défaut si arrondissement non listé
    DEFAULT_CAPACITY = 6

    # Arrondissements avec capacité
    CAPACITIES = {
        "Ville-Marie": 15, "Le Plateau-Mont-Royal": 10,
        "Rosemont-La Petite-Patrie": 10, "Côte-des-Neiges-Notre-Dame-de-Grâce": 10,
        "Le Sud-Ouest": 8, "Mercier-Hochelaga-Maisonneuve": 8,
        "Ahuntsic-Cartierville": 8, "Villeray-Saint-Michel-Parc-Extension": 8,
        "Saint-Laurent": 7, "Rivière-des-Prairies-Pointe-aux-Trembles": 6,
        "Lachine": 5, "LaSalle": 5, "Verdun": 5,
        "Montréal-Nord": 5, "Saint-Léonard": 5, "Pierrefonds-Roxboro": 5,
        "Anjou": 4, "Outremont": 4,
        "Île-Bizard-Sainte-Geneviève": 3,
    }

    def __init__(self):
        self._corridors = list(CORRIDORS_STRATEGIQUES)
        self._zones: Dict[str, ZoneCapacity] = {}
        self._last_report: Optional[TerritoryReport] = None
        logger.info(f"🗺️ TerritoryPlannerAgent v{self.AGENT_VERSION} initialisé")

    def generate_report(
        self,
        active_permits: List[Dict],
        planned_permits: List[Dict],
        events: Optional[List[Dict]] = None,
    ) -> TerritoryReport:
        """Génère le rapport territorial hebdomadaire."""
        report = TerritoryReport(
            date=date.today().isoformat(),
            total_zones=len(self.CAPACITIES),
        )

        # Construire les zones
        for arr, capacity in self.CAPACITIES.items():
            active = len([p for p in active_permits if p.get("arrondissement") == arr])
            planned = len([p for p in planned_permits if p.get("arrondissement") == arr])

            utilization = (active / capacity * 100) if capacity > 0 else 0
            if utilization >= 90:
                status = "saturated"
                report.zones_saturees += 1
            elif utilization >= 70:
                status = "busy"
            elif utilization >= 40:
                status = "available"
            else:
                status = "available"

            zone = ZoneCapacity(
                zone_id=arr[:3].upper(),
                arrondissement=arr,
                max_chantiers=capacity,
                active_chantiers=active,
                planned_chantiers=planned,
                utilization_pct=round(utilization, 1),
                status=status,
            )
            report.zones.append(zone)
            report.heatmap[arr] = round(utilization, 1)

        # Corridors impactés
        for corridor in self._corridors:
            chantiers_on = 0
            for p in active_permits:
                rue = (p.get("rue", "") or "").lower()
                if corridor.name.lower() in rue:
                    chantiers_on += 1

            corridor.current_chantiers = chantiers_on
            if chantiers_on > 0:
                report.corridors_impactes += 1

        # Contraintes saisonnières
        month = datetime.now().month
        for sc in SEASONAL_CONSTRAINTS:
            if month in sc.months:
                report.seasonal_constraints.extend(sc.constraints)

        # Recommandations automatiques
        report.recommendations = self._generate_recommendations(report)

        self._last_report = report

        logger.info(
            f"🗺️ Rapport territorial: {report.zones_saturees} zones saturées | "
            f"{report.corridors_impactes} corridors impactés"
        )

        return report

    def check_corridor_availability(self, rue: str) -> Optional[StrategicCorridor]:
        """Vérifie si une rue est un corridor stratégique et sa disponibilité."""
        rue_lower = rue.lower()
        for corridor in self._corridors:
            if corridor.name.lower() in rue_lower or rue_lower in corridor.name.lower():
                return corridor
        return None

    def get_seasonal_modifier(self) -> float:
        """Retourne le modificateur saisonnier actuel."""
        month = datetime.now().month
        for sc in SEASONAL_CONSTRAINTS:
            if month in sc.months:
                return sc.risk_modifier
        return 1.0

    def _generate_recommendations(self, report: TerritoryReport) -> List[str]:
        """Génère des recommandations basées sur l'état du territoire."""
        recs = []

        # Zones saturées
        saturated = [z for z in report.zones if z.status == "saturated"]
        if saturated:
            recs.append(
                f"Reporter les nouveaux permis dans {', '.join(z.arrondissement for z in saturated)} "
                f"— capacité atteinte."
            )

        # Corridors à risque
        for corridor in self._corridors:
            if corridor.current_chantiers >= corridor.max_simultaneous_chantiers:
                recs.append(
                    f"Corridor {corridor.name} ({corridor.type_corridor}) saturé — "
                    f"aucun nouveau chantier autorisé."
                )

        # Saisonnalité
        if report.seasonal_constraints:
            recs.append(
                f"Contraintes saisonnières actives — "
                f"voir conditions spéciales ({len(report.seasonal_constraints)} règles)."
            )

        if not recs:
            recs.append("Territoire dans les capacités normales — aucune restriction particulière.")

        return recs

    def to_safety_graph_nodes(self) -> List[Dict[str, Any]]:
        """Export SafetyGraph."""
        if not self._last_report:
            return []

        nodes = []
        for zone in self._last_report.zones:
            nodes.append({
                "type": "TerritoryZone",
                "id": f"territory-{zone.zone_id.lower()}",
                "properties": {
                    "arrondissement": zone.arrondissement,
                    "max_chantiers": zone.max_chantiers,
                    "active_chantiers": zone.active_chantiers,
                    "utilization_pct": zone.utilization_pct,
                    "status": zone.status,
                },
            })

        for corridor in self._corridors:
            nodes.append({
                "type": "StrategicCorridor",
                "id": f"corridor-{corridor.corridor_id.lower()}",
                "properties": {
                    "name": corridor.name,
                    "type": corridor.type_corridor,
                    "priority": corridor.priority,
                    "current_chantiers": corridor.current_chantiers,
                    "max_simultaneous": corridor.max_simultaneous_chantiers,
                },
            })

        return nodes

    def query(self, question: str) -> str:
        """Interface RAG."""
        if not self._last_report:
            return "Aucun rapport territorial généré."

        r = self._last_report
        return (
            f"Territoire MTL: {r.total_zones} zones, {r.zones_saturees} saturées, "
            f"{r.corridors_impactes} corridors impactés. "
            f"Recommandations: {'; '.join(r.recommendations[:2])}"
        )
