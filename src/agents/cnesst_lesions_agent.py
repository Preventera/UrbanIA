"""
=============================================================================
CNESSTLesionsRAGAgent — 8ᵉ source de données pour AX5 UrbanIA
=============================================================================
Ingère les données ouvertes CNESST (lésions professionnelles),
filtre sur SCIAN 23 (Construction), et expose des profils de risque
probabilistes au SafetyGraph pour calibrer les scores UrbanIA.

Source: donneesquebec.ca/recherche/dataset/lesions-professionnelles
Volume: 769 806 lésions totales | 54 403 Construction (2016-2022)
Schéma: 13 colonnes (NATURE_LESION, SIEGE_LESION, GENRE, AGENT_CAUSAL, etc.)

Conformité: Charte AgenticX5 | Primauté de la vie | HITL obligatoire
=============================================================================
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

from src.utils.constants import (
    SCIAN_CONSTRUCTION,
    GENRE_URBAN_RISK_SCORE,
    AGENT_CAUSAL_CHANTIER_PROFIL,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class LesionRecord:
    """Enregistrement unitaire d'une lésion CNESST"""
    id: int
    nature_lesion: str
    siege_lesion: str
    genre: str
    agent_causal: str
    sexe: str
    groupe_age: str
    secteur_scian: str
    ind_tms: bool = False
    ind_machine: bool = False
    ind_psy: bool = False
    ind_surdite: bool = False
    ind_covid: bool = False


@dataclass
class RiskProfile:
    """Profil de risque agrégé pour un type de chantier"""
    scian_code: str
    scian_label: str
    total_lesions: int
    top_genres: List[Dict[str, Any]] = field(default_factory=list)
    top_agents_causaux: List[Dict[str, Any]] = field(default_factory=list)
    top_natures: List[Dict[str, Any]] = field(default_factory=list)
    taux_tms: float = 0.0
    taux_machine: float = 0.0
    urban_risk_score: float = 0.0
    trend_yoy: float = 0.0


@dataclass
class UrbanRiskExport:
    """Données exportées vers SafetyGraph pour UrbanIA"""
    profil_risque_chantier: Dict[str, RiskProfile] = field(default_factory=dict)
    taux_frequence_scian: Dict[str, float] = field(default_factory=dict)
    score_risque_urbain: Dict[str, float] = field(default_factory=dict)
    tendance_tms: List[Dict[str, Any]] = field(default_factory=list)
    distribution_demographique: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# AGENT PRINCIPAL
# =============================================================================

class CNESSTLesionsRAGAgent:
    """
    8ᵉ source de données RAG pour AX5 UrbanIA.
    
    Pipeline:
    1. Ingestion CSV CNESST (7 fichiers, 2016-2022)
    2. Filtrage SCIAN 23 Construction (54 403 / 769 806)
    3. Calcul profils risque par type chantier
    4. Scoring risque urbain exporté
    5. Exposition via SafetyGraph
    """

    AGENT_ID = "cnesst-lesions-rag"
    AGENT_VERSION = "1.0.0"
    SOURCE_PRIORITY = 8  # 8ᵉ source dans rag-multi-sources

    # Colonnes attendues dans les CSV CNESST
    EXPECTED_COLUMNS = [
        "ID", "NATURE_LESION", "SIEGE_LESION", "GENRE",
        "AGENT_CAUSAL_LESION", "SEXE_PERS_PHYS", "GROUPE_AGE",
        "SECTEUR_SCIAN", "IND_LESION_SURDITE", "IND_LESION_MACHINE",
        "IND_LESION_TMS", "IND_LESION_PSY", "IND_LESION_COVID_19",
    ]

    def __init__(self, data_dir: str = "./data/cnesst"):
        self.data_dir = Path(data_dir)
        self.df_all: Optional[pd.DataFrame] = None
        self.df_construction: Optional[pd.DataFrame] = None
        self.risk_profiles: Dict[str, RiskProfile] = {}
        self.urban_risk_export: Optional[UrbanRiskExport] = None
        self._loaded = False
        logger.info(f"🏗️ CNESSTLesionsRAGAgent v{self.AGENT_VERSION} initialisé | data_dir={data_dir}")

    # =========================================================================
    # PHASE 1 — INGESTION
    # =========================================================================

    def load_csv_files(self, years: Optional[List[int]] = None) -> pd.DataFrame:
        """
        Charge les fichiers CSV CNESST depuis le répertoire data.
        Nommage attendu: lesions-YYYY*.csv (convention donneesquebec.ca)
        """
        if years is None:
            years = list(range(2016, 2023))

        frames = []
        for csv_file in sorted(self.data_dir.glob("lesions*.csv")):
            try:
                df = pd.read_csv(csv_file, encoding="utf-8-sig")
                # Normaliser les noms de colonnes
                df.columns = [c.strip().replace('"', '').replace('\t', '') for c in df.columns]
                
                # Extraire l'année du nom de fichier
                year_str = ''.join(filter(str.isdigit, csv_file.stem[:12]))
                if year_str:
                    df["_year"] = int(year_str[:4])
                
                frames.append(df)
                logger.info(f"  ✅ {csv_file.name}: {len(df):,} enregistrements")
            except Exception as e:
                logger.error(f"  ❌ {csv_file.name}: {e}")

        if not frames:
            logger.warning("⚠️ Aucun fichier CSV CNESST trouvé dans {self.data_dir}")
            return pd.DataFrame()

        self.df_all = pd.concat(frames, ignore_index=True)
        logger.info(f"📊 Total chargé: {len(self.df_all):,} lésions ({len(frames)} fichiers)")
        return self.df_all

    # =========================================================================
    # PHASE 2 — FILTRAGE CONSTRUCTION
    # =========================================================================

    def filter_construction(self) -> pd.DataFrame:
        """Filtre sur SECTEUR_SCIAN contenant 'CONSTRUCTION'"""
        if self.df_all is None:
            raise ValueError("Données non chargées. Appeler load_csv_files() d'abord.")

        mask = self.df_all["SECTEUR_SCIAN"].str.contains(
            "CONSTRUCTION", case=False, na=False
        )
        self.df_construction = self.df_all[mask].copy()
        
        # Normaliser les flags binaires
        for col in ["IND_LESION_TMS", "IND_LESION_MACHINE", "IND_LESION_PSY",
                     "IND_LESION_SURDITE", "IND_LESION_COVID_19"]:
            if col in self.df_construction.columns:
                self.df_construction[col] = (
                    self.df_construction[col].fillna("").str.strip().str.upper() == "OUI"
                )

        pct = len(self.df_construction) / len(self.df_all) * 100
        logger.info(
            f"🏗️ Construction filtré: {len(self.df_construction):,} / "
            f"{len(self.df_all):,} ({pct:.1f}%)"
        )
        return self.df_construction

    # =========================================================================
    # PHASE 3 — PROFILS DE RISQUE
    # =========================================================================

    def build_risk_profiles(self) -> Dict[str, RiskProfile]:
        """
        Construit les profils de risque par type de chantier.
        Chaque profil contient les distributions probabilistes des genres
        d'accident, agents causaux et natures de lésion.
        """
        if self.df_construction is None:
            self.filter_construction()

        df = self.df_construction

        # Profil global Construction
        profile = RiskProfile(
            scian_code="23",
            scian_label="Construction (tous)",
            total_lesions=len(df),
        )

        # Top genres d'accident
        genre_dist = df["GENRE"].value_counts()
        profile.top_genres = [
            {
                "genre": genre,
                "count": int(count),
                "pct": round(count / len(df) * 100, 1),
                "urban_risk_score": GENRE_URBAN_RISK_SCORE.get(genre, 3),
            }
            for genre, count in genre_dist.head(10).items()
        ]

        # Top agents causaux
        agent_dist = df["AGENT_CAUSAL_LESION"].value_counts()
        profile.top_agents_causaux = [
            {
                "agent": agent,
                "count": int(count),
                "pct": round(count / len(df) * 100, 1),
                "chantier_profil": AGENT_CAUSAL_CHANTIER_PROFIL.get(agent, "general"),
            }
            for agent, count in agent_dist.head(10).items()
        ]

        # Top natures de lésion
        nature_dist = df["NATURE_LESION"].value_counts()
        profile.top_natures = [
            {"nature": nature, "count": int(count), "pct": round(count / len(df) * 100, 1)}
            for nature, count in nature_dist.head(10).items()
        ]

        # Taux indicateurs
        profile.taux_tms = round(df["IND_LESION_TMS"].sum() / len(df) * 100, 1)
        profile.taux_machine = round(df["IND_LESION_MACHINE"].sum() / len(df) * 100, 1)

        # Score risque urbain moyen pondéré
        urban_scores = df["GENRE"].map(GENRE_URBAN_RISK_SCORE).fillna(3)
        profile.urban_risk_score = round(urban_scores.mean(), 2)

        # Tendance YoY
        if "_year" in df.columns:
            yearly = df.groupby("_year").size()
            if len(yearly) >= 2:
                first_year = yearly.iloc[0]
                last_year = yearly.iloc[-1]
                profile.trend_yoy = round((last_year - first_year) / first_year * 100, 1)

        self.risk_profiles["23"] = profile
        logger.info(
            f"📈 Profil risque Construction: {profile.total_lesions:,} lésions | "
            f"TMS={profile.taux_tms}% | Urban risk={profile.urban_risk_score}/10 | "
            f"Tendance={profile.trend_yoy:+.1f}%"
        )
        return self.risk_profiles

    # =========================================================================
    # PHASE 4 — SCORE RISQUE URBAIN EXPORTÉ
    # =========================================================================

    def compute_urban_risk_export(self) -> UrbanRiskExport:
        """
        Calcule les variables prédictives exportées vers SafetyGraph
        pour consommation par UrbanIA.
        
        51.6% des lésions Construction ont une composante de risque
        potentiellement exporté vers l'espace urbain.
        """
        if not self.risk_profiles:
            self.build_risk_profiles()

        df = self.df_construction
        export = UrbanRiskExport()

        # 1. Profils risque par type chantier
        export.profil_risque_chantier = self.risk_profiles

        # 2. Taux fréquence par année
        if "_year" in df.columns:
            yearly_counts = df.groupby("_year").size()
            export.taux_frequence_scian = {
                str(year): int(count) for year, count in yearly_counts.items()
            }

        # 3. Score risque urbain par genre × agent causal
        genres_urbains = [
            "FRAPPE PAR UN OBJET",
            "CHUTE A UN NIVEAU INFERIEUR",
            "ACCIDENT DE LA ROUTE",
            "COINCE,ECRASE PAR EQUIPEMENT,OBJET",
            "HEURTER UN OBJET",
        ]
        urban_mask = df["GENRE"].isin(genres_urbains)
        urban_count = urban_mask.sum()
        urban_pct = round(urban_count / len(df) * 100, 1)
        export.score_risque_urbain = {
            "total_lesions_urbaines": int(urban_count),
            "pct_lesions_urbaines": urban_pct,
            "par_genre": {
                genre: int(count)
                for genre, count in df[urban_mask]["GENRE"].value_counts().items()
            },
        }

        # 4. Tendance TMS (série temporelle)
        if "_year" in df.columns:
            tms_yearly = df.groupby("_year")["IND_LESION_TMS"].sum()
            export.tendance_tms = [
                {"year": int(year), "tms_count": int(count)}
                for year, count in tms_yearly.items()
            ]

        # 5. Distribution démographique
        export.distribution_demographique = {
            "sexe": df["SEXE_PERS_PHYS"].value_counts().to_dict(),
            "groupe_age": df["GROUPE_AGE"].value_counts().to_dict(),
        }

        self.urban_risk_export = export
        self._loaded = True
        logger.info(
            f"🌆 Export urbain prêt: {urban_count:,} lésions à composante urbaine "
            f"({urban_pct}% du total Construction)"
        )
        return export

    # =========================================================================
    # INTERFACE RAG
    # =========================================================================

    def query(self, question: str) -> str:
        """
        Interface RAG : répond aux questions en langage naturel
        sur les lésions CNESST Construction.
        """
        if not self._loaded:
            self.load_csv_files()
            self.compute_urban_risk_export()

        # Recherche sémantique simplifiée (à remplacer par embeddings Chroma)
        q = question.lower()
        profile = self.risk_profiles.get("23")

        if not profile:
            return "Données CNESST non disponibles."

        if "tms" in q or "musculo" in q:
            return (
                f"Les TMS représentent {profile.taux_tms}% des lésions Construction "
                f"({int(self.df_construction['IND_LESION_TMS'].sum()):,} cas sur 7 ans). "
                f"Tendance: en hausse."
            )

        if "chute" in q or "hauteur" in q:
            chutes = [g for g in profile.top_genres if "CHUTE" in g["genre"]]
            total = sum(g["count"] for g in chutes)
            return (
                f"Les chutes représentent {total:,} lésions Construction: "
                + ", ".join(f'{g["genre"]} ({g["count"]:,})' for g in chutes)
            )

        if "urbain" in q or "piéton" in q or "risque" in q:
            export = self.urban_risk_export
            return (
                f"{export.score_risque_urbain['total_lesions_urbaines']:,} lésions "
                f"({export.score_risque_urbain['pct_lesions_urbaines']}%) ont une "
                f"composante de risque exporté vers l'espace urbain."
            )

        # Réponse par défaut
        return (
            f"CNESST Construction: {profile.total_lesions:,} lésions (2016-2022). "
            f"Top genre: {profile.top_genres[0]['genre']} ({profile.top_genres[0]['pct']}%). "
            f"Score risque urbain moyen: {profile.urban_risk_score}/10."
        )

    # =========================================================================
    # EXPORT SAFETYGRAPH
    # =========================================================================

    def to_safety_graph_nodes(self) -> List[Dict[str, Any]]:
        """
        Génère les nœuds SafetyGraph à injecter dans FalkorDB.
        Types de nœuds: ProfilRisqueChantier, TauxFrequenceSCIAN,
        ScoreRisqueUrbainExporté, TendanceTMS, ProfilAgentCausal.
        """
        if not self._loaded:
            self.load_csv_files()
            self.compute_urban_risk_export()

        nodes = []
        profile = self.risk_profiles.get("23")
        export = self.urban_risk_export

        if not profile or not export:
            return nodes

        # Nœud ProfilRisqueChantier
        nodes.append({
            "type": "ProfilRisqueChantier",
            "id": "cnesst-construction-23",
            "properties": {
                "scian": "23",
                "total_lesions": profile.total_lesions,
                "urban_risk_score": profile.urban_risk_score,
                "taux_tms_pct": profile.taux_tms,
                "trend_yoy_pct": profile.trend_yoy,
                "source": "CNESST données ouvertes",
                "agent_id": self.AGENT_ID,
            },
        })

        # Nœuds par genre urbain
        for genre_data in profile.top_genres:
            if genre_data["urban_risk_score"] >= 5:
                nodes.append({
                    "type": "ScoreRisqueUrbainExporte",
                    "id": f"urban-risk-{genre_data['genre'][:20].lower().replace(' ', '-')}",
                    "properties": {
                        "genre": genre_data["genre"],
                        "count": genre_data["count"],
                        "pct": genre_data["pct"],
                        "score": genre_data["urban_risk_score"],
                    },
                })

        logger.info(f"🔗 {len(nodes)} nœuds SafetyGraph générés pour CNESST Construction")
        return nodes


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

    agent = CNESSTLesionsRAGAgent(data_dir="./data/cnesst")
    agent.load_csv_files()
    agent.compute_urban_risk_export()

    # Test query RAG
    print("\n" + "=" * 60)
    print(agent.query("Quel est le risque urbain des chantiers?"))
    print(agent.query("Parle-moi des TMS en construction"))
    print(agent.query("Les chutes de hauteur?"))
