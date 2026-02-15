"""
=============================================================================
NudgeAgent — Communication différenciée 9 profils usagers
=============================================================================
Agent qui génère des messages de prévention adaptés à chaque profil
d'usager urbain exposé aux risques de chantier.

9 profils usagers (par vulnerability_score décroissant):
  1. PMR (10)           — Personne à mobilité réduite
  2. Piéton (10)        — Piéton régulier
  3. Cycliste (9)       — Cycliste actif
  4. Transport comm (7) — Usager STM/REM
  5. Résident (6)       — Résident zone impactée
  6. Livraison (5)      — Livreur / coursier
  7. Automobiliste (4)  — Conducteur véhicule
  8. Urgence (3)        — Services d'urgence
  9. Coordonnateur (0)  — Agent de coordination AGIR

Canaux:
  - Push notification (piéton, cycliste, PMR)
  - SMS (automobiliste, livraison)
  - Affichage dynamique (tous)
  - Dashboard coordonnateur (coordonnateur)
  - Radio urgence (urgence)

Conformité: Charte AgenticX5 | Primauté de la vie | HITL ≥ orange
=============================================================================
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class Canal(Enum):
    PUSH = "push_notification"
    SMS = "sms"
    AFFICHAGE = "affichage_dynamique"
    DASHBOARD = "dashboard"
    RADIO = "radio_urgence"
    EMAIL = "email"


class Langue(Enum):
    FR = "fr"
    EN = "en"


@dataclass
class UserProfile:
    """Profil d'usager urbain"""
    id: str
    name_fr: str
    name_en: str
    vulnerability_score: int           # 0-10
    canaux: List[Canal] = field(default_factory=list)
    icon: str = ""
    needs_accessible: bool = False     # Nécessite format accessible (PMR)


# 9 profils définis
PROFILES = {
    "pmr": UserProfile("pmr", "Personne à mobilité réduite", "Person with reduced mobility", 10,
                        [Canal.PUSH, Canal.SMS, Canal.AFFICHAGE], "♿", needs_accessible=True),
    "pieton": UserProfile("pieton", "Piéton", "Pedestrian", 10,
                           [Canal.PUSH, Canal.AFFICHAGE], "🚶"),
    "cycliste": UserProfile("cycliste", "Cycliste", "Cyclist", 9,
                             [Canal.PUSH, Canal.AFFICHAGE], "🚲"),
    "transport_commun": UserProfile("transport_commun", "Usager transport en commun", "Transit rider", 7,
                                     [Canal.PUSH, Canal.AFFICHAGE], "🚌"),
    "resident": UserProfile("resident", "Résident", "Resident", 6,
                             [Canal.PUSH, Canal.EMAIL], "🏠"),
    "livraison": UserProfile("livraison", "Livreur / coursier", "Delivery / courier", 5,
                              [Canal.SMS, Canal.PUSH], "📦"),
    "automobiliste": UserProfile("automobiliste", "Automobiliste", "Driver", 4,
                                  [Canal.SMS, Canal.AFFICHAGE], "🚗"),
    "urgence": UserProfile("urgence", "Services d'urgence", "Emergency services", 3,
                            [Canal.RADIO, Canal.DASHBOARD], "🚑"),
    "coordonnateur": UserProfile("coordonnateur", "Coordonnateur AGIR", "AGIR coordinator", 0,
                                  [Canal.DASHBOARD, Canal.EMAIL], "📋"),
}


@dataclass
class Nudge:
    """Message de prévention personnalisé"""
    nudge_id: str
    profile_id: str
    canal: str
    langue: str
    titre: str
    message: str
    action_suggeree: str
    severity: str
    zone_id: str
    timestamp: str
    requires_hitl: bool = False
    itineraire_alt: Optional[str] = None
    accessible: bool = False


@dataclass
class NudgeCampaign:
    """Campagne de nudges pour un événement de risque"""
    campaign_id: str
    zone_id: str
    trigger: str                       # coactivity | cascade | weather | score_orange | score_red
    nudges: List[Nudge] = field(default_factory=list)
    profiles_cibled: List[str] = field(default_factory=list)
    total_nudges: int = 0
    timestamp: str = ""


class NudgeAgent:
    """
    Agent de communication différenciée pour 9 profils usagers.
    
    Génère des messages de prévention adaptés à chaque profil
    en fonction de la situation de risque détectée par les autres agents.
    
    Pipeline:
    1. Réception alerte (CoactivityAgent, CascadeAgent, Scoring)
    2. Détermination des profils ciblés selon la sévérité
    3. Génération des messages différenciés
    4. Dispatch par canal approprié
    5. Log pour traçabilité (Charte AgenticX5)
    """

    AGENT_ID = "nudge-agent"
    AGENT_VERSION = "1.0.0"

    # Profils ciblés par sévérité
    TARGETING = {
        "red": list(PROFILES.keys()),                                              # Tous les 9
        "orange": ["pmr", "pieton", "cycliste", "transport_commun", "coordonnateur"],  # 5
        "yellow": ["pieton", "cycliste", "coordonnateur"],                          # 3
        "green": ["coordonnateur"],                                                 # 1
    }

    def __init__(self, langue: str = "fr"):
        self.langue = Langue(langue)
        self._campaigns: List[NudgeCampaign] = []
        self._nudge_counter = 0
        logger.info(f"📢 NudgeAgent v{self.AGENT_VERSION} initialisé | Langue: {langue}")

    def generate_campaign(
        self,
        zone_id: str,
        severity: str,
        trigger: str,
        context: Dict[str, Any],
    ) -> NudgeCampaign:
        """
        Génère une campagne de nudges pour un événement de risque.
        
        Args:
            zone_id: Zone impactée
            severity: green/yellow/orange/red
            trigger: Type de déclencheur
            context: Données contextuelles (rues, score, météo, etc.)
        """
        campaign = NudgeCampaign(
            campaign_id=f"CAMP-{zone_id}-{datetime.now().strftime('%Y%m%d%H%M')}",
            zone_id=zone_id,
            trigger=trigger,
            timestamp=datetime.now().isoformat(),
        )

        # Déterminer les profils ciblés
        target_profiles = self.TARGETING.get(severity, ["coordonnateur"])
        campaign.profiles_cibled = target_profiles

        # Générer un nudge par profil × canal
        for profile_id in target_profiles:
            profile = PROFILES.get(profile_id)
            if not profile:
                continue

            for canal in profile.canaux:
                self._nudge_counter += 1
                nudge = self._create_nudge(
                    profile=profile,
                    canal=canal,
                    severity=severity,
                    zone_id=zone_id,
                    context=context,
                )
                campaign.nudges.append(nudge)

        campaign.total_nudges = len(campaign.nudges)
        self._campaigns.append(campaign)

        logger.info(
            f"📢 Campagne {campaign.campaign_id}: {campaign.total_nudges} nudges | "
            f"{len(target_profiles)} profils | Sévérité: {severity} | Trigger: {trigger}"
        )

        return campaign

    def _create_nudge(
        self,
        profile: UserProfile,
        canal: Canal,
        severity: str,
        zone_id: str,
        context: Dict,
    ) -> Nudge:
        """Crée un nudge personnalisé pour un profil spécifique."""
        # Générer le contenu selon le profil
        content = self._generate_content(profile, severity, context)

        return Nudge(
            nudge_id=f"NDG-{self._nudge_counter:06d}",
            profile_id=profile.id,
            canal=canal.value,
            langue=self.langue.value,
            titre=content["titre"],
            message=content["message"],
            action_suggeree=content["action"],
            severity=severity,
            zone_id=zone_id,
            timestamp=datetime.now().isoformat(),
            requires_hitl=severity in ("orange", "red"),
            itineraire_alt=content.get("itineraire"),
            accessible=profile.needs_accessible,
        )

    def _generate_content(
        self, profile: UserProfile, severity: str, context: Dict
    ) -> Dict[str, str]:
        """Génère le contenu textuel adapté au profil."""
        rues = context.get("rues", ["zone de travaux"])
        rue_text = ", ".join(rues[:2]) if isinstance(rues, list) else str(rues)
        score = context.get("score", 0)
        weather = context.get("weather", "")
        chantiers = context.get("chantiers", 0)

        if self.langue == Langue.FR:
            return self._content_fr(profile, severity, rue_text, score, weather, chantiers)
        return self._content_en(profile, severity, rue_text, score, weather, chantiers)

    def _content_fr(self, profile, severity, rues, score, weather, chantiers) -> Dict:
        """Contenu en français."""
        contents = {
            "pmr": {
                "red": {
                    "titre": "⚠️ ALERTE ACCESSIBILITÉ CRITIQUE",
                    "message": f"Zone {rues} — {chantiers} chantiers simultanés bloquent les parcours accessibles. Détours importants sans rampe d'accès.",
                    "action": "Évitez cette zone. Utilisez l'itinéraire alternatif accessible.",
                    "itineraire": f"Contourner par les rues accessibles au nord de {rues}",
                },
                "orange": {
                    "titre": "🟠 Accessibilité réduite",
                    "message": f"Travaux {rues} — trottoirs rétrécis ou temporairement inaccessibles. Soyez vigilant.",
                    "action": "Planifiez un itinéraire alternatif accessible.",
                    "itineraire": f"Rues parallèles à {rues}",
                },
            },
            "pieton": {
                "red": {
                    "titre": "🔴 DANGER PIÉTON — Zone à risque élevé",
                    "message": f"Zone {rues} — {chantiers} chantiers actifs créent des détours dangereux. {score:.0f}/100 risque. Traversées non sécurisées.",
                    "action": "Empruntez les passages balisés uniquement. Restez visible.",
                },
                "orange": {
                    "titre": "🟠 Attention piéton — Travaux actifs",
                    "message": f"Travaux {rues} — trottoir fermé côté sud. Suivez la signalisation de détour.",
                    "action": "Utilisez le passage piéton temporaire balisé.",
                },
                "yellow": {
                    "titre": "🟡 Info travaux",
                    "message": f"Travaux en cours {rues}. Circulation piétonne maintenue avec signalisation.",
                    "action": "Suivez la signalisation.",
                },
            },
            "cycliste": {
                "red": {
                    "titre": "🔴 DANGER CYCLISTE — Piste fermée",
                    "message": f"Piste cyclable fermée {rues}. Partage de voie avec véhicules lourds. Risque élevé ({score:.0f}/100).",
                    "action": "Descendez de vélo dans la zone de travaux. Utilisez l'itinéraire vélo alternatif.",
                    "itineraire": f"Piste cyclable de contournement via rues parallèles",
                },
                "orange": {
                    "titre": "🟠 Piste cyclable déviée",
                    "message": f"Déviation cyclable {rues}. Réduisez votre vitesse et restez visible.",
                    "action": "Suivez le balisage de déviation cyclable.",
                },
                "yellow": {
                    "titre": "🟡 Travaux — attention cycliste",
                    "message": f"Travaux {rues}. Piste cyclable maintenue avec rétrécissement.",
                    "action": "Réduisez votre vitesse.",
                },
            },
            "transport_commun": {
                "red": {
                    "titre": "🔴 Perturbation majeure transport",
                    "message": f"Arrêts déplacés {rues}. Détours autobus importants. Prévoir 15-20 min supplémentaires.",
                    "action": "Vérifiez les alertes STM avant votre départ.",
                },
                "orange": {
                    "titre": "🟠 Arrêt temporairement déplacé",
                    "message": f"L'arrêt {rues} est déplacé de 150m vers le nord en raison de travaux.",
                    "action": "Rendez-vous à l'arrêt temporaire.",
                },
            },
            "resident": {
                "red": {
                    "titre": "🔴 Travaux majeurs — votre quartier",
                    "message": f"Chantiers multiples {rues}. Bruit, poussière et détours importants pour les prochains jours.",
                    "action": "Consultez le calendrier des travaux sur montreal.ca.",
                },
                "orange": {
                    "titre": "🟠 Travaux dans votre secteur",
                    "message": f"Travaux {rues}. Accès modifié pour quelques jours.",
                    "action": "Planifiez vos déplacements en conséquence.",
                },
            },
            "livraison": {
                "red": {
                    "titre": "🔴 ZONE FERMÉE — Livraisons",
                    "message": f"Accès livraison impossible {rues}. Utilisez le point de dépôt alternatif.",
                    "action": "Point de dépôt temporaire signalé sur place.",
                },
                "orange": {
                    "titre": "🟠 Accès livraison restreint",
                    "message": f"Accès restreint {rues}. Fenêtre de livraison: 6h-8h uniquement.",
                    "action": "Planifiez vos livraisons en dehors des heures de pointe.",
                },
            },
            "automobiliste": {
                "red": {
                    "titre": "🔴 FERMETURE DE RUE",
                    "message": f"Fermeture complète {rues}. Détour obligatoire. Ralentissez: piétons déviés sur la chaussée.",
                    "action": "Suivez le détour balisé. Attention aux piétons.",
                },
                "orange": {
                    "titre": "🟠 Circulation ralentie",
                    "message": f"Travaux {rues} — voie réduite. Présence de piétons et cyclistes déviés. Vigilance.",
                    "action": "Réduisez votre vitesse à 30 km/h dans la zone.",
                },
            },
            "urgence": {
                "red": {
                    "titre": "🔴 ACCÈS URGENCE MODIFIÉ",
                    "message": f"Route habituelle {rues} fermée. Accès alternatif validé par SPVM.",
                    "action": "Utiliser l'itinéraire alternatif d'urgence.",
                    "itineraire": f"Accès nord via boulevard parallèle",
                },
                "orange": {
                    "titre": "🟠 Restriction accès urgence",
                    "message": f"Largeur réduite {rues}. Véhicules lourds: vérifier la clearance.",
                    "action": "Confirmer la clearance avant passage.",
                },
            },
            "coordonnateur": {
                "red": {
                    "titre": "🔴 INTERVENTION REQUISE — Coactivité critique",
                    "message": f"Zone {rues}: {chantiers} chantiers simultanés, score {score:.0f}/100. "
                               f"HITL obligatoire (Charte AgenticX5). Valider les mesures de mitigation.",
                    "action": "Déclencher le protocole de coordination inter-chantiers. Valider le plan de signalisation.",
                },
                "orange": {
                    "titre": "🟠 Validation requise",
                    "message": f"Zone {rues}: score risque {score:.0f}/100. Coactivité détectée. Révision recommandée.",
                    "action": "Vérifier la signalisation et les corridors piétons.",
                },
                "yellow": {
                    "titre": "🟡 Surveillance — zone active",
                    "message": f"Zone {rues}: {chantiers} chantiers actifs. Situation sous contrôle.",
                    "action": "Surveiller l'évolution.",
                },
                "green": {
                    "titre": "✅ Zone normale",
                    "message": f"Zone {rues}: situation normale. Score {score:.0f}/100.",
                    "action": "Aucune action requise.",
                },
            },
        }

        profile_content = contents.get(profile.id, {})
        specific = profile_content.get(severity, profile_content.get("yellow", profile_content.get("orange", {
            "titre": f"ℹ️ Info travaux — {rues}",
            "message": f"Travaux en cours {rues}.",
            "action": "Restez vigilant.",
        })))

        return specific

    def _content_en(self, profile, severity, rues, score, weather, chantiers) -> Dict:
        """Contenu en anglais (simplifié)."""
        severity_labels = {"red": "CRITICAL", "orange": "WARNING", "yellow": "NOTICE", "green": "INFO"}
        return {
            "titre": f"{severity_labels.get(severity, 'INFO')} — Construction zone {rues}",
            "message": f"Active construction {rues}. {chantiers} work zones. Risk score: {score:.0f}/100. Stay alert.",
            "action": "Follow posted detour signs and stay on marked paths.",
        }

    # =========================================================================
    # DISPATCH
    # =========================================================================

    def dispatch(self, campaign: NudgeCampaign) -> Dict[str, int]:
        """
        Dispatch les nudges par canal.
        En production: intégration avec les APIs de notification.
        Pour l'instant: log pour traçabilité.
        """
        stats = {}
        for nudge in campaign.nudges:
            canal = nudge.canal
            stats[canal] = stats.get(canal, 0) + 1

            logger.info(
                f"  📤 [{nudge.nudge_id}] {nudge.canal} → {nudge.profile_id} | "
                f"{nudge.severity} | {nudge.titre[:50]}"
            )

        return stats

    # =========================================================================
    # EXPORT
    # =========================================================================

    def to_safety_graph_nodes(self) -> List[Dict[str, Any]]:
        """Export SafetyGraph — campagnes + nudges."""
        nodes = []
        for campaign in self._campaigns[-5:]:  # 5 dernières campagnes
            nodes.append({
                "type": "NudgeCampaign",
                "id": f"nudge-{campaign.campaign_id.lower()}",
                "properties": {
                    "zone_id": campaign.zone_id,
                    "trigger": campaign.trigger,
                    "total_nudges": campaign.total_nudges,
                    "profiles_cibled": "|".join(campaign.profiles_cibled),
                    "timestamp": campaign.timestamp,
                },
            })
        return nodes

    def get_stats(self) -> Dict[str, Any]:
        """Statistiques des campagnes."""
        return {
            "total_campaigns": len(self._campaigns),
            "total_nudges": sum(c.total_nudges for c in self._campaigns),
            "nudges_by_profile": self._stats_by_profile(),
            "nudges_by_canal": self._stats_by_canal(),
        }

    def _stats_by_profile(self) -> Dict[str, int]:
        counts = {}
        for c in self._campaigns:
            for n in c.nudges:
                counts[n.profile_id] = counts.get(n.profile_id, 0) + 1
        return counts

    def _stats_by_canal(self) -> Dict[str, int]:
        counts = {}
        for c in self._campaigns:
            for n in c.nudges:
                counts[n.canal] = counts.get(n.canal, 0) + 1
        return counts

    def query(self, question: str) -> str:
        """Interface RAG."""
        stats = self.get_stats()
        return (
            f"NudgeAgent: {stats['total_campaigns']} campagnes, "
            f"{stats['total_nudges']} nudges envoyés, "
            f"9 profils usagers, 5 canaux de communication."
        )
