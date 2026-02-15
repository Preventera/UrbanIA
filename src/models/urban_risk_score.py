"""
=============================================================================
AX5 UrbanIA — Moteur de scoring risque urbain composite
=============================================================================
Combine les 3 couches de données pour produire un score de risque urbain
calibré sur données probantes CNESST (54K lésions) + SAAQ (8K zone travaux)
+ 7 sources temps réel MTL.

Score = f(profil_chantier_CNESST, zone_travaux_SAAQ, flux_urbains_MTL)

Conformité: Charte AgenticX5 | Primauté de la vie | HITL pour orange/rouge
=============================================================================
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from src.utils.constants import (
    ALERT_THRESHOLDS,
    USER_PROFILES,
    GENRE_URBAN_RISK_SCORE,
    SAAQ_GRAVITE_POIDS,
)

logger = logging.getLogger(__name__)


@dataclass
class UrbanRiskScore:
    """Score de risque urbain composite pour une zone"""
    zone_id: str
    score: float                          # 0-100
    severity: str                         # green/yellow/orange/red
    requires_hitl: bool                   # True si orange ou rouge
    
    # Composantes du score
    couche1_cnesst: float = 0.0           # Score calibré lésions professionnelles
    couche2_saaq: float = 0.0             # Score calibré accidents zone travaux
    couche3_mtl: float = 0.0              # Score flux urbains temps réel
    
    # Facteurs de modulation
    coactivity_factor: float = 1.0        # ×1.5 si chantiers adjacents
    weather_factor: float = 1.0           # ×1.3 si pluie/verglas
    time_factor: float = 1.0              # ×1.2 si heure de pointe
    
    # Métadonnées
    confidence: str = "medium"            # low/medium/high
    sources_used: list = None
    target_profiles: list = None


class UrbanRiskScoringEngine:
    """
    Moteur de scoring composite 3 couches.
    
    Pondérations:
    - Couche 1 (CNESST) : 35% — fondation probante, ce qui blesse SUR le chantier
    - Couche 2 (SAAQ)   : 25% — ce qui blesse EN TRANSIT zone travaux
    - Couche 3 (MTL)    : 40% — exposition temps réel AUTOUR du chantier
    
    Les pondérations reflètent l'importance de l'exposition actuelle (Couche 3)
    tout en ancrant la prédiction dans la sinistralité réelle (Couches 1+2 = 60%).
    """

    WEIGHT_COUCHE1_CNESST = 0.35
    WEIGHT_COUCHE2_SAAQ = 0.25
    WEIGHT_COUCHE3_MTL = 0.40

    def __init__(self):
        logger.info("🧠 UrbanRiskScoringEngine initialisé")

    def compute_score(
        self,
        zone_id: str,
        cnesst_data: Optional[Dict[str, Any]] = None,
        saaq_data: Optional[Dict[str, Any]] = None,
        mtl_data: Optional[Dict[str, Any]] = None,
    ) -> UrbanRiskScore:
        """
        Calcule le score de risque urbain composite pour une zone.
        
        Args:
            zone_id: Identifiant de la zone urbaine
            cnesst_data: Profil risque chantier (CNESSTLesionsRAGAgent)
            saaq_data: Profil zone travaux (SAAQWorkZoneAgent)
            mtl_data: Flux urbains temps réel (7 sources MTL)
        """
        # Couche 1 — Score CNESST (0-100)
        couche1 = self._score_couche1(cnesst_data) if cnesst_data else 50.0

        # Couche 2 — Score SAAQ (0-100)
        couche2 = self._score_couche2(saaq_data) if saaq_data else 50.0

        # Couche 3 — Score MTL (0-100)
        couche3 = self._score_couche3(mtl_data) if mtl_data else 50.0

        # Score brut pondéré
        raw_score = (
            couche1 * self.WEIGHT_COUCHE1_CNESST
            + couche2 * self.WEIGHT_COUCHE2_SAAQ
            + couche3 * self.WEIGHT_COUCHE3_MTL
        )

        # Facteurs de modulation
        coactivity = mtl_data.get("coactivity_factor", 1.0) if mtl_data else 1.0
        weather = mtl_data.get("weather_factor", 1.0) if mtl_data else 1.0
        time_mod = mtl_data.get("time_factor", 1.0) if mtl_data else 1.0

        final_score = min(100.0, raw_score * coactivity * weather * time_mod)

        # Déterminer sévérité
        severity = "green"
        for level, thresholds in ALERT_THRESHOLDS.items():
            if thresholds["min"] <= final_score < thresholds["max"]:
                severity = level
                break
        if final_score >= 85:
            severity = "red"

        # HITL obligatoire si orange ou rouge (Charte AgenticX5)
        requires_hitl = severity in ("orange", "red")

        # Sources utilisées
        sources = []
        if cnesst_data:
            sources.append("CNESST")
        if saaq_data:
            sources.append("SAAQ")
        if mtl_data:
            sources.extend(mtl_data.get("sources_active", []))

        # Confidence
        n_sources = len(sources)
        confidence = "high" if n_sources >= 5 else "medium" if n_sources >= 3 else "low"

        # Profils ciblés
        target_profiles = self._determine_target_profiles(severity, saaq_data)

        score = UrbanRiskScore(
            zone_id=zone_id,
            score=round(final_score, 1),
            severity=severity,
            requires_hitl=requires_hitl,
            couche1_cnesst=round(couche1, 1),
            couche2_saaq=round(couche2, 1),
            couche3_mtl=round(couche3, 1),
            coactivity_factor=coactivity,
            weather_factor=weather,
            time_factor=time_mod,
            confidence=confidence,
            sources_used=sources,
            target_profiles=target_profiles,
        )

        if requires_hitl:
            logger.warning(
                f"⚠️ HITL REQUIS | Zone {zone_id} | Score {final_score:.1f} | "
                f"Sévérité {severity.upper()} | Profils: {target_profiles}"
            )
        else:
            logger.info(
                f"✅ Zone {zone_id} | Score {final_score:.1f} | {severity} | "
                f"Confiance: {confidence}"
            )

        return score

    def _score_couche1(self, cnesst_data: Dict[str, Any]) -> float:
        """Score Couche 1 — calibré sur lésions CNESST Construction"""
        urban_risk = cnesst_data.get("urban_risk_score", 5.0)
        taux_tms = cnesst_data.get("taux_tms_pct", 26.0)
        trend = cnesst_data.get("trend_yoy_pct", 0.0)

        base = urban_risk * 10  # 0-100
        tms_bonus = min(15, taux_tms * 0.5)  # TMS augmente le risque
        trend_bonus = min(10, max(0, trend * 0.2))  # Tendance hausse

        return min(100, base + tms_bonus + trend_bonus)

    def _score_couche2(self, saaq_data: Dict[str, Any]) -> float:
        """Score Couche 2 — calibré sur accidents SAAQ zone travaux"""
        risk_score = saaq_data.get("risk_score", 1.5)
        pietons = saaq_data.get("accidents_pietons", 0)
        cyclistes = saaq_data.get("accidents_cyclistes", 0)
        mortels = saaq_data.get("accidents_mortels_graves", 0)

        base = risk_score * 30  # Score gravité pondéré
        vulnerable = min(30, (pietons + cyclistes) * 0.15)
        severity_bonus = min(20, mortels * 2)

        return min(100, base + vulnerable + severity_bonus)

    def _score_couche3(self, mtl_data: Dict[str, Any]) -> float:
        """Score Couche 3 — flux urbains temps réel"""
        flux_pietons = mtl_data.get("flux_pietons", 0)
        flux_cyclistes = mtl_data.get("flux_cyclistes", 0)
        entraves_actives = mtl_data.get("entraves_actives", 0)

        # Normalisation sur densité urbaine Montréal
        flux_score = min(40, (flux_pietons + flux_cyclistes) / 100)
        entrave_score = min(30, entraves_actives * 10)
        base = 20  # Score de base zone urbaine

        return min(100, base + flux_score + entrave_score)

    def _determine_target_profiles(
        self, severity: str, saaq_data: Optional[Dict]
    ) -> list:
        """Détermine les profils usagers à alerter selon la sévérité"""
        if severity == "red":
            return list(USER_PROFILES.keys())  # Tous les profils
        elif severity == "orange":
            profiles = ["pieton", "cycliste", "pmr", "coordonnateur_agir"]
            if saaq_data and saaq_data.get("accidents_veh_lourds", 0) > 0:
                profiles.append("automobiliste")
            return profiles
        elif severity == "yellow":
            return ["pieton", "cycliste", "coordonnateur_agir"]
        return ["coordonnateur_agir"]  # Green = monitoring seulement
