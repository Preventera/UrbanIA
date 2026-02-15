"""
=============================================================================
SAAQWorkZoneAgent — 9ᵉ source de données pour AX5 UrbanIA
=============================================================================
Ingère les données ouvertes SAAQ (accidents routiers),
filtre sur CD_ZON_TRAVX_ROUTR = 'O' (zone de travaux),
et expose des profils de risque piéton/cycliste au SafetyGraph.

Source: SAAQ données ouvertes (via SafeFleet-Hub)
Volume: 303 972 accidents totaux | 8 173 en zone de travaux (2020-2022)
Colonnes clés: CD_ZON_TRAVX_ROUTR, IND_PIETON, IND_VELO, GRAVITE

Conformité: Charte AgenticX5 | Primauté de la vie | HITL obligatoire
=============================================================================
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

from src.utils.constants import SAAQ_GRAVITE_POIDS, SAAQ_GENRE_ACCIDENT

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class WorkZoneAccident:
    """Accident en zone de travaux routiers"""
    year: int
    region: str
    gravite: str
    genre_accident: str
    heure: str
    pieton: bool = False
    cycliste: bool = False
    veh_lourd: bool = False
    moto_cyclo: bool = False
    vitesse_autorisee: Optional[int] = None
    condition_meteo: Optional[str] = None


@dataclass
class WorkZoneRiskProfile:
    """Profil de risque pour une zone de travaux"""
    region: str
    total_accidents: int
    accidents_pietons: int
    accidents_cyclistes: int
    accidents_mortels_graves: int
    accidents_veh_lourds: int
    peak_hours: List[str] = field(default_factory=list)
    risk_score: float = 0.0


# =============================================================================
# AGENT PRINCIPAL
# =============================================================================

class SAAQWorkZoneAgent:
    """
    9ᵉ source de données RAG pour AX5 UrbanIA.
    
    Pipeline:
    1. Ingestion CSV SAAQ (3 fichiers, 2020-2022)
    2. Filtrage CD_ZON_TRAVX_ROUTR = 'O' (8 173 / 303 972)
    3. Calcul profils risque piéton/cycliste par zone
    4. Scoring risque par profil usager vulnérable
    5. Exposition via SafetyGraph
    
    Insight clé: 36.6% des accidents zone travaux sont à Montréal
    """

    AGENT_ID = "saaq-workzone-rag"
    AGENT_VERSION = "1.0.0"
    SOURCE_PRIORITY = 9  # 9ᵉ source dans rag-multi-sources

    EXPECTED_COLUMNS = [
        "AN", "NO_SEQ_COLL", "MS_ACCDN", "HR_ACCDN", "JR_SEMN_ACCDN",
        "GRAVITE", "NB_VICTIMES_TOTAL", "NB_VEH_IMPLIQUES_ACCDN",
        "REG_ADM", "VITESSE_AUTOR", "CD_GENRE_ACCDN", "CD_ETAT_SURFC",
        "CD_ECLRM", "CD_ENVRN_ACCDN", "CD_CATEG_ROUTE", "CD_ASPCT_ROUTE",
        "CD_LOCLN_ACCDN", "CD_CONFG_ROUTE", "CD_ZON_TRAVX_ROUTR",
        "CD_COND_METEO", "IND_AUTO_CAMION_LEGER", "IND_VEH_LOURD",
        "IND_MOTO_CYCLO", "IND_VELO", "IND_PIETON",
    ]

    def __init__(self, data_dir: str = "./data/saaq"):
        self.data_dir = Path(data_dir)
        self.df_all: Optional[pd.DataFrame] = None
        self.df_workzone: Optional[pd.DataFrame] = None
        self.risk_profiles: Dict[str, WorkZoneRiskProfile] = {}
        self._loaded = False
        logger.info(f"🚛 SAAQWorkZoneAgent v{self.AGENT_VERSION} initialisé | data_dir={data_dir}")

    # =========================================================================
    # PHASE 1 — INGESTION
    # =========================================================================

    def load_csv_files(self) -> pd.DataFrame:
        """Charge les CSV SAAQ depuis le répertoire data."""
        frames = []
        for csv_file in sorted(self.data_dir.glob("rapports-accident*.csv")):
            try:
                df = pd.read_csv(csv_file, encoding="utf-8-sig")
                df.columns = [c.strip().replace('"', '').replace('\t', '') for c in df.columns]
                frames.append(df)
                logger.info(f"  ✅ {csv_file.name}: {len(df):,} enregistrements")
            except Exception as e:
                logger.error(f"  ❌ {csv_file.name}: {e}")

        if not frames:
            logger.warning(f"⚠️ Aucun fichier CSV SAAQ trouvé dans {self.data_dir}")
            return pd.DataFrame()

        self.df_all = pd.concat(frames, ignore_index=True)
        logger.info(f"📊 Total SAAQ chargé: {len(self.df_all):,} accidents")
        return self.df_all

    # =========================================================================
    # PHASE 2 — FILTRAGE ZONE TRAVAUX
    # =========================================================================

    def filter_work_zones(self) -> pd.DataFrame:
        """
        Filtre sur CD_ZON_TRAVX_ROUTR = 'O'
        Résultat: 8 173 accidents en zone de travaux routiers
        """
        if self.df_all is None:
            raise ValueError("Données non chargées. Appeler load_csv_files() d'abord.")

        self.df_workzone = self.df_all[
            self.df_all["CD_ZON_TRAVX_ROUTR"] == "O"
        ].copy()

        pct = len(self.df_workzone) / len(self.df_all) * 100
        logger.info(
            f"🚧 Zone travaux filtré: {len(self.df_workzone):,} / "
            f"{len(self.df_all):,} ({pct:.1f}%)"
        )

        # Stats rapides
        pietons = (self.df_workzone["IND_PIETON"] == "O").sum()
        cyclistes = (self.df_workzone.get("IND_VELO", pd.Series()) == "O").sum()
        mortels = self.df_workzone["GRAVITE"].str.contains("Mortel", na=False).sum()
        logger.info(
            f"  👤 Piétons: {pietons} | 🚲 Cyclistes: {cyclistes} | "
            f"💀 Mortels/graves: {mortels}"
        )

        return self.df_workzone

    # =========================================================================
    # PHASE 3 — PROFILS DE RISQUE PAR RÉGION
    # =========================================================================

    def build_risk_profiles(self) -> Dict[str, WorkZoneRiskProfile]:
        """
        Construit les profils de risque zone travaux par région.
        Focus: Montréal (36.6% des accidents zone travaux).
        """
        if self.df_workzone is None:
            self.filter_work_zones()

        df = self.df_workzone

        # Profil global
        global_profile = WorkZoneRiskProfile(
            region="Québec (tous)",
            total_accidents=len(df),
            accidents_pietons=int((df["IND_PIETON"] == "O").sum()),
            accidents_cyclistes=int((df.get("IND_VELO", pd.Series()) == "O").sum()),
            accidents_mortels_graves=int(
                df["GRAVITE"].str.contains("Mortel", na=False).sum()
            ),
            accidents_veh_lourds=int((df["IND_VEH_LOURD"] == "O").sum()),
        )

        # Heures de pointe
        hr_counts = df["HR_ACCDN"].value_counts()
        global_profile.peak_hours = list(hr_counts.head(3).index)

        # Score de risque pondéré
        gravite_scores = df["GRAVITE"].map(SAAQ_GRAVITE_POIDS).fillna(1.0)
        global_profile.risk_score = round(gravite_scores.mean(), 2)

        self.risk_profiles["global"] = global_profile

        # Profils par région
        for region, group in df.groupby("REG_ADM"):
            if pd.isna(region):
                continue
            profile = WorkZoneRiskProfile(
                region=str(region),
                total_accidents=len(group),
                accidents_pietons=int((group["IND_PIETON"] == "O").sum()),
                accidents_cyclistes=int((group.get("IND_VELO", pd.Series()) == "O").sum()),
                accidents_mortels_graves=int(
                    group["GRAVITE"].str.contains("Mortel", na=False).sum()
                ),
                accidents_veh_lourds=int((group["IND_VEH_LOURD"] == "O").sum()),
            )

            hr_counts = group["HR_ACCDN"].value_counts()
            profile.peak_hours = list(hr_counts.head(3).index)
            gravite_scores = group["GRAVITE"].map(SAAQ_GRAVITE_POIDS).fillna(1.0)
            profile.risk_score = round(gravite_scores.mean(), 2)

            region_key = str(region).split("(")[0].strip().lower().replace(" ", "_")
            self.risk_profiles[region_key] = profile

        logger.info(f"📍 {len(self.risk_profiles)} profils régionaux générés")

        # Log Montréal spécifiquement
        mtl = self.risk_profiles.get("montréal")
        if mtl:
            logger.info(
                f"🏙️ Montréal: {mtl.total_accidents} accidents zone travaux | "
                f"Piétons: {mtl.accidents_pietons} | Cyclistes: {mtl.accidents_cyclistes} | "
                f"Mortels: {mtl.accidents_mortels_graves}"
            )

        self._loaded = True
        return self.risk_profiles

    # =========================================================================
    # PHASE 4 — CROISEMENT AVEC CNESST
    # =========================================================================

    def cross_reference_cnesst(
        self, cnesst_urban_risk: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Croise les données SAAQ zone travaux avec les lésions CNESST
        pour produire un score de risque urbain composite.
        
        SAAQ dit: combien d'accidents piétons/cyclistes EN zone travaux
        CNESST dit: quels types de lésions SUR le chantier exportent du risque
        
        Résultat: score composite calibré sur les deux registres.
        """
        if not self._loaded:
            self.build_risk_profiles()

        global_profile = self.risk_profiles.get("global")
        if not global_profile:
            return {}

        # Score composite
        saaq_score = global_profile.risk_score
        cnesst_score = cnesst_urban_risk.get("urban_risk_score", 5.0)
        pct_urban = cnesst_urban_risk.get("pct_lesions_urbaines", 51.6)

        composite = {
            "saaq_workzone_score": saaq_score,
            "cnesst_urban_score": cnesst_score,
            "composite_score": round((saaq_score * 0.4 + cnesst_score * 0.6), 2),
            "total_events_croises": (
                global_profile.total_accidents
                + cnesst_urban_risk.get("total_lesions_urbaines", 0)
            ),
            "pietons_saaq": global_profile.accidents_pietons,
            "cyclistes_saaq": global_profile.accidents_cyclistes,
            "mortels_saaq": global_profile.accidents_mortels_graves,
            "pct_cnesst_urbain": pct_urban,
            "confidence": "high",
            "sources": ["CNESST données ouvertes", "SAAQ données ouvertes"],
        }

        logger.info(
            f"🔗 Score composite CNESST×SAAQ: {composite['composite_score']}/10 | "
            f"{composite['total_events_croises']:,} événements croisés"
        )
        return composite

    # =========================================================================
    # INTERFACE RAG
    # =========================================================================

    def query(self, question: str) -> str:
        """Interface RAG pour questions en langage naturel."""
        if not self._loaded:
            self.load_csv_files()
            self.build_risk_profiles()

        q = question.lower()
        global_p = self.risk_profiles.get("global")
        mtl_p = self.risk_profiles.get("montréal")

        if not global_p:
            return "Données SAAQ zone travaux non disponibles."

        if "montréal" in q or "mtl" in q:
            if mtl_p:
                return (
                    f"Montréal: {mtl_p.total_accidents} accidents en zone de travaux "
                    f"(36.6% du Québec). {mtl_p.accidents_pietons} piétons, "
                    f"{mtl_p.accidents_cyclistes} cyclistes, "
                    f"{mtl_p.accidents_mortels_graves} mortels/graves."
                )

        if "piéton" in q:
            return (
                f"{global_p.accidents_pietons} accidents impliquant des piétons "
                f"en zone de travaux routiers au Québec (2020-2022)."
            )

        if "cycliste" in q or "vélo" in q:
            return (
                f"{global_p.accidents_cyclistes} accidents impliquant des cyclistes "
                f"en zone de travaux routiers au Québec (2020-2022)."
            )

        return (
            f"SAAQ zone travaux: {global_p.total_accidents:,} accidents (2020-2022). "
            f"Piétons: {global_p.accidents_pietons}, Cyclistes: {global_p.accidents_cyclistes}, "
            f"Mortels/graves: {global_p.accidents_mortels_graves}."
        )

    # =========================================================================
    # EXPORT SAFETYGRAPH
    # =========================================================================

    def to_safety_graph_nodes(self) -> List[Dict[str, Any]]:
        """Génère les nœuds SafetyGraph pour FalkorDB."""
        if not self._loaded:
            self.load_csv_files()
            self.build_risk_profiles()

        nodes = []

        for key, profile in self.risk_profiles.items():
            nodes.append({
                "type": "WorkZoneRiskProfile",
                "id": f"saaq-workzone-{key}",
                "properties": {
                    "region": profile.region,
                    "total_accidents": profile.total_accidents,
                    "accidents_pietons": profile.accidents_pietons,
                    "accidents_cyclistes": profile.accidents_cyclistes,
                    "accidents_mortels_graves": profile.accidents_mortels_graves,
                    "accidents_veh_lourds": profile.accidents_veh_lourds,
                    "risk_score": profile.risk_score,
                    "peak_hours": profile.peak_hours,
                    "source": "SAAQ données ouvertes",
                    "agent_id": self.AGENT_ID,
                },
            })

        logger.info(f"🔗 {len(nodes)} nœuds SafetyGraph générés pour SAAQ zone travaux")
        return nodes


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

    agent = SAAQWorkZoneAgent(data_dir="./data/saaq")
    agent.load_csv_files()
    agent.build_risk_profiles()

    print("\n" + "=" * 60)
    print(agent.query("Accidents piétons à Montréal?"))
    print(agent.query("Combien de cyclistes blessés en zone travaux?"))
