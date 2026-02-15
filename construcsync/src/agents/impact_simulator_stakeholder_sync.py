"""
=============================================================================
ImpactSimulatorAgent — Simulation d'impact territorial AVANT autorisation
=============================================================================
Agent qui simule l'impact d'un nouveau chantier sur le territoire
AVANT que le permis ne soit émis, en utilisant les modèles de cascade
et de coactivité d'UrbanIA.

Simulation "What-If":
  "Que se passe-t-il si on autorise ce chantier maintenant ?"
  → Score UrbanIA simulé
  → Effets cascade prédits
  → Usagers impactés estimés
  → Comparaison avec/sans le chantier

Conformité: Charte AgenticX5 | Primauté de la vie
=============================================================================
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class SimulationScenario:
    """Scénario de simulation"""
    scenario_id: str
    permit_id: str
    name: str                           # "avec_chantier" | "sans_chantier" | "reporté_30j"
    score_urbania: float = 0.0
    cascade_score: float = 0.0
    coactivity_multiplier: float = 1.0
    users_impacted: int = 0
    pietons_redirected: int = 0
    cyclistes_redirected: int = 0
    corridors_impacted: int = 0
    estimated_incidents: float = 0.0    # Incidents prédits (basé sur historique)


@dataclass
class SimulationReport:
    """Rapport de simulation comparatif"""
    simulation_id: str
    permit_id: str
    zone_id: str
    scenarios: List[SimulationScenario] = field(default_factory=list)
    recommendation: str = ""
    delta_risk: float = 0.0             # Différence de risque avec/sans
    delta_users: int = 0                # Usagers supplémentaires impactés
    optimal_scenario: str = ""
    timestamp: str = ""


class ImpactSimulatorAgent:
    """
    Agent de simulation d'impact pré-autorisation.
    
    Exécute des simulations "What-If" pour prédire l'impact
    d'un nouveau chantier avant l'émission du permis.
    """

    AGENT_ID = "impact-simulator"
    AGENT_VERSION = "1.0.0"

    # Taux d'incident historique par 1000 usagers exposés (CNESST+SAAQ calibré)
    INCIDENT_RATE = {
        "pieton": 0.036,        # 3.6 incidents / 1000 piétons exposés
        "cycliste": 0.048,      # 4.8 / 1000 cyclistes
        "automobiliste": 0.012, # 1.2 / 1000 autos
    }

    def __init__(self):
        self._simulations: List[SimulationReport] = []
        logger.info(f"🔮 ImpactSimulatorAgent v{self.AGENT_VERSION} initialisé")

    def simulate(
        self,
        permit_id: str,
        zone_id: str,
        current_score: float,
        current_chantiers: int,
        flux_pietons: int,
        flux_cyclistes: int,
        permit_impact: Dict,
    ) -> SimulationReport:
        """
        Simule l'impact d'un nouveau chantier.
        
        Args:
            permit_id: ID du permis à simuler
            zone_id: Zone urbaine
            current_score: Score UrbanIA actuel
            current_chantiers: Nombre de chantiers actifs
            flux_pietons: Flux piétons actuel
            flux_cyclistes: Flux cyclistes actuel
            permit_impact: Données du permis {type, emprise, duree, impact_pietons, etc.}
        """
        sim_id = f"SIM-{permit_id}-{datetime.now().strftime('%H%M%S')}"

        # Scénario 1: SANS le nouveau chantier (baseline)
        baseline = SimulationScenario(
            scenario_id=f"{sim_id}-baseline",
            permit_id=permit_id,
            name="sans_chantier",
            score_urbania=current_score,
            coactivity_multiplier=self._current_coactivity(current_chantiers),
            users_impacted=0,
            pietons_redirected=0,
            cyclistes_redirected=0,
        )

        # Scénario 2: AVEC le nouveau chantier
        with_chantier = self._simulate_with_chantier(
            permit_id, current_score, current_chantiers,
            flux_pietons, flux_cyclistes, permit_impact,
        )

        # Scénario 3: REPORTÉ de 30 jours
        deferred = self._simulate_deferred(
            permit_id, current_score, current_chantiers,
            flux_pietons, flux_cyclistes, permit_impact,
        )

        report = SimulationReport(
            simulation_id=sim_id,
            permit_id=permit_id,
            zone_id=zone_id,
            scenarios=[baseline, with_chantier, deferred],
            delta_risk=round(with_chantier.score_urbania - baseline.score_urbania, 1),
            delta_users=with_chantier.users_impacted,
            timestamp=datetime.now().isoformat(),
        )

        # Déterminer le scénario optimal
        scores = {
            "avec_chantier": with_chantier.score_urbania + with_chantier.estimated_incidents * 50,
            "reporté_30j": deferred.score_urbania + deferred.estimated_incidents * 50,
        }
        report.optimal_scenario = min(scores, key=scores.get)

        # Recommandation
        if report.delta_risk > 25:
            report.recommendation = (
                f"Impact significatif (+{report.delta_risk:.0f} pts). "
                f"Reporter de 30j réduirait le risque de "
                f"{with_chantier.score_urbania - deferred.score_urbania:.0f} pts."
            )
        elif report.delta_risk > 10:
            report.recommendation = (
                f"Impact modéré (+{report.delta_risk:.0f} pts). "
                f"Approuvable avec conditions de mitigation."
            )
        else:
            report.recommendation = f"Impact faible (+{report.delta_risk:.0f} pts). Approuvable."

        self._simulations.append(report)

        logger.info(
            f"🔮 Simulation {sim_id}: Δ risque = +{report.delta_risk:.0f} pts | "
            f"Δ usagers = +{report.delta_users} | Optimal: {report.optimal_scenario}"
        )

        return report

    def _simulate_with_chantier(
        self, permit_id, current_score, current_chantiers,
        flux_pietons, flux_cyclistes, permit_impact,
    ) -> SimulationScenario:
        """Simule le scénario AVEC le nouveau chantier."""
        new_chantiers = current_chantiers + 1
        coact = self._current_coactivity(new_chantiers)

        # Impact sur les flux
        emprise = permit_impact.get("emprise_type", "occupation_partielle")
        redirect_ratio = {"fermeture_complete": 0.9, "trottoir": 0.6, "occupation_partielle": 0.3}.get(emprise, 0.3)

        pietons_redir = int(flux_pietons * redirect_ratio) if permit_impact.get("impact_pietons") else 0
        cyclistes_redir = int(flux_cyclistes * redirect_ratio) if permit_impact.get("impact_cyclistes") else 0

        # Score simulé
        type_risk = {"demolition": 15, "excavation": 12, "aqueduc": 10, "voirie": 8, "batiment": 5}.get(
            permit_impact.get("type_travaux", "").lower(), 6
        )

        simulated_score = min(100, current_score + type_risk * coact + (pietons_redir + cyclistes_redir) / 100)

        # Incidents prédits
        incidents = (
            pietons_redir * self.INCIDENT_RATE["pieton"] / 1000 +
            cyclistes_redir * self.INCIDENT_RATE["cycliste"] / 1000
        ) * permit_impact.get("duree_jours", 30)

        return SimulationScenario(
            scenario_id=f"SIM-{permit_id}-with",
            permit_id=permit_id,
            name="avec_chantier",
            score_urbania=round(simulated_score, 1),
            cascade_score=round(type_risk * coact * 5, 1),
            coactivity_multiplier=coact,
            users_impacted=pietons_redir + cyclistes_redir,
            pietons_redirected=pietons_redir,
            cyclistes_redirected=cyclistes_redir,
            estimated_incidents=round(incidents, 2),
        )

    def _simulate_deferred(
        self, permit_id, current_score, current_chantiers,
        flux_pietons, flux_cyclistes, permit_impact,
    ) -> SimulationScenario:
        """Simule le scénario REPORTÉ de 30 jours."""
        # Hypothèse: 30j plus tard, 30% des chantiers actuels seront terminés
        future_chantiers = max(0, int(current_chantiers * 0.7))
        coact = self._current_coactivity(future_chantiers + 1)

        emprise = permit_impact.get("emprise_type", "occupation_partielle")
        redirect_ratio = {"fermeture_complete": 0.9, "trottoir": 0.6, "occupation_partielle": 0.3}.get(emprise, 0.3)

        pietons_redir = int(flux_pietons * redirect_ratio * 0.8) if permit_impact.get("impact_pietons") else 0
        cyclistes_redir = int(flux_cyclistes * redirect_ratio * 0.8) if permit_impact.get("impact_cyclistes") else 0

        type_risk = {"demolition": 15, "excavation": 12, "aqueduc": 10, "voirie": 8, "batiment": 5}.get(
            permit_impact.get("type_travaux", "").lower(), 6
        )

        simulated_score = min(100, current_score * 0.85 + type_risk * coact + (pietons_redir + cyclistes_redir) / 120)

        incidents = (
            pietons_redir * self.INCIDENT_RATE["pieton"] / 1000 +
            cyclistes_redir * self.INCIDENT_RATE["cycliste"] / 1000
        ) * permit_impact.get("duree_jours", 30)

        return SimulationScenario(
            scenario_id=f"SIM-{permit_id}-deferred",
            permit_id=permit_id,
            name="reporté_30j",
            score_urbania=round(simulated_score, 1),
            cascade_score=round(type_risk * coact * 4, 1),
            coactivity_multiplier=coact,
            users_impacted=pietons_redir + cyclistes_redir,
            pietons_redirected=pietons_redir,
            cyclistes_redirected=cyclistes_redir,
            estimated_incidents=round(incidents, 2),
        )

    @staticmethod
    def _current_coactivity(n_chantiers: int) -> float:
        if n_chantiers >= 5:
            return 2.0
        elif n_chantiers >= 4:
            return 1.8
        elif n_chantiers >= 3:
            return 1.5
        elif n_chantiers >= 2:
            return 1.3
        return 1.0

    def to_safety_graph_nodes(self) -> List[Dict[str, Any]]:
        nodes = []
        for sim in self._simulations[-10:]:
            nodes.append({
                "type": "ImpactSimulation",
                "id": f"sim-{sim.simulation_id.lower()}",
                "properties": {
                    "permit_id": sim.permit_id,
                    "delta_risk": sim.delta_risk,
                    "delta_users": sim.delta_users,
                    "optimal_scenario": sim.optimal_scenario,
                    "recommendation": sim.recommendation[:100],
                },
            })
        return nodes

    def query(self, question: str) -> str:
        if not self._simulations:
            return "Aucune simulation disponible."
        last = self._simulations[-1]
        return (
            f"Dernière simulation {last.simulation_id}: "
            f"Δ risque = +{last.delta_risk:.0f} pts, "
            f"Δ usagers = +{last.delta_users}, "
            f"scénario optimal: {last.optimal_scenario}."
        )


"""
=============================================================================
StakeholderSyncAgent — Coordination des parties prenantes
=============================================================================
Agent qui orchestre la communication et la coordination entre
les parties prenantes d'un chantier municipal:
  - Ville (Bureau des permis, arrondissement)
  - Entrepreneur / donneur d'ouvrage
  - Services d'urgence (SPVM, SIM, Urgences-santé)
  - STM (transport en commun)
  - Résidents et commerçants
  - Coordonnateur AGIR

Conformité: Charte AgenticX5 | HITL obligatoire
=============================================================================
"""


@dataclass
class Stakeholder:
    """Partie prenante"""
    id: str
    name: str
    role: str                           # ville | entrepreneur | urgence | stm | resident | agir
    contact: str = ""
    notification_canal: str = "email"   # email | sms | dashboard | radio
    priority: int = 5


@dataclass
class CoordinationTask:
    """Tâche de coordination"""
    task_id: str
    permit_id: str
    stakeholder_id: str
    action: str
    deadline: str
    status: str = "pending"             # pending | sent | acknowledged | completed
    timestamp: str = ""


@dataclass
class CoordinationPlan:
    """Plan de coordination pour un chantier"""
    plan_id: str
    permit_id: str
    stakeholders: List[Stakeholder] = field(default_factory=list)
    tasks: List[CoordinationTask] = field(default_factory=list)
    timeline: List[Dict] = field(default_factory=list)
    status: str = "draft"               # draft | active | completed
    timestamp: str = ""


class StakeholderSyncAgent:
    """
    Agent de coordination des parties prenantes.
    
    Génère automatiquement le plan de coordination pour chaque
    chantier autorisé, incluant les notifications, les réunions
    et les validations requises.
    """

    AGENT_ID = "stakeholder-sync"
    AGENT_VERSION = "1.0.0"

    # Templates de parties prenantes par type de chantier
    STAKEHOLDER_TEMPLATES = {
        "voirie": [
            Stakeholder("SH-VILLE", "Bureau des permis", "ville", priority=10),
            Stakeholder("SH-ARR", "Arrondissement", "ville", priority=8),
            Stakeholder("SH-SPVM", "SPVM", "urgence", priority=9, notification_canal="radio"),
            Stakeholder("SH-SIM", "SIM (pompiers)", "urgence", priority=9, notification_canal="radio"),
            Stakeholder("SH-STM", "STM", "stm", priority=8),
            Stakeholder("SH-AGIR", "Coordonnateur AGIR", "agir", priority=10, notification_canal="dashboard"),
        ],
        "aqueduc": [
            Stakeholder("SH-VILLE", "Bureau des permis", "ville", priority=10),
            Stakeholder("SH-EAU", "Service de l'eau", "ville", priority=10),
            Stakeholder("SH-SPVM", "SPVM", "urgence", priority=8, notification_canal="radio"),
            Stakeholder("SH-AGIR", "Coordonnateur AGIR", "agir", priority=10, notification_canal="dashboard"),
            Stakeholder("SH-RES", "Résidents zone", "resident", priority=6, notification_canal="sms"),
        ],
        "default": [
            Stakeholder("SH-VILLE", "Bureau des permis", "ville", priority=10),
            Stakeholder("SH-ARR", "Arrondissement", "ville", priority=7),
            Stakeholder("SH-AGIR", "Coordonnateur AGIR", "agir", priority=10, notification_canal="dashboard"),
        ],
    }

    def __init__(self):
        self._plans: List[CoordinationPlan] = []
        self._task_counter = 0
        logger.info(f"🤝 StakeholderSyncAgent v{self.AGENT_VERSION} initialisé")

    def generate_plan(
        self,
        permit_id: str,
        type_travaux: str,
        severity: str,
        conditions: List[str],
        date_debut: str,
    ) -> CoordinationPlan:
        """Génère le plan de coordination pour un chantier autorisé."""
        plan = CoordinationPlan(
            plan_id=f"PLAN-{permit_id}",
            permit_id=permit_id,
            timestamp=datetime.now().isoformat(),
        )

        # Sélectionner les parties prenantes
        template_key = type_travaux.lower() if type_travaux.lower() in self.STAKEHOLDER_TEMPLATES else "default"
        plan.stakeholders = list(self.STAKEHOLDER_TEMPLATES[template_key])

        # Si sévérité élevée → ajouter urgences + résidents
        if severity in ("orange", "red"):
            existing_ids = {s.id for s in plan.stakeholders}
            extras = [
                Stakeholder("SH-SPVM", "SPVM", "urgence", priority=9, notification_canal="radio"),
                Stakeholder("SH-SIM", "SIM", "urgence", priority=9, notification_canal="radio"),
                Stakeholder("SH-USANTE", "Urgences-santé", "urgence", priority=8, notification_canal="radio"),
                Stakeholder("SH-RES", "Résidents zone", "resident", priority=6, notification_canal="sms"),
                Stakeholder("SH-COM", "Commerçants zone", "resident", priority=5, notification_canal="email"),
            ]
            for s in extras:
                if s.id not in existing_ids:
                    plan.stakeholders.append(s)
                    existing_ids.add(s.id)

        # Générer les tâches de coordination
        plan.tasks = self._generate_tasks(plan, conditions, date_debut, severity)

        # Timeline
        plan.timeline = self._generate_timeline(date_debut, plan.tasks)

        plan.status = "active"
        self._plans.append(plan)

        logger.info(
            f"🤝 Plan {plan.plan_id}: {len(plan.stakeholders)} parties prenantes, "
            f"{len(plan.tasks)} tâches, sévérité {severity}"
        )

        return plan

    def _generate_tasks(
        self, plan: CoordinationPlan, conditions: List[str],
        date_debut: str, severity: str,
    ) -> List[CoordinationTask]:
        """Génère les tâches de coordination."""
        tasks = []

        try:
            start = datetime.fromisoformat(date_debut)
        except (ValueError, TypeError):
            start = datetime.now()

        # J-7: Notifications pré-chantier
        for sh in plan.stakeholders:
            self._task_counter += 1
            tasks.append(CoordinationTask(
                task_id=f"T-{self._task_counter:04d}",
                permit_id=plan.permit_id,
                stakeholder_id=sh.id,
                action=f"Notification pré-chantier à {sh.name} via {sh.notification_canal}",
                deadline=(start - timedelta(days=7)).isoformat(),
            ))

        # J-3: Validation signalisation
        self._task_counter += 1
        tasks.append(CoordinationTask(
            task_id=f"T-{self._task_counter:04d}",
            permit_id=plan.permit_id,
            stakeholder_id="SH-AGIR",
            action="Validation plan de signalisation sur le terrain",
            deadline=(start - timedelta(days=3)).isoformat(),
        ))

        # J-1: Confirmation finale
        self._task_counter += 1
        tasks.append(CoordinationTask(
            task_id=f"T-{self._task_counter:04d}",
            permit_id=plan.permit_id,
            stakeholder_id="SH-VILLE",
            action="Confirmation finale début des travaux",
            deadline=(start - timedelta(days=1)).isoformat(),
        ))

        # Conditions spécifiques
        for i, condition in enumerate(conditions):
            self._task_counter += 1
            tasks.append(CoordinationTask(
                task_id=f"T-{self._task_counter:04d}",
                permit_id=plan.permit_id,
                stakeholder_id="SH-AGIR",
                action=f"Vérifier condition: {condition}",
                deadline=start.isoformat(),
            ))

        # Si haute sévérité: réunion de coordination
        if severity in ("orange", "red"):
            self._task_counter += 1
            tasks.append(CoordinationTask(
                task_id=f"T-{self._task_counter:04d}",
                permit_id=plan.permit_id,
                stakeholder_id="SH-AGIR",
                action="Réunion de coordination inter-chantiers (tous les intervenants)",
                deadline=(start - timedelta(days=5)).isoformat(),
            ))

        return tasks

    def _generate_timeline(self, date_debut: str, tasks: List[CoordinationTask]) -> List[Dict]:
        """Génère la timeline de coordination."""
        timeline = []
        for task in sorted(tasks, key=lambda t: t.deadline):
            timeline.append({
                "date": task.deadline[:10],
                "task": task.action[:80],
                "stakeholder": task.stakeholder_id,
                "status": task.status,
            })
        return timeline

    def to_safety_graph_nodes(self) -> List[Dict[str, Any]]:
        nodes = []
        for plan in self._plans[-10:]:
            nodes.append({
                "type": "CoordinationPlan",
                "id": f"coord-{plan.plan_id.lower()}",
                "properties": {
                    "permit_id": plan.permit_id,
                    "stakeholders_count": len(plan.stakeholders),
                    "tasks_count": len(plan.tasks),
                    "status": plan.status,
                },
            })
        return nodes

    def query(self, question: str) -> str:
        return (
            f"StakeholderSync: {len(self._plans)} plans de coordination, "
            f"templates pour voirie/aqueduc/défaut, "
            f"notifications multi-canal (email, SMS, radio, dashboard)."
        )
