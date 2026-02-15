"""
=============================================================================
Connecteur Entraves CIFS — Source #1, Couche 3
=============================================================================
Récupère les entraves de chantiers actives à Montréal depuis
donnees.montreal.ca. C'est la source primaire pour localiser les
chantiers en temps réel et calculer les zones de risque UrbanIA.

Dataset: Entraves routières - Info-travaux
Refresh: Temps réel
URL: donnees.montreal.ca/dataset/entraves
=============================================================================
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from src.connectors.mtl_opendata import MTLOpenDataClient

logger = logging.getLogger(__name__)

# Resource ID pour les entraves (à vérifier sur donnees.montreal.ca)
CIFS_RESOURCE_ID = "a2bc8014-488c-495d-941b-e7ae1999d1bd"


@dataclass
class Entrave:
    """Entrave de chantier active"""
    id: str
    rue: str
    de_rue: str = ""
    a_rue: str = ""
    type_entrave: str = ""           # occupation_chaussee, fermeture, etc.
    date_debut: Optional[str] = None
    date_fin: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    arrondissement: Optional[str] = None
    description: Optional[str] = None
    impact_score: float = 5.0        # Score d'impact calculé (0-10)


@dataclass
class CIFSSummary:
    """Résumé des entraves actives"""
    total_entraves: int = 0
    entraves_actives: List[Entrave] = field(default_factory=list)
    par_arrondissement: Dict[str, int] = field(default_factory=dict)
    par_type: Dict[str, int] = field(default_factory=dict)
    zones_coactivite: List[Dict] = field(default_factory=list)
    timestamp: str = ""


class CIFSConnector:
    """
    Connecteur pour les entraves CIFS (Info-travaux Montréal).
    
    Source #1 de la Couche 3 UrbanIA.
    Identifie les chantiers actifs et calcule les zones de risque
    basées sur la densité d'entraves et la coactivité.
    """

    SOURCE_ID = "cifs"
    SOURCE_NAME = "Entraves CIFS"
    COUCHE = 3
    REFRESH = "temps_reel"

    def __init__(self, client: Optional[MTLOpenDataClient] = None):
        self.client = client or MTLOpenDataClient()
        self._last_summary: Optional[CIFSSummary] = None
        logger.info("🚧 CIFSConnector initialisé")

    async def fetch_entraves_actives(self) -> List[Entrave]:
        """
        Récupère toutes les entraves actives en ce moment.
        Filtre sur les entraves dont la date_fin est dans le futur.
        """
        # Essayer le cache (5 min pour données temps réel)
        cached = self.client.load_cache("cifs_entraves", max_age_minutes=5)
        if cached:
            return [Entrave(**e) for e in cached]

        logger.info("🚧 Récupération entraves CIFS temps réel...")

        records = await self.client.fetch_all_records(
            CIFS_RESOURCE_ID, batch_size=500, max_records=10000
        )

        entraves = []
        now = datetime.now().isoformat()

        for r in records:
            # Filtrer entraves actives
            date_fin = r.get("DATE_FIN_PLANIFIEE") or r.get("date_fin") or ""
            if date_fin and date_fin < now:
                continue

            entrave = Entrave(
                id=str(r.get("ID_ENTRAVE") or r.get("_id", "")),
                rue=r.get("NOM_VOIE") or r.get("rue") or "",
                de_rue=r.get("DE_RUE") or "",
                a_rue=r.get("A_RUE") or "",
                type_entrave=r.get("TYPE_ENTRAVE") or r.get("type") or "",
                date_debut=r.get("DATE_DEBUT_PLANIFIEE") or r.get("date_debut"),
                date_fin=date_fin,
                latitude=self._parse_float(r.get("LATITUDE") or r.get("latitude")),
                longitude=self._parse_float(r.get("LONGITUDE") or r.get("longitude")),
                arrondissement=r.get("ARRONDISSEMENT") or r.get("arrondissement"),
                description=r.get("DESCRIPTION") or "",
            )
            entrave.impact_score = self._compute_impact_score(entrave)
            entraves.append(entrave)

        logger.info(f"  🚧 {len(entraves)} entraves actives trouvées")

        # Sauvegarder en cache
        self.client.save_cache("cifs_entraves", [e.__dict__ for e in entraves])

        return entraves

    async def get_summary(self) -> CIFSSummary:
        """Produit un résumé des entraves actives pour le scoring UrbanIA."""
        entraves = await self.fetch_entraves_actives()

        summary = CIFSSummary(
            total_entraves=len(entraves),
            entraves_actives=entraves,
            timestamp=datetime.now().isoformat(),
        )

        # Par arrondissement
        for e in entraves:
            arr = e.arrondissement or "Inconnu"
            summary.par_arrondissement[arr] = summary.par_arrondissement.get(arr, 0) + 1

        # Par type
        for e in entraves:
            t = e.type_entrave or "Inconnu"
            summary.par_type[t] = summary.par_type.get(t, 0) + 1

        # Détection zones de coactivité (clusters de chantiers)
        summary.zones_coactivite = self._detect_coactivity(entraves)

        self._last_summary = summary
        return summary

    def get_zone_data(self, arrondissement: str) -> Dict[str, Any]:
        """Données de zone pour le scoring UrbanIA."""
        if not self._last_summary:
            return {"entraves_actives": 0, "coactivity_factor": 1.0}

        count = self._last_summary.par_arrondissement.get(arrondissement, 0)

        # Facteur coactivité: >5 entraves dans même arrondissement = risque accru
        coactivity = 1.0
        if count >= 10:
            coactivity = 1.5
        elif count >= 5:
            coactivity = 1.3
        elif count >= 3:
            coactivity = 1.1

        return {
            "entraves_actives": count,
            "coactivity_factor": coactivity,
            "source": self.SOURCE_ID,
        }

    def _detect_coactivity(self, entraves: List[Entrave], radius_km: float = 0.3) -> List[Dict]:
        """Détecte les clusters d'entraves proches (coactivité)."""
        clusters = []
        used = set()

        for i, e1 in enumerate(entraves):
            if i in used or not e1.latitude or not e1.longitude:
                continue

            cluster = [e1]
            for j, e2 in enumerate(entraves):
                if j <= i or j in used or not e2.latitude or not e2.longitude:
                    continue

                dist = self._haversine(e1.latitude, e1.longitude, e2.latitude, e2.longitude)
                if dist <= radius_km:
                    cluster.append(e2)
                    used.add(j)

            if len(cluster) >= 3:
                clusters.append({
                    "center_lat": sum(e.latitude for e in cluster) / len(cluster),
                    "center_lon": sum(e.longitude for e in cluster) / len(cluster),
                    "count": len(cluster),
                    "rues": list(set(e.rue for e in cluster)),
                    "risk_multiplier": min(2.0, 1.0 + len(cluster) * 0.15),
                })
                used.add(i)

        if clusters:
            logger.info(f"  ⚠️ {len(clusters)} zones de coactivité détectées")

        return clusters

    @staticmethod
    def _compute_impact_score(entrave: Entrave) -> float:
        """Score d'impact d'une entrave (0-10)."""
        score = 5.0

        # Type d'entrave
        type_scores = {
            "fermeture": 9.0,
            "occupation_chaussee": 6.0,
            "restriction": 5.0,
            "detour": 7.0,
        }
        t = (entrave.type_entrave or "").lower()
        for key, val in type_scores.items():
            if key in t:
                score = val
                break

        return score

    @staticmethod
    def _parse_float(val) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2) -> float:
        """Distance en km entre deux points GPS."""
        import math
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
