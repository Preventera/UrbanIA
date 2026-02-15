"""
=============================================================================
PermitOptimizerAgent — Séquencement optimal des permis de chantier
=============================================================================
Agent de planification en AMONT qui analyse chaque demande de permis
de chantier AVANT son émission pour évaluer le risque de coactivité
et recommander un séquencement optimal sur le territoire.

Position dans la chaîne:
  PermitOptimizer (planification) → UrbanIA (surveillance) → NudgeAgent (alerte)

Inputs:
  - Permis AGIR (demandes en cours + émis)
  - SafetyGraph UrbanIA (historique risque par zone)
  - CNESST (profil risque par type de travaux)
  - SAAQ (zones accidentogènes)
  - Calendrier municipal (événements, festivals, marchés)

Outputs:
  - Score de risque prédictif PAR DEMANDE de permis
  - Recommandation: approuver / reporter / conditionner
  - Fenêtre optimale de travaux
  - Conditions de mitigation requises
  - Rapport d'impact territorial

Conformité: Charte AgenticX5 | HITL obligatoire sur toute décision de permis
=============================================================================
"""

import logging
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from enum import Enum

logger = logging.getLogger(__name__)


class PermitStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    CONDITIONAL = "conditional"
    DEFERRED = "deferred"
    REJECTED = "rejected"


class Recommendation(Enum):
    APPROVE = "approuver"
    DEFER = "reporter"
    CONDITION = "conditionner"
    ESCALATE = "escalader_hitl"


@dataclass
class PermitRequest:
    """Demande de permis de chantier"""
    permit_id: str
    applicant: str = ""                      # Entrepreneur / donneur d'ouvrage
    rue: str = ""
    de_rue: str = ""
    a_rue: str = ""
    arrondissement: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    type_travaux: str = ""              # aqueduc, voirie, bâtiment, telecom, etc.
    date_debut_demandee: str = ""
    date_fin_demandee: str = ""
    duree_jours: int = 0
    emprise_type: str = ""              # fermeture_complete, occupation_partielle, trottoir
    impact_pietons: bool = False
    impact_cyclistes: bool = False
    impact_transport: bool = False
    urgence: bool = False               # Travaux d'urgence (bris aqueduc, etc.)
    status: PermitStatus = PermitStatus.PENDING


@dataclass
class ConflictAnalysis:
    """Analyse des conflits avec les chantiers existants"""
    permit_id: str
    conflicts_found: int = 0
    nearby_active: List[Dict] = field(default_factory=list)      # Chantiers actifs <300m
    nearby_planned: List[Dict] = field(default_factory=list)     # Permis planifiés <300m
    temporal_overlap_days: int = 0
    coactivity_score: float = 0.0      # 0-100 score de coactivité prédictive
    cascade_risk: float = 0.0           # 0-100 risque d'effet cascade
    vulnerable_users_exposed: int = 0
    historical_risk: float = 0.0        # Score historique CNESST+SAAQ pour cette zone


@dataclass
class PermitDecision:
    """Décision et recommandation pour un permis"""
    permit_id: str
    recommendation: Recommendation
    risk_score: float                   # 0-100
    severity: str                       # green/yellow/orange/red
    requires_hitl: bool                 # Toujours True pour permis
    conditions: List[str] = field(default_factory=list)
    optimal_window: Optional[Dict] = None  # {start, end} fenêtre optimale
    mitigation_required: List[str] = field(default_factory=list)
    conflict_analysis: Optional[ConflictAnalysis] = None
    reasoning: str = ""
    timestamp: str = ""


@dataclass
class TerritorySnapshot:
    """État du territoire à un moment donné"""
    date: str
    total_active: int = 0
    total_planned: int = 0
    zones_saturees: List[str] = field(default_factory=list)      # Arrondissements saturés
    coactivity_hotspots: List[Dict] = field(default_factory=list)
    capacity_remaining: Dict[str, float] = field(default_factory=dict)  # % capacité par arr.


class PermitOptimizerAgent:
    """
    Agent de séquencement optimal des permis de chantier.
    
    Se positionne EN AMONT d'UrbanIA pour prévenir la coactivité
    plutôt que la détecter après coup.
    
    Pipeline par demande:
    1. Recevoir demande de permis
    2. Scanner le territoire (actifs + planifiés)
    3. Analyser les conflits spatiaux et temporels
    4. Calculer le score de risque prédictif
    5. Croiser avec données historiques (CNESST + SAAQ)
    6. Recommander: approuver / reporter / conditionner
    7. Si reporter → calculer fenêtre optimale
    8. Si conditionner → générer conditions de mitigation
    9. Soumettre au HITL pour validation finale
    """

    AGENT_ID = "permit-optimizer"
    AGENT_VERSION = "1.0.0"

    # Capacité territoire par arrondissement (max chantiers simultanés recommandés)
    TERRITORY_CAPACITY = {
        "Ville-Marie": 15,
        "Le Plateau-Mont-Royal": 10,
        "Rosemont-La Petite-Patrie": 10,
        "Côte-des-Neiges-Notre-Dame-de-Grâce": 10,
        "Le Sud-Ouest": 8,
        "Mercier-Hochelaga-Maisonneuve": 8,
        "Ahuntsic-Cartierville": 8,
        "Villeray-Saint-Michel-Parc-Extension": 8,
        "Rivière-des-Prairies-Pointe-aux-Trembles": 6,
        "Lachine": 5,
        "LaSalle": 5,
        "Verdun": 5,
        "Saint-Laurent": 7,
        "Anjou": 4,
        "Montréal-Nord": 5,
        "Outremont": 4,
        "Pierrefonds-Roxboro": 5,
        "Saint-Léonard": 5,
        "Île-Bizard-Sainte-Geneviève": 3,
    }

    # Seuils de risque
    RISK_THRESHOLDS = {
        "green": (0, 30),       # Approuver
        "yellow": (30, 55),     # Approuver avec suivi
        "orange": (55, 75),     # Conditionner
        "red": (75, 100),       # Reporter ou escalader
    }

    # Poids de scoring
    WEIGHTS = {
        "coactivity": 0.30,
        "vulnerable_users": 0.25,
        "historical_risk": 0.20,
        "cascade_potential": 0.15,
        "territory_saturation": 0.10,
    }

    # Facteurs par type de travaux
    TYPE_RISK = {
        "aqueduc": 7,
        "egout": 7,
        "voirie": 6,
        "batiment": 4,
        "telecom": 3,
        "gaz": 8,
        "electricite": 5,
        "amenagement": 4,
        "demolition": 9,
        "excavation": 8,
    }

    # Facteurs par type d'emprise
    EMPRISE_RISK = {
        "fermeture_complete": 10,
        "occupation_partielle": 5,
        "trottoir": 7,
        "piste_cyclable": 6,
        "stationnement": 2,
    }

    def __init__(self):
        self._active_permits: List[PermitRequest] = []
        self._planned_permits: List[PermitRequest] = []
        self._decisions: List[PermitDecision] = []
        self._territory_cache: Optional[TerritorySnapshot] = None
        logger.info(f"📋 PermitOptimizerAgent v{self.AGENT_VERSION} initialisé")

    # =========================================================================
    # PIPELINE PRINCIPAL
    # =========================================================================

    def evaluate_permit(
        self,
        request: PermitRequest,
        active_chantiers: Optional[List[Dict]] = None,
        historical_data: Optional[Dict] = None,
    ) -> PermitDecision:
        """
        Évalue une demande de permis et produit une recommandation.
        
        Args:
            request: Demande de permis à évaluer
            active_chantiers: Chantiers actuellement actifs (depuis CIFS)
            historical_data: Données historiques CNESST+SAAQ pour la zone
        """
        logger.info(f"📋 Évaluation permis {request.permit_id} | {request.rue} | {request.type_travaux}")

        # Urgence → approuver immédiatement avec conditions
        if request.urgence:
            return self._approve_urgent(request)

        # 1. Analyse des conflits
        conflicts = self._analyze_conflicts(request, active_chantiers or [])

        # 2. Score de risque prédictif
        risk_score = self._compute_risk_score(request, conflicts, historical_data)

        # 3. Déterminer la sévérité
        severity = self._get_severity(risk_score)

        # 4. Produire la recommandation
        decision = self._make_decision(request, risk_score, severity, conflicts)

        # 5. Si reporter → trouver fenêtre optimale
        if decision.recommendation in (Recommendation.DEFER, Recommendation.CONDITION):
            decision.optimal_window = self._find_optimal_window(request, active_chantiers or [])

        # 6. Générer les conditions de mitigation
        if decision.recommendation == Recommendation.CONDITION:
            decision.mitigation_required = self._generate_mitigation(request, conflicts)

        self._decisions.append(decision)

        logger.info(
            f"  → {decision.recommendation.value} | Score: {risk_score:.0f}/100 | "
            f"Sévérité: {severity} | Conflits: {conflicts.conflicts_found}"
        )

        return decision

    # =========================================================================
    # ANALYSE DES CONFLITS
    # =========================================================================

    def _analyze_conflicts(
        self, request: PermitRequest, active_chantiers: List[Dict]
    ) -> ConflictAnalysis:
        """Analyse les conflits spatiaux et temporels."""
        analysis = ConflictAnalysis(permit_id=request.permit_id)

        if not request.latitude or not request.longitude:
            return analysis

        # Chantiers actifs à proximité (<300m)
        for ch in active_chantiers:
            lat = ch.get("latitude")
            lon = ch.get("longitude")
            if not lat or not lon:
                continue

            dist = self._haversine_m(request.latitude, request.longitude, lat, lon)
            if dist <= 300:
                analysis.nearby_active.append({
                    "id": ch.get("id", ""),
                    "rue": ch.get("rue", ""),
                    "distance_m": round(dist),
                    "type": ch.get("type_entrave", ""),
                })

        # Permis planifiés à proximité
        for permit in self._planned_permits:
            if permit.permit_id == request.permit_id:
                continue
            if not permit.latitude or not permit.longitude:
                continue

            dist = self._haversine_m(
                request.latitude, request.longitude,
                permit.latitude, permit.longitude,
            )
            if dist <= 300:
                # Vérifier chevauchement temporel
                overlap = self._temporal_overlap(request, permit)
                if overlap > 0:
                    analysis.nearby_planned.append({
                        "permit_id": permit.permit_id,
                        "rue": permit.rue,
                        "distance_m": round(dist),
                        "overlap_days": overlap,
                    })
                    analysis.temporal_overlap_days = max(analysis.temporal_overlap_days, overlap)

        analysis.conflicts_found = len(analysis.nearby_active) + len(analysis.nearby_planned)

        # Score de coactivité prédictive
        if analysis.conflicts_found > 0:
            base = min(100, analysis.conflicts_found * 25)
            proximity_bonus = sum(
                max(0, (300 - ch["distance_m"]) / 30)
                for ch in analysis.nearby_active
            )
            analysis.coactivity_score = min(100, base + proximity_bonus)

        # Estimation usagers vulnérables
        analysis.vulnerable_users_exposed = self._estimate_vulnerable_users(
            request, analysis.conflicts_found
        )

        return analysis

    def _temporal_overlap(self, req1: PermitRequest, req2: PermitRequest) -> int:
        """Calcule le chevauchement temporel en jours entre deux permis."""
        try:
            start1 = datetime.fromisoformat(req1.date_debut_demandee).date()
            end1 = datetime.fromisoformat(req1.date_fin_demandee).date()
            start2 = datetime.fromisoformat(req2.date_debut_demandee).date()
            end2 = datetime.fromisoformat(req2.date_fin_demandee).date()

            overlap_start = max(start1, start2)
            overlap_end = min(end1, end2)
            delta = (overlap_end - overlap_start).days

            return max(0, delta)
        except (ValueError, TypeError):
            return 0

    def _estimate_vulnerable_users(self, request: PermitRequest, conflicts: int) -> int:
        """Estime le nombre d'usagers vulnérables exposés."""
        base = 0
        if request.impact_pietons:
            base += 500
        if request.impact_cyclistes:
            base += 200
        if request.impact_transport:
            base += 300

        # Multiplier par le nombre de conflits (coactivité)
        multiplier = 1.0 + conflicts * 0.3

        # Facteur arrondissement (densité)
        density_factor = {
            "Ville-Marie": 2.0, "Le Plateau-Mont-Royal": 1.5,
            "Rosemont-La Petite-Patrie": 1.2,
        }.get(request.arrondissement, 1.0)

        return int(base * multiplier * density_factor)

    # =========================================================================
    # SCORING
    # =========================================================================

    def _compute_risk_score(
        self,
        request: PermitRequest,
        conflicts: ConflictAnalysis,
        historical: Optional[Dict] = None,
    ) -> float:
        """Score de risque prédictif (0-100)."""

        # 1. Coactivité (30%)
        coactivity = conflicts.coactivity_score

        # 2. Usagers vulnérables (25%)
        vuln_score = min(100, conflicts.vulnerable_users_exposed / 20)

        # 3. Risque historique CNESST+SAAQ (20%)
        hist_score = 0
        if historical:
            hist_score = min(100, (
                historical.get("cnesst_urban_risk", 0) * 8 +
                historical.get("saaq_accidents_zone", 0) * 2
            ))

        # 4. Potentiel de cascade (15%)
        type_risk = self.TYPE_RISK.get(request.type_travaux.lower(), 5)
        emprise_risk = self.EMPRISE_RISK.get(request.emprise_type.lower(), 5)
        cascade = min(100, (type_risk + emprise_risk) * 5 + request.duree_jours)

        # 5. Saturation territoire (10%)
        arr = request.arrondissement
        capacity = self.TERRITORY_CAPACITY.get(arr, 8)
        active_count = len([
            p for p in self._active_permits
            if p.arrondissement == arr
        ]) + len([
            c for c in conflicts.nearby_active
        ])
        saturation = min(100, (active_count / capacity) * 100)

        # Score composite pondéré
        score = (
            coactivity * self.WEIGHTS["coactivity"] +
            vuln_score * self.WEIGHTS["vulnerable_users"] +
            hist_score * self.WEIGHTS["historical_risk"] +
            cascade * self.WEIGHTS["cascade_potential"] +
            saturation * self.WEIGHTS["territory_saturation"]
        )

        conflicts.historical_risk = hist_score
        conflicts.cascade_risk = cascade

        return round(min(100, score), 1)

    # =========================================================================
    # DÉCISION
    # =========================================================================

    def _make_decision(
        self,
        request: PermitRequest,
        risk_score: float,
        severity: str,
        conflicts: ConflictAnalysis,
    ) -> PermitDecision:
        """Produit la recommandation basée sur le score."""

        if severity == "red":
            rec = Recommendation.DEFER
            reasoning = (
                f"Score risque {risk_score:.0f}/100 (critique). "
                f"{conflicts.conflicts_found} conflits détectés, "
                f"{conflicts.vulnerable_users_exposed} usagers vulnérables exposés. "
                f"Reporter à une fenêtre moins chargée."
            )
        elif severity == "orange":
            rec = Recommendation.CONDITION
            reasoning = (
                f"Score risque {risk_score:.0f}/100 (élevé). "
                f"Approuvable sous conditions de mitigation."
            )
        elif severity == "yellow":
            rec = Recommendation.APPROVE
            reasoning = (
                f"Score risque {risk_score:.0f}/100 (modéré). "
                f"Approuvé avec suivi renforcé."
            )
            if conflicts.conflicts_found > 0:
                rec = Recommendation.CONDITION
                reasoning += f" {conflicts.conflicts_found} conflits mineurs détectés."
        else:
            rec = Recommendation.APPROVE
            reasoning = f"Score risque {risk_score:.0f}/100 (faible). Approuvé."

        return PermitDecision(
            permit_id=request.permit_id,
            recommendation=rec,
            risk_score=risk_score,
            severity=severity,
            requires_hitl=True,  # Toujours HITL pour les permis
            conflict_analysis=conflicts,
            reasoning=reasoning,
            timestamp=datetime.now().isoformat(),
        )

    def _approve_urgent(self, request: PermitRequest) -> PermitDecision:
        """Approuve un permis d'urgence avec conditions obligatoires."""
        return PermitDecision(
            permit_id=request.permit_id,
            recommendation=Recommendation.APPROVE,
            risk_score=0,
            severity="yellow",
            requires_hitl=True,
            conditions=[
                "Travaux d'urgence — autorisation immédiate",
                "Signalisation temporaire obligatoire dans les 30 minutes",
                "Notification piétons/cyclistes via NudgeAgent",
                "Rapport post-intervention dans les 24h",
            ],
            mitigation_required=[
                "Signaleur obligatoire",
                "Éclairage de nuit si nocturne",
                "Protection piétons périmètre 50m",
            ],
            reasoning="Permis d'urgence — approbation automatique avec conditions.",
            timestamp=datetime.now().isoformat(),
        )

    # =========================================================================
    # FENÊTRE OPTIMALE
    # =========================================================================

    def _find_optimal_window(
        self, request: PermitRequest, active_chantiers: List[Dict]
    ) -> Dict[str, str]:
        """
        Calcule la fenêtre temporelle optimale pour le chantier.
        Cherche la période où la coactivité sera minimale.
        """
        try:
            requested_start = datetime.fromisoformat(request.date_debut_demandee).date()
        except (ValueError, TypeError):
            requested_start = date.today()

        duree = max(1, request.duree_jours)
        best_start = None
        best_score = float("inf")

        # Scanner les 90 prochains jours
        for offset in range(0, 90):
            candidate_start = requested_start + timedelta(days=offset)
            candidate_end = candidate_start + timedelta(days=duree)

            # Compter les conflits pendant cette fenêtre
            conflicts_count = 0
            for permit in self._planned_permits:
                if permit.permit_id == request.permit_id:
                    continue
                try:
                    p_start = datetime.fromisoformat(permit.date_debut_demandee).date()
                    p_end = datetime.fromisoformat(permit.date_fin_demandee).date()
                    if p_start <= candidate_end and p_end >= candidate_start:
                        if permit.latitude and request.latitude:
                            dist = self._haversine_m(
                                request.latitude, request.longitude,
                                permit.latitude, permit.longitude,
                            )
                            if dist <= 300:
                                conflicts_count += 1
                except (ValueError, TypeError):
                    continue

            # Score = conflits + pénalité de report
            report_penalty = offset * 0.5
            window_score = conflicts_count * 10 + report_penalty

            if window_score < best_score:
                best_score = window_score
                best_start = candidate_start

        if best_start:
            return {
                "start": best_start.isoformat(),
                "end": (best_start + timedelta(days=duree)).isoformat(),
                "report_jours": (best_start - requested_start).days,
                "conflicts_prevus": int(best_score / 10),
            }

        return {
            "start": requested_start.isoformat(),
            "end": (requested_start + timedelta(days=duree)).isoformat(),
            "report_jours": 0,
            "conflicts_prevus": 0,
        }

    # =========================================================================
    # CONDITIONS DE MITIGATION
    # =========================================================================

    def _generate_mitigation(
        self, request: PermitRequest, conflicts: ConflictAnalysis
    ) -> List[str]:
        """Génère les conditions de mitigation requises."""
        conditions = []

        # Signalisation
        if conflicts.conflicts_found >= 2:
            conditions.append("Plan de signalisation coordonné inter-chantiers obligatoire")
        if request.emprise_type == "fermeture_complete":
            conditions.append("Signalisation avancée 200m en amont")

        # Piétons
        if request.impact_pietons:
            conditions.append("Corridor piéton sécurisé largeur min 1.5m maintenu en tout temps")
            if conflicts.vulnerable_users_exposed > 500:
                conditions.append("Signaleur piéton aux intersections 7h-19h")

        # Cyclistes
        if request.impact_cyclistes:
            conditions.append("Déviation cyclable balisée avec signalisation au sol")

        # PMR
        if request.impact_pietons:
            conditions.append("Parcours accessible PMR maintenu (pente max 5%, largeur 1.5m)")

        # Coactivité
        if conflicts.conflicts_found >= 3:
            conditions.append("Réunion de coordination inter-entrepreneurs hebdomadaire obligatoire")
            conditions.append("Coordonnateur de chantier dédié (temps plein)")

        # Transport
        if request.impact_transport:
            conditions.append("Notification STM 72h avant début des travaux")
            conditions.append("Plan de relocalisation des arrêts validé par STM")

        # Horaires
        if conflicts.coactivity_score >= 60:
            conditions.append("Travaux bruyants limités 7h-19h (lundi-vendredi)")
            conditions.append("Livraisons matériaux avant 7h ou après 19h")

        # Durée
        if request.duree_jours > 30:
            conditions.append("Rapport d'avancement bi-mensuel au Bureau des permis")

        return conditions

    # =========================================================================
    # ÉTAT DU TERRITOIRE
    # =========================================================================

    def get_territory_snapshot(self) -> TerritorySnapshot:
        """Produit un snapshot de l'état du territoire."""
        snapshot = TerritorySnapshot(date=date.today().isoformat())

        snapshot.total_active = len(self._active_permits)
        snapshot.total_planned = len(self._planned_permits)

        # Capacité par arrondissement
        for arr, capacity in self.TERRITORY_CAPACITY.items():
            active = len([p for p in self._active_permits if p.arrondissement == arr])
            remaining = max(0, 1.0 - (active / capacity))
            snapshot.capacity_remaining[arr] = round(remaining * 100, 1)

            if remaining <= 0.1:
                snapshot.zones_saturees.append(arr)

        self._territory_cache = snapshot
        return snapshot

    def register_permit(self, permit: PermitRequest, status: str = "planned"):
        """Enregistre un permis dans le système."""
        if status == "active":
            self._active_permits.append(permit)
        else:
            self._planned_permits.append(permit)

    # =========================================================================
    # EXPORT SAFETYGRAPH
    # =========================================================================

    def to_safety_graph_nodes(self) -> List[Dict[str, Any]]:
        """Export SafetyGraph — décisions de permis."""
        nodes = []
        for d in self._decisions[-20:]:
            nodes.append({
                "type": "PermitDecision",
                "id": f"permit-{d.permit_id.lower()}",
                "properties": {
                    "recommendation": d.recommendation.value,
                    "risk_score": d.risk_score,
                    "severity": d.severity,
                    "requires_hitl": d.requires_hitl,
                    "conflicts_found": d.conflict_analysis.conflicts_found if d.conflict_analysis else 0,
                    "vulnerable_users": d.conflict_analysis.vulnerable_users_exposed if d.conflict_analysis else 0,
                    "conditions_count": len(d.conditions) + len(d.mitigation_required),
                    "timestamp": d.timestamp,
                },
            })
        return nodes

    def query(self, question: str) -> str:
        """Interface RAG."""
        q = question.lower()
        if "territoire" in q or "capacité" in q or "saturation" in q:
            snap = self.get_territory_snapshot()
            saturees = ", ".join(snap.zones_saturees) if snap.zones_saturees else "aucune"
            return (
                f"Territoire: {snap.total_active} chantiers actifs, "
                f"{snap.total_planned} planifiés. "
                f"Zones saturées: {saturees}."
            )

        return (
            f"PermitOptimizer: {len(self._decisions)} décisions rendues, "
            f"{len(self._active_permits)} permis actifs, "
            f"{len(self._planned_permits)} planifiés."
        )

    @staticmethod
    def _get_severity(score: float) -> str:
        if score >= 75:
            return "red"
        elif score >= 55:
            return "orange"
        elif score >= 30:
            return "yellow"
        return "green"

    @staticmethod
    def _haversine_m(lat1, lon1, lat2, lon2) -> float:
        R = 6371000
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
